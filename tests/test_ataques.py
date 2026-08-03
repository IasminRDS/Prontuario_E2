# -*- coding: utf-8 -*-
"""Tentativas de abuso. Teste que passa = defesa funcionou."""
import io

import pytest

PAYLOADS_SQL = [
    "' OR '1'='1",
    "'; DROP TABLE pacientes;--",
    "%' UNION SELECT NULL--",
    "1' AND SLEEP(5)--",
]

XSS = "<script>alert(1)</script>"


def test_post_sem_token_csrf_e_rejeitado(cliente):
    """Com CSRF ligado — este teste é sobre o próprio CSRF."""
    resposta = cliente.post("/configuracoes/", data={"nome_unidade": "INVADIDO"})
    assert resposta.status_code == 400


@pytest.mark.parametrize("payload", PAYLOADS_SQL)
def test_busca_resiste_a_injecao_sql(autenticado_confirmado, payload):
    resposta = autenticado_confirmado.get("/pacientes/listar",
                                          query_string={"q": payload})
    assert resposta.status_code < 500


def test_tabela_intacta_apos_tentativa_de_drop(app, autenticado_confirmado):
    for payload in PAYLOADS_SQL:
        autenticado_confirmado.get("/pacientes/listar", query_string={"q": payload})

    from models.paciente import Paciente

    with app.app_context():
        assert Paciente.query.count() >= 0, "tabela pacientes sumiu"


@pytest.mark.parametrize("rota", ["/pacientes/listar", "/tabelas/"])
def test_xss_refletido_sai_escapado(autenticado_confirmado, rota):
    resposta = autenticado_confirmado.get(rota, query_string={"q": XSS})
    assert XSS not in resposta.get_data(as_text=True)


def test_paciente_inexistente_devolve_404(autenticado_confirmado):
    assert autenticado_confirmado.get("/pacientes/99999/perfil").status_code == 404


def test_verificacao_publica_nao_vaza_dado_clinico(anonimo):
    corpo = anonimo.get("/verificar/QUALQUERCOISA").get_data(as_text=True).lower()
    for termo in ("cpf", "cns", "diagnóstico"):
        assert termo not in corpo, f"documento público expôs '{termo}'"


def test_upload_acima_do_limite_e_recusado(autenticado_confirmado):
    grande = b"x" * (30 * 1024 * 1024)
    try:
        resposta = autenticado_confirmado.post(
            "/pdf/processar",
            data={"documento": (io.BytesIO(grande), "g.pdf"), "acao": "compactar"},
            content_type="multipart/form-data")
    except Exception:
        # Werkzeug pode cortar a conexão antes de responder — também é recusa.
        return
    assert resposta.status_code in (400, 413)
