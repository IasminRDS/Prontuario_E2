"""Eventos vitais do municipio: a referencia externa do comparativo

Revision ID: b8e52d704fc1
Revises: a7c41e93b8d2
Create Date: 2026-09-13 12:00:00.000000

O comparativo territorial media a producao DA REDE por municipio. Faltava o
termo de comparacao externo: quanto o municipio inteiro produz de evento
vital, independentemente de quem o atendeu. Sem isso, a tela responde "onde
minha rede trabalhou mais", e nao "como minha rede se situa no municipio".

Tres colunas, e o ano junto pela mesma razao da populacao: evento vital e
contagem anual, e comparar anos diferentes na mesma tabela produz um numero de
aparencia normal e significado nenhum.

**A fonte e o IBGE, nao o DATASUS, e a distincao importa.** Estes numeros vem
do REGISTRO CIVIL (cartorio), publicado nas tabelas 2609 e 2654 do SIDRA. O
SIM e o SINASC contam os mesmos eventos por outra via — a notificacao em
saude — e os totais NAO coincidem. Citar um como se fosse o outro seria erro
de fonte, e por isso a coluna guarda tambem de onde veio.

Nullable, como a populacao: municipio sem carga aparece como "—" na tela, e
nunca como zero. Zero e um valor; ausencia nao e.
"""
import sqlalchemy as sa
from alembic import op

revision = "b8e52d704fc1"
down_revision = "a7c41e93b8d2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("municipios") as lote:
        lote.add_column(sa.Column("nascidos_vivos", sa.Integer(), nullable=True))
        lote.add_column(sa.Column("obitos", sa.Integer(), nullable=True))
        lote.add_column(sa.Column("vitais_ano", sa.Integer(), nullable=True))
        lote.add_column(sa.Column("vitais_fonte", sa.String(60), nullable=True))


def downgrade():
    with op.batch_alter_table("municipios") as lote:
        lote.drop_column("vitais_fonte")
        lote.drop_column("vitais_ano")
        lote.drop_column("obitos")
        lote.drop_column("nascidos_vivos")
