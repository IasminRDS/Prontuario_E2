# -*- coding: utf-8 -*-
"""Invariantes das migrations.

O `flask db upgrade` do CI já executa a cadeia nos dois bancos, mas só descobre
o problema depois de gerar a migration e empurrar. Estes testes falham antes.
"""
import pathlib
import re

import pytest

VERSOES = pathlib.Path(__file__).resolve().parent.parent / "migrations" / "versions"


def _arquivos():
    return sorted(VERSOES.glob("*.py"))


def test_nenhuma_constraint_anonima():
    """`create_foreign_key(None, ...)` quebra a cadeia em SQLite.

    O SQLite não sabe ALTER TABLE para adicionar chave estrangeira, então o
    Alembic recria a tabela em modo batch — e nesse modo uma constraint sem nome
    levanta "Constraint must have a name". O autogenerate produz `None` por
    padrão, então isso reaparece a cada migration nova que mexa em FK.
    """
    anonimas = []
    for arquivo in _arquivos():
        texto = arquivo.read_text(encoding="utf-8")
        for achado in re.finditer(
                r"(create_foreign_key|drop_constraint|create_unique_constraint)"
                r"\(\s*None", texto):
            linha = texto[:achado.start()].count("\n") + 1
            anonimas.append(f"  {arquivo.name}:{linha} — {achado.group(1)}(None, ...)")

    assert not anonimas, (
        "constraint sem nome — a migration não roda em SQLite:\n"
        + "\n".join(anonimas)
    )


def test_cadeia_de_revisoes_e_linear():
    """Duas migrations com o mesmo `down_revision` são um ramo silencioso.

    O `db upgrade` escolhe um caminho e o outro nunca roda; a divergência só
    aparece quando falta uma coluna em produção.
    """
    anteriores = {}
    for arquivo in _arquivos():
        texto = arquivo.read_text(encoding="utf-8")
        rev = re.search(r"^revision = ['\"]([^'\"]+)", texto, re.M)
        anterior = re.search(r"^down_revision = (?:['\"]([^'\"]+)['\"]|None)",
                             texto, re.M)
        if not rev or not anterior:
            continue
        chave = anterior.group(1)
        anteriores.setdefault(chave, []).append(f"{arquivo.name} ({rev.group(1)})")

    ramos = {k: v for k, v in anteriores.items() if len(v) > 1}
    assert not ramos, f"revisões partindo do mesmo ponto: {ramos}"


def test_toda_migration_tem_downgrade():
    """Sem downgrade, um deploy ruim não tem volta pelo caminho normal."""
    sem_volta = []
    for arquivo in _arquivos():
        texto = arquivo.read_text(encoding="utf-8")
        corpo = texto.split("def downgrade()", 1)
        if len(corpo) < 2:
            sem_volta.append(arquivo.name)
            continue
        # `pass` sozinho conta como ausência, exceto quando a migration
        # declara explicitamente que não há o que desfazer.
        trecho = corpo[1]
        if re.match(r"[^\n]*:\s*\n\s*pass\s*$", trecho.strip()):
            sem_volta.append(arquivo.name)
    assert not sem_volta, f"migrations sem downgrade: {sem_volta}"


@pytest.mark.parametrize("arquivo", _arquivos(), ids=lambda p: p.name)
def test_migration_documenta_o_porque(arquivo):
    """Docstring que só repete o título não explica decisão nenhuma.

    Migration é o registro de por que o schema mudou; daqui a um ano é a única
    fonte disponível.
    """
    texto = arquivo.read_text(encoding="utf-8")
    doc = re.match(r'"""(.*?)"""', texto, re.S)
    assert doc, f"{arquivo.name} sem docstring"
    linhas = [l for l in doc.group(1).strip().splitlines()
              if l.strip() and not l.strip().startswith(("Revision ID",
                                                         "Revises",
                                                         "Create Date"))]
    assert len(linhas) > 1, (
        f"{arquivo.name}: a docstring só tem o título — falta o porquê")
