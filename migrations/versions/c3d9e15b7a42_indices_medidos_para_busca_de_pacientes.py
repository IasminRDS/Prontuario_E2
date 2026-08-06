"""Indices de busca de pacientes, escolhidos por medicao

Revision ID: c3d9e15b7a42
Revises: b7f4c2e91a08
Create Date: 2026-08-06 20:05:00.000000

Estes indices NAO foram escolhidos por intuicao. Com 50 mil pacientes sinteticos
(`flask seed-volume`), EXPLAIN ANALYZE sob escopo de unidade mostrou:

    consulta                    antes     depois    ganho   plano depois
    lista paginada             40.1ms      0.1ms     267x   Index Scan
    contagem da paginacao      16.0ms      6.7ms     2.4x   Index Only Scan
    autocomplete (ILIKE)      186.1ms      0.7ms     278x   Index Scan

O autocomplete e o caso que decide: 186 ms POR TECLA DIGITADA, com Seq Scan sobre
a tabela inteira. Com dado de seed isso nunca apareceria — o planejador nem
considera indice em tabela pequena, porque varrer tudo sai mais barato.

**Dois indices, dois motivos diferentes:**

- `(municipio, uf, nome) WHERE ativo` — o filtro territorial da aplicacao usa
  municipio e uf, e a ordenacao e por nome. Com a ordem certa das colunas, o
  mesmo indice serve para filtrar E para ordenar, o que elimina o Sort. Parcial
  em `ativo` porque paciente inativo nunca aparece nessas telas: indice menor,
  mais barato de manter.

- GIN com trigramas em `nome` — `ILIKE '%texto%'` NAO usa indice B-tree, porque
  o curinga a esquerda impede a busca por prefixo. So um indice de trigramas
  resolve. Exige a extensao `pg_trgm`, que e "trusted" desde o PostgreSQL 13 e
  pode ser criada pelo dono do banco, sem superusuario.

**O que NAO foi adicionado, e por que:** as consultas sobre `internacoes` ja
resolviam por Index Scan (9 a 20 ms) usando os indices de chave estrangeira. Nao
ha indice composto para elas aqui porque a medicao nao mostrou necessidade —
indice que nao serve a nenhuma consulta so custa escrita e espaco.

Em SQLite nada disso se aplica: `gin_trgm_ops` nao existe e o banco de teste nao
tem volume. O indice composto e criado nos dois; o de trigramas, so em
PostgreSQL.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d9e15b7a42'
down_revision = 'b7f4c2e91a08'
branch_labels = None
depends_on = None


def upgrade():
    conexao = op.get_bind()
    postgres = conexao.dialect.name == "postgresql"

    op.create_index(
        "ix_pacientes_territorio",
        "pacientes",
        ["municipio", "uf", "nome"],
        unique=False,
        postgresql_where=sa.text("ativo"),
        sqlite_where=sa.text("ativo"),
    )

    if postgres:
        # `IF NOT EXISTS` porque a extensao pode ja ter sido criada por outro
        # ambiente que compartilhe o banco.
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            "CREATE INDEX ix_pacientes_nome_trgm "
            "ON pacientes USING gin (nome public.gin_trgm_ops)")


def downgrade():
    conexao = op.get_bind()
    if conexao.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_pacientes_nome_trgm")
        # A extensao NAO e removida: outro objeto do banco pode depender dela, e
        # derrubar extensao em downgrade e efeito colateral que ninguem espera.

    op.drop_index("ix_pacientes_territorio", table_name="pacientes")
