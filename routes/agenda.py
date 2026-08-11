from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required

from database.db import db
from models.agenda_evento import AgendaEvento  # crie este model (abaixo)
from utils.rbac import requer_permissao

agenda_bp = Blueprint("agenda", __name__, url_prefix="/agenda")


@agenda_bp.route("/", methods=["GET"])
@login_required
def index():
    return render_template("agenda/index.html")


@agenda_bp.route("/api/eventos", methods=["GET"])
@login_required
def api_listar_eventos():
    data = request.args.get("data")
    status = request.args.get("status")
    paciente = request.args.get("paciente", "").strip()

    q = AgendaEvento.query.filter(AgendaEvento.ativo == True)

    if data:
        q = q.filter(AgendaEvento.data == data)
    if status:
        q = q.filter(AgendaEvento.status == status)
    if paciente:
        q = q.filter(AgendaEvento.paciente_nome.ilike(f"%{paciente}%"))

    eventos = q.order_by(AgendaEvento.data.asc(), AgendaEvento.hora.asc()).all()

    return jsonify(
        [
            {
                "id": e.id,
                "paciente_nome": e.paciente_nome,
                "data": e.data,
                "hora": e.hora,
                "tipo": e.tipo,
                "status": e.status,
                "observacao": e.observacao,
                "ativo": e.ativo,
            }
            for e in eventos
        ]
    )


@agenda_bp.route("/api/eventos", methods=["POST"])
@login_required
@requer_permissao("schedule:write")
def api_criar_evento():
    data = request.get_json(silent=True) or request.form

    paciente_nome = (data.get("paciente_nome") or "").strip()
    data_evento = (data.get("data") or "").strip()
    hora = (data.get("hora") or "").strip()
    tipo = (data.get("tipo") or "consulta").strip()
    observacao = (data.get("observacao") or "").strip()
    status = (data.get("status") or "agendado").strip()

    if not paciente_nome:
        return (
            jsonify({"ok": False, "erro": "Campo 'paciente_nome' é obrigatório."}),
            400,
        )
    if not data_evento:
        return jsonify({"ok": False, "erro": "Campo 'data' é obrigatório."}), 400
    if not hora:
        return jsonify({"ok": False, "erro": "Campo 'hora' é obrigatório."}), 400

    permitidos = {"agendado", "confirmado", "em_atendimento", "finalizado", "cancelado"}
    if status not in permitidos:
        status = "agendado"

    try:
        ev = AgendaEvento(
            paciente_nome=paciente_nome,
            data=data_evento,
            hora=hora,
            tipo=tipo,
            status=status,
            observacao=observacao,
            ativo=True,
        )
        db.session.add(ev)
        db.session.commit()
        return (
            jsonify(
                {"ok": True, "id": ev.id, "msg": "Compromisso criado com sucesso."}
            ),
            201,
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "erro": str(e)}), 400


@agenda_bp.route("/api/eventos/<int:evento_id>/status", methods=["POST"])
@login_required
@requer_permissao("schedule:write")
def api_status_evento(evento_id):
    data = request.get_json(silent=True) or request.form
    status = (data.get("status") or "").strip()

    permitidos = {"agendado", "confirmado", "em_atendimento", "finalizado", "cancelado"}
    if status not in permitidos:
        return jsonify({"ok": False, "erro": "Status inválido."}), 400

    ev = AgendaEvento.query.get_or_404(evento_id)

    try:
        ev.status = status
        db.session.commit()
        return jsonify({"ok": True, "msg": "Status atualizado com sucesso."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "erro": str(e)}), 400
