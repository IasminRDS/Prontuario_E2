"""Modo de chegada ao pronto-socorro

Revision ID: d81f4e0a76c5
Revises: c6b83f2a41d7
Create Date: 2026-08-09 10:00:00.000000

O formulário de acolhimento do PS oferece "Modo de chegada" com cinco opções —
espontâneo, SAMU, viatura policial, transferência e outros — e a coluna nunca
existiu. O campo era preenchido e descartado.

Ele já cobrou caro duas vezes: `tests/test_contrato_formularios.py` o cataloga
desde o início como campo descartado, e a exportação do relatório de PS o LIA,
derrubando o arquivo inteiro com AttributeError até a correção de 9.4.12.

**Por que virar coluna em vez de sair do formulário.** A distinção entre chegada
espontânea e chegada por SAMU não é cosmética: separa demanda espontânea de
demanda regulada, que são linhas de cuidado diferentes e financiadas de formas
diferentes. É o tipo de dado que o relatório de produção do PS precisa e que
não se recupera depois — ninguém reconstrói de memória como o paciente chegou.

A coluna é NULLABLE: os atendimentos já registrados chegaram sem que o dado
fosse guardado, e atribuir "espontâneo" a todos seria inventar procedência.
"""
import sqlalchemy as sa
from alembic import op

revision = "d81f4e0a76c5"
down_revision = "c6b83f2a41d7"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("atendimentos_ps") as lote:
        lote.add_column(sa.Column("modo_chegada", sa.String(length=20),
                                  nullable=True))


def downgrade():
    with op.batch_alter_table("atendimentos_ps") as lote:
        lote.drop_column("modo_chegada")
