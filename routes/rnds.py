# -*- coding: utf-8 -*-
"""Integrações RNDS — envio de registros clínicos em FHIR R4.

Porte de `modules/rnds` + `infra/fhir` do backend NestJS. Os mappers convertem os
models locais em recursos FHIR (Patient, Encounter, MedicationRequest,
Observation, Immunization).

O envio real depende de certificado ICP-Brasil e credenciais do DATASUS. Aqui o
despacho é SIMULADO — o payload é montado, validado e persistido em
`envios_rnds`, com protocolo sintético. A troca para o cliente real é isolada em
`_despachar`.
"""
import json
import uuid
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from models.lgpd import EnvioRnds
from models.paciente import Paciente
from models.prontuario import Prontuario
from utils.audit import registrar
from utils.rbac import requer_permissao
from utils.terminologias import descricao_cid

rnds_bp = Blueprint("rnds", __name__, url_prefix="/rnds")

TIPOS = ("Patient", "Encounter", "Observation")
SISTEMA_CNS = "https://saude.gov.br/sid/cns"
SISTEMA_CPF = "https://saude.gov.br/fhir/sid/cpf"
SISTEMA_CID = "http://hl7.org/fhir/sid/icd-10"


# --------------------------------------------------------------------------
# Mappers FHIR R4
# --------------------------------------------------------------------------

def _map_patient(paciente):
    identificadores = []
    if paciente.cns:
        identificadores.append({"system": SISTEMA_CNS, "value": paciente.cns})
    if paciente.cpf:
        identificadores.append({
            "system": SISTEMA_CPF,
            "value": "".join(c for c in paciente.cpf if c.isdigit()),
        })

    sexo = {"M": "male", "F": "female"}.get((paciente.sexo or "").upper(), "unknown")

    recurso = {
        "resourceType": "Patient",
        "identifier": identificadores,
        "active": bool(paciente.ativo),
        "name": [{"use": "official", "text": paciente.nome}],
        "gender": sexo,
    }
    if paciente.data_nascimento:
        recurso["birthDate"] = paciente.data_nascimento.isoformat()
    if paciente.nome_mae:
        recurso["extension"] = [{
            "url": "http://www.saude.gov.br/fhir/r4/StructureDefinition/BRNomeMae-1.0",
            "valueString": paciente.nome_mae,
        }]
    if paciente.municipio or paciente.uf:
        recurso["address"] = [{
            "city": paciente.municipio,
            "state": paciente.uf,
            "postalCode": paciente.cep,
            "country": "BR",
        }]
    return recurso


def _map_encounter(prontuario):
    recurso = {
        "resourceType": "Encounter",
        "status": "finished" if prontuario.assinado else "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
        "subject": {"reference": f"Patient/{prontuario.paciente_id}"},
    }
    if prontuario.criado_em:
        recurso["period"] = {"start": prontuario.criado_em.isoformat()}
    if prontuario.cid_principal:
        recurso["diagnosis"] = [{
            "condition": {
                "coding": [{
                    "system": SISTEMA_CID,
                    "code": prontuario.cid_principal,
                    "display": descricao_cid(prontuario.cid_principal) or "",
                }]
            },
            "rank": 1,
        }]
    return recurso


def _map_observation(prontuario):
    """Sinais vitais do prontuário como um Observation com componentes."""
    sinais = (
        ("8480-6", "Pressão arterial", prontuario.pressao_arterial, None),
        ("8310-5", "Temperatura corporal", prontuario.temperatura, "Cel"),
        ("8867-4", "Frequência cardíaca", prontuario.frequencia_cardiaca, "/min"),
        ("9279-1", "Frequência respiratória", prontuario.frequencia_respiratoria, "/min"),
        ("59408-5", "Saturação de O2", prontuario.saturacao_o2, "%"),
        ("29463-7", "Peso corporal", prontuario.peso, "kg"),
        ("8302-2", "Altura", prontuario.altura, "cm"),
        ("2339-0", "Glicemia", prontuario.glicemia, "mg/dL"),
    )

    componentes = []
    for codigo, nome, valor, unidade in sinais:
        if valor in (None, ""):
            continue
        item = {"code": {"coding": [{"system": "http://loinc.org", "code": codigo, "display": nome}]}}
        if unidade:
            item["valueQuantity"] = {"value": float(valor), "unit": unidade}
        else:
            item["valueString"] = str(valor)
        componentes.append(item)

    if not componentes:
        return None

    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "vital-signs",
        }]}],
        "subject": {"reference": f"Patient/{prontuario.paciente_id}"},
        "effectiveDateTime": (prontuario.criado_em or datetime.utcnow()).isoformat(),
        "component": componentes,
    }


