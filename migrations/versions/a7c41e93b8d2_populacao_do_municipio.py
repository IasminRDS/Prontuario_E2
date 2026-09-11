"""Populacao do municipio: o denominador que faltava

Revision ID: a7c41e93b8d2
Revises: d81f4e0a76c5
Create Date: 2026-09-11 12:00:00.000000

O sistema agregava por municipio e so sabia CONTAR. Contagem compara mal:
Salvador sempre tera mais atendimentos que Bom Jesus da Lapa, e disso nao se
conclui nada sobre desempenho. Indicador exige denominador, e o denominador da
saude publica e a populacao residente.

**Duas colunas, e nao uma.** `populacao_ano` existe porque populacao e
estimativa referida a um ano. Taxa calculada com denominadores de anos
diferentes nao e comparavel, e sem o ano guardado nao ha como saber que se
esta comparando coisas distintas — o erro some dentro de um numero de aparencia
normal.

**Nullable, e isso e decisao.** Municipio sem populacao carregada nao pode
virar taxa zero: zero e um valor, e valor errado aqui le-se como resultado. O
model devolve `None` nesse caso e a tela mostra "sem denominador". A carga e
opcional justamente porque a relacao completa vem do IBGE, fora do repositorio.

A fonte fica de fora do codigo de proposito: sao 5.570 municipios, a estimativa
muda todo ano, e embutir a tabela seria embutir uma foto que envelhece em
silencio. O carregamento e por `flask municipios-importar`, que passa a aceitar
as colunas opcionais `populacao` e `populacao_ano`.
"""
import sqlalchemy as sa
from alembic import op

revision = "a7c41e93b8d2"
down_revision = "d81f4e0a76c5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("municipios") as lote:
        lote.add_column(sa.Column("populacao", sa.Integer(), nullable=True))
        lote.add_column(sa.Column("populacao_ano", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("municipios") as lote:
        lote.drop_column("populacao_ano")
        lote.drop_column("populacao")
