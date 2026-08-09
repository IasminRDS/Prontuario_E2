# -*- coding: utf-8 -*-
from flask import (Blueprint, current_app, flash, jsonify, redirect,
                   render_template, request, url_for)
from flask_login import login_required, current_user
from models.triagem import Triagem
from models.paciente import Paciente
from database.db import db
from utils.audit import audit_log, auditar_aqui
from utils.numeros import decimal_de, inteiro_de
from datetime import datetime, date
from utils.rbac import requer_permissao

triagem_bp = Blueprint("triagem", __name__, url_prefix="/triagem")


@triagem_bp.route("/")
@login_required
@requer_permissao("triage:read")
def index():
    """Painel de triagem do dia — fila por classificação."""
    hoje = date.today()
    triagens = (
        Triagem.query.filter(
            db.func.date(Triagem.criado_em) == hoje,
            Triagem.unidade_id == current_user.unidade_id,
        )
        .order_by(
            db.case(
                (Triagem.classificacao == "vermelho", 1),
                (Triagem.classificacao == "laranja", 2),
                (Triagem.classificacao == "amarelo", 3),
                (Triagem.classificacao == "verde", 4),
                (Triagem.classificacao == "azul", 5),
                else_=6,
            ),
            Triagem.criado_em,
        )
        .all()
    )

    contadores = {}
    for cor in ["vermelho", "laranja", "amarelo", "verde", "azul"]:
        contadores[cor] = sum(1 for t in triagens if t.classificacao == cor)

    return render_template(
        "triagem/index.html", triagens=triagens, contadores=contadores, hoje=hoje
    )


@triagem_bp.route("/nova", methods=["GET", "POST"])
@triagem_bp.route("/nova/<int:paciente_id>", methods=["GET", "POST"])
@login_required
@requer_permissao("triage:write")
def nova(paciente_id=None):
    pacientes = Paciente.query.filter_by(ativo=True).order_by(Paciente.nome).all()

    if request.method == "POST":
        try:
            import json

            disc_raw = request.form.getlist("discriminadores")

            # Converte ANTES de montar o objeto e NOMEANDO o campo. Antes, a
            # conversão acontecia dentro da construção: um valor ilegível
            # derrubava a triagem inteira e a tela mostrava a exceção crua do
            # Python, sem dizer qual campo. E era `float()` direto, sem trocar
            # a vírgula — "38,4" era aceito pelo prontuário e recusado aqui.
            vitais = {}
            for campo, converter in (
                ("temperatura", decimal_de), ("saturacao_o2", decimal_de),
                ("glicemia", decimal_de), ("peso", decimal_de),
                ("altura", decimal_de), ("frequencia_cardiaca", inteiro_de),
                ("frequencia_respiratoria", inteiro_de),
                ("dor_escala", inteiro_de),
            ):
                try:
                    vitais[campo] = converter(request.form.get(campo))
                except ValueError:
                    flash(f"{campo.replace('_', ' ').capitalize()}: valor "
                          f"inválido. Use número, com vírgula ou ponto.",
                          "warning")
                    return render_template(
                        "triagem/form.html", pacientes=pacientes,
                        paciente_sel=(Paciente.query.get(paciente_id)
                                      if paciente_id else None))

            t = Triagem(
                paciente_id=int(request.form["paciente_id"]),
                unidade_id=current_user.unidade_id,
                realizado_por=current_user.id,
                agendamento_id=request.form.get("agendamento_id") or None,
                classificacao=request.form.get("classificacao", "verde"),
                queixa_principal=request.form.get("queixa_principal", "").strip()
                or None,
                pressao_arterial=request.form.get("pressao_arterial", "").strip()
                or None,
                temperatura=vitais["temperatura"],
                frequencia_cardiaca=vitais["frequencia_cardiaca"],
                frequencia_respiratoria=vitais["frequencia_respiratoria"],
                saturacao_o2=vitais["saturacao_o2"],
                glicemia=vitais["glicemia"],
                peso=vitais["peso"],
                altura=vitais["altura"],
                dor_escala=vitais["dor_escala"],
                discriminadores=json.dumps(disc_raw) if disc_raw else None,
                observacoes=request.form.get("observacoes", "").strip() or None,
                status="aguardando",
            )
            db.session.add(t)
            db.session.flush()
            auditar_aqui("triagens", "create")
            db.session.commit()
            flash(f"Triagem registrada — classificação: {t.cor_info[0]}.", "success")
            return redirect(url_for("triagem.index"))
        except Exception:
            # REGISTRA a exceção e NÃO a exibe: o texto cru do Python não ajuda
            # quem tria e revela detalhe interno na tela.
            db.session.rollback()
            current_app.logger.exception("falha ao registrar triagem")
            flash("Não foi possível registrar a triagem. A equipe técnica foi "
                  "notificada.", "danger")

    paciente_sel = Paciente.query.get(paciente_id) if paciente_id else None
    return render_template(
        "triagem/form.html", pacientes=pacientes, paciente_sel=paciente_sel
    )


@triagem_bp.route("/<int:id>")
@login_required
@requer_permissao("triage:read")
def visualizar(id):
    t = Triagem.query.get_or_404(id)
    import json

    discriminadores = []
    if t.discriminadores:
        try:
            discriminadores = json.loads(t.discriminadores)
        except Exception:
            pass
    return render_template(
        "triagem/visualizar.html", triagem=t, discriminadores=discriminadores
    )


@triagem_bp.route("/<int:id>/status", methods=["POST"])
@login_required
@requer_permissao("triage:write")
def atualizar_status(id):
    t = Triagem.query.get_or_404(id)
    novo = request.form.get("status")
    if novo in ("aguardando", "em_atendimento", "finalizado"):
        t.status = novo
        auditar_aqui("triagens", "update")
        db.session.commit()
    return redirect(url_for("triagem.index"))


@triagem_bp.route("/paciente/<int:paciente_id>")
@login_required
@requer_permissao("triage:read")
def historico_paciente(paciente_id):
    paciente = Paciente.query.get_or_404(paciente_id)
    triagens = (
        Triagem.query.filter_by(paciente_id=paciente_id)
        .order_by(Triagem.criado_em.desc())
        .all()
    )
    return render_template(
        "triagem/historico.html", paciente=paciente, triagens=triagens
    )
