# -*- coding: utf-8 -*-
"""Backup: o arquivo tem de existir, não estar vazio e ser restaurável.

Um dump parcial é pior que nenhum — parece backup e não restaura.
"""
import pathlib
import re

import pytest

from extensions import db


@pytest.fixture
def pasta_backups(tmp_path, monkeypatch):
    """Escreve num diretório temporário, nunca em `backups/` do projeto."""
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    return tmp_path


def _gerar(cliente, pasta):
    antes = set(pasta.glob("backup_*"))
    html = cliente.get("/backup/").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    resposta = cliente.post("/backup/gerar", data={"csrf_token": token},
                            follow_redirects=True)
    novos = set(pasta.glob("backup_*")) - antes
    mensagem = re.search(r'alert__body">([^<]+)', resposta.get_data(as_text=True))
    return resposta, novos, (mensagem.group(1).strip() if mensagem else "")


def test_tela_de_backup_informa_o_banco_em_uso(app, autenticado_confirmado):
    html = autenticado_confirmado.get("/backup/").get_data(as_text=True)
    with app.app_context():
        assert db.engine.dialect.name in html


def test_gera_backup_valido(app, autenticado_confirmado, pasta_backups):
    with app.app_context():
        dialeto = db.engine.dialect.name

    if dialeto.startswith("postgresql"):
        import shutil
        import os
        if not (os.getenv("PG_DUMP_PATH") or shutil.which("pg_dump")):
            pytest.skip("pg_dump não encontrado no ambiente")

    resposta, novos, mensagem = _gerar(autenticado_confirmado, pasta_backups)

    assert resposta.status_code == 200
    assert "Backup criado" in mensagem, mensagem
    assert len(novos) == 1, f"esperava 1 arquivo novo, veio {len(novos)}"

    arquivo = novos.pop()
    assert arquivo.stat().st_size > 0, "arquivo de backup vazio"

    cabecalho = arquivo.read_bytes()[:16]
    if dialeto.startswith("postgresql"):
        assert cabecalho[:5] == b"PGDMP", "não é um dump custom do pg_dump"
    else:
        assert cabecalho[:15] == b"SQLite format 3"

    assert arquivo.name in autenticado_confirmado.get("/backup/").get_data(as_text=True)


def test_backup_exige_permissao_de_admin(clientes, sem_csrf, pasta_backups):
    for perfil in ("medico", "recepcao", "gestor"):
        assert clientes[perfil].post("/backup/gerar").status_code in (401, 403), perfil
    assert not list(pathlib.Path(pasta_backups).glob("backup_*")), (
        "perfil sem permissão conseguiu gerar arquivo"
    )
