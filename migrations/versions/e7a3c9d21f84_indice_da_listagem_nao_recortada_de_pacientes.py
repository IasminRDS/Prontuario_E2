"""Indice da listagem de pacientes sem recorte territorial

Revision ID: e7a3c9d21f84
Revises: b8e52d704fc1
Create Date: 2026-09-14 15:40:00.000000

Este indice tambem foi escolhido por medicao, nao por intuicao. Com 50 mil
pacientes sinteticos (`flask seed-volume`) e o protocolo do `flask
medir-desempenho` (descarta a partida, repete, reporta mediana e amplitude
interquartil), a listagem paginada SEM recorte territorial media:

    consulta                              antes      depois    plano depois
    listagem paginada (escopo SISTEMA)   55.76ms     1.24ms    Index Scan

**Por que faltava um indice, se `c3d9e15b7a42` ja indexou a busca.** Aquela
migration criou `ix_pacientes_territorio (municipio, uf, nome) WHERE ativo`, que
serve o usuario de UNIDADE: o filtro territorial fixa municipio e uf, e o mesmo
indice ordena por nome sem Sort. Mas o operador da plataforma (escopo SISTEMA ou
ESTADO) NAO filtra por municipio nem uf — e um indice cujas colunas de cabeca
sao (municipio, uf) nao serve uma consulta que so ordena por nome. O planejador
caia em Seq Scan da tabela inteira (50.001 linhas, 906 buffers) mais um top-N
heapsort. Um indice apenas em `nome`, parcial em `ativo`, da a ordem direto e
elimina o Sort (Index Scan, 22 buffers).

**O que este indice NAO e.** Nao e correcao urgente de producao: a listagem
alfabetica nacional sem recorte e o caminho do operador da plataforma, nao uma
tela de uso continuo. O valor e sobretudo empirico — e a "avaliacao de indices
compostos baseados em uso real" que a secao 13 anota, medida no proprio sistema.
O usuario de unidade, que e o caso comum, ja era servido pelo indice anterior e
nao muda.

Parcial em `ativo` pela mesma razao do territorial: paciente inativo nao aparece
nessas telas, entao indice menor e mais barato de manter. Em SQLite as opcoes
`postgresql_*`/`sqlite_where` produzem um indice comum sobre `nome`, inofensivo —
o banco de teste nao tem volume e o planejador nem o considera.
"""
from alembic import op
import sqlalchemy as sa


revision = 'e7a3c9d21f84'
down_revision = 'b8e52d704fc1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_pacientes_listagem_nome",
        "pacientes",
        ["nome"],
        unique=False,
        postgresql_where=sa.text("ativo"),
        sqlite_where=sa.text("ativo"),
    )


def downgrade():
    op.drop_index("ix_pacientes_listagem_nome", table_name="pacientes")
