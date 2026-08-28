# -*- coding: utf-8 -*-
"""Fila de envio à RNDS.

O que estes testes protegem: um documento clínico não pode se perder porque a
RNDS estava fora do ar, não pode ser enviado duas vezes, e uma recusa de
validação não pode ficar sendo retentada para sempre.

O transporte é mockado — o cliente real exige certificado ICP-Brasil. O que se
verifica aqui é a máquina de estados da fila, que é onde mora o risco.
"""
import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
import requests

from extensions import db
from models.lgpd import EnvioRnds
from routes import rnds
from services import rnds_cliente, rnds_fila
from services.rnds_cliente import (
    ClienteRnds,
    RndsIndisponivel,
    RndsRejeitou,
    chave_idempotencia,
)

RECURSO = {"resourceType": "Patient", "id": "1",
           "name": [{"text": "Fulano de Teste"}]}

# Nomes de recurso FHIR que a página /sobre poderia citar.
CANDIDATOS_FHIR = {
    "Patient", "Encounter", "Observation", "MedicationRequest",
    "Immunization", "Condition", "Procedure", "DiagnosticReport",
}


@pytest.fixture
def fila_limpa(app):
    with app.app_context():
        EnvioRnds.query.delete()
        db.session.commit()
    yield
    with app.app_context():
        EnvioRnds.query.delete()
        db.session.commit()


class ClienteFalso:
    """Substitui o transporte, mantendo o contrato do cliente real."""

    simulado = False
    configurado = True

    def __init__(self, comportamento):
        self.comportamento = comportamento
        self.chamadas = []

    def enviar(self, tipo, recurso, chave):
        self.chamadas.append((tipo, chave))
        resultado = self.comportamento
        if isinstance(resultado, Exception):
            raise resultado
        return resultado


@pytest.fixture
def usar_cliente(monkeypatch):
    def aplicar(comportamento):
        falso = ClienteFalso(comportamento)
        monkeypatch.setattr(rnds_fila, "obter_cliente", lambda: falso)
        return falso

    return aplicar


# --------------------------------------------------------------- idempotência
def test_chave_muda_com_o_conteudo():
    a = chave_idempotencia("Patient", "pacientes", 1, json.dumps(RECURSO))
    b = chave_idempotencia("Patient", "pacientes", 1, json.dumps(
        {**RECURSO, "name": [{"text": "Outro"}]}))
    assert a != b
    assert a == chave_idempotencia("Patient", "pacientes", 1, json.dumps(RECURSO))


def test_mesmo_documento_nao_entra_duas_vezes(app, fila_limpa):
    with app.app_context():
        primeiro, novo1 = rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()
        segundo, novo2 = rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()

        assert novo1 is True and novo2 is False
        assert primeiro.id == segundo.id
        assert EnvioRnds.query.count() == 1


# ------------------------------------------------------------------- sucesso
def test_envio_bem_sucedido_marca_protocolo(app, fila_limpa, usar_cliente):
    falso = usar_cliente("PROTO-123")
    with app.app_context():
        rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()

        resumo = rnds_fila.processar()
        assert resumo["enviados"] == 1

        envio = EnvioRnds.query.one()
        assert envio.status == "enviado"
        assert envio.protocolo == "PROTO-123"
        assert envio.enviado_em is not None
        assert envio.proxima_tentativa is None
        assert envio.erro is None
        # A chave de idempotência viaja para a RNDS.
        assert falso.chamadas[0][1] == envio.chave_idempotencia


def test_envio_ja_concluido_nao_e_reenviado(app, fila_limpa, usar_cliente):
    falso = usar_cliente("PROTO-1")
    with app.app_context():
        rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()
        rnds_fila.processar()
        rnds_fila.processar()
        assert len(falso.chamadas) == 1, "documento enviado duas vezes"


