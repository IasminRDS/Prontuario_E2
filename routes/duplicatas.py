# -*- coding: utf-8 -*-
"""Fila de revisão de cadastros duplicados.

A varredura sugere; quem decide é gente. Nenhum par é unificado
automaticamente, nem quando o CPF coincide — unificar dois pacientes errados
mistura o histórico clínico de duas pessoas, e desfazer isso é muito pior do que
revisar uma fila.
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from models.duplicata import CandidatoDuplicata
from models.paciente import Paciente
from services import deduplicacao
from utils.audit import registrar
from utils.rbac import requer_permissao

duplicatas_bp = Blueprint("duplicatas", __name__, url_prefix="/pacientes/duplicatas")

# Campos comparados lado a lado na tela de revisão.
CAMPOS_COMPARACAO = (
    ("nome", "Nome"),
    ("nome_social", "Nome social"),
    ("data_nascimento", "Nascimento"),
    ("sexo", "Sexo"),
    ("cpf", "CPF"),
    ("cns", "CNS"),
    ("nome_mae", "Nome da mãe"),
    ("telefone", "Telefone"),
    ("municipio", "Município"),
    ("uf", "UF"),
)


@duplicatas_bp.get("/")
@login_required
@requer_permissao("patient:update")
def index():
    status = (request.args.get("status") or "pendente").strip()

    consulta = CandidatoDuplicata.query
    if status in ("pendente", "unificado", "distintos"):
        consulta = consulta.filter(CandidatoDuplicata.status == status)

    candidatos = (consulta
                  .order_by(CandidatoDuplicata.score.desc(),
                            CandidatoDuplicata.detectado_em.desc())
                  .limit(200).all())

    contagens = dict(
        db.session.query(CandidatoDuplicata.status,
                         func.count(CandidatoDuplicata.id))
        .group_by(CandidatoDuplicata.status).all()
    )

    return render_template("duplicatas/index.html",
                           candidatos=candidatos, contagens=contagens,
                           status=status)


@duplicatas_bp.get("/<int:id>")
@login_required
@requer_permissao("patient:update")
def revisar(id):
    """Lado a lado dos dois cadastros, com o volume clínico de cada um.

    O volume é o que mais pesa na escolha de quem sobrevive: absorver o cadastro
    com menos histórico move menos registro e erra menos.
    """
    candidato = CandidatoDuplicata.query.get_or_404(id)

    def volume(paciente_id):
        return {
            nome: db.session.execute(
                db.select(func.count()).select_from(tabela)
                .where(coluna == paciente_id)).scalar()
            for tabela, coluna, nome in _tabelas_clinicas()
        }

    return render_template(
        "duplicatas/revisar.html",
        candidato=candidato,
        campos=CAMPOS_COMPARACAO,
        volume_menor=volume(candidato.paciente_menor_id),
        volume_maior=volume(candidato.paciente_maior_id),
    )


def _tabelas_clinicas():
    """Tabelas cujo volume ajuda a decidir qual cadastro preservar."""
    interessantes = {
        "prontuarios": "Prontuários",
        "atendimentos": "Atendimentos",
        "internacoes": "Internações",
        "exames_solicitados": "Exames",
        "prescricoes": "Prescrições",
        "agendamentos": "Agendamentos",
    }
    saida = []
    for tabela in db.metadata.sorted_tables:
        if tabela.name not in interessantes:
            continue
        coluna = tabela.columns.get("paciente_id")
        if coluna is not None:
            saida.append((tabela, coluna, interessantes[tabela.name]))
    return saida


@duplicatas_bp.post("/<int:id>/unificar")
@login_required
@requer_permissao("patient:update")
def unificar(id):
    candidato = CandidatoDuplicata.query.get_or_404(id)
    sobrevivente_id = request.form.get("sobrevivente_id", type=int)

    validos = {candidato.paciente_menor_id, candidato.paciente_maior_id}
    if sobrevivente_id not in validos:
        flash("Escolha qual cadastro deve ser preservado.", "warning")
        return redirect(url_for("duplicatas.revisar", id=id))

    absorvido_id = (validos - {sobrevivente_id}).pop()
    sobrevivente = Paciente.query.get_or_404(sobrevivente_id)
    absorvido = Paciente.query.get_or_404(absorvido_id)

    try:
        resumo = deduplicacao.unificar(sobrevivente, absorvido,
                                       usuario_id=current_user.id)
    except ValueError as erro:
        db.session.rollback()
        flash(str(erro), "danger")
        return redirect(url_for("duplicatas.revisar", id=id))

    total = sum(resumo["registros_movidos"].values())
    registrar("pacientes", sobrevivente.id, "update",
              f"Unificação: paciente #{absorvido.id} absorvido por "
              f"#{sobrevivente.id}; {total} registro(s) movido(s); "
              f"campos herdados: {', '.join(resumo['campos_herdados']) or 'nenhum'}")
    db.session.commit()

    flash(f"Cadastros unificados: {total} registro(s) movido(s) para "
          f"{sobrevivente.nome_exibicao}.", "success")
    return redirect(url_for("duplicatas.index"))


@duplicatas_bp.post("/<int:id>/distintos")
@login_required
@requer_permissao("patient:update")
def distintos(id):
    candidato = CandidatoDuplicata.query.get_or_404(id)
    deduplicacao.marcar_distintos(candidato, usuario_id=current_user.id)
    registrar("candidatos_duplicata", candidato.id, "update",
              "Par revisado: pessoas distintas")
    db.session.commit()

    flash("Registrado como pessoas distintas. O par não volta à fila.", "success")
    return redirect(url_for("duplicatas.index"))


@duplicatas_bp.post("/varrer")
@login_required
@requer_permissao("patient:update")
def varrer():
    analisados, novos = deduplicacao.varrer()
    flash(f"Varredura concluída: {analisados} par(es) analisado(s), "
          f"{novos} novo(s) candidato(s).", "success")
    return redirect(url_for("duplicatas.index"))
