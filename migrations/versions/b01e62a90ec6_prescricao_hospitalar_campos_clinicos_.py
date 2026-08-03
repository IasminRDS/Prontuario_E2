"""Prescricao hospitalar: campos clinicos, assinatura e detalhamento do item

Revision ID: b01e62a90ec6
Revises: c08b950ed8fb
Create Date: 2026-08-02 21:15:13.232271

A rota e os templates deste módulo sempre escreveram e leram campos que nunca
existiram no schema — criar prescrição hospitalar falhava com TypeError, capturado
por um `except` que o transformava em flash. Esta migration cria o que faltava.

O `prescricao_hosp_id` vira `prescricao_id` por RENAME, não por drop+add: o
autogenerate propôs drop+add, o que apagaria o vínculo de todo item já gravado.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b01e62a90ec6'
down_revision = 'c08b950ed8fb'
branch_labels = None
depends_on = None


def upgrade():
    # Rename preserva os dados e a constraint; o nome da FK acompanha a coluna.
    op.alter_column('itens_prescricao_hosp', 'prescricao_hosp_id',
                    new_column_name='prescricao_id')

    with op.batch_alter_table('itens_prescricao_hosp', schema=None) as batch_op:
        batch_op.add_column(sa.Column('concentracao', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('diluicao', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('velocidade', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('horarios', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('duracao', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('ordem', sa.Integer(), nullable=True))

    # Itens já gravados não têm ordem; sem isto ficariam com NULL e a ordenação
    # do template dependeria do acaso.
    op.execute('UPDATE itens_prescricao_hosp SET ordem = 0 WHERE ordem IS NULL')

    with op.batch_alter_table('prescricoes_hospitalares', schema=None) as batch_op:
        batch_op.add_column(sa.Column('unidade_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('validade_ate', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('dieta', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('decubito', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('sinais_vitais', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('assinada_em', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('assinada_por', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_pres_hosp_assinada_por_medicos',
                                    'medicos', ['assinada_por'], ['id'])
        batch_op.create_foreign_key('fk_pres_hosp_unidade_id_unidades',
                                    'unidades_saude', ['unidade_id'], ['id'])


def downgrade():
    with op.batch_alter_table('prescricoes_hospitalares', schema=None) as batch_op:
        batch_op.drop_constraint('fk_pres_hosp_unidade_id_unidades', type_='foreignkey')
        batch_op.drop_constraint('fk_pres_hosp_assinada_por_medicos', type_='foreignkey')
        batch_op.drop_column('assinada_por')
        batch_op.drop_column('assinada_em')
        batch_op.drop_column('sinais_vitais')
        batch_op.drop_column('decubito')
        batch_op.drop_column('dieta')
        batch_op.drop_column('validade_ate')
        batch_op.drop_column('unidade_id')

    with op.batch_alter_table('itens_prescricao_hosp', schema=None) as batch_op:
        batch_op.drop_column('ordem')
        batch_op.drop_column('duracao')
        batch_op.drop_column('horarios')
        batch_op.drop_column('velocidade')
        batch_op.drop_column('diluicao')
        batch_op.drop_column('concentracao')

    op.alter_column('itens_prescricao_hosp', 'prescricao_id',
                    new_column_name='prescricao_hosp_id')
