# -*- coding: utf-8 -*-
"""Semeia uma linha por tabela, em ordem topológica, respeitando FK e NOT NULL.

O objetivo não é dado realista: é fazer os laços dos templates EXECUTAREM. Com
as tabelas vazias, a varredura de rotas responde 200 em tudo sem renderizar uma
única linha — foi assim que dez telas quebradas passaram despercebidas.
"""
import datetime as dt
import decimal

import sqlalchemy as sa

from extensions import db

# Tabelas com semântica própria, semeadas pelo conftest.
PULAR = {"alembic_version", "users", "audit_logs"}

_contador = {"n": 0}


def _valor(coluna):
    tipo = coluna.type
    _contador["n"] += 1
    n = _contador["n"]

    if isinstance(tipo, sa.Boolean):
        return True
    if isinstance(tipo, (sa.Integer, sa.SmallInteger, sa.BigInteger)):
        return n
    if isinstance(tipo, sa.Numeric):
        return decimal.Decimal("1.50")
    if isinstance(tipo, sa.Float):
        return 1.5
    if isinstance(tipo, sa.DateTime):
        # Meio-dia de hoje, e não `now()`: instante fixo deixa a semeadura
        # determinística. Com `now()`, uma linha semeada perto da virada do dia
        # cai de um lado ou do outro de qualquer janela de relatório, e o teste
        # passa ou falha conforme a hora em que roda.
        #
        # Isto não cobre coluna nulável COM default — essa o seeder pula, e vale
        # o default do model (`utcnow`).
        return dt.datetime.combine(dt.date.today(), dt.time(12, 0))
    if isinstance(tipo, sa.Date):
        return dt.date.today()
    if isinstance(tipo, sa.Time):
        return dt.time(8, 30)
    if isinstance(tipo, sa.Text):
        return f"Texto de teste {n}"

    largura = getattr(tipo, "length", None) or 40
    nome = coluna.name.lower()
    if "cpf" in nome:
        # `pacientes.cpf` e `pacientes.cns` são UNIQUE. Com valor fixo, esta
        # semeadura ocupava o documento que os testes de deduplicação escrevem à
        # mão, e o par deles só passava enquanto rodassem ANTES daqui — uma
        # ordem que qualquer arquivo de teste novo em ordem alfabética anterior
        # inverte. O contador dá um documento por linha; o formato de 11 e 15
        # dígitos é o que `validar_cpf`/`validar_cns` exigem.
        base = f"{90000000000 + n:011d}"
    elif "cns" in nome:
        base = f"{700000000000000 + n:015d}"
    elif "email" in nome:
        base = f"teste{n}@exemplo.local"
    elif nome in ("data", "data_str"):
        base = dt.date.today().isoformat()
    elif nome == "hora":
        base = "08:30"
    elif "sexo" in nome:
        base = "M"
    else:
        base = f"T{n}"
    return base[:largura]


def semear_uma_linha_por_tabela():
    """Devolve (semeadas, puladas). Idempotente: pula tabela que já tem dado."""
    semeadas, puladas = [], []

    for tabela in db.metadata.sorted_tables:
        if tabela.name in PULAR:
            continue

        ja_tem = db.session.execute(
            sa.select(sa.func.count()).select_from(tabela)).scalar()
        if ja_tem:
            puladas.append(tabela.name)
            continue

        linha = {}
        impossivel = False

        for coluna in tabela.columns:
            if coluna.primary_key and coluna.autoincrement:
                continue

            if coluna.foreign_keys:
                fk = next(iter(coluna.foreign_keys))
                # Ordenar não é capricho: sem ORDER BY o PostgreSQL pode
                # devolver qualquer linha, e o dado semeado passaria a apontar
                # para uma unidade diferente a cada execução — com RLS ligado,
                # isso vira teste que falha de forma intermitente.
                referencia = db.session.execute(
                    sa.select(fk.column).select_from(fk.column.table)
                    .order_by(fk.column.asc()).limit(1)
                ).scalar()
                if referencia is None:
                    if not coluna.nullable:
                        impossivel = True
                        break
                    continue
                linha[coluna.name] = referencia
                continue

            tem_padrao = coluna.default is not None or coluna.server_default is not None
            if coluna.nullable and tem_padrao:
                continue
            # Preenche os opcionais também: é no opcional nulo que template quebra.
            linha[coluna.name] = _valor(coluna)

        if impossivel:
            puladas.append(tabela.name)
            continue

        try:
            db.session.execute(sa.insert(tabela).values(**linha))
            db.session.commit()
            semeadas.append(tabela.name)
        except Exception:
            db.session.rollback()
            puladas.append(tabela.name)

    return semeadas, puladas