def _montar(tipo, entity_id):
    """Devolve (recurso_fhir, tabela, paciente_id) ou (None, None, None)."""
    if tipo == "Patient":
        p = Paciente.query.get(entity_id)
        return (_map_patient(p), "pacientes", p.id) if p else (None, None, None)

    pr = Prontuario.query.get(entity_id)
    if not pr:
        return None, None, None
    if tipo == "Encounter":
        return _map_encounter(pr), "prontuarios", pr.paciente_id
    if tipo == "Observation":
        return _map_observation(pr), "prontuarios", pr.paciente_id
    return None, None, None


def _despachar(_recurso):
    """Ponto único de troca para o cliente RNDS real.

    Hoje devolve um protocolo sintético. Ao integrar de verdade, é aqui que
    entram o mTLS com certificado ICP-Brasil e o POST ao endpoint do DATASUS.
    """
    return f"SIM-{uuid.uuid4().hex[:16].upper()}"


# --------------------------------------------------------------------------
# Rotas
# --------------------------------------------------------------------------

@rnds_bp.get("/")
@login_required
@requer_permissao("reports:read")
def index():
    status = (request.args.get("status") or "").strip()

    query = EnvioRnds.query
    if status in ("pendente", "enviado", "erro"):
        query = query.filter(EnvioRnds.status == status)

    envios = query.order_by(EnvioRnds.criado_em.desc()).limit(200).all()

    contagens = dict(
        db.session.query(EnvioRnds.status, func.count(EnvioRnds.id))
        .group_by(EnvioRnds.status)
        .all()
    )

    return render_template(
        "rnds/index.html",
        envios=envios,
        contagens=contagens,
        status=status,
        tipos=TIPOS,
    )


@rnds_bp.get("/preview/<tipo>/<int:entity_id>")
@login_required
@requer_permissao("reports:read")
def preview(tipo, entity_id):
    """Mostra o JSON FHIR que seria enviado, sem enviar."""
    if tipo not in TIPOS:
        flash("Tipo de recurso não suportado.", "danger")
        return redirect(url_for("rnds.index"))

    recurso, _tabela, _pid = _montar(tipo, entity_id)
    if not recurso:
        flash("Registro não encontrado ou sem dados suficientes para o recurso.", "warning")
        return redirect(url_for("rnds.index"))

    return render_template(
        "rnds/preview.html",
        tipo=tipo,
        entity_id=entity_id,
        payload=json.dumps(recurso, indent=2, ensure_ascii=False),
    )


@rnds_bp.post("/enviar")
@login_required
@requer_permissao("reports:read")
def enviar():
    tipo = (request.form.get("tipo") or "").strip()
    entity_id = request.form.get("entity_id", type=int)

    if tipo not in TIPOS or not entity_id:
        flash("Informe o tipo de recurso e o identificador.", "warning")
        return redirect(url_for("rnds.index"))

    recurso, tabela, paciente_id = _montar(tipo, entity_id)
    if not recurso:
        flash("Registro não encontrado ou sem dados suficientes.", "warning")
        return redirect(url_for("rnds.index"))

    envio = EnvioRnds(
        tipo=tipo,
        entidade_tabela=tabela,
        entidade_id=entity_id,
        paciente_id=paciente_id,
        payload=json.dumps(recurso, ensure_ascii=False),
        criado_por=current_user.id,
        tentativas=1,
    )

    try:
        envio.protocolo = _despachar(recurso)
        envio.status = "enviado"
        envio.enviado_em = datetime.utcnow()
        mensagem = f"{tipo} enviado à RNDS — protocolo {envio.protocolo}."
        categoria = "success"
    except Exception as exc:  # noqa: BLE001 — qualquer falha de transporte
        envio.status = "erro"
        envio.erro = str(exc)
        mensagem = f"Falha no envio: {exc}"
        categoria = "danger"

    db.session.add(envio)
    registrar("envios_rnds", entity_id, "create",
              f"Envio RNDS de {tipo}#{entity_id}: {envio.status}")
    db.session.commit()

    flash(mensagem, categoria)
    return redirect(url_for("rnds.index"))


@rnds_bp.post("/envios/<int:id>/reenviar")
@login_required
@requer_permissao("reports:read")
def reenviar(id):
    envio = EnvioRnds.query.get_or_404(id)

    recurso, _t, _p = _montar(envio.tipo, envio.entidade_id)
    if not recurso:
        flash("O registro de origem não existe mais.", "warning")
        return redirect(url_for("rnds.index"))

    envio.tentativas = (envio.tentativas or 0) + 1
    envio.payload = json.dumps(recurso, ensure_ascii=False)

    try:
        envio.protocolo = _despachar(recurso)
        envio.status = "enviado"
        envio.enviado_em = datetime.utcnow()
        envio.erro = None
        flash(f"Reenviado — protocolo {envio.protocolo}.", "success")
    except Exception as exc:  # noqa: BLE001
        envio.status = "erro"
        envio.erro = str(exc)
        flash(f"Reenvio falhou: {exc}", "danger")

    registrar("envios_rnds", envio.id, "update",
              f"Reenvio RNDS (tentativa {envio.tentativas}): {envio.status}")
    db.session.commit()

    return redirect(url_for("rnds.index"))
