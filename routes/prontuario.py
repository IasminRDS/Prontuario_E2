from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from database.db import db
from models.prontuario import Prontuario
from models.paciente import Paciente
from models.medico import Medico
from utils.security import validar_cid10, pode_acessar_prontuario, pode_acessar_paciente
from utils.audit import audit_log, auditar_aqui
from utils.audit import log_auditoria

prontuario_bp = Blueprint("prontuario", __name__, url_prefix="/prontuarios")

def to_dict(p):
    return {
        "id": p.id,
        "paciente_id": p.paciente_id,
        "atendimento_id": p.atendimento_id,
        "medico_id": p.medico_id,
        "unidade_id": p.unidade_id,
        "subjetivo": p.subjetivo,
        "objetivo": p.objetivo,
        "avaliacao": p.avaliacao,
        "plano": p.plano,
        "pressao_arterial": p.pressao_arterial,
        "temperatura": p.temperatura,
        "frequencia_cardiaca": p.frequencia_cardiaca,
        "frequencia_respiratoria": p.frequencia_respiratoria,
        "saturacao_o2": p.saturacao_o2,
        "peso": p.peso,
        "altura": p.altura,
        "glicemia": p.glicemia,
        "cid_principal": p.cid_principal,
        "cid_secundario": p.cid_secundario,
        "prescricao": p.prescricao,
        "encaminhamento": p.encaminhamento,
        "retorno_dias": p.retorno_dias,
        "assinado": p.assinado,
        "assinado_em": p.assinado_em.isoformat() if p.assinado_em else None,
        "criado_em": p.criado_em.isoformat() if p.criado_em else None,
        "atualizado_em": p.atualizado_em.isoformat() if p.atualizado_em else None,
    }


def _query_prontuario_escopo():
    q = Prontuario.query

    if current_user.perfil == "admin":
        return q

    if current_user.unidade_id:
        q = q.filter(Prontuario.unidade_id == current_user.unidade_id)
    else:
        q = q.filter(Prontuario.id == -1)

    return q


@prontuario_bp.get("/")
@login_required
def listar_prontuarios():
    q = _query_prontuario_escopo()

    paciente_id = request.args.get("paciente_id", type=int)
    cid = (request.args.get("cid") or "").strip().upper()

    if paciente_id:
        q = q.filter(Prontuario.paciente_id == paciente_id)
    if cid:
        q = q.filter(
            (Prontuario.cid_principal == cid) | (Prontuario.cid_secundario == cid)
        )

    itens = q.order_by(Prontuario.criado_em.desc()).all()

    auditar_aqui("prontuarios", "list")

    return (
        jsonify(
            [
                {
                    "id": p.id,
                    "paciente_id": p.paciente_id,
                    "atendimento_id": p.atendimento_id,
                    "medico_id": p.medico_id,
                    "unidade_id": p.unidade_id,
                    "subjetivo": p.subjetivo,
                    "objetivo": p.objetivo,
                    "avaliacao": p.avaliacao,
                    "plano": p.plano,
                    "cid_principal": p.cid_principal,
                    "cid_secundario": p.cid_secundario,
                    "assinado": p.assinado,
                    "assinado_em": p.assinado_em.isoformat() if p.assinado_em else None,
                    "criado_em": p.criado_em.isoformat() if p.criado_em else None,
                }
                for p in itens
            ]
        ),
        200,
    )


@prontuario_bp.get("/<int:prontuario_id>")
@login_required
@log_auditoria("prontuarios", "view")
def obter_prontuario(prontuario_id):
    p = Prontuario.query.get_or_404(prontuario_id)
    if not pode_acessar_prontuario(p, current_user):
        return jsonify({"erro": "Sem permissão"}), 403
    
    return jsonify(to_dict(p)), 200

    return (
        jsonify(
            {
                "id": p.id,
                "paciente_id": p.paciente_id,
                "atendimento_id": p.atendimento_id,
                "medico_id": p.medico_id,
                "unidade_id": p.unidade_id,
                "subjetivo": p.subjetivo,
                "objetivo": p.objetivo,
                "avaliacao": p.avaliacao,
                "plano": p.plano,
                "pressao_arterial": p.pressao_arterial,
                "temperatura": p.temperatura,
                "frequencia_cardiaca": p.frequencia_cardiaca,
                "frequencia_respiratoria": p.frequencia_respiratoria,
                "saturacao_o2": p.saturacao_o2,
                "peso": p.peso,
                "altura": p.altura,
                "glicemia": p.glicemia,
                "cid_principal": p.cid_principal,
                "cid_secundario": p.cid_secundario,
                "prescricao": p.prescricao,
                "encaminhamento": p.encaminhamento,
                "retorno_dias": p.retorno_dias,
                "assinado": p.assinado,
                "assinado_em": p.assinado_em.isoformat() if p.assinado_em else None,
                "criado_em": p.criado_em.isoformat() if p.criado_em else None,
                "atualizado_em": (
                    p.atualizado_em.isoformat() if p.atualizado_em else None
                ),
            }
        ),
        200,
    )


