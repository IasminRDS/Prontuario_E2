from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import or_

from database.db import db
from models.catalogo_exame import CatalogoExame
from utils.rbac import requer_permissao

catalogo_exames_bp = Blueprint("catalogo_exames", __name__, url_prefix="/catalogo-exames")


@catalogo_exames_bp.get("/")
@login_required
def index():
    q = (request.args.get("q") or "").strip()
    query = CatalogoExame.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(CatalogoExame.nome.ilike(like), CatalogoExame.codigo.ilike(like), CatalogoExame.grupo.ilike(like)))
    itens = query.order_by(CatalogoExame.nome.asc()).all()
    return render_template("catalogo_exames/index.html", itens=itens, q=q)


@catalogo_exames_bp.post("/novo")
@login_required
@requer_permissao("exam:write")
def novo():
    nome = (request.form.get("nome") or "").strip()
    codigo = (request.form.get("codigo") or "").strip().upper()
    grupo = (request.form.get("grupo") or "").strip()

    if not nome or not codigo:
        flash("Nome e código são obrigatórios.", "warning")
        return redirect(url_for("catalogo_exames.index"))

    if CatalogoExame.query.filter_by(codigo=codigo).first():
        flash("Já existe exame com esse código.", "warning")
        return redirect(url_for("catalogo_exames.index"))

    db.session.add(CatalogoExame(nome=nome, codigo=codigo, grupo=grupo or "Geral", ativo=True))
    db.session.commit()
    flash("Exame adicionado ao catálogo.", "success")
    return redirect(url_for("catalogo_exames.index"))