# -*- coding: utf-8 -*-
"""Validação dos recursos FHIR contra a especificação R4.

Este é o quinto detector, e cobre a camada que os outros quatro não alcançam:
o recurso que **sai do sistema bem formado e chega inválido**. O JSON é JSON, a
fila aceita, o cliente simulado devolve protocolo — e a recusa, quando vem, vem
do outro lado da rede, horas depois, num ambiente que exige certificado
ICP-Brasil para ser sequer visitado.

Os modelos vêm do `fhirclient`, gerados da **FHIR 4.0.1** — a mesma versão que o
sistema declara. Não é o validador oficial do HL7: aquele confere também os
perfis (`BRIndividuo-1.0`), e exige Java 11, que esta máquina não tem. O que
está aqui confere a especificação base — cardinalidade, tipo, campo obrigatório,
formato — que é onde estavam os defeitos reais.

Na primeira execução ele reprovou **9 dos 10 recursos** que o sistema produzia:

- `effectiveDateTime` e `period.start` sem fuso horário. `isoformat()` devolve
  "2026-03-04T10:30:00", que não é um `dateTime` válido quando há hora.
- `Encounter.diagnosis.condition` recebendo um CodeableConcept. O campo é uma
  **referência** a um Condition; o CID-10 posto ali era descartado inteiro, e o
  diagnóstico não viajava. Nenhum teste anterior acusava, porque nada quebrava.
"""
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from fhirclient.models.encounter import Encounter
from fhirclient.models.fhirabstractbase import FHIRValidationError
from fhirclient.models.observation import Observation
from fhirclient.models.patient import Patient

from routes import rnds

MODELOS = {"Patient": Patient, "Encounter": Encounter, "Observation": Observation}


def validar(tipo, recurso):
    """Levanta `FHIRValidationError` se o recurso não for R4 válido."""
    MODELOS[tipo](recurso, strict=True).as_json()


def paciente_completo(**campos):
    base = dict(
        id=7, cns="700000000000000", cpf="123.456.789-09",
        nome="Fulano de Teste", sexo="F", ativo=True,
        data_nascimento=date(1990, 5, 2), nome_mae="Maria de Souza",
        municipio="Feira de Santana", uf="BA", municipio_ibge="2910800",
        cep="44100-000")
    base.update(campos)
    return SimpleNamespace(**base)


def prontuario_completo(**campos):
    base = dict(
        id=3, paciente=paciente_completo(), paciente_id=7,
        criado_em=datetime(2026, 3, 4, 10, 30), assinado=True,
        cid_principal="J06", pressao_arterial="120/80", temperatura=36.6,
        frequencia_cardiaca=72, frequencia_respiratoria=18, saturacao_o2=98,
        peso=70.0, altura=1.70, glicemia=95)
    base.update(campos)
    return SimpleNamespace(**base)


def gerar_todos(paciente, prontuario):
    """Tudo o que os mappers produzem, como pares (tipo, recurso)."""
    recursos = [("Patient", rnds._map_patient(paciente)),
                ("Encounter", rnds._map_encounter(prontuario))]
    recursos += [("Observation", r) for r in rnds._map_observations(prontuario)]
    return recursos


# --------------------------------------------------------------- o que sai
def test_todo_recurso_gerado_e_r4_valido():
    """Prontuário com tudo preenchido: dez recursos, todos válidos."""
    recursos = gerar_todos(paciente_completo(), prontuario_completo())
    assert len(recursos) == 10

    for tipo, recurso in recursos:
        validar(tipo, recurso)


@pytest.mark.parametrize("campos", [
    {"cns": None}, {"cpf": None}, {"cns": None, "cpf": None},
    {"nome_mae": None}, {"municipio_ibge": None}, {"cep": None},
    {"data_nascimento": None}, {"sexo": "X"},
])
def test_patient_continua_valido_com_dado_faltando(campos):
    """Cadastro incompleto é o caso comum, não a exceção."""
    validar("Patient", rnds._map_patient(paciente_completo(**campos)))


@pytest.mark.parametrize("campos", [
    {"cid_principal": None}, {"assinado": False}, {"criado_em": None},
    {"pressao_arterial": "sem registro"},
])
def test_encounter_continua_valido_com_dado_faltando(campos):
    validar("Encounter", rnds._map_encounter(prontuario_completo(**campos)))


