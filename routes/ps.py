# -*- coding: utf-8 -*-
"""Pronto-socorro — painel com o ciclo completo do atendimento de urgência.

Este é o fluxo detalhado (chegada → chamada → observação → desfecho), sobre o
model `AtendimentoPS`. O blueprint `pronto_socorro` continua servindo a fila
simplificada; os dois compartilham a mesma tabela.

Porte de `modules/pronto-socorro` + do FSM de `modules/encounters` do backend
NestJS. O módulo tinha 4 templates e nenhuma rota.
"""
from datetime import datetime, timedelta

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required

from extensions import db
from models.medico import Medico
from models.paciente import Paciente
from models.pronto_socorro import AtendimentoPS
from models.triagem import Triagem
from utils.audit import registrar
from utils.rbac import requer_permissao

ps_bp = Blueprint("ps", __name__, url_prefix="/ps")

# FSM do atendimento. A ordem importa: só se avança para um estado alcançável.
TRANSICOES = {
    "em_espera": ("em_atendimento", "evadiu", "cancelado"),
    "em_atendimento": ("em_observacao", "alta", "internado", "obito", "transferido"),
    "em_observacao": ("em_atendimento", "alta", "internado", "obito", "transferido"),
}
DESFECHOS = ("alta", "internado", "transferido", "obito", "evadiu")
ESTADOS_ABERTOS = ("em_espera", "em_atendimento", "em_observacao")

CLASSIFICACOES = ("vermelho", "laranja", "amarelo", "verde", "azul")

# Ordem de atendimento: gravidade primeiro, depois tempo de espera.
_PESO_RISCO = {"vermelho": 0, "laranja": 1, "amarelo": 2, "verde": 3, "azul": 4}

#: Cores de Manchester da mais grave para a menos. A ordem é a do protocolo e é
#: a mesma que ordena a fila — daí sair de `_PESO_RISCO` em vez de ser reescrita.
ORDEM_CORES = tuple(sorted(_PESO_RISCO, key=_PESO_RISCO.get))


def _classificacao(atendimento):
    """Cor Manchester do atendimento, vinda da triagem vinculada."""
    if atendimento.triagem_id:
        t = db.session.get(Triagem, atendimento.triagem_id)
        if t and t.classificacao:
            return t.classificacao
    return None


def _ordenar_fila(atendimentos):
    return sorted(
        atendimentos,
        key=lambda a: (
            _PESO_RISCO.get(_classificacao(a), 9),
            a.data_chegada or datetime.utcnow(),
        ),
    )


