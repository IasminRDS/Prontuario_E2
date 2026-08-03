# -*- coding: utf-8 -*-
"""Autenticação: quem entra, quem não entra e o que o sistema revela tentando."""
import re

import pyotp
import pytest

from tests.conftest import PERFIS, SENHA, autenticar

ROTAS_PROTEGIDAS = [
    "/", "/pacientes/listar", "/prontuarios/", "/auditoria/", "/admin/",
    "/conta/", "/exportacao/", "/internacao/api/leitos", "/portal-cidadao/",
    "/vigilancia/",
]


@pytest.mark.parametrize("rota", ROTAS_PROTEGIDAS)
def test_anonimo_nao_acessa_rota_protegida(anonimo, rota):
    resposta = anonimo.get(rota)
    assert resposta.status_code != 200, f"{rota} respondeu 200 para anônimo"


def test_login_valido_autentica(app, zera_limite):
    cliente = autenticar(app, PERFIS["admin"][1])
    assert cliente.get("/pacientes/").status_code == 200


def test_senha_errada_nao_autentica(app, zera_limite):
    cliente = autenticar(app, PERFIS["admin"][1], senha="errada-de-proposito")
    assert cliente.get("/pacientes/").status_code != 200


class TestMFA:
    """Com segundo fator ativo, a senha sozinha não pode bastar."""

    @pytest.fixture
    def usuario_com_mfa(self, app):
        from extensions import db
        from models.user import User

        with app.app_context():
            u = User.query.filter_by(email=PERFIS["medico"][1]).first()
            u.mfa_secret = pyotp.random_base32()
            u.mfa_ativo = True
            db.session.commit()
            segredo = u.mfa_secret

        yield segredo

        with app.app_context():
            u = User.query.filter_by(email=PERFIS["medico"][1]).first()
            u.mfa_ativo = False
            u.mfa_secret = None
            db.session.commit()

    def test_senha_sozinha_nao_autentica(self, app, usuario_com_mfa, sem_csrf,
                                         zera_limite):
        c = app.test_client()
        c.post("/auth/login", data={"email": PERFIS["medico"][1], "senha": SENHA},
               follow_redirects=True)
        assert c.get("/pacientes/").status_code != 200

    def test_codigo_errado_e_rejeitado(self, app, usuario_com_mfa, sem_csrf,
                                       zera_limite):
        c = app.test_client()
        c.post("/auth/login", data={"email": PERFIS["medico"][1], "senha": SENHA})
        c.post("/auth/mfa/verify", data={"codigo": "000000"}, follow_redirects=True)
        assert c.get("/pacientes/").status_code != 200

    def test_codigo_correto_autentica(self, app, usuario_com_mfa, sem_csrf,
                                      zera_limite):
        c = app.test_client()
        c.post("/auth/login", data={"email": PERFIS["medico"][1], "senha": SENHA})
        c.post("/auth/mfa/verify",
               data={"codigo": pyotp.TOTP(usuario_com_mfa).now()},
               follow_redirects=True)
        assert c.get("/pacientes/").status_code == 200


def test_login_limita_forca_bruta(app, sem_csrf, zera_limite):
    c = app.test_client()
    codigos = [
        c.post("/auth/login",
               data={"email": PERFIS["admin"][1], "senha": f"errada{i}"}).status_code
        for i in range(12)
    ]
    assert 429 in codigos, f"12 tentativas sem bloqueio: {sorted(set(codigos))}"


def _mensagem(resposta):
    achado = re.search(r'alert__body">([^<]+)', resposta.get_data(as_text=True))
    return (achado.group(1) if achado else "").strip()


def test_nao_permite_enumerar_usuario(app, sem_csrf, zera_limite):
    """Usuário inexistente e senha errada precisam responder igual.

    Cada tentativa usa cliente e contador limpos: se o limitador entrar no meio,
    a segunda resposta vira a tela de 429 — sem a mensagem — e o teste acusa
    diferença que não é do sistema.
    """
    from utils.seguranca_http import _tentativas

    inexistente = app.test_client().post(
        "/auth/login", data={"email": "naoexiste@exemplo.local", "senha": "x"},
        follow_redirects=True)
    _tentativas.clear()
    senha_errada = app.test_client().post(
        "/auth/login", data={"email": PERFIS["admin"][1], "senha": "errada"},
        follow_redirects=True)

    assert _mensagem(inexistente) == _mensagem(senha_errada)
    assert _mensagem(inexistente), "esperava uma mensagem de erro visível"


@pytest.mark.parametrize("destino", [
    "https://evil.example.com/roubo",
    "//evil.example.com",
])
def test_nao_redireciona_para_host_externo(app, sem_csrf, zera_limite, destino):
    c = app.test_client()
    resposta = c.post(f"/auth/login?next={destino}",
                      data={"email": PERFIS["admin"][1], "senha": SENHA,
                            "next": destino})
    assert "evil.example.com" not in resposta.headers.get("Location", "")


@pytest.mark.parametrize("atributo", ["HttpOnly", "SameSite"])
def test_cookie_de_sessao_tem_protecao(anonimo, atributo):
    cookie = anonimo.get("/auth/login").headers.get("Set-Cookie", "")
    assert not cookie or atributo in cookie
