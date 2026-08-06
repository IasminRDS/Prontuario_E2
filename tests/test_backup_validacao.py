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
import pathlib
import shutil

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
