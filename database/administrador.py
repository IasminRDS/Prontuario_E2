# -*- coding: utf-8 -*-
"""Criação do primeiro administrador.

Uma instalação nova nascia sem administrador: o seed cria apenas um médico, e
não havia caminho nenhum para criar alguém com acesso a `/admin/`,
`/configuracoes/`, `/unidades/` ou `/backup/`. Quem clonasse o repositório
chegava a um sistema que não podia ser administrado.

A lógica fica aqui, e não dentro do comando, para poder ser testada sem simular
terminal.
"""
from database.db import db
from models.unidade_saude import UnidadeSaude
from models.user import User
from utils.rbac import SUPER_ADMIN, _normalizar

SENHA_MINIMA = 8


class ErroBootstrap(Exception):
    """Impede a criação, com motivo legível para quem está no terminal."""


def criar_administrador(nome, email, senha, unidade_id=None, perfil="admin"):
    """Cria um usuário administrador. Devolve o User (ainda não commitado)."""
    nome = (nome or "").strip()
    email = (email or "").strip().lower()

    if not nome:
        raise ErroBootstrap("informe o nome.")
    if "@" not in email:
        raise ErroBootstrap(f"e-mail inválido: {email!r}")
    if len(senha or "") < SENHA_MINIMA:
        raise ErroBootstrap(
            f"a senha precisa de ao menos {SENHA_MINIMA} caracteres.")
    if User.query.filter_by(email=email).first():
        raise ErroBootstrap(f"já existe usuário com o e-mail {email}.")

    e_super = _normalizar(perfil) == SUPER_ADMIN

    if unidade_id is None and not e_super:
        # Sem unidade, o Row-Level Security compara `unidade_id` com NULL e não
        # libera linha nenhuma: o admin nasceria enxergando um sistema vazio.
        unidade = UnidadeSaude.query.order_by(UnidadeSaude.id.asc()).first()
        if unidade is None:
            raise ErroBootstrap(
                "não há nenhuma unidade cadastrada. Rode `flask seed` antes, "
                "ou informe --unidade-id.")
        unidade_id = unidade.id

    if unidade_id is not None and not db.session.get(UnidadeSaude, unidade_id):
        raise ErroBootstrap(f"unidade {unidade_id} não existe.")

    usuario = User(
        nome=nome,
        email=email,
        perfil=perfil,
        unidade_id=unidade_id,
        nivel_acesso="UNIDADE",
        ativo=True,
    )
    usuario.set_password(senha)
    db.session.add(usuario)
    return usuario