@prontuario_bp.post("/")
@login_required
@audit_log(acao_default="create", tabela_default="prontuarios")
def criar_prontuario():
    data = request.get_json(silent=True) or {}

    paciente_id = data.get("paciente_id")
    if not paciente_id:
        return jsonify({"erro": "paciente_id é obrigatório"}), 400

    paciente = Paciente.query.get(paciente_id)
    if not paciente:
        return jsonify({"erro": "Paciente não encontrado"}), 404

    if not pode_acessar_paciente(paciente, current_user):
        return (
            jsonify({"erro": "Sem permissão para criar prontuário para este paciente"}),
            403,
        )

    cid_principal = (data.get("cid_principal") or "").strip().upper()
    cid_secundario = (data.get("cid_secundario") or "").strip().upper()

    if cid_principal and not validar_cid10(cid_principal):
        return jsonify({"erro": "CID principal inválido"}), 400
    if cid_secundario and not validar_cid10(cid_secundario):
        return jsonify({"erro": "CID secundário inválido"}), 400

    medico_id = data.get("medico_id")
    if current_user.perfil == "medico":
        # tenta vincular automaticamente ao medico do usuário logado
        m = Medico.query.filter_by(user_id=current_user.id).first()
        if m:
            medico_id = m.id

    novo = Prontuario(
        paciente_id=paciente_id,
        atendimento_id=data.get("atendimento_id"),
        medico_id=medico_id,
        unidade_id=current_user.unidade_id,  # trava na unidade do usuário
        subjetivo=data.get("subjetivo"),
        objetivo=data.get("objetivo"),
        avaliacao=data.get("avaliacao"),
        plano=data.get("plano"),
        pressao_arterial=data.get("pressao_arterial"),
        temperatura=data.get("temperatura"),
        frequencia_cardiaca=data.get("frequencia_cardiaca"),
        frequencia_respiratoria=data.get("frequencia_respiratoria"),
        saturacao_o2=data.get("saturacao_o2"),
        peso=data.get("peso"),
        altura=data.get("altura"),
        glicemia=data.get("glicemia"),
        cid_principal=cid_principal or None,
        cid_secundario=cid_secundario or None,
        prescricao=data.get("prescricao"),
        encaminhamento=data.get("encaminhamento"),
        retorno_dias=data.get("retorno_dias"),
    )

    db.session.add(novo)
    db.session.commit()

    auditar_aqui("prontuarios", "create")

    return jsonify({"mensagem": "Prontuário criado com sucesso", "id": novo.id}), 201


@prontuario_bp.put("/<int:prontuario_id>")
@login_required
@audit_log(acao_default="update", tabela_default="prontuarios")
def atualizar_prontuario(prontuario_id):
    p = Prontuario.query.get_or_404(prontuario_id)

    if not pode_acessar_prontuario(p, current_user):
        return jsonify({"erro": "Sem permissão para editar este prontuário"}), 403

    if p.assinado and current_user.perfil != "admin":
        return jsonify({"erro": "Prontuário assinado não pode ser editado"}), 409

    data = request.get_json(silent=True) or {}

    cid_principal = (data.get("cid_principal", p.cid_principal) or "").strip().upper()
    cid_secundario = (
        (data.get("cid_secundario", p.cid_secundario) or "").strip().upper()
    )

    if cid_principal and not validar_cid10(cid_principal):
        return jsonify({"erro": "CID principal inválido"}), 400
    if cid_secundario and not validar_cid10(cid_secundario):
        return jsonify({"erro": "CID secundário inválido"}), 400

    p.subjetivo = data.get("subjetivo", p.subjetivo)
    p.objetivo = data.get("objetivo", p.objetivo)
    p.avaliacao = data.get("avaliacao", p.avaliacao)
    p.plano = data.get("plano", p.plano)
    p.pressao_arterial = data.get("pressao_arterial", p.pressao_arterial)
    p.temperatura = data.get("temperatura", p.temperatura)
    p.frequencia_cardiaca = data.get("frequencia_cardiaca", p.frequencia_cardiaca)
    p.frequencia_respiratoria = data.get(
        "frequencia_respiratoria", p.frequencia_respiratoria
    )
    p.saturacao_o2 = data.get("saturacao_o2", p.saturacao_o2)
    p.peso = data.get("peso", p.peso)
    p.altura = data.get("altura", p.altura)
    p.glicemia = data.get("glicemia", p.glicemia)
    p.cid_principal = cid_principal or None
    p.cid_secundario = cid_secundario or None
    p.prescricao = data.get("prescricao", p.prescricao)
    p.encaminhamento = data.get("encaminhamento", p.encaminhamento)
    p.retorno_dias = data.get("retorno_dias", p.retorno_dias)

    db.session.commit()

    auditar_aqui("prontuarios", "update")

    return jsonify({"mensagem": "Prontuário atualizado com sucesso"}), 200


@prontuario_bp.post("/<int:prontuario_id>/assinar")
@login_required
@audit_log(acao_default="sign", tabela_default="prontuarios")
def assinar_prontuario(prontuario_id):
    p = Prontuario.query.get_or_404(prontuario_id)

    if not pode_acessar_prontuario(p, current_user):
        return jsonify({"erro": "Sem permissão para assinar este prontuário"}), 403

    if current_user.perfil not in ("medico", "admin"):
        return jsonify({"erro": "Apenas médico/admin pode assinar prontuário"}), 403

    if p.assinado:
        return jsonify({"mensagem": "Prontuário já estava assinado"}), 200

    p.assinar()
    db.session.commit()

    auditar_aqui("prontuarios", "sign")

    return jsonify({"mensagem": "Prontuário assinado com sucesso"}), 200


@prontuario_bp.delete("/<int:prontuario_id>")
@login_required
@audit_log(acao_default="delete", tabela_default="prontuarios")
def excluir_prontuario(prontuario_id):
    if current_user.perfil != "admin":
        return jsonify({"erro": "Apenas admin pode excluir prontuário"}), 403

    p = Prontuario.query.get_or_404(prontuario_id)
    db.session.delete(p)
    db.session.commit()

    auditar_aqui("prontuarios", "delete")

    return jsonify({"mensagem": "Prontuário excluído com sucesso"}), 200