@ps_bp.get("/")
@login_required
@requer_permissao("emergency:write")
def painel():
    """Painel operacional: espera, em atendimento e em observação."""
    abertos = (
        AtendimentoPS.query
        .filter(AtendimentoPS.status.in_(ESTADOS_ABERTOS))
        .all()
    )

    fila = _ordenar_fila([a for a in abertos if a.status == "em_espera"])
    em_atendimento = [a for a in abertos if a.status == "em_atendimento"]
    em_observacao = [a for a in abertos if a.status == "em_observacao"]

    # Classificação resolvida uma vez, para o template não repetir consulta.
    cores = {a.id: _classificacao(a) for a in abertos}

    agora = datetime.utcnow()
    espera_maxima = None
    if fila:
        mais_antigo = min(a.data_chegada for a in fila if a.data_chegada)
        espera_maxima = int((agora - mais_antigo).total_seconds() // 60)

    # O painel mostra a fila AGRUPADA por cor de Manchester, e é assim que ele
    # sempre foi escrito — lia `fila[cor]` e `ORDEM_CORES`, que a rota nunca
    # passou. O `{% if fila[cor] %}` dava falso em todas as cores e a tela
    # inteira aparecia vazia, mesmo com gente esperando.
    #
    # `sem_classificacao` NÃO é enfeite: `_classificacao` devolve None para quem
    # chegou sem triagem vinculada, e sem esta faixa esses pacientes sumiriam do
    # painel. Fila de pronto-socorro que esconde quem espera é o pior defeito
    # possível nesta tela — pior que mostrar sem cor.
    por_cor = {cor: [] for cor in ORDEM_CORES}
    sem_classificacao = []
    for atendimento in fila:
        cor = cores.get(atendimento.id)
        (por_cor[cor] if cor in por_cor else sem_classificacao).append(atendimento)

    return render_template(
        "ps/painel.html",
        fila=por_cor,
        sem_classificacao=sem_classificacao,
        ORDEM_CORES=ORDEM_CORES,
        em_atendimento=em_atendimento,
        em_observacao=em_observacao,
        cores=cores,
        agora=agora,
        espera_maxima=espera_maxima,
        classificacoes=CLASSIFICACOES,
        stats={
            **{cor: len(itens) for cor, itens in por_cor.items()},
            "sem_classificacao": len(sem_classificacao),
            "total": len(abertos),
            "espera": len(fila),
            "atendimento": len(em_atendimento),
            "observacao": len(em_observacao),
        },
    )


@ps_bp.route("/entrada", methods=["GET", "POST"])
@ps_bp.route("/entrada/<int:paciente_id>", methods=["GET", "POST"])
@login_required
@requer_permissao("emergency:write")
def entrada(paciente_id=None):
    """Acolhimento: registra a chegada do paciente ao PS."""
    pacientes = Paciente.query.filter_by(ativo=True).order_by(Paciente.nome).all()
    medicos = Medico.query.all()

    if request.method == "POST":
        paciente = db.session.get(Paciente, request.form.get("paciente_id", type=int) or 0)
        queixa = (request.form.get("queixa_principal") or "").strip()

        if not paciente:
            flash("Selecione o paciente.", "warning")
        elif not queixa:
            flash("A queixa principal é obrigatória.", "warning")
        else:
            # Um paciente não pode ter dois atendimentos abertos no PS.
            aberto = AtendimentoPS.query.filter(
                AtendimentoPS.paciente_id == paciente.id,
                AtendimentoPS.status.in_(ESTADOS_ABERTOS),
            ).first()
            if aberto:
                flash(
                    f"{paciente.nome} já tem atendimento aberto no PS.", "warning"
                )
                return redirect(url_for("ps.visualizar", id=aberto.id))

            # Vincula a triagem mais recente do paciente, se houver.
            triagem = (
                Triagem.query
                .filter_by(paciente_id=paciente.id)
                .order_by(Triagem.criado_em.desc())
                .first()
            )

            a = AtendimentoPS(
                paciente_id=paciente.id,
                medico_id=request.form.get("medico_id", type=int),
                triagem_id=triagem.id if triagem else None,
                unidade_id=current_user.unidade_id,
                motivo_consulta=queixa,
                diagnostico_preliminar=(request.form.get("hipotese_diag") or "").strip() or None,
                status="em_espera",
                data_chegada=datetime.utcnow(),
                criado_por=current_user.id,
            )
            db.session.add(a)
            db.session.flush()

            registrar("atendimentos_ps", a.id, "create",
                      f"Entrada no PS: {paciente.nome} — {queixa[:80]}")
            db.session.commit()

            flash(f"{paciente.nome} registrado na fila do pronto-socorro.", "success")
            return redirect(url_for("ps.painel"))

    return render_template(
        "ps/entrada.html",
        pacientes=pacientes,
        medicos=medicos,
        paciente_sel=db.session.get(Paciente, paciente_id) if paciente_id else None,
        classificacoes=CLASSIFICACOES,
    )


@ps_bp.get("/<int:id>")
@login_required
@requer_permissao("emergency:write")
def visualizar(id):
    ps = AtendimentoPS.query.get_or_404(id)

    registrar("atendimentos_ps", ps.id, "read",
              f"Atendimento de PS consultado (paciente {ps.paciente_id})", commit=True)

    return render_template(
        "ps/visualizar.html",
        ps=ps,
        classificacao=_classificacao(ps),
        desfechos=DESFECHOS,
        # O seletor de "Médico responsável" existia no template e a rota nunca
        # mandou a lista: renderizava vazio, e chamar o paciente atribuindo um
        # médico era impossível pela tela.
        medicos=Medico.query.order_by(Medico.id.asc()).all(),
        proximos=TRANSICOES.get(ps.status, ()),
        # A tela não deve repetir a lista de estados: ela derivava de nomes que
        # não existem mais ('aguardando_triagem', 'evasao') e por isso escondia
        # a ação principal. A máquina de estados aqui é a única fonte.
        desfechos_possiveis=[s for s in TRANSICOES.get(ps.status, ())
                             if s in DESFECHOS],
    )


@ps_bp.post("/<int:id>/chamar")
@login_required
@requer_permissao("emergency:write")
def chamar(id):
    """Chama o paciente da fila para atendimento."""
    ps = AtendimentoPS.query.get_or_404(id)

    if "em_atendimento" not in TRANSICOES.get(ps.status, ()):
        flash(f"Não é possível chamar um atendimento em '{ps.status}'.", "warning")
        return redirect(url_for("ps.visualizar", id=ps.id))

    ps.status = "em_atendimento"
    ps.data_atendimento = datetime.utcnow()

    medico = Medico.query.filter_by(user_id=current_user.id).first()
    if medico and not ps.medico_id:
        ps.medico_id = medico.id

    espera = None
    if ps.data_chegada:
        espera = int((ps.data_atendimento - ps.data_chegada).total_seconds() // 60)

    registrar("atendimentos_ps", ps.id, "update",
              f"Paciente chamado para atendimento"
              + (f" — espera de {espera} min" if espera is not None else ""))
    db.session.commit()

    flash("Paciente chamado.", "success")
    return redirect(url_for("ps.visualizar", id=ps.id))


@ps_bp.post("/<int:id>/observacao")
@login_required
@requer_permissao("emergency:write")
def colocar_observacao(id):
    ps = AtendimentoPS.query.get_or_404(id)

    if "em_observacao" not in TRANSICOES.get(ps.status, ()):
        flash(f"Não é possível colocar em observação a partir de '{ps.status}'.",
              "warning")
        return redirect(url_for("ps.visualizar", id=ps.id))

    ps.status = "em_observacao"

    conduta = (request.form.get("conduta") or "").strip()
    if conduta:
        ps.conduta = conduta

    registrar("atendimentos_ps", ps.id, "update", "Paciente em observação")
    db.session.commit()

    flash("Paciente em observação.", "success")
    return redirect(url_for("ps.visualizar", id=ps.id))


@ps_bp.post("/<int:id>/desfecho")
@login_required
@requer_permissao("emergency:write")
def desfecho(id):
    """Encerra o atendimento: alta, internação, transferência, óbito ou evasão."""
    ps = AtendimentoPS.query.get_or_404(id)
    escolhido = (request.form.get("desfecho") or "").strip()

    if escolhido not in DESFECHOS:
        flash("Selecione o desfecho.", "warning")
        return redirect(url_for("ps.visualizar", id=ps.id))
    if escolhido not in TRANSICOES.get(ps.status, ()):
        flash(f"Desfecho '{escolhido}' não é alcançável de '{ps.status}'.", "warning")
        return redirect(url_for("ps.visualizar", id=ps.id))

    ps.status = escolhido
    ps.data_liberacao = datetime.utcnow()

    conduta = (request.form.get("conduta") or "").strip()
    if conduta:
        ps.conduta = conduta
    hipotese = (request.form.get("hipotese_diag") or "").strip()
    if hipotese:
        ps.diagnostico_preliminar = hipotese

    permanencia = None
    if ps.data_chegada:
        permanencia = int((ps.data_liberacao - ps.data_chegada).total_seconds() // 60)

    registrar("atendimentos_ps", ps.id, "update",
              f"Desfecho: {escolhido}"
              + (f" — permanência de {permanencia} min" if permanencia is not None else ""))
    db.session.commit()

    flash(f"Atendimento encerrado: {escolhido}.", "success")
    return redirect(url_for("ps.painel"))


@ps_bp.get("/historico")
@login_required
@requer_permissao("emergency:write", "clinical:read")
def historico():
    """Atendimentos encerrados, com tempo de permanência."""
    dias = request.args.get("dias", type=int) or 30
    dias = min(max(dias, 1), 365)
    situacao = (request.args.get("desfecho") or "").strip()
    pagina = request.args.get("pagina", type=int) or 1

    corte = datetime.utcnow() - timedelta(days=dias)
    query = AtendimentoPS.query.filter(
        AtendimentoPS.data_chegada >= corte,
        AtendimentoPS.status.notin_(ESTADOS_ABERTOS),
    )
    if situacao in DESFECHOS:
        query = query.filter(AtendimentoPS.status == situacao)

    paginacao = (
        query.order_by(AtendimentoPS.data_chegada.desc())
        .paginate(page=pagina, per_page=40, error_out=False)
    )

    return render_template(
        "ps/historico.html",
        atendimentos=paginacao.items,
        paginacao=paginacao,
        dias=dias,
        data_i=corte,
        data_f=datetime.utcnow(),
        desfecho=situacao,
        desfechos=DESFECHOS,
        cores={a.id: _classificacao(a) for a in paginacao.items},
    )
