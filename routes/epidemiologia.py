# -*- coding: utf-8 -*-
"""Painel epidemiológico regional.

Porte de `modules/epidemiologia` do backend NestJS: resumo, agravos, notificações
por município, ocupação de leitos, fila de regulação e distribuição Manchester.

Os gráficos são barras em CSS puro — sem biblioteca externa, porque a página
precisa funcionar em rede restrita de unidade de saúde.
"""
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import func

from extensions import db
from models.encaminhamento import Encaminhamento
from models.internacao import Internacao, Leito, Setor
from models.notificacao import NotificacaoCompulsoria
from models.paciente import Paciente
from models.triagem import Triagem
from utils.rbac import requer_permissao

epidemiologia_bp = Blueprint("epidemiologia", __name__, url_prefix="/epidemiologia")

# Cores Manchester, na ordem de gravidade decrescente.
MANCHESTER = (
    ("vermelho", "Emergência", "Atendimento imediato"),
    ("laranja", "Muito urgente", "até 10 min"),
    ("amarelo", "Urgente", "até 60 min"),
    ("verde", "Pouco urgente", "até 120 min"),
    ("azul", "Não urgente", "até 240 min"),
)


def _por_agravo(desde):
    linhas = (
        db.session.query(
            NotificacaoCompulsoria.agravo, func.count(NotificacaoCompulsoria.id)
        )
        .filter(NotificacaoCompulsoria.detectado_em >= desde)
        .group_by(NotificacaoCompulsoria.agravo)
        .order_by(func.count(NotificacaoCompulsoria.id).desc())
        .limit(12)
        .all()
    )
    return [{"rotulo": a, "valor": n} for a, n in linhas]


def _por_municipio(desde):
    linhas = (
        db.session.query(Paciente.municipio, func.count(NotificacaoCompulsoria.id))
        .join(NotificacaoCompulsoria, NotificacaoCompulsoria.paciente_id == Paciente.id)
        .filter(NotificacaoCompulsoria.detectado_em >= desde)
        .group_by(Paciente.municipio)
        .order_by(func.count(NotificacaoCompulsoria.id).desc())
        .limit(10)
        .all()
    )
    return [{"rotulo": m or "Não informado", "valor": n} for m, n in linhas]


def _ocupacao_por_setor():
    saida = []
    for setor in Setor.query.filter_by(ativo=True).order_by(Setor.nome).all():
        total = Leito.query.filter_by(setor_id=setor.id, ativo=True).count()
        if not total:
            continue
        ocupados = Leito.query.filter_by(setor_id=setor.id, ativo=True, status="ocupado").count()
        saida.append({
            "rotulo": setor.nome,
            "sigla": setor.sigla,
            "total": total,
            "ocupados": ocupados,
            "pct": round(ocupados / total * 100),
        })
    return saida


def _manchester(desde):
    contagens = dict(
        db.session.query(Triagem.classificacao, func.count(Triagem.id))
        .filter(Triagem.criado_em >= desde)
        .group_by(Triagem.classificacao)
        .all()
    )
    total = sum(contagens.values()) or 1
    return [
        {
            "cor": cor,
            "rotulo": rotulo,
            "meta": meta,
            "valor": contagens.get(cor, 0),
            "pct": round(contagens.get(cor, 0) / total * 100),
        }
        for cor, rotulo, meta in MANCHESTER
    ]


@epidemiologia_bp.get("/")
@login_required
@requer_permissao("reports:read")
def index():
    dias = request.args.get("dias", type=int) or 30
    dias = min(max(dias, 7), 365)
    desde = datetime.utcnow() - timedelta(days=dias)

    leitos_total = Leito.query.filter_by(ativo=True).count()
    leitos_ocupados = Leito.query.filter_by(ativo=True, status="ocupado").count()

    resumo = {
        "notificacoes": NotificacaoCompulsoria.query.filter(
            NotificacaoCompulsoria.detectado_em >= desde
        ).count(),
        "notificacoes_pendentes": NotificacaoCompulsoria.query.filter_by(status="pendente").count(),
        "internacoes_ativas": Internacao.query.filter_by(status="ativa").count(),
        "leitos_total": leitos_total,
        "leitos_ocupados": leitos_ocupados,
        "ocupacao_pct": round(leitos_ocupados / leitos_total * 100) if leitos_total else 0,
        "regulacao_fila": Encaminhamento.query.filter_by(status="solicitado").count(),
        "triagens": Triagem.query.filter(Triagem.criado_em >= desde).count(),
    }

    return render_template(
        "epidemiologia/index.html",
        dias=dias,
        resumo=resumo,
        agravos=_por_agravo(desde),
        municipios=_por_municipio(desde),
        setores=_ocupacao_por_setor(),
        manchester=_manchester(desde),
    )