# -------------------------------------------------------- falha transitória
def test_indisponibilidade_agenda_nova_tentativa(app, fila_limpa, usar_cliente):
    usar_cliente(RndsIndisponivel("502 Bad Gateway"))
    with app.app_context():
        rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()

        resumo = rnds_fila.processar()
        assert resumo["adiados"] == 1

        envio = EnvioRnds.query.one()
        assert envio.status == "pendente", "o documento precisa continuar na fila"
        assert envio.tentativas == 1
        assert envio.proxima_tentativa > datetime.utcnow()
        assert "502" in envio.erro


def test_recuo_cresce_e_tem_teto(app, fila_limpa, usar_cliente):
    usar_cliente(RndsIndisponivel("timeout"))
    with app.app_context():
        rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()
        envio = EnvioRnds.query.one()

        esperas = []
        for _ in range(5):
            envio.proxima_tentativa = datetime.utcnow() - timedelta(seconds=1)
            db.session.commit()
            antes = datetime.utcnow()
            rnds_fila.processar()
            db.session.refresh(envio)
            esperas.append((envio.proxima_tentativa - antes).total_seconds())

        assert esperas == sorted(esperas), f"recuo não é crescente: {esperas}"
        assert max(esperas) <= rnds_fila.RECUO_MAXIMO_MIN * 60 + 5


def test_envio_adiado_nao_e_tentado_antes_da_hora(app, fila_limpa, usar_cliente):
    falso = usar_cliente(RndsIndisponivel("fora do ar"))
    with app.app_context():
        rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()
        rnds_fila.processar()
        assert len(falso.chamadas) == 1

        rnds_fila.processar()  # ainda dentro da janela de recuo
        assert len(falso.chamadas) == 1, "tentou antes da hora marcada"


def test_para_de_tentar_apos_o_maximo(app, fila_limpa, usar_cliente):
    usar_cliente(RndsIndisponivel("fora do ar"))
    with app.app_context():
        rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()
        envio = EnvioRnds.query.one()

        for _ in range(rnds_fila.MAX_TENTATIVAS):
            envio.proxima_tentativa = datetime.utcnow() - timedelta(seconds=1)
            db.session.commit()
            rnds_fila.processar()
            db.session.refresh(envio)

        assert envio.tentativas == rnds_fila.MAX_TENTATIVAS
        assert envio.status == "erro"
        assert envio.proxima_tentativa is None, (
            "envio esgotado não pode continuar agendado"
        )


# ---------------------------------------------------------- falha definitiva
def test_recusa_de_validacao_nao_e_retentada(app, fila_limpa, usar_cliente):
    """422 da RNDS: o mesmo conteúdo daria o mesmo erro para sempre."""
    falso = usar_cliente(RndsRejeitou("recusado (422): CNS inválido"))
    with app.app_context():
        rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()

        resumo = rnds_fila.processar()
        assert resumo["recusados"] == 1

        envio = EnvioRnds.query.one()
        assert envio.status == "erro"
        assert envio.proxima_tentativa is None
        assert "CNS inválido" in envio.erro

        rnds_fila.processar()
        assert len(falso.chamadas) == 1, "recusa definitiva foi retentada"


def test_payload_ilegivel_nao_fica_em_loop(app, fila_limpa, usar_cliente):
    """Conteúdo corrompido é defeito do gravado, não da rede.

    Antes caía no ramo genérico de exceção e era reagendado — ficaria sendo
    retentado por horas até esgotar as tentativas, sem chance de dar certo.
    """
    falso = usar_cliente("PROTO")
    with app.app_context():
        rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()
        envio = EnvioRnds.query.one()
        envio.payload = "isto nao e json"
        db.session.commit()

        resumo = rnds_fila.processar()
        assert resumo["recusados"] == 1
        db.session.refresh(envio)
        assert envio.status == "erro"
        assert envio.proxima_tentativa is None
        assert "JSON" in envio.erro
        assert falso.chamadas == [], "nem chegou a tentar a rede"


