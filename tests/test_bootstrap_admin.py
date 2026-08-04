# -*- coding: utf-8 -*-
"""Criação do primeiro administrador.

Sem este caminho, uma instalação nova nasce sem ninguém capaz de administrá-la:
o seed cria só um médico.
"""
import pytest

from database.administrador import ErroBootstrap, criar_administrador
from extensions import db
from models.user import User

SENHA = "senha-boa-123"


@pytest.fixture
def limpar(app):
    """Não remove nada — e isso é deliberado.

    O administrador criado faz login, o que grava auditoria apontando para ele.
    Apagá-lo exigiria apagar o registro de auditoria antes, e isso romperia a
    cadeia de hash que `test_cadeia_de_auditoria_permanece_integra` verifica.

    Manter os usuários é inofensivo: cada teste usa um e-mail próprio, e o
    schema da suíte é recriado a cada execução.
    """
    yield


def test_cria_administrador_utilizavel(app, limpar):
    with app.app_context():
        usuario = criar_administrador("Ana Gestora", "ana@bootstrap.local", SENHA)
        db.session.commit()

        assert usuario.perfil == "admin"
        assert usuario.ativo is True
        assert usuario.check_password(SENHA)
        # Sem unidade o RLS não libera nada — o admin nasceria vendo um sistema
        # vazio, que foi exatamente o defeito que motivou este comando.
        assert usuario.unidade_id is not None


def test_o_administrador_criado_consegue_entrar_e_administrar(app, limpar):
    from tests.conftest import autenticar

    with app.app_context():
        criar_administrador("Bruno Admin", "bruno@bootstrap.local", SENHA)
        db.session.commit()

    cliente = autenticar(app, "bruno@bootstrap.local", SENHA)
    assert cliente.get("/admin/").status_code == 200
    assert cliente.get("/configuracoes/").status_code == 200


def test_recusa_senha_curta(app, limpar):
    with app.app_context():
        with pytest.raises(ErroBootstrap, match="8 caracteres"):
            criar_administrador("X", "curta@bootstrap.local", "1234567")


def test_recusa_email_repetido(app, limpar):
    with app.app_context():
        criar_administrador("Um", "repetido@bootstrap.local", SENHA)
        db.session.commit()
        with pytest.raises(ErroBootstrap, match="já existe"):
            criar_administrador("Dois", "repetido@bootstrap.local", SENHA)


def test_recusa_email_invalido(app, limpar):
    with app.app_context():
        with pytest.raises(ErroBootstrap, match="inválido"):
            criar_administrador("X", "sem-arroba", SENHA)


def test_recusa_unidade_inexistente(app, limpar):
    with app.app_context():
        with pytest.raises(ErroBootstrap, match="não existe"):
            criar_administrador("X", "unidade@bootstrap.local", SENHA,
                                unidade_id=999999)


def test_super_admin_pode_ficar_sem_unidade(app, limpar):
    """Operador da plataforma atravessa o isolamento territorial."""
    with app.app_context():
        usuario = criar_administrador("Root", "root@bootstrap.local", SENHA,
                                      perfil="SuperAdmin")
        db.session.commit()
        assert usuario.unidade_id is None

        from utils.rls import escopo_do_usuario
        assert escopo_do_usuario(usuario)["nivel"] == "SISTEMA"
