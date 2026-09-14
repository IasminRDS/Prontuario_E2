# -*- coding: utf-8 -*-
"""`flask backup-validar`: o backup restaura e bate com a origem?

O procedimento existia como verificação manual feita uma vez. Verificação manual
feita uma vez não vale nada três meses depois — por isso virou comando, e o
comando tem teste.

A divisão aqui é deliberada: a lógica pura (reescrita de schema, seleção de
binário, recusa em SQLite) roda em qualquer ambiente; o restore de verdade só
roda onde há PostgreSQL **e** cliente instalado, e é pulado com motivo explícito
no resto. Um teste de integração que se pula em silêncio é pior que não existir.
"""

import pytest

from services import backup_validacao as bv


# --------------------------------------------------------- lógica pura
def test_reescrita_troca_o_schema_de_todas_as_formas():
    sql = (
        "CREATE SCHEMA public;\n"
        "SET search_path = public, pg_catalog;\n"
        "CREATE TABLE public.pacientes (id integer);\n"
        "COPY public.pacientes (id) FROM stdin;\n"
        "ALTER TABLE ONLY public.pacientes ADD CONSTRAINT pk PRIMARY KEY (id);\n"
    )
    saida = bv._reescrever_schema(sql, "alvo")

    assert "public." not in saida, "sobrou referência a public"
    assert "CREATE SCHEMA alvo;" in saida
    assert "SET search_path = alvo;" in saida
    assert "COPY alvo.pacientes" in saida
    assert "ALTER TABLE ONLY alvo.pacientes" in saida


def test_reescrita_nao_toca_palavra_public_solta():
    """`public` dentro de dado não pode virar nome de schema."""
    sql = "INSERT INTO public.notas VALUES ('atendimento ao publico', 'public');"
    saida = bv._reescrever_schema(sql, "alvo")

    assert "alvo.notas" in saida
    assert "'atendimento ao publico'" in saida
    assert "'public'" in saida


def test_arquivo_inexistente_e_recusado(app):
    with app.app_context():
        with pytest.raises(bv.BackupInvalido, match="não encontrado"):
            bv.validar("nao/existe/backup.dump")


def test_sqlite_recusa_com_motivo(app, tmp_path):
    """Em SQLite o comando precisa dizer por que não se aplica, não estourar."""
    from extensions import db

    with app.app_context():
        if db.engine.dialect.name == "postgresql":
            pytest.skip("este caso é sobre o comportamento em SQLite")

        falso = tmp_path / "backup.dump"
        falso.write_bytes(b"PGDMP")
        with pytest.raises(bv.BackupInvalido, match="só existe para PostgreSQL"):
            bv.validar(str(falso))


# --------------------------------------------------- integração de verdade
def _cliente_disponivel():
    from routes.backup import _localizar_pg_dump

    return _localizar_pg_dump() is not None


@pytest.fixture
def dump_do_banco(app, tmp_path):
    """Gera um dump do banco de teste com o mesmo caminho que a aplicação usa."""
    import os
    import subprocess

    from extensions import db
    from routes.backup import _localizar_pg_dump

    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("restore real só se aplica a PostgreSQL")
        if not _cliente_disponivel():
            pytest.skip("cliente do PostgreSQL não instalado nesta máquina")
        pg_dump = _localizar_pg_dump()
        url = db.engine.url
    destino = tmp_path / "teste.dump"

    ambiente = dict(os.environ)
    ambiente["PGPASSWORD"] = url.password or ""
    ambiente["PGOPTIONS"] = "-c app.nivel=SISTEMA"

    resultado = subprocess.run(
        [pg_dump, "--host", url.host or "localhost", "--port", str(url.port or 5432),
         "--dbname", url.database, "--username", url.username or "",
         "--format", "custom", "--no-owner", "--no-privileges",
         "--enable-row-security", "--file", str(destino)],
        env=ambiente, capture_output=True, text=True)
    assert resultado.returncode == 0, f"pg_dump falhou: {resultado.stderr[:300]}"
    return destino


def test_restore_reproduz_as_contagens(app, dados_clinicos, dump_do_banco):
    """Ida e volta: dump do banco vivo, restaura, e cada tabela tem de bater."""
    with app.app_context():
        comparacoes, erros = bv.validar(str(dump_do_banco))

    assert not erros, f"o restore acusou erros: {erros[:5]}"
    assert comparacoes, "nenhuma tabela foi conferida"

    divergentes = [(t, a, b) for t, a, b in comparacoes if a != b]
    assert not divergentes, f"contagem diferente após restore: {divergentes}"


