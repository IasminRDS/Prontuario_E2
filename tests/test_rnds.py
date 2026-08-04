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

import pytest
import requests

from extensions import db
from models.lgpd import EnvioRnds
from services import rnds_cliente, rnds_fila
from services.rnds_cliente import (
    ClienteRnds,
    RndsIndisponivel,
    RndsRejeitou,
    chave_idempotencia,
)

RECURSO = {"resourceType": "Patient", "id": "1",
           "name": [{"text": "Fulano de Teste"}]}


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
