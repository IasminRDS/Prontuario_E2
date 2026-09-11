# -*- coding: utf-8 -*-
"""Integrações RNDS — envio de registros clínicos em FHIR R4.

Porte de `modules/rnds` + `infra/fhir` do backend NestJS. Os mappers convertem os
models locais em três recursos FHIR: Patient, Encounter e Observation. É o que
`TIPOS` declara e o que `_montar` sabe construir — MedicationRequest e
Immunization ainda não existem aqui, e a lista acima já esteve dizendo que sim.

Um prontuário rende VÁRIOS Observation, não um só: `Observation.code` é
obrigatório e identifica UMA grandeza, então temperatura, frequência cardíaca e
pressão arterial não cabem no mesmo recurso.

A tela **enfileira**; quem envia é `services.rnds_fila.processar`, chamado pelo
comando `flask rnds-processar` (cron) ou pelo botão "Processar fila". Manter o
POST fora da requisição é o que garante que uma indisponibilidade momentânea da
RNDS não vire registro clínico perdido.

Sem certificado ICP-Brasil configurado, `services.rnds_cliente` entrega um
cliente simulado, que devolve protocolo prefixado com `SIM-`. O ambiente de
demonstração continua funcionando sem fingir que houve envio de verdade.
"""
import json
import re
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from models.lgpd import EnvioRnds
from models.paciente import Paciente
from models.prontuario import Prontuario
from services import rnds_cliente, rnds_fila
from utils.audit import registrar
from utils.rbac import requer_permissao
from utils.terminologias import descricao_cid

rnds_bp = Blueprint("rnds", __name__, url_prefix="/rnds")

TIPOS = ("Patient", "Encounter", "Observation")
# Identificadores e perfis conferidos no guia publicado (rnds-fhir.saude.gov.br),
# um a um, nas representações JSON dos próprios recursos. As duas famílias de URL
# abaixo NÃO são um descuido: os NamingSystem são publicados sob
# `http://rnds.saude.gov.br/fhir/r4/`, e os perfis sob
# `https://rnds-fhir.saude.gov.br/`. URL canônica é identificador opaco, não
# endereço — uniformizar as duas quebraria a correspondência.
SISTEMA_CNS = "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cns"
SISTEMA_CPF = "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cpf"
PERFIL_INDIVIDUO = "https://rnds-fhir.saude.gov.br/StructureDefinition/BRIndividuo-1.0"
EXTENSAO_PARENTES = ("https://rnds-fhir.saude.gov.br/StructureDefinition/"
                     "BRParentesIndividuo-1.0")

# A RNDS não publica perfil de Encounter nem de sinal vital — o modelo
# computacional do RAC ainda está em construção no guia. Onde ela não define,
# vale o perfil básico do próprio HL7, que existe e é verificável; inventar uma
# URL sob o domínio do Ministério seria pior que não declarar nada.
PERFIL_SINAL_VITAL = "http://hl7.org/fhir/StructureDefinition/vitalsigns"
PERFIL_PRESSAO = "http://hl7.org/fhir/StructureDefinition/bp"

SISTEMA_CID = "http://hl7.org/fhir/sid/icd-10"

# O Condition do diagnóstico vai contido no Encounter; `BRCondicaoSaude` NÃO
# serve aqui: ela exige `stage.assessment` apontando para diagnóstico de
# laboratório e liga o `code` a uma terminologia de suspeita diagnóstica. É
# perfil do documento de exame, não de diagnóstico clínico.
ID_DIAGNOSTICO = "diagnostico-principal"
SISTEMA_LOINC = "http://loinc.org"
SISTEMA_UCUM = "http://unitsofmeasure.org"
SISTEMA_CATEGORIA = "http://terminology.hl7.org/CodeSystem/observation-category"

