"""Ativa Row-Level Security nas tabelas com escopo territorial

Revision ID: d264aace5cce
Revises: 5aad58eaed4b
Create Date: 2026-08-03 21:20:02.079310

A aplicação já filtra por unidade em Python. O RLS coloca a mesma regra dentro
do banco, para que uma consulta nova que esqueça o filtro não enxergue registro
clínico de outro município — a proteção deixa de depender de ninguém lembrar.

As políticas FALHAM FECHADAS: sem os parâmetros de escopo definidos na
transação, nada é liberado. `utils/rls.registrar` cuida de defini-los no início
de cada transação; fora de requisição (migration, CLI) o escopo é SISTEMA.

Só PostgreSQL. Em SQLite a migration não faz nada e o filtro em Python segue
sendo a única barreira.

"""
from alembic import op

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from utils.rls import aplicar_politicas, remover_politicas, tabelas_protegidas  # noqa: E402


revision = 'd264aace5cce'
down_revision = '5aad58eaed4b'
branch_labels = None
depends_on = None


def _alvos():
    """Tabelas com `unidade_id`, lidas do metadata da aplicação."""
    from extensions import db

    import models  # noqa: F401  — popula o metadata

    return tabelas_protegidas(db.metadata)


def upgrade():
    conexao = op.get_bind()
    if conexao.dialect.name != "postgresql":
        return
    # O SQL das políticas vive em utils/rls.py, não aqui: é o mesmo que os
    # testes aplicam. Duas cópias divergiriam, e a divergência só apareceria
    # quando alguém confiasse numa proteção que não existe.
    aplicar_politicas(conexao, _alvos())


def downgrade():
    conexao = op.get_bind()
    if conexao.dialect.name != "postgresql":
        return
    remover_politicas(conexao, _alvos())
