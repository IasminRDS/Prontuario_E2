"""Campos da AIH e da APAC que as telas pediam e o schema nao tinha

Revision ID: e2f7b48c9d13
Revises: d5e8a71c3f60
Create Date: 2026-08-08 12:00:00.000000

As telas de AIH e de APAC pediam campos que os models nao possuiam. Quem
preenchia via a mensagem de sucesso e perdia o que digitou — o defeito que
`tests/test_contrato_formularios.py` cataloga, e que estava registrado como
pendencia justamente porque completar exigia decidir o schema.

A decisao foi tomada com base no que a AIH e a APAC SAO: documentos do SUS com
campos definidos. Nao ha invencao aqui, so a transcricao dos campos que as
proprias telas ja nomeavam.

**Tres campos do formulario NAO viraram coluna, de proposito:**

`dias_permanencia` e derivado de `data_internacao` e `data_saida`. Guardar o
derivado ao lado das duas datas cria a possibilidade de divergirem, e quando
divergem nao ha como saber qual esta certo. Virou propriedade no model.

`cid` e `procedimento`, na APAC, nao eram campos faltando: eram os nomes que o
template usava para `cid_principal` e `procedimento_principal`, que ja existiam.
Criar coluna para eles teria duplicado dado — pior que a lacuna original. O
template e que foi corrigido.

`valor_total` continua coluna, e nao propriedade de `valor_sh + valor_sp`,
porque `aih_lista` o soma em SQL (`func.sum`) e propriedade Python nao agrega no
banco. A rota passa a calcula-lo na escrita, de modo que os tres nunca divergem.
"""
import sqlalchemy as sa
from alembic import op

revision = "e2f7b48c9d13"
down_revision = "d5e8a71c3f60"
branch_labels = None
depends_on = None


# (nome, tipo) — a ordem e a do formulario, para a leitura lado a lado.
COLUNAS_AIH = [
    ("competencia", sa.String(length=7)),          # AAAA/MM
    ("tipo_aih", sa.String(length=2)),             # 1 normal, 5 longa permanencia
    ("carater_internacao", sa.String(length=2)),   # 01 eletivo, 02 urgencia...
    ("cid_secundario", sa.String(length=10)),
    ("procedimento_secundario", sa.String(length=255)),
    ("data_internacao", sa.Date()),
    ("data_saida", sa.Date()),
    ("motivo_saida", sa.String(length=40)),
    ("valor_sh", sa.Numeric(10, 2)),               # servicos hospitalares
    ("valor_sp", sa.Numeric(10, 2)),               # servicos profissionais
    ("observacoes", sa.Text()),
]

COLUNAS_APAC = [
    ("competencia", sa.String(length=7)),
    ("tipo", sa.String(length=20)),                # inicial, continuidade, unica
    ("justificativa", sa.Text()),
]


def upgrade():
    # Todas NULLABLE: sao autorizacoes ja existentes, emitidas antes destes
    # campos. Exigir preenchimento retroativo seria inventar dado de faturamento.
    with op.batch_alter_table("faturamento_aih") as lote:
        for nome, tipo in COLUNAS_AIH:
            lote.add_column(sa.Column(nome, tipo, nullable=True))

    with op.batch_alter_table("faturamento_apac") as lote:
        for nome, tipo in COLUNAS_APAC:
            lote.add_column(sa.Column(nome, tipo, nullable=True))

    # A competencia e o recorte de TODO relatorio de faturamento do SUS: e por
    # ela que se fecha o mes. Sem indice, o filtro varre a tabela inteira.
    op.create_index("ix_faturamento_aih_competencia", "faturamento_aih",
                    ["competencia"])
    op.create_index("ix_faturamento_apac_competencia", "faturamento_apac",
                    ["competencia"])


def downgrade():
    op.drop_index("ix_faturamento_apac_competencia", table_name="faturamento_apac")
    op.drop_index("ix_faturamento_aih_competencia", table_name="faturamento_aih")

    with op.batch_alter_table("faturamento_apac") as lote:
        for nome, _tipo in reversed(COLUNAS_APAC):
            lote.drop_column(nome)

    with op.batch_alter_table("faturamento_aih") as lote:
        for nome, _tipo in reversed(COLUNAS_AIH):
            lote.drop_column(nome)