def test_recursos_de_dado_semeado_sao_validos(app, dados_clinicos):
    """O mesmo, contra o que está de fato no banco.

    Os stubs acima medem o mapper; este mede o mapper mais o que as colunas
    realmente guardam — que é onde mora o `None` que ninguém previu.
    """
    from models.paciente import Paciente
    from models.prontuario import Prontuario

    with app.app_context():
        paciente = Paciente.query.order_by(Paciente.id.asc()).first()
        prontuario = Prontuario.query.order_by(Prontuario.id.asc()).first()
        assert paciente and prontuario, "sem dado semeado não se mede nada"

        validar("Patient", rnds._map_patient(paciente))
        validar("Encounter", rnds._map_encounter(prontuario))
        for recurso in rnds._map_observations(prontuario):
            validar("Observation", recurso)


# ------------------------------------------------------- o diagnóstico viaja
def test_cid_vai_como_condition_referenciado():
    """Em R4, `diagnosis.condition` é Reference — não CodeableConcept."""
    encontro = rnds._map_encounter(prontuario_completo(cid_principal="J06"))

    contido = encontro["contained"][0]
    assert contido["resourceType"] == "Condition"
    assert contido["code"]["coding"][0]["code"] == "J06"
    assert contido["subject"] == encontro["subject"]

    referencia = encontro["diagnosis"][0]["condition"]
    assert referencia == {"reference": "#" + contido["id"]}
    assert "coding" not in referencia


def test_sem_cid_nao_ha_condition_contido():
    encontro = rnds._map_encounter(prontuario_completo(cid_principal=None))
    assert "contained" not in encontro
    assert "diagnosis" not in encontro


# ------------------------------------------------------------- instante
def test_todo_instante_declara_fuso():
    recursos = gerar_todos(paciente_completo(), prontuario_completo())
    momentos = [r["effectiveDateTime"] for t, r in recursos if t == "Observation"]
    momentos.append(rnds._map_encounter(prontuario_completo())["period"]["start"])

    assert momentos, "nenhum instante para conferir"
    for momento in momentos:
        assert momento.endswith("Z"), f"dateTime sem fuso: {momento}"


# ------------------------------------------- o validador validando de verdade
class TestOValidadorReprova:
    """Um validador que aprova tudo é pior que nenhum: dá falsa garantia.

    Cada caso aqui é um defeito que o sistema JÁ TEVE. Se algum deles parar de
    reprovar, o detector deixou de detectar — e os testes acima viram enfeite.
    """

    def _observation_base(self):
        return {
            "resourceType": "Observation", "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5"}]},
            "subject": {"identifier": {"system": "s", "value": "v"}},
            "effectiveDateTime": "2026-03-04T10:30:00Z",
            "valueQuantity": {"value": 36.6, "unit": "Cel",
                              "system": "http://unitsofmeasure.org", "code": "Cel"},
        }

    def test_reprova_observation_sem_code(self):
        recurso = self._observation_base()
        del recurso["code"]
        with pytest.raises(FHIRValidationError, match="code"):
            validar("Observation", recurso)

    def test_reprova_datetime_sem_fuso(self):
        recurso = self._observation_base()
        recurso["effectiveDateTime"] = "2026-03-04T10:30:00"
        with pytest.raises(FHIRValidationError):
            validar("Observation", recurso)

    def test_reprova_diagnostico_como_codeableconcept(self):
        encontro = {
            "resourceType": "Encounter", "status": "finished",
            "class": {"code": "AMB"},
            "diagnosis": [{"condition": {"coding": [{"code": "J06"}]}}],
        }
        with pytest.raises(FHIRValidationError):
            validar("Encounter", encontro)

    def test_reprova_campo_que_nao_existe_no_recurso(self):
        recurso = self._observation_base()
        recurso["pressaoArterialQualquer"] = "120/80"
        with pytest.raises(FHIRValidationError):
            validar("Observation", recurso)

    def test_reprova_tipo_errado(self):
        with pytest.raises(FHIRValidationError):
            validar("Patient", {"resourceType": "Patient", "birthDate": 1990})