def test_reenfileirar_devolve_a_fila(app, fila_limpa, usar_cliente):
    usar_cliente(RndsRejeitou("422"))
    with app.app_context():
        rnds_fila.enfileirar("Patient", RECURSO, "pacientes", 1)
        db.session.commit()
        rnds_fila.processar()
        envio = EnvioRnds.query.one()
        assert envio.status == "erro"

        rnds_fila.reenfileirar(envio)
        db.session.commit()
        assert envio.status == "pendente"
        assert envio.tentativas == 0
        assert envio.proxima_tentativa is not None


# ------------------------------------------------------------- classificação
class TestClassificacaoDeErro:
    """Separar transitório de definitivo é o cerne da fila.

    Classificar errado tem dois custos opostos: retentar para sempre um
    documento que a RNDS nunca vai aceitar, ou desistir de um que só precisava
    de mais um minuto.
    """

    @pytest.fixture
    def cliente(self, monkeypatch):
        monkeypatch.setenv("RNDS_AUTH_URL", "https://auth.exemplo.local/token")
        monkeypatch.setenv("RNDS_EHR_URL", "https://ehr.exemplo.local/fhir/r4")
        monkeypatch.setenv("RNDS_CERTIFICADO", "/tmp/cert.pem")
        c = ClienteRnds()
        c._token = "token-de-teste"
        c._token_expira_em = 9e18
        return c

    def _resposta(self, status, corpo="", cabecalhos=None):
        resposta = requests.Response()
        resposta.status_code = status
        resposta._content = corpo.encode("utf-8")
        resposta.headers.update(cabecalhos or {})
        return resposta

    @pytest.mark.parametrize("status", [500, 502, 503, 429])
    def test_5xx_e_429_sao_transitorios(self, cliente, monkeypatch, status):
        monkeypatch.setattr(requests, "post",
                            lambda *a, **k: self._resposta(status))
        with pytest.raises(RndsIndisponivel):
            cliente.enviar("Patient", RECURSO, "chave")

    @pytest.mark.parametrize("status", [400, 404, 422])
    def test_4xx_de_validacao_e_definitivo(self, cliente, monkeypatch, status):
        monkeypatch.setattr(requests, "post",
                            lambda *a, **k: self._resposta(status, "erro"))
        with pytest.raises(RndsRejeitou):
            cliente.enviar("Patient", RECURSO, "chave")

    @pytest.mark.parametrize("status", [401, 403])
    def test_nao_autorizado_descarta_token_e_permite_retentar(
            self, cliente, monkeypatch, status):
        """Token pode expirar antes do prazo declarado — não é culpa do documento."""
        monkeypatch.setattr(requests, "post",
                            lambda *a, **k: self._resposta(status))
        with pytest.raises(RndsIndisponivel):
            cliente.enviar("Patient", RECURSO, "chave")
        assert cliente._token is None, "token inválido precisa ser descartado"

    def test_timeout_e_transitorio(self, cliente, monkeypatch):
        def estourar(*a, **k):
            raise requests.Timeout("tempo esgotado")

        monkeypatch.setattr(requests, "post", estourar)
        with pytest.raises(RndsIndisponivel):
            cliente.enviar("Patient", RECURSO, "chave")

    def test_protocolo_vem_do_cabecalho_ou_do_corpo(self, cliente, monkeypatch):
        monkeypatch.setattr(requests, "post", lambda *a, **k: self._resposta(
            201, "", {"X-Protocolo": "ABC-999"}))
        assert cliente.enviar("Patient", RECURSO, "chave") == "ABC-999"

        monkeypatch.setattr(requests, "post", lambda *a, **k: self._resposta(
            201, json.dumps({"id": "do-corpo"})))
        assert cliente.enviar("Patient", RECURSO, "chave") == "do-corpo"


def test_sem_certificado_usa_cliente_simulado(monkeypatch):
    for variavel in ("RNDS_AUTH_URL", "RNDS_EHR_URL", "RNDS_CERTIFICADO"):
        monkeypatch.delenv(variavel, raising=False)
    assert rnds_cliente.esta_configurado() is False
    cliente = rnds_cliente.obter_cliente(forcar_novo=True)
    assert cliente.simulado is True
    assert cliente.enviar("Patient", RECURSO, "a" * 64).startswith("SIM-")


