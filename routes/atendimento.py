# -*- coding: utf-8 -*-
"""Atendimentos ambulatoriais — consultas e evolução clínica."""
from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from extensions import db
from models.atendimento import Atendimento
from models.medico import Medico
from models.paciente import Paciente
from models.prontuario import Prontuario
from utils.audit import registrar
from utils.rbac import requer_permissao

atendimento_bp = Blueprint("atendimento", __name__)


@atendimento_bp.get("/atendimentos")
@login_required
@requer_permissao("clinical:read", "clinical:write")
def index():
    termo = (request.args.get("q") or "").strip()
    pagina = request.args.get("pagina", type=int) or 1

    query = Atendimento.query
    if termo:
        like = f"%{termo}%"
        query = query.join(Paciente, Atendimento.paciente_id == Paciente.id).filter(
            Paciente.nome.ilike(like) | Paciente.cpf.ilike(like) | Paciente.cns.ilike(like)
        )

    paginacao = (
        query.order_by(Atendimento.data_hora.desc())
        .paginate(page=pagina, per_page=30, error_out=False)
    )

    ids_pac = {a.paciente_id for a in paginacao.items}
    pacientes = (
        {p.id: p for p in Paciente.query.filter(Paciente.id.in_(ids_pac)).all()}
        if ids_pac else {}
    )

    ids_med = {a.medico_id for a in paginacao.items if a.medico_id}
    medicos = (
        {m.id: m for m in Medico.query.filter(Medico.id.in_(ids_med)).all()}
        if ids_med else {}
    )

    # Prontuário vinculado, para saber se o atendimento já foi documentado.
    ids_at = [a.id for a in paginacao.items]
    prontuarios = {}
    if ids_at:
        prontuarios = {
            pr.atendimento_id: pr
            for pr in Prontuario.query.filter(Prontuario.atendimento_id.in_(ids_at)).all()
        }

    return render_template(
        "atendimento/index.html",
        paginacao=paginacao,
        atendimentos=paginacao.items,
        pacientes=pacientes,
        medicos=medicos,
        prontuarios=prontuarios,
        termo=termo,
    )


@atendimento_bp.post("/atendimento")
@login_required
@requer_permissao("clinical:write")
def criar_atendimento():
    dados = request.get_json(silent=True) or request.form
    if not dados:
        return jsonify({"erro": "corpo vazio"}), 400

    paciente_id = dados.get("paciente_id")
    if not paciente_id:
        return jsonify({"erro": "paciente_id é obrigatório"}), 400
    if not Paciente.query.get(paciente_id):
        return jsonify({"erro": "paciente não encontrado"}), 404

    # O campo do model é `data_hora`; `data` não existe e levantava TypeError.
    quando = dados.get("data_hora") or dados.get("data")
    try:
        data_hora = datetime.fromisoformat(quando) if quando else datetime.utcnow()
    except (TypeError, ValueError):
        return jsonify({"erro": "data_hora inválida (use ISO 8601)"}), 400

    atendimento = Atendimento(
        paciente_id=paciente_id,
        medico_id=dados.get("medico_id"),
        data_hora=data_hora,
        tipo=(dados.get("tipo") or "consulta"),
    )
    db.session.add(atendimento)
    db.session.flush()

    registrar("atendimentos", atendimento.id, "create",
              f"Atendimento criado para paciente #{paciente_id}")
    db.session.commit()

    return jsonify({"id": atendimento.id, "msg": "Atendimento criado"}), 201
