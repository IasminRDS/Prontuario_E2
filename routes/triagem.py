# -*- coding: utf-8 -*-
from flask import (Blueprint, current_app, flash, redirect,
                   render_template, request, url_for)
from flask_login import login_required, current_user
from models.triagem import Triagem
from models.paciente import Paciente
from database.db import db
from utils.audit import auditar_aqui
from utils.numeros import decimal_de, inteiro_de
from utils import sinais_vitais
from datetime import datetime, date
from utils.rbac import requer_permissao
from utils.rls import alcanca_todas_as_unidades

triagem_bp = Blueprint("triagem", __name__, url_prefix="/triagem")


@triagem_bp.route("/")
@login_required
@requer_permissao("triage:read")
def index():
    """Painel de triagem do dia — fila por classificação."""
    hoje = date.today()
    # O operador da plataforma não tem lotação, e filtrar por ela o deixava com
    # a fila vazia. Quem atravessa o isolamento não leva filtro de unidade em
    # Python: o RLS já governa o que ele alcança.
    condicoes = [db.func.date(Triagem.criado_em) == hoje]
    if not alcanca_todas_as_unidades():
        condicoes.append(Triagem.unidade_id == current_user.unidade_id)

    triagens = (
        Triagem.query.filter(*condicoes)
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


# Os sinais vitais da triagem e como converter cada um. Fora do corpo da rota
# para que a conversão, a conferência de plausibilidade e a reexibição do
# formulário percorram a MESMA lista: escritas três vezes, um campo novo entraria
# numa e faltaria nas outras duas sem que nada acusasse.
CAMPOS_VITAIS = (
    ("temperatura", decimal_de), ("saturacao_o2", decimal_de),
    ("glicemia", decimal_de), ("peso", decimal_de),
    ("altura", decimal_de), ("frequencia_cardiaca", inteiro_de),
    ("frequencia_respiratoria", inteiro_de),
    ("dor_escala", inteiro_de),
)

CAMPOS_REEXIBIDOS = tuple(c for c, _conv in CAMPOS_VITAIS) + (
    "pressao_arterial", "paciente_id", "classificacao", "queixa_principal",
    "observacoes",
)


def _reexibir(pacientes, paciente_id, enviado):
    """O formulário de volta com o que a pessoa digitou.

    `paciente_sel` vinha só da URL, então quem entrava por `/triagem/nova` e
    escolhia o paciente na lista perdia a escolha junto com o resto.

    **A vírgula é trocada por ponto na devolução, e isso não é capricho.** Os
    campos de sinal vital são `type="number"`, e um `value="70,5"` é recusado
    pelo próprio navegador: o atributo está no HTML e o campo aparece VAZIO.
    Devolver o texto exatamente como veio faria a reexibição passar no teste que
    lê o HTML e falhar na tela — que é a forma de defeito que este projeto mais
    persegue. Só isso se normaliza: texto que não é número volta como veio, e o
    campo numérico o descarta de qualquer forma.
    """
    devolvido = dict(enviado)
    for campo, _conv in CAMPOS_VITAIS:
        valor = devolvido.get(campo)
        if valor:
            devolvido[campo] = valor.replace(",", ".")
    enviado = devolvido

    # Só reconsulta se for número: `paciente_id` vem do POST, e um valor
    # qualquer aí faria `query.get` estourar no banco. A rota tem um `except`
    # largo em volta, então não viraria erro 500 — viraria a mensagem genérica
    # "não foi possível registrar a triagem", que aponta para o lugar errado.
    escolhido = enviado.get("paciente_id") or paciente_id
    escolhido = escolhido if str(escolhido or "").isdigit() else None
    return render_template(
        "triagem/form.html", pacientes=pacientes, enviado=enviado,
        paciente_sel=Paciente.query.get(escolhido) if escolhido else None)


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

            # O que foi digitado, cru, para devolver à tela quando algum campo
            # for recusado. Sem isto a enfermagem reescrevia os oito sinais
            # vitais por causa de um — e formulário que pune quem erra é
            # formulário que se aprende a contornar, que é o oposto do que a
            # conferência de plausibilidade existe para conseguir.
            enviado = {c: request.form.get(c) for c in CAMPOS_REEXIBIDOS}
            enviado["discriminadores"] = disc_raw

            # Converte ANTES de montar o objeto e NOMEANDO o campo. Antes, a
            # conversão acontecia dentro da construção: um valor ilegível
            # derrubava a triagem inteira e a tela mostrava a exceção crua do
            # Python, sem dizer qual campo. E era `float()` direto, sem trocar
            # a vírgula — "38,4" era aceito pelo prontuário e recusado aqui.
            vitais = {}
            for campo, converter in CAMPOS_VITAIS:
                try:
                    vitais[campo] = converter(request.form.get(campo))
                except ValueError:
                    flash(f"{campo.replace('_', ' ').capitalize()}: valor "
                          f"inválido. Use número, com vírgula ou ponto.",
                          "warning")
                    return _reexibir(pacientes, paciente_id, enviado)

            # A conversão só diz se o texto É um número; esta pergunta é se o
            # número PODE ser aquela medida. Sem ela, uma altura de 172 —
            # metros, que é o que o rótulo do campo pede — era gravada, entrava
            # no IMC e saía num recurso FHIR bem formado e impossível.
            implausiveis = sinais_vitais.conferir_muitos(
                dict(vitais, pressao_arterial=request.form.get("pressao_arterial")))
            if implausiveis:
                for mensagem in implausiveis:
                    flash(mensagem, "warning")
                return _reexibir(pacientes, paciente_id, enviado)

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
        "triagem/form.html", pacientes=pacientes, paciente_sel=paciente_sel,
        enviado={}
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