# ---------------------------------------------------------------- pela tela
def test_tela_enfileira_sem_enviar(app, fila_limpa, autenticado_confirmado,
                                   dados_clinicos, usar_cliente):
    falso = usar_cliente("PROTO")
    cliente = autenticado_confirmado

    import re
    html = cliente.get("/rnds/").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)

    from models.paciente import Paciente

    with app.app_context():
        paciente_id = Paciente.query.first().id

    cliente.post("/rnds/enviar",
                 data={"csrf_token": token, "tipo": "Patient",
                       "entity_id": paciente_id},
                 follow_redirects=True)

    with app.app_context():
        envio = EnvioRnds.query.one()
        assert envio.status == "pendente", "a tela não pode enviar na requisição"
    assert falso.chamadas == [], "houve POST à RNDS dentro da requisição"


def test_tela_avisa_quando_o_cliente_e_simulado(autenticado_confirmado, monkeypatch):
    monkeypatch.setattr(rnds_cliente, "esta_configurado", lambda: False)
    html = autenticado_confirmado.get("/rnds/").get_data(as_text=True)
    assert "Cliente simulado" in html


# --------------------------------------------------------------- mappers FHIR
class TestMappersFhir:
    """O defeito que estes testes seguram não levanta exceção em lugar nenhum.

    O JSON sai bem formado, a fila aceita, o cliente simulado devolve protocolo
    e o receptor entende outra coisa — ou recusa, longe daqui, horas depois. É a
    mesma família dos detectores da suíte: erro que não vira erro.
    """

    def _paciente(self, **campos):
        base = dict(id=7, cns="700000000000000", cpf="123.456.789-09",
                    nome="Fulano", sexo="F", ativo=True, data_nascimento=None,
                    nome_mae=None, municipio="Feira de Santana", uf="BA",
                    municipio_ibge="2910800", cep="44100-000")
        base.update(campos)
        return SimpleNamespace(**base)

    def _prontuario(self, paciente=None, **campos):
        base = dict(id=3, paciente=paciente or self._paciente(),
                    paciente_id=7, criado_em=datetime(2026, 3, 4, 10, 30),
                    assinado=True, cid_principal=None,
                    pressao_arterial=None, temperatura=None,
                    frequencia_cardiaca=None, frequencia_respiratoria=None,
                    saturacao_o2=None, peso=None, altura=None, glicemia=None)
        base.update(campos)
        return SimpleNamespace(**base)

    # -------------------------------------------------------------- estrutura
    def test_todo_observation_declara_o_que_mediu(self):
        """`Observation.code` é 1..1 na especificação.

        A versão anterior empacotava todos os sinais como `component` de um
        único recurso SEM `code`: inválido, e só a RNDS diria isso.
        """
        recursos = rnds._map_observations(self._prontuario(
            pressao_arterial="120/80", temperatura=36.6, frequencia_cardiaca=72,
            saturacao_o2=98, peso=70.0, altura=1.7, glicemia=95))

        assert len(recursos) == 7, "uma grandeza medida, um Observation"
        for recurso in recursos:
            assert recurso["resourceType"] == "Observation"
            codigo = recurso["code"]["coding"][0]
            assert codigo["code"], f"Observation sem code: {recurso}"
            assert codigo["system"] == rnds.SISTEMA_LOINC

    def test_cada_recurso_carrega_valor_ou_componentes(self):
        recursos = rnds._map_observations(self._prontuario(
            pressao_arterial="130/85", temperatura=37.2))
        for recurso in recursos:
            assert "valueQuantity" in recurso or "component" in recurso

    def test_prontuario_sem_medicao_nao_gera_recurso(self):
        assert rnds._map_observations(self._prontuario()) == []

    # ------------------------------------------------------------ pressao
    def test_pressao_vira_painel_com_sistolica_e_diastolica(self):
        """8480-6 é a sistólica — um número, não o par.

        Gravar "120/80" ali passava pelo transporte e chegava sem sentido.
        """
        recursos = rnds._map_observations(
            self._prontuario(pressao_arterial="120/80"))
        painel = recursos[0]

        assert painel["code"]["coding"][0]["code"] == "85354-9"
        codigos = [c["code"]["coding"][0]["code"] for c in painel["component"]]
        assert codigos == ["8480-6", "8462-4"]

        sistolica, diastolica = painel["component"]
        assert sistolica["valueQuantity"]["value"] == 120.0
        assert diastolica["valueQuantity"]["value"] == 80.0
        assert sistolica["valueQuantity"]["code"] == "mm[Hg]"
        assert "valueString" not in painel

    def test_pressao_aceita_a_grafia_com_x(self):
        recursos = rnds._map_observations(
            self._prontuario(pressao_arterial="120 x 80"))
        assert recursos[0]["component"][0]["valueQuantity"]["value"] == 120.0

    @pytest.mark.parametrize("bruto", ["", "normal", "12080", "120/", "abc/def"])
    def test_pressao_ilegivel_nao_vira_recurso_errado(self, bruto):
        """Melhor não enviar do que enviar afirmando outra coisa."""
        recursos = rnds._map_observations(
            self._prontuario(pressao_arterial=bruto, temperatura=36.5))
        codigos = [r["code"]["coding"][0]["code"] for r in recursos]
        assert "85354-9" not in codigos
        assert codigos == ["8310-5"], "o resto da medição continua saindo"

    # ------------------------------------------------------------- unidades
    def test_valor_traz_unidade_ucum_codificada(self):
        recursos = rnds._map_observations(self._prontuario(temperatura=36.6))
        quantidade = recursos[0]["valueQuantity"]
        assert quantidade["system"] == "http://unitsofmeasure.org"
        assert quantidade["code"] == "Cel"

    def test_altura_sai_em_metros(self):
        """O model calcula IMC como peso/altura**2 — a coluna está em metros.

        O mapper anunciava "cm", e 1.70 cm não é uma pessoa.
        """
        recursos = rnds._map_observations(self._prontuario(altura=1.70))
        assert recursos[0]["valueQuantity"] == {
            "value": 1.7, "unit": "m", "code": "m",
            "system": "http://unitsofmeasure.org"}

    def test_glicemia_nao_se_declara_sinal_vital(self):
        recursos = rnds._map_observations(self._prontuario(glicemia=95))
        categoria = recursos[0]["category"][0]["coding"][0]["code"]
        assert categoria == "laboratory"

    # ---------------------------------------------------------- referencia
    def test_subject_usa_o_cns_quando_existe(self):
        """`Patient/37` é o cadastro 37 DESTE banco; a RNDS não resolve isso."""
        encontro = rnds._map_encounter(self._prontuario())
        assert encontro["subject"] == {
            "identifier": {"system": rnds.SISTEMA_CNS,
                           "value": "700000000000000"}}

    def test_subject_cai_para_o_cpf_sem_cns(self):
        paciente = self._paciente(cns=None)
        encontro = rnds._map_encounter(self._prontuario(paciente=paciente))
        assert encontro["subject"] == {
            "identifier": {"system": rnds.SISTEMA_CPF, "value": "12345678909"}}

    def test_sem_documento_sobra_a_referencia_local(self):
        paciente = self._paciente(cns=None, cpf=None)
        encontro = rnds._map_encounter(self._prontuario(paciente=paciente))
        assert encontro["subject"] == {"reference": "Patient/7"}


