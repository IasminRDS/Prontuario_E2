# -*- coding: utf-8 -*-
"""Cópia de segurança do banco.

O procedimento depende do dialeto em uso, e é por isso que esta tela não pode
simplesmente copiar um arquivo: em Postgres não existe arquivo para copiar. A
origem é sempre `db.engine.url` — nunca um caminho escrito à mão — para que o
backup acompanhe o `DATABASE_URL` de quem estiver rodando.
"""
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime
from glob import glob
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import login_required

from extensions import db
from utils.audit import registrar
from utils.rbac import requer_permissao

backup_bp = Blueprint("backup", __name__, url_prefix="/backup")

BASE_DIR = Path(__file__).resolve().parent.parent

# pg_dump não pode demorar para sempre: a requisição HTTP fica presa até ele
# terminar.
TIMEOUT_DUMP = int(os.getenv("BACKUP_TIMEOUT", "600"))


def _pasta_destino():
    destino = Path(os.getenv("BACKUP_DIR") or (BASE_DIR / "backups"))
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def _existentes():
    """Backups já gerados, do mais recente para o mais antigo."""
    arquivos = []
    for caminho in _pasta_destino().glob("backup_*"):
        if not caminho.is_file():
            continue
        info = caminho.stat()
        arquivos.append({
            "nome": caminho.name,
            "bytes": info.st_size,
            "criado_em": datetime.fromtimestamp(info.st_mtime),
        })
    return sorted(arquivos, key=lambda a: a["criado_em"], reverse=True)


def _localizar_pg_dump():
    """Acha o pg_dump. O PATH do processo web quase nunca tem o bin do Postgres.

    Ordem: PG_DUMP_PATH explícito, depois PATH, depois o diretório convencional
    de instalação no Windows. Não achando, quem chama avisa o operador — falhar
    em silêncio aqui significa acreditar num backup que não existe.
    """
    explicito = os.getenv("PG_DUMP_PATH")
    if explicito:
        return explicito if Path(explicito).is_file() else None

    no_path = shutil.which("pg_dump")
    if no_path:
        return no_path

    for padrao in (r"C:\Program Files\PostgreSQL\*\bin\pg_dump.exe",
                   "/usr/lib/postgresql/*/bin/pg_dump",
                   "/usr/bin/pg_dump"):
        achados = sorted(glob(padrao), reverse=True)
        if achados:
            return achados[0]

    return None


def _backup_sqlite(url, carimbo):
    """Usa a API de backup do próprio SQLite, não `copy2`.

    Copiar o arquivo enquanto há escrita em curso produz uma cópia corrompida
    silenciosamente; `Connection.backup` respeita o journal e devolve um banco
    consistente.
    """
    origem = url.database
    if not origem or not Path(origem).is_file():
        return None, f"Arquivo SQLite não encontrado em {origem or '(vazio)'}."

    destino = _pasta_destino() / f"backup_{carimbo}.db"
    entrada = sqlite3.connect(f"file:{origem}?mode=ro", uri=True)
    try:
        saida = sqlite3.connect(destino)
        try:
            entrada.backup(saida)
        finally:
            saida.close()
    finally:
        entrada.close()

    return destino, None


def _backup_postgres(url, carimbo):
    executavel = _localizar_pg_dump()
    if not executavel:
        return None, ("pg_dump não encontrado. Instale o cliente do PostgreSQL "
                      "ou aponte PG_DUMP_PATH para o executável.")

    destino = _pasta_destino() / f"backup_{carimbo}.dump"

    comando = [
        executavel,
        "--host", url.host or "localhost",
        "--port", str(url.port or 5432),
        "--dbname", url.database,
        # Formato custom: comprimido e restaurável seletivamente com pg_restore.
        "--format", "custom",
        # O dono e as permissões pertencem ao ambiente, não ao dump; sem isto o
        # restore num servidor com outras roles falha.
        "--no-owner", "--no-privileges",
        # Com Row-Level Security ativo, o pg_dump se recusa a rodar sem esta
        # opção — e a recusa é acertada: ele não quer produzir um dump
        # silenciosamente parcial. Combinada com o PGOPTIONS abaixo, que abre a
        # conexão no escopo SISTEMA, o dump sai completo.
        #
        # Em produção o certo é um papel dedicado com BYPASSRLS fazendo o dump:
        # aí a completude não depende de uma variável de ambiente estar certa.
        "--enable-row-security",
        "--file", str(destino),
    ]
    if url.username:
        comando += ["--username", url.username]

    # A senha vai por variável de ambiente do processo filho, não na linha de
    # comando — argumento de processo é legível por qualquer usuário da máquina.
    ambiente = dict(os.environ)
    if url.password:
        ambiente["PGPASSWORD"] = url.password

    # Com Row-Level Security em FORCE, o pg_dump também é barrado: ele conecta
    # como dono das tabelas e sem escopo definido, então as políticas não
    # liberam linha nenhuma e o dump falha. PGOPTIONS define o escopo já na
    # abertura da conexão, que é o único momento disponível — não há como rodar
    # um SET antes do dump.
    opcoes = ambiente.get("PGOPTIONS", "")
    ambiente["PGOPTIONS"] = f"{opcoes} -c app.nivel=SISTEMA".strip()

    try:
        proc = subprocess.run(comando, env=ambiente, capture_output=True,
                              text=True, timeout=TIMEOUT_DUMP)
    except subprocess.TimeoutExpired:
        destino.unlink(missing_ok=True)
        return None, f"pg_dump excedeu {TIMEOUT_DUMP}s e foi interrompido."
    except OSError as exc:
        destino.unlink(missing_ok=True)
        return None, f"Não foi possível executar o pg_dump: {exc}"

    if proc.returncode != 0:
        # Um dump parcial é pior que nenhum: parece backup e não restaura.
        destino.unlink(missing_ok=True)
        linhas = [l.strip() for l in (proc.stderr or "").splitlines() if l.strip()]
        # A causa está na PRIMEIRA linha de erro; a última costuma ser o
        # "Query was:", que não diz nada a quem lê o aviso na tela.
        causa = next((l for l in linhas if "error" in l.lower() or "erro" in l.lower()),
                     linhas[0] if linhas else "")
        return None, causa or f"pg_dump falhou (código {proc.returncode})."

    return destino, None


@backup_bp.get("/")
@login_required
@requer_permissao("admin:full")
def index():
    return render_template(
        "backup/index.html",
        dialeto=db.engine.dialect.name,
        banco=db.engine.url.database,
        pasta=str(_pasta_destino()),
        backups=_existentes(),
    )


@backup_bp.post("/gerar")
@login_required
@requer_permissao("admin:full")
def gerar():
    url = db.engine.url
    dialeto = db.engine.dialect.name
    carimbo = datetime.now().strftime("%Y%m%d_%H%M%S")

    if dialeto == "sqlite":
        destino, erro = _backup_sqlite(url, carimbo)
    elif dialeto.startswith("postgresql"):
        destino, erro = _backup_postgres(url, carimbo)
    else:
        destino, erro = None, f"Backup automático não implementado para '{dialeto}'."

    if erro:
        current_app.logger.warning("Backup falhou (%s): %s", dialeto, erro)
        flash(f"Backup não gerado: {erro}", "danger")
        return redirect(url_for("backup.index"))

    tamanho = destino.stat().st_size
    registrar("backup", None, "create",
              f"Backup {dialeto} gerado em {destino} ({tamanho} bytes)",
              commit=True)

    flash(f"Backup criado: {destino.name} ({tamanho // 1024} KB)", "success")
    return redirect(url_for("backup.index"))
