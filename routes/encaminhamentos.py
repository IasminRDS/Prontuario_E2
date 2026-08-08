# -*- coding: utf-8 -*-
"""Encaminhamentos — solicitação de vaga em outro serviço.

É o lado do SOLICITANTE. O parecer do regulador vive em `routes/regulacao.py`:
`regulation:write` pede, `regulation:decide` autoriza. Essa separação é a mesma
do `modules/regulacao` do backend NestJS.

O módulo tinha 4 templates e nenhuma rota — as telas eram inalcançáveis.
"""
from datetime import datetime

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required

from extensions import db
from models.encaminhamento import Encaminhamento
from models.medico import Medico
from models.paciente import Paciente
from models.unidade_saude import UnidadeSaude
from utils.audit import registrar
from utils.rbac import requer_permissao

encaminhamentos_bp = Blueprint(
    "encaminhamentos", __name__, url_prefix="/encaminhamentos"
)

# O vocabulário e a ordem de gravidade vêm do model — ver a nota lá sobre por
# que ele não é declarado aqui, embora seja esta rota que o valida na escrita.
PRIORIDADES = Encaminhamento.PRIORIDADES
ORDEM_DE_GRAVIDADE = {p: i for i, p in enumerate(PRIORIDADES)}

SITUACOES = ("solicitado", "autorizado", "negado", "agendado", "realizado", "cancelado")

ESPECIALIDADES = (
    "Cardiologia", "Dermatologia", "Endocrinologia", "Gastroenterologia",
    "Ginecologia e Obstetrícia", "Neurologia", "Oftalmologia", "Oncologia",
    "Ortopedia", "Otorrinolaringologia", "Pediatria", "Pneumologia",
    "Psiquiatria", "Reumatologia", "Urologia", "Cirurgia Geral",
    "Cirurgia Vascular", "Nefrologia", "Hematologia", "Infectologia",
)

POR_PAGINA = 30


@encaminhamentos_bp.get("/")
@login_required
@requer_permissao("regulation:read")
def painel():
    situacao = (request.args.get("status") or "").strip()
    prioridade = (request.args.get("prioridade") or "").strip()
    # O campo "Especialidade" existia no formulário e a rota nunca leu o
    # parâmetro: digitar e clicar em Filtrar devolvia a lista inteira, e o valor
    # digitado sumia do campo porque `filtro_esp` também não era passado.
    especialidade = (request.args.get("especialidade") or "").strip()
    pagina = request.args.get("page", type=int) or 1

    query = Encaminhamento.query
    if situacao in SITUACOES:
        query = query.filter(Encaminhamento.status == situacao)
    if prioridade in PRIORIDADES:
        query = query.filter(Encaminhamento.prioridade == prioridade)
    if especialidade:
        query = query.filter(
            Encaminhamento.especialidade.ilike(f"%{especialidade}%"))

    ordem = db.case(
        ORDEM_DE_GRAVIDADE, value=Encaminhamento.prioridade, else_=9,
    )
    encaminhamentos = (
        query.order_by(ordem, Encaminhamento.data_solicitacao.asc())
        .paginate(page=pagina, per_page=POR_PAGINA, error_out=False)
    )

    return render_template(
        "encaminhamentos/painel.html",
        encaminhamentos=encaminhamentos,
        status=situacao,
        prioridade=prioridade,
        filtro_esp=especialidade,
        prioridades=PRIORIDADES,
        situacoes=SITUACOES,
        agora=datetime.utcnow(),
    )


@encaminhamentos_bp.get("/paciente/<int:paciente_id>")
@login_required
@requer_permissao("regulation:read")
def lista_paciente(paciente_id):
    paciente = Paciente.query.get_or_404(paciente_id)
    encaminhamentos = (
        Encaminhamento.query
        .filter_by(paciente_id=paciente.id)
        .order_by(Encaminhamento.data_solicitacao.desc())
        .all()
    )
    # A tela separa o que ainda tramita do que já se encerrou. A separação vem
    # daqui e não do template: é regra de domínio.
    encerrados = ("realizado", "cancelado", "negado")
    ativos = [e for e in encaminhamentos if e.status not in encerrados]
    historico = [e for e in encaminhamentos if e.status in encerrados]

    return render_template("encaminhamentos/lista.html", paciente=paciente,
                           encaminhamentos=encaminhamentos,
                           ativos=ativos, historico=historico)


@encaminhamentos_bp.get("/<int:id>")
@login_required
@requer_permissao("regulation:read")
def visualizar(id):
    enc = Encaminhamento.query.get_or_404(id)
    registrar("encaminhamentos", enc.id, "read",
              f"Encaminhamento consultado (paciente {enc.paciente_id})", commit=True)
    return render_template("encaminhamentos/visualizar.html", enc=enc,
                           situacoes=SITUACOES)


