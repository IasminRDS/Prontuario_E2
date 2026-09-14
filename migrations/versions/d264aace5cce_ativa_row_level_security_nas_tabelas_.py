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
import sqlalchemy as sa
from alembic import op

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from utils.rls import aplicar_politicas, remover_politicas  # noqa: E402


revision = 'd264aace5cce'
down_revision = '5aad58eaed4b'
branch_labels = None
depends_on = None

# Congelado, e não importado de `utils.rls`: migration é retrato de um momento.
# Este é o conteúdo de `FORA_DO_ESCOPO` quando esta revisão foi escrita, e ele
# precisa continuar sendo, ainda que a lista da aplicação mude — senão aplicar
# as migrations do zero passaria a produzir um banco diferente do que produziu
# quando alguém as aplicou pela primeira vez.
FORA_DO_ESCOPO = {"users", "medicos", "leitos", "mov_estoque"}


def _alvos(conexao):
    """Tabelas que TÊM `unidade_id` no banco, agora.

    Lia o metadata da aplicação, e é aí que estava o defeito: o metadata
    descreve os models de HOJE, não o schema no ponto desta revisão. Num banco
    vazio, `administracoes_med` e outras sete só ganham a coluna em
    `c6b83f2a41d7`, que roda DEPOIS — e `CREATE POLICY` sobre coluna inexistente
    derrubava `flask db upgrade` inteiro. O caminho de instalação documentado no
    README não funcionava a partir do zero; a suíte não via porque monta o
    schema com `create_all`, e quem desenvolve não via porque seu banco já tinha
    as colunas.

    Perguntar ao BANCO resolve nos dois sentidos: num banco vazio protege o que
    existe neste ponto e deixa o resto para a migration que cria as colunas; num
    banco já migrado, encontra tudo. E deixa de depender dos models, que é o que
    uma migration nunca deveria fazer.
    """
    inspetor = sa.inspect(conexao)
    return tuple(sorted(
        nome for nome in inspetor.get_table_names()
        if nome not in FORA_DO_ESCOPO
        and any(c["name"] == "unidade_id" for c in inspetor.get_columns(nome))
    ))


def upgrade():
    conexao = op.get_bind()
    if conexao.dialect.name != "postgresql":
        return
    # O SQL das políticas vive em utils/rls.py, não aqui: é o mesmo que os
    # testes aplicam. Duas cópias divergiriam, e a divergência só apareceria
    # quando alguém confiasse numa proteção que não existe.
    aplicar_politicas(conexao, _alvos(conexao))


def downgrade():
    conexao = op.get_bind()
    if conexao.dialect.name != "postgresql":
        return
    remover_politicas(conexao, _alvos(conexao))