# Uma grandeza por Observation: (código LOINC, rótulo, atributo, unidade UCUM,
# categoria). A categoria não é decoração - glicemia é exame de laboratório, e
# anunciá-la como sinal vital faz o receptor arquivá-la no lugar errado.
SINAIS_VITAIS = (
    ("8310-5", "Temperatura corporal", "temperatura", "Cel", "vital-signs"),
    ("8867-4", "Frequência cardíaca", "frequencia_cardiaca", "/min", "vital-signs"),
    ("9279-1", "Frequência respiratória", "frequencia_respiratoria", "/min", "vital-signs"),
    ("59408-5", "Saturação de O2 por oximetria de pulso", "saturacao_o2", "%", "vital-signs"),
    ("29463-7", "Peso corporal", "peso", "kg", "vital-signs"),
    ("8302-2", "Altura", "altura", "m", "vital-signs"),
    ("2339-0", "Glicemia", "glicemia", "mg/dL", "laboratory"),
)

# "120/80", "120 x 80". Duas grandezas escritas num campo de texto, que é como o
# prontuário de papel registra e como a tela captura.
PRESSAO = re.compile(r"^\s*(\d{2,3})\s*[/xX]\s*(\d{2,3})\s*$")


# --------------------------------------------------------------------------
# Mappers FHIR R4
# --------------------------------------------------------------------------

def _digitos(valor):
    return "".join(c for c in (valor or "") if c.isdigit())


def _instante(momento):
    """`dateTime` do FHIR com fuso, que a especificação exige quando há hora.

    `isoformat()` sozinho devolve "2026-03-04T10:30:00", sem fuso, e isso NÃO é
    um dateTime válido — o validador reprova. As colunas do sistema são gravadas
    com `datetime.utcnow()`, então o instante já está em UTC e o que falta é
    dizê-lo. Foi o validador que achou isto; nenhum teste anterior acusava.
    """
    return (momento or datetime.utcnow()).replace(microsecond=0).isoformat() + "Z"


def _referencia_paciente(paciente):
    """Como um recurso clínico aponta para o paciente.

    O id da tabela local não significa nada do outro lado: `Patient/37` é o
    trigésimo sétimo cadastro DESTE banco, e a RNDS não tem como resolvê-lo.
    Havendo documento oficial, a referência vai por identificador nacional.
    Sem CNS nem CPF sobra a referência local, que serve para inspeção mas não
    estabelece vínculo — e por isso ela é o último recurso.
    """
    if paciente is None:
        return None
    if paciente.cns:
        return {"identifier": {"system": SISTEMA_CNS, "value": paciente.cns}}
    if paciente.cpf:
        return {"identifier": {"system": SISTEMA_CPF, "value": _digitos(paciente.cpf)}}
    return {"reference": f"Patient/{paciente.id}"}


def _map_endereco(paciente):
    """Endereço no formato BREndereco-1.0, ou None.

    Três exigências do perfil que o mapeamento anterior contrariava: município e
    UF não vão por nome, vão por CÓDIGO; `country` é 0..0, ou seja, PROIBIDO — e
    a versão anterior mandava "BR"; e os três campos são 1..1.

    O código do município tem SEIS dígitos aqui. O de sete que o sistema guarda
    traz o dígito verificador, que o value set da RNDS não usa. A UF sai dos dois
    primeiros dígitos do mesmo código, como número e não como sigla.

    Faltando qualquer um dos três, o endereço inteiro fica de fora: endereço
    incompleto não passa na validação e derruba o recurso todo junto.
    """
    ibge = _digitos(getattr(paciente, "municipio_ibge", None))
    cep = _digitos(paciente.cep)
    if len(ibge) != 7 or len(cep) != 8:
        return None
    return [{
        "city": ibge[:6],
        "state": ibge[:2],
        "postalCode": f"{cep[:5]}-{cep[5:]}",
    }]


