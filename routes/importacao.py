import csv
import io
from flask import Blueprint, Response, render_template, request, redirect, url_for, flash
from flask_login import login_required

from database.db import db
from models.paciente import Paciente
from utils.rbac import requer_permissao

importacao_bp = Blueprint("importacao", __name__, url_prefix="/importacao")

# Colunas aceitas no CSV. `nome`, `data_nascimento` e `sexo` são NOT NULL no
# model — sem elas o INSERT falha, então a validação acontece por linha, antes
# de tentar gravar.
COLUNAS = (
    "nome", "nome_social", "cpf", "cns", "data_nascimento", "sexo", "nome_mae",
    "telefone", "email", "cep", "logradouro", "numero", "bairro", "municipio", "uf",
)
OBRIGATORIAS = ("nome", "data_nascimento", "sexo")


@importacao_bp.get("/csv")
@login_required
@requer_permissao("patient:create")
def csv_form():
    return render_template("importacao/csv.html", preview=None, resultado=None,
                           colunas=COLUNAS, obrigatorias=OBRIGATORIAS)


@importacao_bp.get("/pacientes")
@login_required
@requer_permissao("patient:create")
def pacientes():
    """Tela de importação de pacientes (mesma do CSV, rota nomeada)."""
    return render_template("importacao/pacientes.html", preview=None, resultado=None,
                           colunas=COLUNAS, obrigatorias=OBRIGATORIAS)


@importacao_bp.get("/modelo.csv")
@login_required
@requer_permissao("patient:create")
def modelo_csv():
    """Baixa o CSV modelo já com o cabeçalho correto e uma linha de exemplo."""
    buf = io.StringIO()
    escritor = csv.writer(buf, delimiter=";")
    escritor.writerow(COLUNAS)
    escritor.writerow([
        "Maria da Silva", "", "12345678901", "", "1985-04-12", "F",
        "Ana da Silva", "77999998888", "", "48900000", "Rua A", "100",
        "Centro", "Juazeiro", "BA",
    ])

    return Response(
        "﻿" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="modelo_pacientes.csv"'},
    )


@importacao_bp.post("/csv")
@login_required
@requer_permissao("patient:create")
def csv_importar():
    arquivo = request.files.get("arquivo")
    if not arquivo or not arquivo.filename.lower().endswith(".csv"):
        flash("Envie um arquivo CSV válido.", "warning")
        return redirect(url_for("importacao.csv_form"))

    conteudo = arquivo.read().decode("utf-8-sig", errors="ignore")
    reader = csv.DictReader(io.StringIO(conteudo))

    colunas = set(reader.fieldnames or [])
    faltando = [c for c in OBRIGATORIAS if c not in colunas]
    if faltando:
        flash(
            f"O CSV precisa ter as colunas: {', '.join(faltando)}. "
            "Baixe o modelo para conferir o cabeçalho.",
            "danger",
        )
        return redirect(url_for("importacao.csv_form"))

    from datetime import date

    inseridos = 0
    ignorados = 0
    erros = 0
    preview = []
    problemas = []

    for i, row in enumerate(reader, start=2):  # linha 1 é o cabeçalho
        if len(preview) < 10:
            preview.append(row)

        nome = (row.get("nome") or "").strip()
        nascimento_bruto = (row.get("data_nascimento") or "").strip()
        sexo = (row.get("sexo") or "").strip().upper()[:1]

        # Validação por linha: uma linha ruim não derruba o lote inteiro, e o
        # motivo volta para a tela em vez de virar um contador anônimo.
        if not nome:
            erros += 1
            problemas.append(f"Linha {i}: nome vazio")
            continue
        if not nascimento_bruto:
            erros += 1
            problemas.append(f"Linha {i} ({nome}): data_nascimento vazia")
            continue
        try:
            nascimento = date.fromisoformat(nascimento_bruto)
        except ValueError:
            erros += 1
            problemas.append(
                f"Linha {i} ({nome}): data_nascimento '{nascimento_bruto}' "
                "não está no formato AAAA-MM-DD"
            )
            continue
        if nascimento > date.today():
            erros += 1
            problemas.append(f"Linha {i} ({nome}): data de nascimento no futuro")
            continue
        if sexo not in ("M", "F"):
            erros += 1
            problemas.append(f"Linha {i} ({nome}): sexo deve ser M ou F")
            continue

        cpf = "".join(c for c in (row.get("cpf") or "") if c.isdigit())
        cns = "".join(c for c in (row.get("cns") or "") if c.isdigit())

        if cpf and Paciente.query.filter_by(cpf=cpf).first():
            ignorados += 1
            continue
        if cns and Paciente.query.filter_by(cns=cns).first():
            ignorados += 1
            continue

        db.session.add(Paciente(
            nome=nome,
            nome_social=(row.get("nome_social") or "").strip() or None,
            cpf=cpf or None,
            cns=cns or None,
            data_nascimento=nascimento,
            sexo=sexo,
            nome_mae=(row.get("nome_mae") or "").strip() or None,
            telefone=(row.get("telefone") or "").strip() or None,
            email=(row.get("email") or "").strip() or None,
            cep=(row.get("cep") or "").strip() or None,
            logradouro=(row.get("logradouro") or "").strip() or None,
            numero=(row.get("numero") or "").strip() or None,
            bairro=(row.get("bairro") or "").strip() or None,
            municipio=(row.get("municipio") or "").strip() or None,
            uf=(row.get("uf") or "").strip().upper() or None,
            ativo=True,
        ))
        inseridos += 1

    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        flash(f"Erro ao salvar no banco: {exc}", "danger")
        return redirect(url_for("importacao.csv_form"))

    from utils.audit import registrar

    registrar("pacientes", None, "create",
              f"Importação CSV: {inseridos} inserido(s), {ignorados} duplicado(s), "
              f"{erros} com erro", commit=True)

    resultado = {
        "inseridos": inseridos,
        "ignorados": ignorados,
        "erros": erros,
        "total_linhas": inseridos + ignorados + erros,
        "problemas": problemas[:50],
    }
    flash(
        f"Importação concluída: {inseridos} inserido(s), {ignorados} duplicado(s), "
        f"{erros} com erro.",
        "success" if not erros else "warning",
    )
    return render_template("importacao/csv.html", preview=preview, resultado=resultado,
                           colunas=COLUNAS, obrigatorias=OBRIGATORIAS)