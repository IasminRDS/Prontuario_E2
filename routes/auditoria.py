# -*- coding: utf-8 -*-
"""Trilha de auditoria (LGPD) — lê a tabela `audit_logs` de verdade.

Antes esta tela devolvia uma lista `LOGS` fixa criada no import do módulo, sem
nunca tocar o banco — e o model `AuditLog` existia sem ninguém o consultar.
"""
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import or_

from extensions import db
from models.audit_log import AuditLog
from models.user import User
from utils.rbac import requer_permissao

auditoria_bp = Blueprint("auditoria", __name__, url_prefix="/auditoria")

POR_PAGINA = 50


@auditoria_bp.get("/")
@login_required
@requer_permissao("audit:read")
def index():
    q = (request.args.get("q") or "").strip()
    acao = (request.args.get("acao") or "").strip()
    tabela = (request.args.get("tabela") or "").strip()
    dias = request.args.get("dias", type=int) or 30
    pagina = request.args.get("pagina", type=int) or 1

    query = AuditLog.query

    if dias > 0:
        query = query.filter(AuditLog.criado_em >= datetime.utcnow() - timedelta(days=dias))
    if acao:
        query = query.filter(AuditLog.acao == acao)
    if tabela:
        query = query.filter(AuditLog.tabela == tabela)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            AuditLog.descricao.ilike(like),
            AuditLog.tabela.ilike(like),
            AuditLog.ip.ilike(like),
        ))

    paginacao = (
        query.order_by(AuditLog.criado_em.desc(), AuditLog.id.desc())
        .paginate(page=pagina, per_page=POR_PAGINA, error_out=False)
    )

    # Resolve os nomes de usuário num único SELECT, em vez de N+1 pelo relationship.
    ids = {l.usuario_id for l in paginacao.items if l.usuario_id}
    nomes = {}
    if ids:
        nomes = {
            u.id: u.nome
            for u in User.query.filter(User.id.in_(ids)).all()
        }

    logs = [
        {
            "quando": l.criado_em,
            "usuario": nomes.get(l.usuario_id, "—" if not l.usuario_id else f"#{l.usuario_id}"),
            "acao": l.acao,
            "tabela": l.tabela,
            "registro_id": l.registro_id,
            "descricao": l.descricao,
            "ip": l.ip,
        }
        for l in paginacao.items
    ]

    return render_template(
        "auditoria/index.html",
        logs=logs,
        paginacao=paginacao,
        filtros={"q": q, "acao": acao, "tabela": tabela, "dias": dias},
        acoes=_distintos(AuditLog.acao),
        tabelas=_distintos(AuditLog.tabela),
    )


@auditoria_bp.get("/verificar")
@login_required
@requer_permissao("audit:read")
def verificar():
    """Recalcula a cadeia de hashes e reporta rupturas."""
    from utils.audit import verificar_integridade

    total, problemas = verificar_integridade()
    return render_template(
        "auditoria/verificar.html",
        total=total,
        problemas=problemas,
        integra=not problemas,
    )


def _distintos(coluna):
    """Valores distintos de uma coluna, para popular os filtros."""
    try:
        return sorted(
            v[0] for v in AuditLog.query.with_entities(coluna).distinct().all() if v[0]
        )
    except Exception:
        # Sem o rollback, esta falha aborta a transação em PostgreSQL e derruba
        # também a listagem de logs que vem logo depois.
        db.session.rollback()
        return []