def _map_patient(paciente):
    identificadores = []
    if paciente.cns:
        identificadores.append({"system": SISTEMA_CNS, "value": paciente.cns})
    if paciente.cpf:
        identificadores.append({"system": SISTEMA_CPF, "value": _digitos(paciente.cpf)})

    sexo = {"M": "male", "F": "female"}.get((paciente.sexo or "").upper(), "unknown")

    recurso = {
        "resourceType": "Patient",
        "meta": {"profile": [PERFIL_INDIVIDUO]},
        "identifier": identificadores,
        "active": bool(paciente.ativo),
        "name": [{"use": "official", "text": paciente.nome}],
        "gender": sexo,
    }
    if paciente.data_nascimento:
        recurso["birthDate"] = paciente.data_nascimento.isoformat()
    if paciente.nome_mae:
        # `BRNomeMae-1.0` era de uma geração anterior do guia e não existe mais.
        # O que está publicado é uma extensão COMPOSTA: o parentesco num código e
        # o nome num HumanName — e não uma string solta.
        recurso["extension"] = [{
            "url": EXTENSAO_PARENTES,
            "extension": [
                {"url": "relationship", "valueCode": "mother"},
                {"url": "parent", "valueHumanName": {"text": paciente.nome_mae}},
            ],
        }]

    endereco = _map_endereco(paciente)
    if endereco:
        recurso["address"] = endereco
    return recurso


def _map_encounter(prontuario):
    sujeito = _referencia_paciente(prontuario.paciente)

    # Sem `meta.profile`: a RNDS não publica perfil de Encounter, e o modelo
    # computacional do RAC — que seria o lugar dele — ainda está em construção
    # no guia. Declarar uma URL inventada é pior que declarar nada.
    recurso = {
        "resourceType": "Encounter",
        "status": "finished" if prontuario.assinado else "in-progress",
        # AMB porque este mapper converte o prontuário ambulatorial. Internação
        # e pronto-socorro são outros models e ainda não são enviados.
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB",
            "display": "ambulatory",
        },
        "subject": sujeito,
    }
    if prontuario.criado_em:
        recurso["period"] = {"start": _instante(prontuario.criado_em)}
    if prontuario.cid_principal:
        # `Encounter.diagnosis.condition` é uma REFERÊNCIA a um Condition, não um
        # CodeableConcept. A versão anterior punha o CID-10 direto ali: o
        # validador descarta o campo inteiro por não reconhecê-lo, e o
        # diagnóstico simplesmente não viajava. Nada acusava.
        #
        # O Condition vai `contained` porque não há id que a RNDS resolva — a
        # mesma razão que fez a referência ao paciente ser por identificador.
        recurso["contained"] = [{
            "resourceType": "Condition",
            "id": ID_DIAGNOSTICO,
            "code": {"coding": [{
                "system": SISTEMA_CID,
                "code": prontuario.cid_principal,
                "display": descricao_cid(prontuario.cid_principal) or "",
            }]},
            "subject": sujeito,
        }]
        recurso["diagnosis"] = [{
            "condition": {"reference": f"#{ID_DIAGNOSTICO}"},
            "rank": 1,
        }]
    return recurso


def _observacao(codigo, rotulo, categoria, sujeito, momento, perfil=None):
    """Esqueleto de um Observation.

    `code` é 1..1 na especificação: um Observation sem ele é inválido, ainda que
    o JSON esteja bem formado - a rejeição só apareceria do lado da RNDS.
    """
    recurso = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": SISTEMA_CATEGORIA, "code": categoria}]}],
        "code": {"coding": [{"system": SISTEMA_LOINC, "code": codigo,
                             "display": rotulo}]},
        "subject": sujeito,
        "effectiveDateTime": momento,
    }
    if perfil:
        recurso["meta"] = {"profile": [perfil]}
    return recurso


def _quantidade(valor, unidade):
    """Valor com unidade UCUM codificada, e não só o rótulo legível."""
    return {"value": float(valor), "unit": unidade,
            "system": SISTEMA_UCUM, "code": unidade}


