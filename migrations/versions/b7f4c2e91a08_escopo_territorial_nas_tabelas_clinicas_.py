"""Escopo territorial nas tabelas clinicas que ficavam fora do RLS

Revision ID: b7f4c2e91a08
Revises: 95ac871bfcd4
Create Date: 2026-08-06 21:10:00.000000

O RLS protegia apenas as tabelas que ja tinham `unidade_id`, e cinco tabelas
clinicas centrais nao tinham: cirurgias, encaminhamentos, atendimentos_ps,
evolucoes_internacao e itens_prescricao. Para elas a promessa do RLS — "uma
consulta que esqueca o filtro nao enxerga registro de outro municipio" — nao
valia, e o isolamento dependia so do Python.

Desnormalizamos `unidade_id` em vez de escrever politica com subconsulta ao pai:
a politica passa a ser a mesma comparacao direta das demais tabelas
(`unidade_id = current_setting(...)`), sem um EXISTS por linha lida. O custo e a
redundancia, que e o preco conhecido de RLS performatico.

O backfill sai do PAI de cada tabela, nao de chute:

    cirurgias           <- internacoes.unidade_id (quando ha internacao),
                           senao users.unidade_id de quem criou
    encaminhamentos     <- unidade_origem_id (a propria tabela ja tinha)
    atendimentos_ps     <- triagens.unidade_id, senao users.unidade_id
    evolucoes_internacao<- internacoes.unidade_id
    itens_prescricao    <- prescricoes.unidade_id

A coluna nasce NULLABLE de proposito. Linha antiga sem pai resoluvel fica NULL, e
NULL nao casa com nenhuma politica: fica invisivel para todo escopo territorial e
so aparece no nivel SISTEMA. Falha fechada — o contrario (assumir uma unidade
qualquer) atribuiria registro clinico ao municipio errado, que e pior que
esconder.
"""
from alembic import op
import sqlalchemy as sa


revision = 'b7f4c2e91a08'
down_revision = '95ac871bfcd4'
branch_labels = None
depends_on = None


# tabela -> SQL de backfill.
#
# Sem alias de tabela no UPDATE: o SQLite não aceita `UPDATE t alias SET ...`, e
# a cadeia precisa rodar nos dois bancos. As subconsultas referenciam a tabela
# alvo pelo nome completo, o que é válido em ambos.
BACKFILL = {
    "cirurgias": """
        UPDATE cirurgias SET unidade_id = COALESCE(
            (SELECT i.unidade_id FROM internacoes i
              WHERE i.id = cirurgias.internacao_id),
            (SELECT u.unidade_id FROM users u WHERE u.id = cirurgias.criado_por)
        ) WHERE unidade_id IS NULL
    """,
    "encaminhamentos": """
        UPDATE encaminhamentos SET unidade_id = unidade_origem_id
        WHERE unidade_id IS NULL
    """,
    "atendimentos_ps": """
        UPDATE atendimentos_ps SET unidade_id = COALESCE(
            (SELECT t.unidade_id FROM triagens t
              WHERE t.id = atendimentos_ps.triagem_id),
            (SELECT u.unidade_id FROM users u
              WHERE u.id = atendimentos_ps.criado_por)
        ) WHERE unidade_id IS NULL
    """,
    "evolucoes_internacao": """
        UPDATE evolucoes_internacao SET unidade_id =
            (SELECT i.unidade_id FROM internacoes i
              WHERE i.id = evolucoes_internacao.internacao_id)
        WHERE unidade_id IS NULL
    """,
    "itens_prescricao": """
        UPDATE itens_prescricao SET unidade_id =
            (SELECT p.unidade_id FROM prescricoes p
              WHERE p.id = itens_prescricao.prescricao_id)
        WHERE unidade_id IS NULL
    """,
}

TABELAS = tuple(BACKFILL)


def upgrade():
    for tabela in TABELAS:
        with op.batch_alter_table(tabela, schema=None) as batch_op:
            batch_op.add_column(sa.Column('unidade_id', sa.Integer(), nullable=True))
            batch_op.create_index(batch_op.f(f'ix_{tabela}_unidade_id'),
                                  ['unidade_id'], unique=False)
            # Constraint nomeada: anonima quebra o modo batch do SQLite.
            batch_op.create_foreign_key(
                f'fk_{tabela}_unidade_id_unidades_saude',
                'unidades_saude', ['unidade_id'], ['id'])

    for tabela in TABELAS:
        op.execute(sa.text(BACKFILL[tabela]))

    # As politicas so existem em PostgreSQL; em SQLite o upgrade para aqui.
    if op.get_bind().dialect.name != "postgresql":
        return

    from utils.rls import aplicar_politicas

    aplicar_politicas(op.get_bind(), TABELAS)


def downgrade():
    conexao = op.get_bind()
    if conexao.dialect.name == "postgresql":
        from utils.rls import remover_politicas

        remover_politicas(conexao, TABELAS)

    for tabela in TABELAS:
        with op.batch_alter_table(tabela, schema=None) as batch_op:
            batch_op.drop_constraint(f'fk_{tabela}_unidade_id_unidades_saude',
                                     type_='foreignkey')
            batch_op.drop_index(batch_op.f(f'ix_{tabela}_unidade_id'))
            batch_op.drop_column('unidade_id')
