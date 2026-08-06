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


def _to_int_env(nome, padrao):
    try:
        return int(os.getenv(nome) or padrao)
    except (TypeError, ValueError):
        return padrao


# Abaixo disto o arquivo não pode ser um dump: um schema vazio já passa de
# 100 KB. O caso real que motivou este piso foi um `pg_dump` que falhou na
# autenticação DEPOIS de criar o arquivo, deixando 0 byte no diretório de
# backups com nome perfeitamente plausível.
TAMANHO_MINIMO = _to_int_env("BACKUP_TAMANHO_MINIMO", 4096)

# Quantas cópias manter. Gerar sem expurgar enche o disco em silêncio, e disco
# cheio derruba justamente o banco que se queria proteger.
RETENCAO = _to_int_env("BACKUP_RETENCAO", 10)


def _rotacionar(manter=None):
    """Remove as cópias mais antigas além do limite. Devolve quantas saíram.

    A ordenação é por data de modificação, não pelo nome: nome com carimbo de
    tempo ordena bem por acaso, e o dia em que alguém renomear um arquivo à mão
    o critério silenciosamente passa a apagar o backup errado.
    """
    manter = RETENCAO if manter is None else manter
    if manter <= 0:
        return 0

    pasta = _pasta_destino()
    copias = sorted(
        (p for p in pasta.glob("backup_*") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    removidos = 0
    for antigo in copias[manter:]:
        try:
            antigo.unlink()
            removidos += 1
        except OSError:
            # Falha ao apagar cópia velha não pode derrubar o backup novo, que
            # é o que realmente importa nesta operação.
            continue
    return removidos


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

    # No Windows, o registro é a fonte autoritativa: o instalador grava ali o
    # diretório real, seja qual for a unidade. O glob fixo em
    # `C:\Program Files\PostgreSQL` só acerta a instalação padrão — numa máquina
    # com o Postgres em `F:\PostgreSQL 16` o backup falhava com "pg_dump não
    # encontrado", e o operador só descobria na hora de precisar do backup.
    for base in _bases_do_registro_windows():
        candidato = Path(base) / "bin" / "pg_dump.exe"
        if candidato.is_file():
            return str(candidato)

    padroes = ["/usr/lib/postgresql/*/bin/pg_dump", "/usr/bin/pg_dump"]
    if os.name == "nt":
        for unidade in _unidades_windows():
            padroes += [
                rf"{unidade}\Program Files\PostgreSQL\*\bin\pg_dump.exe",
                rf"{unidade}\PostgreSQL*\bin\pg_dump.exe",
            ]

    for padrao in padroes:
        achados = sorted(glob(padrao), reverse=True)
        if achados:
            return achados[0]

    return None


def _bases_do_registro_windows():
    """Diretórios de instalação declarados pelo instalador do PostgreSQL."""
    if os.name != "nt":
        return []
    try:
        import winreg
    except ImportError:  # pragma: no cover - só existe no Windows
        return []

    bases = []
    for raiz in (r"SOFTWARE\PostgreSQL\Installations",
                 r"SOFTWARE\Wow6432Node\PostgreSQL\Installations"):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, raiz) as chave:
                for i in range(winreg.QueryInfoKey(chave)[0]):
                    try:
                        with winreg.OpenKey(chave, winreg.EnumKey(chave, i)) as sub:
                            bases.append(winreg.QueryValueEx(sub, "Base Directory")[0])
                    except OSError:
                        continue
        except OSError:
            continue
    # Mais recente primeiro, para não cair numa instalação antiga esquecida.
    return sorted(bases, reverse=True)


def _unidades_windows():
    try:
        return os.listdrives()  # Python 3.12+
    except AttributeError:
        return [f"{letra}:" for letra in "CDEFGH"
                if Path(f"{letra}:\\").exists()]


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

    if tamanho < TAMANHO_MINIMO:
        # Arquivo minúsculo não é backup: é um `pg_dump` que criou o arquivo e
        # morreu antes de escrever. Ficando no diretório, vira armadilha para
        # quem for restaurar sob pressão — nome plausível, conteúdo nenhum.
        destino.unlink(missing_ok=True)
        current_app.logger.warning(
            "Backup descartado por tamanho implausível: %s (%s bytes)",
            destino.name, tamanho)
        flash(f"Backup descartado: o arquivo saiu com {tamanho} bytes, "
              "o que indica falha silenciosa do processo de dump.", "danger")
        return redirect(url_for("backup.index"))

    removidos = _rotacionar()

    registrar("backup", None, "create",
              f"Backup {dialeto} gerado em {destino} ({tamanho} bytes)"
              + (f"; {removidos} antigo(s) removido(s)" if removidos else ""),
              commit=True)

    aviso = f"Backup criado: {destino.name} ({tamanho // 1024} KB)"
    if removidos:
        aviso += f" · {removidos} cópia(s) antiga(s) removida(s)"
    flash(aviso, "success")
    return redirect(url_for("backup.index"))
