"""Escopo territorial nas oito tabelas sensiveis que ainda estavam fora

Revision ID: c6b83f2a41d7
Revises: f3a95c07be21
Create Date: 2026-08-08 16:00:00.000000

Dez tabelas nao tinham `unidade_id` e, portanto, nenhuma politica de RLS. A
secao 11.1 da monografia declarava isso, mas declarar a lacuna nao e o mesmo que
nao te-la: seis delas guardam dado identificavel de paciente e duas sao filhas
de tabelas ja protegidas.

**Seis com `paciente_id` e dado identificavel.** `consentimentos_lgpd` prova a
base legal do tratamento; `vacinas_aplicadas` alimenta o cartao do Portal do
Cidadao; `envios_rnds` guarda o payload FHIR, que e o conteudo clinico
serializado; `documentos_assinados`, `faturamento_aih` e `faturamento_apac`
carregam CID e procedimento.

**Duas por coerencia.** `itens_prescricao_hosp` e `administracoes_med` so se
alcancam por um pai ja sob politica — e esse e EXATAMENTE o argumento que a
secao 9.4.1 derrubou. As cinco tabelas clinicas estavam desprotegidas pelo mesmo
raciocinio, e uma consulta que faca `join` direto o contorna. O projeto ja
escolheu desnormalizar as outras cinco para nao depender disso.

**`candidatos_duplicata` fica FORA, e de proposito.** Ela existe para reconciliar
a mesma pessoa cadastrada em municipios diferentes. Escopo territorial ali
destruiria a funcao: o candidato a duplicata que interessa e justamente o que
esta na outra unidade. E o mesmo motivo pelo qual `pacientes` esta fora.

**`agenda_eventos` tambem fica fora, por outro motivo.** Ela nao tem
`paciente_id` NEM uma unica chave estrangeira — nao ha de onde derivar unidade,
e nao ha dado de paciente a proteger. A ausencia total de relacoes numa tabela
de agenda e questao de modelagem, anterior e independente do isolamento.

## A coluna nasce NULLABLE, e isso tem consequencia

Mesma disciplina de `b7f4c2e91a08`: adiciona nula, preenche pelo pai, e o
`NOT NULL` fica para depois de medido. Mas aqui a consequencia precisa ser dita:
com a politica ativa, linha com `unidade_id` nulo fica INVISIVEL para todos os
escopos, menos SISTEMA. E falha fechada, que e o comportamento correto — e
significa que registro que o backfill nao resolver some da tela ate alguem
resolver.

`vacinas_aplicadas` e o caso limite: nao tem `criado_por` nem FK para unidade —
so uma coluna `unidade` de TEXTO LIVRE. O backfill tenta casar esse texto com o
nome da unidade e desiste do resto. Atribuir unidade arbitraria seria inventar
procedencia de registro clinico, que e pior que o registro invisivel: o
invisivel e notado, o incorreto entra em relatorio sem ninguem perceber.
"""
import sqlalchemy as sa
from alembic import op

revision = "c6b83f2a41d7"
down_revision = "f3a95c07be21"
branch_labels = None
depends_on = None


TABELAS = [
    "itens_prescricao_hosp",
    "administracoes_med",
    "documentos_assinados",
    "consentimentos_lgpd",
    "faturamento_aih",
    "faturamento_apac",
    "envios_rnds",
    "vacinas_aplicadas",
]

