# -*- coding: utf-8 -*-
"""Valida um backup restaurando-o de verdade e conferindo as contagens.

Backup que nunca foi restaurado não é backup: é um arquivo. O único jeito de
saber se ele presta é aplicá-lo e comparar o resultado com a origem — e isso
precisa ser repetível, não uma verificação manual feita uma vez e esquecida.

**Restaura num SCHEMA, não num banco novo.** `CREATE DATABASE` exige `CREATEDB`,
que o papel da aplicação não tem (e não deve ter); `CREATE SCHEMA` exige só
`CREATE` no próprio banco, que ele tem. É o mesmo isolamento que a suíte de
testes usa. O schema é destruído no fim, inclusive quando a validação falha.

**Por que `psql` e não a conexão do SQLAlchemy:** o dump em formato custom vira
SQL com `COPY ... FROM stdin`, e o psycopg2 não executa COPY por `execute()`. O
`psql` executa.

**Higiene:** o SQL intermediário é o banco inteiro em TEXTO CLARO. Fica em
arquivo temporário e é apagado no `finally` — inclusive se o restore explodir.
Quem rodar isto em produção precisa de um diretório temporário com acesso
restrito; o dado clínico passa por lá.
"""
import os
import pathlib
import re
import subprocess
import tempfile

# Amostra conferida por padrão: as tabelas cuja perda dói, mais as de apoio que
# denunciam dump parcial (`users` e `unidades_saude` quase nunca estão vazias).
TABELAS_PADRAO = (
    "pacientes", "prontuarios", "internacoes", "cirurgias", "encaminhamentos",
    "atendimentos_ps", "prescricoes", "exames_solicitados", "triagens",
    "audit_logs", "unidades_saude", "users", "leitos",
)

SCHEMA_VALIDACAO = "validacao_restore"


class BackupInvalido(Exception):
    """O backup não restaurou, ou restaurou diferente da origem."""


def _binario(nome):
    from routes.backup import _localizar_pg_dump

    pg_dump = _localizar_pg_dump()
    if not pg_dump:
        raise BackupInvalido(
            "cliente do PostgreSQL não encontrado. Instale-o ou aponte "
            "PG_DUMP_PATH para o executável."
        )
    caminho = pathlib.Path(pg_dump).parent / nome
    if not caminho.is_file():
        raise BackupInvalido(f"{nome} não encontrado em {caminho.parent}")
    return str(caminho)


def _ambiente(url):
    amb = dict(os.environ)
    amb["PGPASSWORD"] = url.password or ""
    # Sem o escopo de sistema, o RLS esconde linhas de outras unidades e a
    # contagem da ORIGEM sairia menor que a real — o teste passaria por engano.
    amb["PGOPTIONS"] = "-c app.nivel=SISTEMA"
    return amb


def _reescrever_schema(sql, schema):
    """Aponta o SQL do dump para o schema de validação em vez de `public`."""
    sql = re.sub(r"\bpublic\.", f"{schema}.", sql)
    sql = sql.replace("CREATE SCHEMA public;", f"CREATE SCHEMA {schema};")
    return re.sub(r"SET search_path = [^;]+;", f"SET search_path = {schema};", sql)


def validar(caminho_dump, tabelas=TABELAS_PADRAO, schema=SCHEMA_VALIDACAO):
    """Restaura `caminho_dump` num schema e compara contagens com a origem.

    Devolve (comparacoes, erros_do_restore), onde `comparacoes` é uma lista de
    (tabela, origem, restaurado). Levanta `BackupInvalido` se nem der para
    restaurar. Não decide aprovação — quem chama compara.
    """
    import sqlalchemy as sa

    from extensions import db

    dump = pathlib.Path(caminho_dump)
    if not dump.is_file():
        raise BackupInvalido(f"arquivo não encontrado: {dump}")

    if db.engine.dialect.name != "postgresql":
        raise BackupInvalido(
            "validação de restore só existe para PostgreSQL; em SQLite o "
            "backup é uma cópia do arquivo e se confere abrindo o banco.")

    pg_restore, psql = _binario("pg_restore.exe" if os.name == "nt" else "pg_restore"), \
        _binario("psql.exe" if os.name == "nt" else "psql")

    url = db.engine.url
    amb = _ambiente(url)
    conexao = ["--host", url.host or "localhost", "--port", str(url.port or 5432),
               "--username", url.username or "", "--dbname", url.database]

    temporario = pathlib.Path(tempfile.mkdtemp(prefix="validacao_backup_"))
    sql_bruto = temporario / "dump.sql"
    sql_schema = temporario / "dump_schema.sql"

    def _psql(*args):
        return subprocess.run([psql] + conexao + ["-v", "ON_ERROR_STOP=0"] + list(args),
                              env=amb, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")

    try:
        saida = subprocess.run(
            [pg_restore, "--no-owner", "--no-privileges", "-f", str(sql_bruto),
             str(dump)],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if saida.returncode != 0:
            raise BackupInvalido(
                f"pg_restore não conseguiu ler o arquivo: {saida.stderr.strip()[:300]}")

        sql_schema.write_text(
            _reescrever_schema(sql_bruto.read_text(encoding="utf-8", errors="replace"),
                               schema),
            encoding="utf-8")

        _psql("-c", f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        _psql("-c", f"CREATE SCHEMA {schema}")

        aplicado = _psql("-f", str(sql_schema))
        erros = [l for l in (aplicado.stderr or "").splitlines() if "ERROR" in l]

        comparacoes = []
        with db.engine.connect() as conn:
            conn.exec_driver_sql("SET app.nivel = 'SISTEMA'")
            def _contar(nome, esquema):
                # Identificador não aceita bind, e f-string em SQL é proibida no
                # projeto (há teste estático). `sa.table` monta o nome já citado
                # pelo dialeto, o que resolve as duas coisas.
                alvo = sa.table(nome, schema=esquema)
                return conn.execute(
                    sa.select(sa.func.count()).select_from(alvo)).scalar()

            for tabela in tabelas:
                try:
                    origem = _contar(tabela, "public")
                except Exception:
                    continue  # tabela não existe nesta versão do schema
                try:
                    restaurado = _contar(tabela, schema)
                except Exception:
                    restaurado = None  # não veio no dump
                comparacoes.append((tabela, origem, restaurado))

        return comparacoes, erros

    finally:
        # A ordem importa: derrubar o schema antes de apagar os arquivos, para
        # que uma falha na remoção não deixe dado clínico restaurado no banco.
        try:
            _psql("-c", f"DROP SCHEMA IF EXISTS {schema} CASCADE")
        finally:
            for arquivo in (sql_bruto, sql_schema):
                if arquivo.exists():
                    arquivo.unlink()
            temporario.rmdir()
