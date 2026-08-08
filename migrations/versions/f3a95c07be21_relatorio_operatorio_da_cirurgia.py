"""Relatorio operatorio da cirurgia: as cinco colunas que a rota ja gravava

Revision ID: f3a95c07be21
Revises: e2f7b48c9d13
Create Date: 2026-08-08 14:00:00.000000

A pendencia registrada era um campo: `cid` em `cirurgia/relatorio_form.html`.
Ao disparar a rota de finalizacao, o problema mostrou-se muito maior.

`cirurgia.finalizar` atribuia CINCO campos que nao sao colunas de `Cirurgia`:
relatorio, achados, intercorrencias, materiais e cid_pos_op. Em Python isso e
legal — atribuir atributo nao mapeado num objeto do SQLAlchemy nao levanta erro,
apenas nao persiste. Entao a rota respondia 200, o status ia para `realizada`, a
sala ia para limpeza, a mensagem dizia "Cirurgia finalizada!" e o RELATORIO
OPERATORIO INTEIRO era descartado.

E o outro lado do defeito que a secao 9.4.6 do TCC descreve: la, agendar
cirurgia nunca criou uma linha; aqui, finalizar nunca guardou o relatorio. As
duas pontas do mesmo fluxo, pelo mesmo motivo — kwargs e atributos conferidos
contra um model que nao os tem.

Verificado disparando a rota antes e depois: antes, os cinco atributos nem
existiam no objeto recarregado do banco; depois, os cinco voltam com o que foi
enviado.

**`cid_pos_op` e nao `cid`:** o formulario ja nomeava o campo assim, e a rota ja
o lia assim. O que estava errado era o `value` do input, que pre-preenchia de
`cir.cid`. Diagnostico pos-operatorio e informacao distinta da hipotese com que
se agendou — sao dois campos, nao um com dois nomes. Se o agendamento precisar
registrar o CID pre-operatorio, isso e outra coluna e outra decisao.
"""
import sqlalchemy as sa
from alembic import op

revision = "f3a95c07be21"
down_revision = "e2f7b48c9d13"
branch_labels = None
depends_on = None


COLUNAS = [
    ("relatorio", sa.Text()),
    ("achados", sa.Text()),
    ("intercorrencias", sa.Text()),
    ("materiais", sa.Text()),
    ("cid_pos_op", sa.String(length=10)),
]


def upgrade():
    # Nullable: as cirurgias ja finalizadas perderam o relatorio de forma
    # irrecuperavel — ele nunca chegou ao banco. Exigir preenchimento
    # retroativo seria pedir que alguem reconstruisse de memoria um documento
    # clinico, que e pior que a lacuna.
    with op.batch_alter_table("cirurgias") as lote:
        for nome, tipo in COLUNAS:
            lote.add_column(sa.Column(nome, tipo, nullable=True))


def downgrade():
    with op.batch_alter_table("cirurgias") as lote:
        for nome, _tipo in reversed(COLUNAS):
            lote.drop_column(nome)