# Cada origem e a MAIS PROXIMA disponivel: o pai clinico quando existe, e o
# usuario que registrou como ultimo recurso. Usuario e recurso pior porque um
# operador com alcance municipal pode registrar em unidade que nao e a dele.
BACKFILL = {
    "itens_prescricao_hosp": """
        UPDATE itens_prescricao_hosp SET unidade_id =
            (SELECT p.unidade_id FROM prescricoes_hospitalares p
              WHERE p.id = itens_prescricao_hosp.prescricao_id)
        WHERE unidade_id IS NULL
    """,
    "administracoes_med": """
        UPDATE administracoes_med SET unidade_id = COALESCE(
            (SELECT p.unidade_id
               FROM itens_prescricao_hosp i
               JOIN prescricoes_hospitalares p ON p.id = i.prescricao_id
              WHERE i.id = administracoes_med.item_prescricao_id),
            (SELECT u.unidade_id FROM users u
              WHERE u.id = administracoes_med.administrado_por)
        ) WHERE unidade_id IS NULL
    """,
    "documentos_assinados": """
        UPDATE documentos_assinados SET unidade_id =
            (SELECT u.unidade_id FROM users u
              WHERE u.id = documentos_assinados.assinado_por)
        WHERE unidade_id IS NULL
    """,
    "consentimentos_lgpd": """
        UPDATE consentimentos_lgpd SET unidade_id =
            (SELECT u.unidade_id FROM users u
              WHERE u.id = consentimentos_lgpd.registrado_por)
        WHERE unidade_id IS NULL
    """,
    "faturamento_aih": """
        UPDATE faturamento_aih SET unidade_id = COALESCE(
            (SELECT i.unidade_id FROM internacoes i
              WHERE i.id = faturamento_aih.internacao_id),
            (SELECT u.unidade_id FROM users u
              WHERE u.id = faturamento_aih.criado_por),
            (SELECT m.unidade_id FROM medicos m
              WHERE m.id = faturamento_aih.medico_solicitante_id)
        ) WHERE unidade_id IS NULL
    """,
    "faturamento_apac": """
        UPDATE faturamento_apac SET unidade_id = COALESCE(
            (SELECT u.unidade_id FROM users u
              WHERE u.id = faturamento_apac.criado_por),
            (SELECT m.unidade_id FROM medicos m
              WHERE m.id = faturamento_apac.medico_solicitante_id)
        ) WHERE unidade_id IS NULL
    """,
    "envios_rnds": """
        UPDATE envios_rnds SET unidade_id =
            (SELECT u.unidade_id FROM users u
              WHERE u.id = envios_rnds.criado_por)
        WHERE unidade_id IS NULL
    """,
    # Sem FK para unidade e sem `criado_por`: so resta casar o texto livre.
    "vacinas_aplicadas": """
        UPDATE vacinas_aplicadas SET unidade_id =
            (SELECT s.id FROM unidades_saude s
              WHERE s.nome = vacinas_aplicadas.unidade)
        WHERE unidade_id IS NULL AND unidade IS NOT NULL
    """,
}


def upgrade():
    for tabela in TABELAS:
        with op.batch_alter_table(tabela, schema=None) as lote:
            lote.add_column(sa.Column("unidade_id", sa.Integer(), nullable=True))
            lote.create_index(lote.f(f"ix_{tabela}_unidade_id"),
                              ["unidade_id"], unique=False)
            # Constraint nomeada: anônima quebra o modo batch do SQLite.
            lote.create_foreign_key(
                f"fk_{tabela}_unidade_id_unidades_saude",
                "unidades_saude", ["unidade_id"], ["id"])

    conexao = op.get_bind()
    for tabela in TABELAS:
        conexao.execute(sa.text(BACKFILL[tabela]))

    # Relata o que sobrou. Nao aborta: diferente de `d5e8a71c3f60`, aqui a
    # coluna continua nula e a politica falha fechada — o registro irresoluvel
    # some da tela em vez de contaminar relatorio. Mas quem roda a migration
    # precisa SABER quantos, senao descobre pela ausencia.
    restantes = []
    for tabela in TABELAS:
        n = conexao.execute(
            sa.text(f"SELECT count(*) FROM {tabela} WHERE unidade_id IS NULL")
        ).scalar()
        if n:
            restantes.append(f"  {tabela}: {n} sem unidade resolvida")
    if restantes:
        print("\nATENCAO — linhas que a politica passara a ocultar:")
        print("\n".join(restantes))
        print("Resolva antes de considerar a migracao concluida.\n")

    if conexao.dialect.name != "postgresql":
        return  # SQLite nao tem RLS; o filtro em Python continua valendo

    from utils.rls import aplicar_politicas

    aplicar_politicas(conexao, TABELAS)


def downgrade():
    conexao = op.get_bind()
    if conexao.dialect.name == "postgresql":
        from utils.rls import remover_politicas

        remover_politicas(conexao, TABELAS)

    for tabela in reversed(TABELAS):
        with op.batch_alter_table(tabela, schema=None) as lote:
            lote.drop_constraint(f"fk_{tabela}_unidade_id_unidades_saude",
                                 type_="foreignkey")
            lote.drop_index(lote.f(f"ix_{tabela}_unidade_id"))
            lote.drop_column("unidade_id")