def _map_pressao(prontuario, sujeito, momento):
    """Pressão arterial: painel 85354-9 com sistólica e diastólica separadas.

    O campo é texto livre. Quando não dá para separar os dois números, o recurso
    não é montado: mandar "120/80" como valor de 8480-6 - que é a sistólica, um
    número - seria um documento aceito pelo transporte e errado no significado.
    """
    casado = PRESSAO.match(prontuario.pressao_arterial or "")
    if not casado:
        return None

    recurso = _observacao("85354-9", "Pressão arterial", "vital-signs",
                          sujeito, momento, perfil=PERFIL_PRESSAO)
    recurso["component"] = [
        {"code": {"coding": [{"system": SISTEMA_LOINC, "code": "8480-6",
                              "display": "Pressão arterial sistólica"}]},
         "valueQuantity": _quantidade(casado.group(1), "mm[Hg]")},
        {"code": {"coding": [{"system": SISTEMA_LOINC, "code": "8462-4",
                              "display": "Pressão arterial diastólica"}]},
         "valueQuantity": _quantidade(casado.group(2), "mm[Hg]")},
    ]
    return recurso


def _map_observations(prontuario):
    """Um Observation por grandeza medida. Lista vazia se não houve medição."""
    sujeito = _referencia_paciente(prontuario.paciente)
    momento = _instante(prontuario.criado_em)

    recursos = []
    pressao = _map_pressao(prontuario, sujeito, momento)
    if pressao:
        recursos.append(pressao)

    for codigo, rotulo, atributo, unidade, categoria in SINAIS_VITAIS:
        valor = getattr(prontuario, atributo, None)
        if valor in (None, ""):
            continue
        # Glicemia é exame de laboratório: declarar o perfil de sinal vital
        # nela seria afirmar uma conformidade que ela não tem.
        perfil = PERFIL_SINAL_VITAL if categoria == "vital-signs" else None
        recurso = _observacao(codigo, rotulo, categoria, sujeito, momento,
                              perfil=perfil)
        recurso["valueQuantity"] = _quantidade(valor, unidade)
        recursos.append(recurso)

    return recursos


def _montar(tipo, entity_id):
    """Devolve (lista_de_recursos, tabela, paciente_id) ou ([], None, None).

    Lista, e não recurso: um prontuário com seis sinais vitais medidos vira seis
    Observation, cada um com seu próprio `code`.
    """
    if tipo == "Patient":
        p = Paciente.query.get(entity_id)
        return ([_map_patient(p)], "pacientes", p.id) if p else ([], None, None)

    pr = Prontuario.query.get(entity_id)
    if not pr:
        return [], None, None
    if tipo == "Encounter":
        return [_map_encounter(pr)], "prontuarios", pr.paciente_id
    if tipo == "Observation":
        return _map_observations(pr), "prontuarios", pr.paciente_id
    return [], None, None


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
        # A tela precisa dizer a verdade sobre o que está acontecendo: sem
        # certificado, nada sai desta máquina.
        cliente_simulado=not rnds_cliente.esta_configurado(),
    )


@rnds_bp.get("/preview/<tipo>/<int:entity_id>")
@login_required
@requer_permissao("reports:read")
def preview(tipo, entity_id):
    """Mostra o JSON FHIR que seria enviado, sem enviar."""
    if tipo not in TIPOS:
        flash("Tipo de recurso não suportado.", "danger")
        return redirect(url_for("rnds.index"))

    recursos, _tabela, _pid = _montar(tipo, entity_id)
    if not recursos:
        flash("Registro não encontrado ou sem dados suficientes para o recurso.", "warning")
        return redirect(url_for("rnds.index"))

    # Um só recurso aparece como objeto; vários, como a lista que de fato será
    # enfileirada. A tela mostra o que sai, e não uma versão arrumada dele.
    conteudo = recursos[0] if len(recursos) == 1 else recursos

    return render_template(
        "rnds/preview.html",
        tipo=tipo,
        entity_id=entity_id,
        quantidade=len(recursos),
        payload=json.dumps(conteudo, indent=2, ensure_ascii=False),
    )