def test_validacao_nao_deixa_schema_para_tras(app, dump_do_banco):
    """O schema temporário some mesmo quando a validação termina bem."""
    import sqlalchemy as sa

    from extensions import db

    with app.app_context():
        bv.validar(str(dump_do_banco))

        with db.engine.connect() as c:
            restou = c.execute(sa.text(
                "select count(*) from information_schema.schemata "
                "where schema_name = :s"), {"s": bv.SCHEMA_VALIDACAO}).scalar()
    assert restou == 0, "o schema de validação ficou no banco"


def test_dump_corrompido_e_recusado(app, tmp_path):
    """Arquivo que não é dump precisa falhar com mensagem, não com traceback."""
    from extensions import db

    with app.app_context():
        if db.engine.dialect.name != "postgresql" or not _cliente_disponivel():
            pytest.skip("precisa de PostgreSQL com cliente instalado")

        lixo = tmp_path / "corrompido.dump"
        lixo.write_bytes(b"isto nao e um dump" * 100)

        with pytest.raises(bv.BackupInvalido, match="pg_restore"):
            bv.validar(str(lixo))


# --- o detector que não detectava, porque lia a tradução -------------------

class _Resultado:
    """O que `subprocess.run` devolve, reduzido ao que a decisão usa."""

    def __init__(self, returncode, stderr=""):
        self.returncode, self.stderr = returncode, stderr


PORTUGUES = (
    'psql:/tmp/dump.sql:25: ERRO:  esquema "validacao_restore" já existe\n'
    'psql:/tmp/dump.sql:31: ERRO:  relação "pacientes" já existe\n'
)
INGLES = (
    'psql:/tmp/dump.sql:25: ERROR:  schema "validacao_restore" already exists\n'
)


def test_restore_que_falhou_em_portugues_e_acusado():
    """O defeito: a decisão lia a palavra "ERROR", que é TRADUZIDA.

    Num servidor em português o PostgreSQL escreve "ERRO:", a lista de erros
    saía vazia e a validação declarava íntegro um restore que errou em todas as
    linhas. O comando existe porque backup não restaurado é um arquivo, e não um
    backup — e era exatamente isso que ele estava aprovando.

    Forçar `lc_messages=C` não serve de correção: é parâmetro que só superusuário
    altera, e o papel da aplicação não é nem deve ser superusuário.
    """
    assert bv._erros_de(_Resultado(1, PORTUGUES)), (
        "restore que falhou em servidor traduzido passou por íntegro")


def test_restore_que_falhou_em_ingles_tambem(): 
    assert bv._erros_de(_Resultado(1, INGLES))


def test_restore_limpo_nao_inventa_erro():
    """O outro sentido: sem isto, bastaria devolver sempre uma lista cheia."""
    assert bv._erros_de(_Resultado(0, "")) == []
    assert bv._erros_de(_Resultado(0, "NOTICE:  extensão já existe")) == [], (
        "aviso de rotina virou erro — e validação que reprova sempre ensina a "
        "ignorar o resultado")


def test_falha_sem_texto_ainda_e_falha():
    """Código de saída não-zero sem stderr não pode virar lista vazia."""
    assert bv._erros_de(_Resultado(2, ""))


# --- e o schema de origem, que era presumido `public` ---------------------

def test_reescrita_parte_do_schema_da_aplicacao_e_nao_de_public():
    """`public` é o caso comum e não é o único.

    A suíte vive num `teste_automatizado_<pid>`, e uma instalação endurecida põe
    a aplicação em schema próprio. Com a origem fixa em `public`, a reescrita não
    casava com nada: o SQL seguia nomeando o schema ORIGINAL, e o restore que se
    anuncia isolado passava a escrever no banco vivo.
    """
    sql = ('CREATE SCHEMA app_hospital;\n'
           'SET search_path = app_hospital;\n'
           'CREATE TABLE app_hospital.pacientes (id integer);\n')
    saida = bv._reescrever_schema(sql, "validacao_restore", origem="app_hospital")

    assert "app_hospital." not in saida, "sobrou referência ao schema de origem"
    assert "CREATE SCHEMA validacao_restore;" in saida
    assert "validacao_restore.pacientes" in saida


def test_reescrita_continua_funcionando_para_public():
    """A instalação comum não pode ter sido quebrada pela generalização."""
    sql = 'CREATE SCHEMA public;\nCREATE TABLE public.pacientes (id integer);\n'
    saida = bv._reescrever_schema(sql, "validacao_restore")

    assert "CREATE SCHEMA validacao_restore;" in saida
    assert "validacao_restore.pacientes" in saida