@encaminhamentos_bp.route("/novo", methods=["GET", "POST"])
@encaminhamentos_bp.route("/novo/<int:paciente_id>", methods=["GET", "POST"])
@login_required
@requer_permissao("regulation:write")
def novo(paciente_id=None):
    pacientes = Paciente.query.filter_by(ativo=True).order_by(Paciente.nome).all()
    unidades = UnidadeSaude.query.filter_by(ativo=True).order_by(UnidadeSaude.nome).all()

    if request.method == "POST":
        paciente = db.session.get(Paciente, request.form.get("paciente_id", type=int) or 0)
        especialidade = (request.form.get("especialidade") or "").strip()
        motivo = (request.form.get("motivo") or "").strip()

        if not paciente:
            flash("Selecione o paciente.", "warning")
        elif not especialidade:
            flash("Informe a especialidade de destino.", "warning")
        elif not motivo:
            flash("O motivo do encaminhamento é obrigatório.", "warning")
        else:
            medico = Medico.query.filter_by(user_id=current_user.id).first()
            prioridade = (request.form.get("prioridade") or "eletivo").strip()

            # A unidade de origem é obrigatória no model: cai na do usuário e,
            # em último caso, na primeira cadastrada.
            origem_id = current_user.unidade_id
            if not origem_id:
                primeira = UnidadeSaude.query.first()
                origem_id = primeira.id if primeira else None
            if not origem_id:
                flash("Cadastre uma unidade de saúde antes de encaminhar.", "danger")
                return redirect(url_for("unidades.index"))

            enc = Encaminhamento(
                paciente_id=paciente.id,
                prontuario_id=request.form.get("prontuario_id", type=int),
                medico_id=medico.id if medico else None,
                unidade_origem_id=origem_id,
                unidade_id=origem_id,
                especialidade=especialidade,
                servico_destino=(request.form.get("servico_destino") or "").strip() or None,
                prioridade=prioridade if prioridade in PRIORIDADES else "eletivo",
                motivo=motivo,
                hipotese_diagnostica=(request.form.get("hipotese_diagnostica") or "").strip() or None,
                cid=(request.form.get("cid") or "").strip().upper() or None,
                observacoes=(request.form.get("observacoes") or "").strip() or None,
                status="solicitado",
            )
            db.session.add(enc)
            db.session.flush()

            registrar("encaminhamentos", enc.id, "create",
                      f"Encaminhamento para {especialidade} — prioridade {enc.prioridade}")
            db.session.commit()

            flash("Encaminhamento solicitado. Aguardando parecer da regulação.", "success")
            return redirect(url_for("encaminhamentos.visualizar", id=enc.id))

    return render_template(
        "encaminhamentos/form.html",
        pacientes=pacientes,
        unidades=unidades,
        paciente=db.session.get(Paciente, paciente_id) if paciente_id else None,
        paciente_sel=db.session.get(Paciente, paciente_id) if paciente_id else None,
        especialidades=ESPECIALIDADES,
        prioridades=PRIORIDADES,
        rotulos_prioridade=Encaminhamento.PRIORIDADE_LABELS,
    )


@encaminhamentos_bp.post("/<int:id>/status")
@login_required
@requer_permissao("regulation:write")
def atualizar_status(id):
    enc = Encaminhamento.query.get_or_404(id)
    novo_status = (request.form.get("status") or "").strip()

    if novo_status not in SITUACOES:
        flash("Situação inválida.", "danger")
        return redirect(url_for("encaminhamentos.visualizar", id=enc.id))

    # Autorizar/negar é parecer de regulador, não do solicitante.
    from utils.rbac import pode
    if novo_status in ("autorizado", "negado") and not pode("regulation:decide"):
        flash("Autorizar ou negar exige perfil de regulação.", "danger")
        return redirect(url_for("encaminhamentos.visualizar", id=enc.id))

    anterior = enc.status
    enc.status = novo_status

    retorno = (request.form.get("retorno_info") or "").strip()
    if retorno:
        enc.retorno_info = retorno
    if novo_status == "realizado" and not enc.data_realizacao:
        enc.data_realizacao = datetime.utcnow()

    registrar("encaminhamentos", enc.id, "update",
              f"Situação: {anterior} → {novo_status}"
              + (f" — {retorno}" if retorno else ""))
    db.session.commit()

    flash(f"Encaminhamento marcado como {novo_status}.", "success")
    return redirect(url_for("encaminhamentos.visualizar", id=enc.id))
