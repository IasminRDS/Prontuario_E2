# -*- coding: utf-8 -*-
"""Configurações do sistema — persistidas na tabela `configuracoes`."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models.configuracao import PADROES, Configuracao
from utils.audit import registrar
from utils.rbac import requer_permissao

configuracoes_bp = Blueprint("configuracoes", __name__, url_prefix="/configuracoes")


@configuracoes_bp.get("/")
@login_required
@requer_permissao("admin:full")
def index():
    return render_template("configuracoes/index.html", cfg=Configuracao.todas())


@configuracoes_bp.post("/")
@login_required
@requer_permissao("admin:full")
def salvar():
    alteradas = []
    for chave in PADROES:
        if chave not in request.form:
            continue
        novo = (request.form.get(chave) or "").strip()
        if chave == "uf":
            novo = novo.upper()
        if novo != Configuracao.obter(chave):
            Configuracao.definir(chave, novo, usuario_id=current_user.id)
            alteradas.append(chave)

    if alteradas:
        registrar(
            "configuracoes",
            None,
            "update",
            f"Configurações alteradas: {', '.join(alteradas)}",
        )
        db.session.commit()
        flash(f"{len(alteradas)} configuração(ões) salva(s).", "success")
    else:
        flash("Nenhuma alteração a salvar.", "info")

    return redirect(url_for("configuracoes.index"))
