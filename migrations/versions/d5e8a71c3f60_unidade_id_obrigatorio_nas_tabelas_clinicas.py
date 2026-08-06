"""unidade_id obrigatorio nas cinco tabelas clinicas

Revision ID: d5e8a71c3f60
Revises: c3d9e15b7a42
Create Date: 2026-08-06 21:40:00.000000

A coluna nasceu NULLABLE em b7f4c2e91a08 de proposito: naquele momento o backfill
nunca tinha sido exercitado com dado real, e declarar obrigatorio o que nao foi
testado e como afirmar cobertura sem medir — o erro que este projeto ja cometeu
com o proprio RLS.

Agora foi medido. Com 9.565 linhas sinteticas nas cinco tabelas, zeradas e
reprocessadas pelo backfill de b7f4c2e91a08, sobraram ZERO orfaos. E o caso
adversarial tambem foi provado: uma cirurgia sem internacao E sem criador nao tem
de onde herdar unidade, permanece nula, e o `SET NOT NULL` falha com erro cru do
PostgreSQL no meio da migration, abortando a transacao.

Por isso esta migration NAO faz o ALTER direto:

1. reexecuta o backfill (idempotente — so toca linha nula);
2. CONTA os orfaos que sobraram;
3. se houver, aborta com mensagem que diz a tabela, a quantidade e o que fazer;
4. so entao aplica NOT NULL.

A diferenca importa em producao: sem o passo 3, o operador recebe
"column contains null values" sem saber em qual das cinco tabelas, quantas linhas
sao, nem o que fazer com elas. Com ele, recebe o diagnostico.

**Por que nao atribuir uma unidade qualquer ao orfao:** seria inventar
procedencia de registro clinico. Um registro atribuido ao municipio errado e pior
que um registro invisivel — o invisivel alguem reclama, o errado entra em
relatorio e ninguem percebe.
"""
from alembic import op
import sqlalchemy as sa


revision = 'd5e8a71c3f60'
down_revision = 'c3d9e15b7a42'
branch_labels = None
depends_on = None

TABELAS = ("cirurgias", "encaminhamentos", "atendimentos_ps",
           "evolucoes_internacao", "itens_prescricao")


def _backfill_da_migration_anterior():
    """Reaproveita o SQL de b7f4c2e91a08 em vez de copia-lo.

    Copia diverge: alguem corrige a origem e esquece a copia, e a migration
    passa a preencher diferente do que preencheu da primeira vez.
    """
    import importlib.util
    import pathlib

    pasta = pathlib.Path(__file__).parent
    caminho = next(pasta.glob("b7f4c2e91a08_*.py"))
    spec = importlib.util.spec_from_file_location("_mig_escopo", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.BACKFILL


def upgrade():
    conexao = op.get_bind()
    backfill = _backfill_da_migration_anterior()

    for tabela in TABELAS:
        op.execute(sa.text(backfill[tabela]))

    orfaos = {}
    for tabela in TABELAS:
        n = conexao.exec_driver_sql(
            f"SELECT count(*) FROM {tabela} WHERE unidade_id IS NULL").scalar()
        if n:
            orfaos[tabela] = n

    if orfaos:
        detalhe = "; ".join(f"{t}: {n} linha(s)" for t, n in orfaos.items())
        raise RuntimeError(
            "Ha registros clinicos sem unidade resoluvel, e por isso a coluna "
            f"nao pode virar obrigatoria: {detalhe}.\n\n"
            "Estas linhas nao tem entidade-pai de onde herdar a unidade "
            "(internacao, prescricao, triagem, unidade de origem ou usuario "
            "criador). Resolva ANTES de repetir a migration, atribuindo a "
            "unidade correta a cada uma — a migration nao chuta procedencia de "
            "registro clinico.\n\n"
            "Para inspecionar:\n"
            "    SET app.nivel = 'SISTEMA';\n"
            "    SELECT id, paciente_id, criado_por FROM <tabela> "
            "WHERE unidade_id IS NULL;"
        )

    for tabela in TABELAS:
        with op.batch_alter_table(tabela, schema=None) as batch_op:
            batch_op.alter_column("unidade_id", existing_type=sa.Integer(),
                                  nullable=False)


def downgrade():
    for tabela in TABELAS:
        with op.batch_alter_table(tabela, schema=None) as batch_op:
            batch_op.alter_column("unidade_id", existing_type=sa.Integer(),
                                  nullable=True)
