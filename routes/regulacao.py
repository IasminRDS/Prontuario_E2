# -*- coding: utf-8 -*-
"""Regulação de vagas — fila de encaminhamentos com parecer do regulador.

Porte de `modules/regulacao` do backend NestJS. Quem solicita (médico) e quem
decide (regulador/gestor) são papéis distintos: `regulation:write` solicita,
`regulation:decide` autoriza, nega ou agenda.
"""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import func

from extensions import db
from models.encaminhamento import Encaminhamento
from models.paciente import Paciente
from utils.audit import registrar
from utils.rbac import requer_permissao

regulacao_bp = Blueprint("regulacao", __name__, url_prefix="/regulacao")

# Estados possíveis de um encaminhamento na regulação.
SITUACOES = ("solicitado", "autorizado", "negado", "agendado", "realizado")

# Esta tela usa os tons do DSGov (`badge--red`), e o painel de encaminhamentos
# usa os tons legados em português (`badge-vermelho`). São duas folhas de estilo,
# não um descuido — por isso aqui se traduz o tom, mas NÃO o vocabulário: as
# chaves e os rótulos continuam vindo do model, que é a autoridade sobre eles.
_TOM_DSGOV = {"vermelho": "red", "amarelo": "amber", "azul": "blue",
              "verde": "slate"}

PRIORIDADES = {
    chave: (rotulo, _TOM_DSGOV[tom])
    for chave, (rotulo, tom) in Encaminhamento.PRIORIDADE_LABELS.items()
}
ORDEM_DE_GRAVIDADE = {p: i for i, p in enumerate(Encaminhamento.PRIORIDADES)}


@regulacao_bp.get("/")
@login_required
@requer_permissao("regulation:read")
def index():
    situacao = (request.args.get("situacao") or "solicitado").strip()
    prioridade = (request.args.get("prioridade") or "").strip()
    especialidade = (request.args.get("especialidade") or "").strip()

    query = Encaminhamento.query
    if situacao in SITUACOES:
        query = query.filter(Encaminhamento.status == situacao)
    if prioridade:
        query = query.filter(Encaminhamento.prioridade == prioridade)
    if especialidade:
        query = query.filter(Encaminhamento.especialidade == especialidade)

    # Ordena por gravidade e depois por antiguidade: quem espera mais, primeiro.
    ordem_prioridade = db.case(
        ORDEM_DE_GRAVIDADE, value=Encaminhamento.prioridade, else_=9,
    )
    fila = (
        query.order_by(ordem_prioridade, Encaminhamento.data_solicitacao.asc())
        .limit(200)
        .all()
    )

    ids = {e.paciente_id for e in fila}
    pacientes = (
        {p.id: p for p in Paciente.query.filter(Paciente.id.in_(ids)).all()} if ids else {}
    )

    contagens = dict(
        db.session.query(Encaminhamento.status, func.count(Encaminhamento.id))
        .group_by(Encaminhamento.status)
        .all()
    )

    especialidades = sorted(
        v[0]
        for v in db.session.query(Encaminhamento.especialidade).distinct().all()
        if v[0]
    )

    return render_template(
        "regulacao/index.html",
        fila=fila,
        pacientes=pacientes,
        contagens=contagens,
        situacao=situacao,
        prioridade=prioridade,
        especialidade=especialidade,
        especialidades=especialidades,
        prioridades=PRIORIDADES,
        agora=datetime.utcnow(),
    )


@regulacao_bp.post("/<int:id>/parecer")
@login_required
@requer_permissao("regulation:decide")
def parecer(id):
    """Parecer do regulador: autorizar, negar ou agendar."""
    enc = Encaminhamento.query.get_or_404(id)
    decisao = (request.form.get("decisao") or "").strip()
    observacao = (request.form.get("observacao") or "").strip()

    if decisao not in ("autorizado", "negado", "agendado", "realizado"):
        flash("Decisão inválida.", "danger")
        return redirect(url_for("regulacao.index"))

    if decisao == "negado" and not observacao:
        flash("Negar exige justificativa — ela fica registrada na auditoria.", "warning")
        return redirect(url_for("regulacao.index"))

    anterior = enc.status
    enc.status = decisao

    if decisao == "agendado":
        quando = (request.form.get("data_agendada") or "").strip()
        if quando:
            try:
                enc.data_agendada = datetime.fromisoformat(quando)
            except ValueError:
                flash("Data de agendamento inválida.", "warning")
                return redirect(url_for("regulacao.index"))
    elif decisao == "realizado":
        enc.data_realizacao = datetime.utcnow()

    if observacao:
        enc.retorno_info = observacao

    registrar(
        "encaminhamentos",
        enc.id,
        "update",
        f"Regulação: {anterior} → {decisao}"
        + (f" — {observacao}" if observacao else ""),
    )
    db.session.commit()

    flash(f"Encaminhamento marcado como {decisao}.", "success")
    return redirect(url_for("regulacao.index", situacao=request.args.get("situacao", "solicitado")))
