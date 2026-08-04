# -*- coding: utf-8 -*-
"""Central de alertas operacionais — calculada a partir do banco.

Antes esta tela devolvia uma lista fixa com um item ("Sistema ativo"). Agora cada
alerta vem de uma consulta real e carrega o link para a tela onde a pendência é
resolvida. Cada fonte é isolada em try/except: uma tabela ausente degrada aquele
alerta, não a página inteira.
"""
from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, render_template, url_for
from flask_login import login_required

from extensions import db
from utils.rbac import pode, requer_permissao

alertas_bp = Blueprint("alertas", __name__, url_prefix="/alertas")

# Havia uma terceira severidade, `INFO`, que nenhuma fonte emitia: o resumo
# sempre mostrava zero para ela. Quando alguma fonte precisar dela, é uma linha
# aqui e outra no mapa de cores do template.
CRITICO, ATENCAO = "critico", "atencao"
_ORDEM = {CRITICO: 0, ATENCAO: 1}

DIAS_VALIDADE_PROXIMA = 60
DIAS_EXAME_ATRASADO = 7
HORAS_ESPERA_PS = 2
HORAS_SEM_EVOLUCAO = 24
OCUPACAO_CRITICA_PCT = 90


def _falhou(mensagem):
    """Registra a falha da fonte e devolve a sessão ao estado utilizável.

    O rollback não é zelo: sem ele o isolamento prometido no topo deste módulo
    não existe em PostgreSQL. Lá o primeiro erro aborta a transação inteira, e
    toda consulta seguinte morre com InFailedSqlTransaction — ou seja, a falha
    de UMA fonte derrubaria silenciosamente todas as outras. Em SQLite o efeito
    não aparece, que é justamente por isso que passou despercebido.
    """
    current_app.logger.exception(mensagem)
    db.session.rollback()


def _alerta(sev, titulo, descricao, href=None, quantidade=None):
    return {
        "severidade": sev,
        "titulo": titulo,
        "descricao": descricao,
        "href": href,
        "quantidade": quantidade,
    }


def _url(endpoint, fallback=None, **kw):
    """url_for tolerante: se o endpoint não existe, devolve o fallback."""
    if endpoint in current_app.view_functions:
        return url_for(endpoint, **kw)
    if fallback and fallback in current_app.view_functions:
        return url_for(fallback)
    return None


def _estoque():
    try:
        from models.estoque import ItemEstoque
    except Exception:
        return []

    saidas = []
    try:
        baixos = ItemEstoque.query.filter(
            ItemEstoque.ativo.is_(True),
            ItemEstoque.quantidade <= ItemEstoque.estoque_minimo,
        ).all()
        if baixos:
            nomes = ", ".join(i.nome for i in baixos[:3])
            resto = f" e mais {len(baixos) - 3}" if len(baixos) > 3 else ""
            saidas.append(_alerta(
                CRITICO,
                f"{len(baixos)} item(ns) abaixo do estoque mínimo",
                f"{nomes}{resto}.",
                _url("estoque.alertas", "estoque.index"),
                len(baixos),
            ))

        limite = date.today() + timedelta(days=DIAS_VALIDADE_PROXIMA)
        vencendo = ItemEstoque.query.filter(
            ItemEstoque.ativo.is_(True),
            ItemEstoque.validade.isnot(None),
            ItemEstoque.validade <= limite,
        ).all()
        vencidos = [i for i in vencendo if i.validade < date.today()]
        proximos = [i for i in vencendo if i.validade >= date.today()]

        if vencidos:
            saidas.append(_alerta(
                CRITICO,
                f"{len(vencidos)} lote(s) vencido(s)",
                "Retire do estoque e registre a perda.",
                _url("estoque.index"),
                len(vencidos),
            ))
        if proximos:
            saidas.append(_alerta(
                ATENCAO,
                f"{len(proximos)} lote(s) vencendo em até {DIAS_VALIDADE_PROXIMA} dias",
                "Priorize o consumo desses lotes.",
                _url("estoque.index"),
                len(proximos),
            ))
    except Exception:
        _falhou("alerta de estoque falhou")
    return saidas


