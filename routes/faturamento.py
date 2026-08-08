# -*- coding: utf-8 -*-
"""Faturamento SUS — AIH e APAC.

AIH (Autorização de Internação Hospitalar) fatura internação; APAC (Autorização
de Procedimentos de Alta Complexidade) fatura procedimento ambulatorial
continuado. Ambos os models já existiam no schema, espelhando o monorepo, e
nenhuma rota os alcançava — o módulo tinha 4 templates inacessíveis.
"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from extensions import db
from models.faturamento import AIH, APAC
from models.internacao import Internacao
from models.medico import Medico
from models.paciente import Paciente
from utils.audit import registrar
from utils.rbac import requer_permissao

faturamento_bp = Blueprint("faturamento", __name__, url_prefix="/faturamento")

STATUS_AIH = ("aberta", "apresentada", "aprovada", "rejeitada", "cancelada")
STATUS_APAC = ("ativa", "encerrada", "cancelada")


def _valor(bruto):
    """Converte texto em Decimal. Devolve None quando vazio, False se inválido."""
    texto = (bruto or "").strip().replace(".", "").replace(",", ".")
    if not texto:
        return None
    try:
        v = Decimal(texto)
    except (InvalidOperation, ValueError):
        return False
    return v if v >= 0 else False


def _data(bruto):
    texto = (bruto or "").strip()
    if not texto:
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return False


def _texto(bruto, limite):
    """Texto aparado e truncado ao limite da coluna.

    Truncar aqui e não deixar o banco recusar: em PostgreSQL o excesso levanta
    `StringDataRightTruncation` no meio da transação, e o operador recebe o erro
    cru do driver em vez de saber qual campo passou do tamanho.
    """
    texto = (bruto or "").strip()
    return texto[:limite] or None


def _competencia(bruto):
    """Competência AAAA/MM. None se vazia, False se malformada.

    É o recorte pelo qual todo faturamento do SUS fecha o mês. Aceitar
    "2026-8" ou "ago/26" faria o relatório de competência agrupar em silêncio
    coisas que não são a mesma competência.
    """
    texto = (bruto or "").strip().replace("-", "/")
    if not texto:
        return None
    if not re.fullmatch(r"\d{4}/(0[1-9]|1[0-2])", texto):
        return False
    return texto


# =========================================================
# AIH
# =========================================================
@faturamento_bp.get("/aih")
@login_required
@requer_permissao("reports:read", "admin:full")
def aih_lista():
    situacao = (request.args.get("status") or "").strip()
    termo = (request.args.get("q") or "").strip()
    # O campo "Competência" existia no filtro e a rota nunca leu o parâmetro:
    # digitar AAAA/MM e filtrar devolvia a lista inteira. É o recorte pelo qual
    # o faturamento fecha o mês, então é o filtro que mais importa aqui.
    comp = _competencia(request.args.get("competencia"))
    comp = comp if comp not in (False, None) else (
        request.args.get("competencia") or "").strip()
    pagina = request.args.get("pagina", type=int) or 1

    query = AIH.query
    if situacao in STATUS_AIH:
        query = query.filter(AIH.status == situacao)
    if comp:
        query = query.filter(AIH.competencia == comp)
    if termo:
        like = f"%{termo}%"
        query = (
            query.join(Paciente, AIH.paciente_id == Paciente.id)
            .filter(or_(
                Paciente.nome.ilike(like),
                AIH.numero_aih.ilike(like),
                AIH.procedimento_principal.ilike(like),
            ))
        )

    paginacao = (
        query.order_by(AIH.data_emissao.desc(), AIH.id.desc())
        .paginate(page=pagina, per_page=30, error_out=False)
    )

    totais = dict(
        db.session.query(AIH.status, func.count(AIH.id)).group_by(AIH.status).all()
    )
    # O total soma o MESMO recorte que a lista mostra. Somar a base inteira ao
    # lado de uma lista filtrada é pior que não somar: os dois números aparecem
    # juntos, não batem, e nada diz por quê.
    soma = db.session.query(func.sum(AIH.valor_total))
    if comp:
        soma = soma.filter(AIH.competencia == comp)
    if situacao in STATUS_AIH:
        soma = soma.filter(AIH.status == situacao)
    valor_total = soma.scalar() or 0

    return render_template(
        "faturamento/aih_lista.html",
        aihs=paginacao.items,
        paginacao=paginacao,
        comp=comp,
        total_valor=valor_total,
        status=situacao,
        q=termo,
        status_possiveis=STATUS_AIH,
        totais=totais,
        valor_total=valor_total,
    )


@faturamento_bp.route("/aih/nova", methods=["GET", "POST"])
@faturamento_bp.route("/aih/<int:id>/editar", methods=["GET", "POST"])
@login_required
@requer_permissao("admin:full")
def aih_form(id=None):
    aih = AIH.query.get_or_404(id) if id else None

    if request.method == "POST":
        paciente = db.session.get(Paciente, request.form.get("paciente_id", type=int) or 0)
        procedimento = (request.form.get("procedimento_principal") or "").strip()

        valor = _valor(request.form.get("valor_total"))
        emissao = _data(request.form.get("data_emissao"))
        apresentacao = _data(request.form.get("data_apresentacao"))
        # Os campos novos passam pela MESMA validação dos antigos: `_valor` e
        # `_data` devolvem False no inválido, e aceitar False aqui gravaria
        # `False` na coluna — que em SQL vira 0, um valor plausível e errado.
        sh = _valor(request.form.get("valor_sh"))
        sp = _valor(request.form.get("valor_sp"))
        internacao = _data(request.form.get("data_internacao"))
        saida = _data(request.form.get("data_saida"))
        competencia = _competencia(request.form.get("competencia"))

        if not paciente:
            flash("Selecione o paciente.", "warning")
        elif not procedimento:
            flash("Informe o procedimento principal.", "warning")
        elif valor is False or sh is False or sp is False:
            flash("Valor inválido.", "warning")
        elif False in (emissao, apresentacao, internacao, saida):
            flash("Data inválida.", "warning")
        elif competencia is False:
            flash("Competência inválida — use AAAA/MM.", "warning")
        elif internacao and saida and saida < internacao:
            flash("A saída não pode ser anterior à internação.", "warning")
        else:
            numero = (request.form.get("numero_aih") or "").strip() or None
            # O número da AIH é único: colisão impede o faturamento.
            if numero:
                conflito = AIH.query.filter(AIH.numero_aih == numero)
                if aih:
                    conflito = conflito.filter(AIH.id != aih.id)
                if conflito.first():
                    flash(f"Já existe AIH com o número {numero}.", "danger")
                    return _render_aih_form(aih)

            situacao = (request.form.get("status") or "aberta").strip()
            novo = aih is None
            if novo:
                aih = AIH(criado_por=current_user.id)
                db.session.add(aih)

            aih.paciente_id = paciente.id
            aih.internacao_id = request.form.get("internacao_id", type=int)
            aih.medico_solicitante_id = request.form.get("medico_solicitante_id", type=int)
            aih.numero_aih = numero
            aih.procedimento_principal = procedimento
            aih.cid_principal = (request.form.get("cid_principal") or "").strip().upper() or None
            aih.data_emissao = emissao or date.today()
            aih.data_apresentacao = apresentacao
            aih.status = situacao if situacao in STATUS_AIH else "aberta"

            # --- campos que a tela já pedia e o schema passou a ter -----------
            aih.competencia = competencia
            aih.tipo_aih = _texto(request.form.get("tipo_aih"), 2)
            aih.carater_internacao = _texto(request.form.get("carater_internacao"), 2)
            aih.cid_secundario = (
                (request.form.get("cid_secundario") or "").strip().upper() or None)
            aih.procedimento_secundario = _texto(
                request.form.get("procedimento_secundario"), 255)
            aih.data_internacao = internacao
            aih.data_saida = saida
            aih.motivo_saida = _texto(request.form.get("motivo_saida"), 40)
            aih.observacoes = (request.form.get("observacoes") or "").strip() or None

            # Na AIH o total é a soma dos serviços hospitalares com os
            # profissionais. Derivar na escrita mantém os três coerentes, sem
            # abrir mão da coluna — `aih_lista` soma `valor_total` em SQL, e
            # propriedade Python não agrega no banco.
            aih.valor_sh = sh
            aih.valor_sp = sp
            aih.valor_total = (sh or 0) + (sp or 0) if (sh or sp) else valor

            db.session.flush()
            registrar("faturamento_aih", aih.id, "create" if novo else "update",
                      f"AIH {aih.numero_aih or aih.id} — {aih.status}")
            db.session.commit()

            flash("AIH salva." if not novo else "AIH criada.", "success")
            return redirect(url_for("faturamento.aih_lista"))

    return _render_aih_form(aih)


def _competencia_atual():
    """AAAA/MM de hoje — o padrão do campo numa AIH ou APAC nova.

    Em UTC pelo mesmo motivo dos relatórios: as colunas são gravadas em UTC, e
    misturar fuso aqui faria a competência virar no dia errado.
    """
    return datetime.utcnow().strftime("%Y/%m")


def _render_aih_form(aih, internacao_id=None):
    # `intern_sel` e `comp_atual` eram lidos pelo template e nunca passados: o
    # formulário abria sem competência preenchida e sem herdar nada da
    # internação escolhida, mesmo vindo de uma.
    selecionada = None
    if internacao_id:
        selecionada = db.session.get(Internacao, internacao_id)
    elif aih is not None:
        selecionada = aih.internacao

    return render_template(
        "faturamento/aih_form.html",
        aih=aih,
        intern_sel=selecionada,
        comp_atual=_competencia_atual(),
        pacientes=Paciente.query.filter_by(ativo=True).order_by(Paciente.nome).all(),
        medicos=Medico.query.all(),
        internacoes=Internacao.query.order_by(Internacao.data_entrada.desc()).limit(200).all(),
        status_possiveis=STATUS_AIH,
    )


# Aliases: os templates apontam para aih_nova/aih_editar.
faturamento_bp.add_url_rule(
    "/aih/nova", endpoint="aih_nova", view_func=aih_form, methods=["GET", "POST"]
)
faturamento_bp.add_url_rule(
    "/aih/<int:id>/editar", endpoint="aih_editar", view_func=aih_form,
    methods=["GET", "POST"],
)


# =========================================================
# APAC
# =========================================================
@faturamento_bp.get("/apac")
@login_required
@requer_permissao("reports:read", "admin:full")
def apac_lista():
    situacao = (request.args.get("status") or "").strip()
    termo = (request.args.get("q") or "").strip()
    pagina = request.args.get("pagina", type=int) or 1

    query = APAC.query
    if situacao in STATUS_APAC:
        query = query.filter(APAC.status == situacao)
    if termo:
        like = f"%{termo}%"
        query = (
            query.join(Paciente, APAC.paciente_id == Paciente.id)
            .filter(or_(
                Paciente.nome.ilike(like),
                APAC.numero_apac.ilike(like),
                APAC.procedimento_principal.ilike(like),
            ))
        )

    paginacao = (
        query.order_by(APAC.data_inicio_validade.desc(), APAC.id.desc())
        .paginate(page=pagina, per_page=30, error_out=False)
    )

    totais = dict(
        db.session.query(APAC.status, func.count(APAC.id)).group_by(APAC.status).all()
    )

    return render_template(
        "faturamento/apac_lista.html",
        apacs=paginacao.items,
        paginacao=paginacao,
        status=situacao,
        q=termo,
        status_possiveis=STATUS_APAC,
        totais=totais,
        hoje=date.today(),
    )


@faturamento_bp.route("/apac/nova", methods=["GET", "POST"])
@faturamento_bp.route("/apac/<int:id>/editar", methods=["GET", "POST"])
@login_required
@requer_permissao("admin:full")
def apac_form(id=None):
    apac = APAC.query.get_or_404(id) if id else None

    if request.method == "POST":
        paciente = db.session.get(Paciente, request.form.get("paciente_id", type=int) or 0)
        procedimento = (request.form.get("procedimento_principal") or "").strip()

        inicio = _data(request.form.get("data_inicio"))
        fim = _data(request.form.get("data_fim"))
        valor = _valor(request.form.get("valor_total"))
        competencia_apac = _competencia(request.form.get("competencia"))

        if not paciente:
            flash("Selecione o paciente.", "warning")
        elif not procedimento:
            flash("Informe o procedimento principal.", "warning")
        elif competencia_apac is False:
            flash("Competência inválida — use AAAA/MM.", "warning")
        elif inicio is False or fim is False:
            flash("Data de validade inválida.", "warning")
        elif not inicio or not fim:
            flash("A APAC precisa de início e fim de validade.", "warning")
        elif fim < inicio:
            flash("O fim da validade não pode ser antes do início.", "warning")
        elif valor is False:
            flash("Valor total inválido.", "warning")
        else:
            numero = (request.form.get("numero_apac") or "").strip() or None
            if numero:
                conflito = APAC.query.filter(APAC.numero_apac == numero)
                if apac:
                    conflito = conflito.filter(APAC.id != apac.id)
                if conflito.first():
                    flash(f"Já existe APAC com o número {numero}.", "danger")
                    return _render_apac_form(apac)

            situacao = (request.form.get("status") or "ativa").strip()
            novo = apac is None
            if novo:
                apac = APAC(criado_por=current_user.id)
                db.session.add(apac)

            apac.paciente_id = paciente.id
            apac.medico_solicitante_id = request.form.get("medico_solicitante_id", type=int)
            apac.numero_apac = numero
            apac.procedimento_principal = procedimento
            apac.cid_principal = (request.form.get("cid_principal") or "").strip().upper() or None
            apac.data_inicio_validade = inicio
            apac.data_fim_validade = fim
            apac.quantidade_aprovada = request.form.get("quantidade", type=int) or 1
            apac.quantidade_realizada = request.form.get("quantidade_realizada", type=int) or 0
            apac.valor_total = valor
            apac.status = situacao if situacao in STATUS_APAC else "ativa"

            # --- campos que a tela já pedia e o schema passou a ter -----------
            apac.competencia = competencia_apac
            apac.tipo = _texto(request.form.get("tipo"), 20)
            apac.justificativa = (
                (request.form.get("justificativa") or "").strip() or None)

            db.session.flush()
            registrar("faturamento_apac", apac.id, "create" if novo else "update",
                      f"APAC {apac.numero_apac or apac.id} — {apac.status}")
            db.session.commit()

            flash("APAC salva." if not novo else "APAC criada.", "success")
            return redirect(url_for("faturamento.apac_lista"))

    return _render_apac_form(apac)


def _render_apac_form(apac):
    return render_template(
        "faturamento/apac_form.html",
        apac=apac,
        comp_atual=(apac.competencia if apac else None) or _competencia_atual(),
        pacientes=Paciente.query.filter_by(ativo=True).order_by(Paciente.nome).all(),
        medicos=Medico.query.all(),
        status_possiveis=STATUS_APAC,
    )


faturamento_bp.add_url_rule(
    "/apac/nova", endpoint="apac_nova", view_func=apac_form, methods=["GET", "POST"]
)
faturamento_bp.add_url_rule(
    "/apac/<int:id>/editar", endpoint="apac_editar", view_func=apac_form,
    methods=["GET", "POST"],
)
