# -*- coding: utf-8 -*-
"""Consulta às terminologias oficiais — CID-10, RENAME, CBO, SIGTAP e CNES.

Porte de `modules/terminologia` do backend NestJS. Serve tanto a tela de consulta
quanto os autocompletes de CID e medicamento espalhados pelos formulários.
"""
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from utils.terminologias import TABELAS, buscar, colunas

terminologia_bp = Blueprint("terminologia", __name__, url_prefix="/tabelas")

LIMITE_TELA = 50
LIMITE_API = 20


@terminologia_bp.get("/")
@login_required
def index():
    tabela = (request.args.get("tabela") or "cid10").strip()
    if tabela not in TABELAS:
        tabela = "cid10"
    termo = (request.args.get("q") or "").strip()

    return render_template(
        "terminologia/index.html",
        tabelas=TABELAS,
        tabela=tabela,
        termo=termo,
        colunas=colunas(tabela),
        resultados=buscar(tabela, termo, LIMITE_TELA),
        limite=LIMITE_TELA,
    )


@terminologia_bp.get("/api/<tabela>")
@login_required
def api(tabela):
    """Autocomplete. Ex.: /tabelas/api/cid10?q=deng"""
    if tabela not in TABELAS:
        return jsonify({"erro": "terminologia desconhecida"}), 404

    limite = min(request.args.get("limite", type=int) or LIMITE_API, 50)
    return jsonify(buscar(tabela, request.args.get("q", ""), limite))