def _exames():
    try:
        from models.exame import ExameSolicitado
    except Exception:
        return []

    try:
        corte = datetime.utcnow() - timedelta(days=DIAS_EXAME_ATRASADO)
        n = ExameSolicitado.query.filter(
            ExameSolicitado.status.in_(("solicitado", "coletado")),
            ExameSolicitado.data_solicitacao <= corte,
        ).count()
        if n:
            return [_alerta(
                ATENCAO,
                f"{n} exame(s) sem resultado há mais de {DIAS_EXAME_ATRASADO} dias",
                "Verifique a pendência com o laboratório.",
                _url("exames.index"),
                n,
            )]
    except Exception:
        _falhou("alerta de exames falhou")
    return []


def _pronto_socorro():
    try:
        from models.pronto_socorro import AtendimentoPS
    except Exception:
        return []

    try:
        corte = datetime.utcnow() - timedelta(hours=HORAS_ESPERA_PS)
        n = AtendimentoPS.query.filter(
            AtendimentoPS.status == "em_espera",
            AtendimentoPS.data_chegada <= corte,
        ).count()
        if n:
            return [_alerta(
                CRITICO,
                f"{n} paciente(s) aguardando no PS há mais de {HORAS_ESPERA_PS}h",
                "Fila de urgência com espera acima do aceitável.",
                _url("pronto_socorro.index"),
                n,
            )]
    except Exception:
        _falhou("alerta de PS falhou")
    return []


def _internacao():
    try:
        from models.internacao import EvolucaoInternacao, Internacao, Leito
    except Exception:
        return []

    saidas = []
    try:
        total = Leito.query.filter_by(ativo=True).count()
        if total:
            ocupados = Leito.query.filter_by(ativo=True, status="ocupado").count()
            pct = round(ocupados / total * 100)
            if pct >= OCUPACAO_CRITICA_PCT:
                saidas.append(_alerta(
                    CRITICO,
                    f"Ocupação de leitos em {pct}%",
                    f"{ocupados} de {total} leitos ocupados.",
                    _url("internacao.leitos"),
                    pct,
                ))
    except Exception:
        _falhou("alerta de ocupação falhou")

    try:
        corte = datetime.utcnow() - timedelta(hours=HORAS_SEM_EVOLUCAO)
        sem_evolucao = 0
        for i in Internacao.query.filter_by(status="ativa").all():
            ultima = (
                EvolucaoInternacao.query
                .filter_by(internacao_id=i.id)
                .order_by(EvolucaoInternacao.criado_em.desc())
                .first()
            )
            referencia = ultima.criado_em if ultima else i.data_entrada
            if referencia and referencia <= corte:
                sem_evolucao += 1
        if sem_evolucao:
            saidas.append(_alerta(
                ATENCAO,
                f"{sem_evolucao} internação(ões) sem evolução há mais de {HORAS_SEM_EVOLUCAO}h",
                "A evolução diária é obrigatória no prontuário.",
                _url("internacao.painel", "internacao.leitos"),
                sem_evolucao,
            ))
    except Exception:
        _falhou("alerta de evolução falhou")
    return saidas


def _vigilancia():
    if not pode("surveillance:read"):
        return []
    try:
        from models.notificacao import NotificacaoCompulsoria
    except Exception:
        return []

    try:
        n = NotificacaoCompulsoria.query.filter_by(status="pendente").count()
        if n:
            return [_alerta(
                ATENCAO,
                f"{n} notificação(ões) compulsória(s) pendente(s)",
                "Agravos de notificação obrigatória aguardando envio ao SINAN.",
                _url("vigilancia.index"),
                n,
            )]
    except Exception:
        _falhou("alerta de vigilância falhou")
    return []


# A tela agrega estoque, fila de urgência e notificações compulsórias de toda a
# unidade. Só `@login_required` deixava a recepção ver o painel operacional
# inteiro; `reports:read` é a mesma permissão que os demais relatórios exigem.
@alertas_bp.get("/")
@login_required
@requer_permissao("reports:read")
def index():
    alertas = (
        _pronto_socorro()
        + _internacao()
        + _estoque()
        + _exames()
        + _vigilancia()
    )
    alertas.sort(key=lambda a: _ORDEM.get(a["severidade"], 9))

    resumo = {
        sev: sum(1 for a in alertas if a["severidade"] == sev)
        for sev in (CRITICO, ATENCAO)
    }
    return render_template("alertas/index.html", alertas=alertas, resumo=resumo)
