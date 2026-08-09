from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import or_

from database.db import db
from models.catalogo_vacina import CatalogoVacina
from utils.rbac import requer_permissao

catalogo_vacinas_bp = Blueprint("catalogo_vacinas", __name__, url_prefix="/catalogo-vacinas")


@catalogo_vacinas_bp.get("/")
@login_required
def index():
    q = (request.args.get("q") or "").strip()
    query = CatalogoVacina.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(CatalogoVacina.nome.ilike(like), CatalogoVacina.codigo.ilike(like), CatalogoVacina.faixa.ilike(like)))
    itens = query.order_by(CatalogoVacina.nome.asc()).all()
    return render_template("catalogo_vacinas/index.html", itens=itens, q=q)


@catalogo_vacinas_bp.post("/novo")
@login_required
@requer_permissao("exam:write")
def novo():
    nome = (request.form.get("nome") or "").strip()
    codigo = (request.form.get("codigo") or "").strip().upper()
    doses = (request.form.get("doses") or "").strip()
    faixa = (request.form.get("faixa") or "").strip()

    if not nome or not codigo:
        flash("Nome e código são obrigatórios.", "warning")
        return redirect(url_for("catalogo_vacinas.index"))

    if CatalogoVacina.query.filter_by(codigo=codigo).first():
        flash("Já existe vacina com esse código.", "warning")
        return redirect(url_for("catalogo_vacinas.index"))

    db.session.add(CatalogoVacina(nome=nome, codigo=codigo, doses=doses or None, faixa=faixa or None, ativo=True))
    db.session.commit()
    flash("Vacina adicionada ao catálogo.", "success")
    return redirect(url_for("catalogo_vacinas.index"))