@rnds_bp.post("/enviar")
@login_required
@requer_permissao("clinical:write")
def enviar():
    tipo = (request.form.get("tipo") or "").strip()
    entity_id = request.form.get("entity_id", type=int)

    if tipo not in TIPOS or not entity_id:
        flash("Informe o tipo de recurso e o identificador.", "warning")
        return redirect(url_for("rnds.index"))

    recursos, tabela, paciente_id = _montar(tipo, entity_id)
    if not recursos:
        flash("Registro não encontrado ou sem dados suficientes.", "warning")
        return redirect(url_for("rnds.index"))

    # Cada recurso vira um envio próprio: a idempotência é por conteúdo, então
    # reenfileirar um prontuário depois de medir mais um sinal vital acrescenta
    # só o que faltava, em vez de duplicar o que já foi.
    novos = repetidos = 0
    for recurso in recursos:
        _envio, novo = rnds_fila.enfileirar(
            tipo, recurso, tabela, entity_id,
            paciente_id=paciente_id, usuario_id=current_user.id)
        if novo:
            novos += 1
        else:
            repetidos += 1

    if not novos:
        db.session.rollback()
        flash(
            f"Este {tipo} já está na fila. "
            "Conteúdo idêntico não é enfileirado duas vezes.", "info")
        return redirect(url_for("rnds.index"))

    registrar("envios_rnds", entity_id, "create",
              f"{tipo}#{entity_id} enfileirado para a RNDS "
              f"({novos} recurso(s))")
    db.session.commit()

    ja_estava = f" {repetidos} já estava(m) na fila." if repetidos else ""
    flash(f"{novos} recurso(s) {tipo} enfileirado(s) para envio à RNDS."
          + ja_estava, "success")
    return redirect(url_for("rnds.index"))


@rnds_bp.post("/processar")
@login_required
@requer_permissao("clinical:write")
def processar():
    """Drena a fila sob demanda.

    O caminho normal é o cron chamando `flask rnds-processar`; este botão existe
    para operar e demonstrar sem depender do agendador.
    """
    resumo = rnds_fila.processar()

    partes = []
    if resumo["enviados"]:
        partes.append(f"{resumo['enviados']} enviado(s)")
    if resumo["adiados"]:
        partes.append(f"{resumo['adiados']} adiado(s) para nova tentativa")
    if resumo["recusados"]:
        partes.append(f"{resumo['recusados']} recusado(s)")

    if not partes:
        flash("Nada pendente na fila.", "info")
    else:
        aviso = " (cliente simulado — sem certificado configurado)" if resumo["simulado"] else ""
        flash("Fila processada: " + ", ".join(partes) + aviso,
              "warning" if resumo["recusados"] else "success")

    return redirect(url_for("rnds.index"))


@rnds_bp.post("/envios/<int:id>/reenviar")
@login_required
@requer_permissao("clinical:write")
def reenviar(id):
    envio = EnvioRnds.query.get_or_404(id)

    recursos, _t, _p = _montar(envio.tipo, envio.entidade_id)
    if not recursos:
        flash("O registro de origem não existe mais.", "warning")
        return redirect(url_for("rnds.index"))

    # Devolve à fila em vez de tentar aqui: o reenvio manual passa pelo mesmo
    # caminho do automático, com o mesmo tratamento de falha.
    rnds_fila.reenfileirar(envio)

    registrar("envios_rnds", envio.id, "update",
              f"Envio {envio.id} devolvido à fila para nova tentativa")
    db.session.commit()

    flash("Envio devolvido à fila. Use 'Processar fila' ou aguarde o agendador.",
          "success")
    return redirect(url_for("rnds.index"))
