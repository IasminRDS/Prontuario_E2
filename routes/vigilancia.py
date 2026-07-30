# -*- coding: utf-8 -*-
"""Vigilância epidemiológica (SINAN).

Porte de `modules/vigilancia` do backend NestJS. Notificações compulsórias são
DETECTADAS a partir do CID registrado no prontuário — o profissional não precisa
lembrar quais agravos são de notificação obrigatória; o sistema varre os CIDs e
monta a fila.
"""
from datetime import datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from models.notificacao import AGRAVOS_POR_CID, NotificacaoCompulsoria, agravo_para_cid
from models.paciente import Paciente
from models.prontuario import Prontuario
from utils.audit import registrar
from utils.rbac import requer_permissao

vigilancia_bp = Blueprint("vigilancia", __name__, url_prefix="/vigilancia")


def _detectar_pendentes(dias=180):
    """Varre prontuários recentes e cria notificação para CID notificável.

    Idempotente: não duplica notificação para o mesmo prontuário.
    """
    corte = datetime.utcnow() - timedelta(days=dias)
    criadas = 0

    prontuarios = (
        Prontuario.query
        .filter(Prontuario.criado_em >= corte)
        .filter(
            db.or_(
                Prontuario.cid_principal.isnot(None),
                Prontuario.cid_secundario.isnot(None),
            )
        )
        .all()
    )

    ja_notificados = {
        n.prontuario_id
        for n in NotificacaoCompulsoria.query
        .with_entities(NotificacaoCompulsoria.prontuario_id)
        .filter(NotificacaoCompulsoria.prontuario_id.isnot(None))
        .all()
    }

    for p in prontuarios:
        if p.id in ja_notificados:
            continue
        for cid in (p.cid_principal, p.cid_secundario):
            agravo = agravo_para_cid(cid)
            if not agravo:
                continue
            db.session.add(NotificacaoCompulsoria(
                paciente_id=p.paciente_id,
                prontuario_id=p.id,
                unidade_id=p.unidade_id,
                cid=cid.strip().upper(),
                agravo=agravo,
                status="pendente",
                detectado_em=p.criado_em or datetime.utcnow(),
            ))
            criadas += 1
            break  # uma notificação por prontuário

    if criadas:
        db.session.commit()
    return criadas


@vigilancia_bp.get("/")
@login_required
@requer_permissao("surveillance:read")
def index():
    novas = _detectar_pendentes()
    if novas:
        flash(f"{novas} nova(s) notificação(ões) compulsória(s) detectada(s) por CID.", "info")

    status = (request.args.get("status") or "pendente").strip()
    agravo = (request.args.get("agravo") or "").strip()

    query = NotificacaoCompulsoria.query
    if status in ("pendente", "enviada", "descartada"):
        query = query.filter(NotificacaoCompulsoria.status == status)
    if agravo:
        query = query.filter(NotificacaoCompulsoria.agravo == agravo)

    fila = query.order_by(NotificacaoCompulsoria.detectado_em.desc()).limit(200).all()

    # Resolve pacientes num SELECT só.
    ids = {n.paciente_id for n in fila}
    pacientes = (
        {p.id: p for p in Paciente.query.filter(Paciente.id.in_(ids)).all()} if ids else {}
    )

    contagens = dict(
        db.session.query(NotificacaoCompulsoria.status, func.count(NotificacaoCompulsoria.id))
        .group_by(NotificacaoCompulsoria.status)
        .all()
    )

    return render_template(
        "vigilancia/index.html",
        fila=fila,
        pacientes=pacientes,
        contagens=contagens,
        status=status,
        agravo=agravo,
        agravos=sorted(set(AGRAVOS_POR_CID.values())),
    )


@vigilancia_bp.post("/<int:id>/enviar")
@login_required
@requer_permissao("surveillance:write")
def enviar(id):
    n = NotificacaoCompulsoria.query.get_or_404(id)
    if n.status != "pendente":
        flash("Esta notificação já foi resolvida.", "warning")
        return redirect(url_for("vigilancia.index"))

    n.status = "enviada"
    n.numero_sinan = (request.form.get("numero_sinan") or "").strip() or None
    n.observacoes = (request.form.get("observacoes") or "").strip() or None
    n.resolvido_em = datetime.utcnow()
    n.resolvido_por = current_user.id

    registrar("notificacoes_compulsorias", n.id, "update",
              f"Notificação de {n.agravo} (CID {n.cid}) enviada ao SINAN")
    db.session.commit()

    flash(f"Notificação de {n.agravo} registrada como enviada ao SINAN.", "success")
    return redirect(url_for("vigilancia.index"))


@vigilancia_bp.post("/<int:id>/descartar")
@login_required
@requer_permissao("surveillance:write")
def descartar(id):
    n = NotificacaoCompulsoria.query.get_or_404(id)
    motivo = (request.form.get("motivo") or "").strip()
    if not motivo:
        flash("Informe o motivo do descarte — ele fica registrado na auditoria.", "warning")
        return redirect(url_for("vigilancia.index"))

    n.status = "descartada"
    n.motivo_descarte = motivo
    n.resolvido_em = datetime.utcnow()
    n.resolvido_por = current_user.id

    registrar("notificacoes_compulsorias", n.id, "update",
              f"Notificação de {n.agravo} descartada: {motivo}")
    db.session.commit()

    flash("Notificação descartada.", "info")
    return redirect(url_for("vigilancia.index"))