# ------------------------------------------------------ a tela contra o codigo
def test_sobre_nao_promete_recurso_que_o_codigo_nao_monta():
    """A página /sobre prometia enviar MedicationRequest. Não existe mapper.

    Este teste reprova nos dois sentidos: recurso anunciado e não implementado
    falha, e recurso implementado que a página esqueceu de citar também.
    """
    from routes.sobre import CONFORMIDADE

    texto = next(d for t, d in CONFORMIDADE if "FHIR" in t)
    citados = {p.strip(".,") for p in texto.split()
               if p.strip(".,") in CANDIDATOS_FHIR}
    assert citados == set(rnds.TIPOS), (
        f"a tela cita {sorted(citados)} e o código monta {sorted(rnds.TIPOS)}")


def test_prontuario_com_varios_sinais_enfileira_um_envio_por_grandeza(
        app, fila_limpa, autenticado_confirmado, dados_clinicos, usar_cliente):
    """Antes era um envio só, com um recurso inválido dentro."""
    import re as _re

    falso = usar_cliente("PROTO")
    cliente = autenticado_confirmado

    from models.paciente import Paciente
    from models.prontuario import Prontuario
    from models.unidade_saude import UnidadeSaude

    with app.app_context():
        paciente = Paciente.query.order_by(Paciente.id.asc()).first()
        unidade = UnidadeSaude.query.order_by(UnidadeSaude.id.asc()).first()
        pr = Prontuario(paciente_id=paciente.id, unidade_id=unidade.id,
                        pressao_arterial="120/80", temperatura=36.6,
                        frequencia_cardiaca=72)
        db.session.add(pr)
        db.session.commit()
        prontuario_id = pr.id

    html = cliente.get("/rnds/").get_data(as_text=True)
    token = _re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    cliente.post("/rnds/enviar",
                 data={"csrf_token": token, "tipo": "Observation",
                       "entity_id": prontuario_id},
                 follow_redirects=True)

    with app.app_context():
        envios = EnvioRnds.query.all()
        assert len(envios) == 3, "pressão, temperatura e frequência cardíaca"
        assert {e.status for e in envios} == {"pendente"}
        chaves = {e.chave_idempotencia for e in envios}
        assert len(chaves) == 3, "conteúdos distintos, chaves distintas"
    assert falso.chamadas == [], "houve POST à RNDS dentro da requisição"


