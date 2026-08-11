# -*- coding: utf-8 -*-
"""Exportação de dados — auditada (LGPD).

Porte de `modules/export` do backend NestJS. Exportar base de pacientes é uma
operação sensível: cada download grava um evento de auditoria com quem exportou,
quantos registros e quais campos.

O RBAC aqui é por PERFIL, não por permissão granular — igual ao backend.
"""
import csv
from datetime import datetime
from io import StringIO

from flask import Blueprint, Response, flash, redirect, render_template, request, url_for
from flask_login import login_required

from extensions import db
from models.audit_log import AuditLog
from models.paciente import Paciente
from utils.audit import registrar
from utils.rbac import requer_perfil

exportacao_bp = Blueprint("exportacao", __name__, url_prefix="/exportacao")

# Conjuntos de campos. "Identificado" inclui dado pessoal direto; "anonimizado"
# serve para uso estatístico e não permite reidentificar o titular.
CAMPOS = {
    "anonimizado": [
        ("id", "Identificador interno"),
        ("data_nascimento", "Data de nascimento"),
        ("sexo", "Sexo"),
        ("raca_cor", "Raça/cor"),
        ("municipio", "Município"),
        ("uf", "UF"),
        ("tipo_sanguineo", "Tipo sanguíneo"),
    ],
    "identificado": [
        ("id", "Identificador interno"),
        ("nome", "Nome"),
        ("cpf", "CPF"),
        ("cns", "CNS"),
        ("data_nascimento", "Data de nascimento"),
        ("sexo", "Sexo"),
        ("nome_mae", "Nome da mãe"),
        ("telefone", "Telefone"),
        ("email", "E-mail"),
        ("municipio", "Município"),
        ("uf", "UF"),
    ],
}


@exportacao_bp.get("/")
@login_required
@requer_perfil("Administrador", "Recepcao")
def index():
    exportacoes = (
        AuditLog.query
        .filter(AuditLog.acao == "export")
        .order_by(AuditLog.criado_em.desc())
        .limit(50)
        .all()
    )
    return render_template(
        "exportacao/index.html",
        campos=CAMPOS,
        total_pacientes=Paciente.query.filter_by(ativo=True).count(),
        exportacoes=exportacoes,
    )


@exportacao_bp.post("/pacientes.csv")
@login_required
@requer_perfil("Administrador", "Recepcao")
def pacientes_csv():
    escopo = (request.form.get("escopo") or "anonimizado").strip()
    if escopo not in CAMPOS:
        flash("Escopo de exportação inválido.", "danger")
        return redirect(url_for("exportacao.index"))

    if escopo == "identificado" and not (request.form.get("ciente") == "1"):
        flash(
            "Para exportar dados identificados é preciso declarar ciência da "
            "responsabilidade sobre o tratamento (LGPD).",
            "warning",
        )
        return redirect(url_for("exportacao.index"))

    colunas = CAMPOS[escopo]
    pacientes = Paciente.query.filter_by(ativo=True).order_by(Paciente.id).all()

    buf = StringIO()
    # delimitador ';' e BOM: é o que o Excel pt-BR abre sem quebrar acento.
    escritor = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    escritor.writerow([rotulo for _campo, rotulo in colunas])

    for p in pacientes:
        linha = []
        for campo, _rotulo in colunas:
            valor = getattr(p, campo, None)
            if isinstance(valor, datetime):
                valor = valor.strftime("%d/%m/%Y")
            elif hasattr(valor, "isoformat"):
                valor = valor.strftime("%d/%m/%Y")
            linha.append("" if valor is None else str(valor))
        escritor.writerow(linha)

    registrar(
        "pacientes",
        None,
        "export",
        f"Exportação CSV de pacientes — escopo {escopo}, "
        f"{len(pacientes)} registro(s), campos: {', '.join(c for c, _ in colunas)}",
    )
    db.session.commit()

    nome = f"pacientes_{escopo}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        "﻿" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@exportacao_bp.post("/auditoria.csv")
@login_required
@requer_perfil("Administrador")
def auditoria_csv():
    """Exporta a trilha de auditoria — inclui os hashes da cadeia."""
    logs = AuditLog.query.order_by(AuditLog.id).all()

    buf = StringIO()
    escritor = csv.writer(buf, delimiter=";")
    escritor.writerow(["id", "quando", "usuario_id", "acao", "tabela",
                       "registro_id", "descricao", "ip", "hash_anterior", "hash_atual"])
    for l in logs:
        escritor.writerow([
            l.id,
            l.criado_em.strftime("%d/%m/%Y %H:%M:%S") if l.criado_em else "",
            l.usuario_id or "",
            l.acao,
            l.tabela,
            l.registro_id or "",
            l.descricao or "",
            l.ip or "",
            l.hash_anterior or "",
            l.hash_atual or "",
        ])

    registrar("audit_logs", None, "export",
              f"Exportação da trilha de auditoria — {len(logs)} evento(s)")
    db.session.commit()

    nome = f"auditoria_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return Response(
        "﻿" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