def test_preview_mostra_todos_os_recursos(app, autenticado_confirmado,
                                          dados_clinicos):
    from models.prontuario import Prontuario

    with app.app_context():
        pr = Prontuario.query.order_by(Prontuario.id.asc()).first()
        pr.temperatura = 36.6
        pr.pressao_arterial = "110/70"
        db.session.commit()
        prontuario_id = pr.id

    resposta = autenticado_confirmado.get(
        f"/rnds/preview/Observation/{prontuario_id}")
    corpo = resposta.get_data(as_text=True)
    assert resposta.status_code == 200
    assert "85354-9" in corpo and "8310-5" in corpo


# ------------------------------------------------- conformidade com o guia RNDS
class TestConformidadeRnds:
    """URIs conferidas uma a uma nas representações JSON do guia publicado.

    São literais aqui de propósito. Um identificador escrito de outro jeito não
    quebra nada visivelmente: o documento sai, o transporte aceita, e o receptor
    simplesmente não reconhece o documento como sendo daquela pessoa.
    """

    def _paciente(self, **campos):
        base = dict(id=7, cns="700000000000000", cpf="123.456.789-09",
                    nome="Fulano", sexo="F", ativo=True, data_nascimento=None,
                    nome_mae=None, municipio="Feira de Santana", uf="BA",
                    municipio_ibge="2910800", cep="44100-000")
        base.update(campos)
        return SimpleNamespace(**base)

    # ------------------------------------------------------- NamingSystem
    def test_namingsystem_sao_os_publicados_pela_rnds(self):
        """rnds-fhir.saude.gov.br/NamingSystem-cns e -cpf.

        Os anteriores (`https://saude.gov.br/sid/cns` e `.../fhir/sid/cpf`) não
        eram só divergentes entre si: nenhum dos dois existe no guia.
        """
        assert rnds.SISTEMA_CNS == "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cns"
        assert rnds.SISTEMA_CPF == "http://rnds.saude.gov.br/fhir/r4/NamingSystem/cpf"

    def test_patient_identifica_por_cns_e_cpf(self):
        recurso = rnds._map_patient(self._paciente())
        sistemas = [i["system"] for i in recurso["identifier"]]
        assert sistemas == [rnds.SISTEMA_CNS, rnds.SISTEMA_CPF]
        assert recurso["identifier"][1]["value"] == "12345678909", "CPF sem máscara"

    # -------------------------------------------------------------- perfis
    def test_patient_declara_o_perfil_do_individuo(self):
        recurso = rnds._map_patient(self._paciente())
        assert recurso["meta"]["profile"] == [
            "https://rnds-fhir.saude.gov.br/StructureDefinition/BRIndividuo-1.0"]

    def test_encounter_nao_declara_perfil_inventado(self):
        """A RNDS não publica perfil de Encounter. Não declarar é a resposta certa."""
        prontuario = SimpleNamespace(
            paciente=self._paciente(), assinado=True, cid_principal=None,
            criado_em=datetime(2026, 3, 4, 10, 30))
        assert "meta" not in rnds._map_encounter(prontuario)

    def test_sinal_vital_declara_perfil_do_hl7_e_glicemia_nao(self):
        prontuario = SimpleNamespace(
            paciente=self._paciente(), criado_em=datetime(2026, 3, 4),
            pressao_arterial="120/80", temperatura=36.6, glicemia=95,
            frequencia_cardiaca=None, frequencia_respiratoria=None,
            saturacao_o2=None, peso=None, altura=None)
        por_codigo = {r["code"]["coding"][0]["code"]: r
                      for r in rnds._map_observations(prontuario)}

        assert por_codigo["85354-9"]["meta"]["profile"] == [
            "http://hl7.org/fhir/StructureDefinition/bp"]
        assert por_codigo["8310-5"]["meta"]["profile"] == [
            "http://hl7.org/fhir/StructureDefinition/vitalsigns"]
        assert "meta" not in por_codigo["2339-0"], (
            "glicemia não é sinal vital e não pode declarar que é")

    # ------------------------------------------------------------ endereco
    def test_endereco_vai_por_codigo_e_sem_country(self):
        """BREndereco-1.0: município e UF por código, `country` proibido (0..0)."""
        recurso = rnds._map_patient(self._paciente())
        assert recurso["address"] == [{
            "city": "291080",       # seis dígitos: o de sete tem verificador
            "state": "29",          # código numérico da UF, não a sigla
            "postalCode": "44100-000",
        }]
        assert "country" not in recurso["address"][0]

    @pytest.mark.parametrize("campos", [
        {"municipio_ibge": None}, {"municipio_ibge": "29108"}, {"cep": None},
        {"cep": "441"},
    ])
    def test_endereco_incompleto_fica_de_fora(self, campos):
        """Os três campos são 1..1: meio endereço reprova o recurso inteiro."""
        recurso = rnds._map_patient(self._paciente(**campos))
        assert "address" not in recurso

    # -------------------------------------------------------- nome da mae
    def test_nome_da_mae_usa_a_extensao_composta(self):
        """`BRNomeMae-1.0` era de outra geração do guia e não existe mais."""
        recurso = rnds._map_patient(self._paciente(nome_mae="Maria de Souza"))
        extensao = recurso["extension"][0]

        assert extensao["url"] == (
            "https://rnds-fhir.saude.gov.br/StructureDefinition/"
            "BRParentesIndividuo-1.0")
        assert extensao["extension"] == [
            {"url": "relationship", "valueCode": "mother"},
            {"url": "parent", "valueHumanName": {"text": "Maria de Souza"}},
        ]
        assert "valueString" not in extensao

    def test_sem_nome_da_mae_nao_ha_extensao(self):
        assert "extension" not in rnds._map_patient(self._paciente())
