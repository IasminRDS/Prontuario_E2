from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import or_

from database.db import db
from models.catalogo_vacina import CatalogoVacina
from utils.rbac import requer_permissao

catalogo_vacinas_bp = Blueprint("catalogo_vacinas", __name__, url_prefix="/catalogo-vacinas")


def _seed_if_empty():
    if CatalogoVacina.query.count() > 0:
        return
    seed = [
        ("BCG", "VAC001", "Dose única", "Ao nascer"),
        ("Hepatite B", "VAC002", "3 doses", "Ao nascer / adultos"),
        ("Pentavalente", "VAC003", "3 doses + reforço", "2, 4, 6 meses"),
        ("Poliomielite (VIP/VOP)", "VAC004", "3 doses + reforços", "2, 4, 6 meses"),
        ("Rotavírus", "VAC005", "2 doses", "2 e 4 meses"),
        ("Pneumocócica 10v", "VAC006", "2 doses + reforço", "2, 4 e 12 meses"),
        ("Meningocócica C", "VAC007", "2 doses + reforço", "3, 5 e 12 meses"),
        ("Febre Amarela", "VAC008", "1 dose + reforço", "9 meses"),
        ("Tríplice Viral (SCR)", "VAC009", "2 doses", "12 e 15 meses"),
        ("Tetraviral", "VAC010", "1 dose", "15 meses"),
        ("DTP", "VAC011", "Reforços", "15 meses e 4 anos"),
        ("HPV quadrivalente", "VAC012", "2 doses", "9 a 14 anos"),
        ("dT (Dupla adulto)", "VAC013", "3 doses + reforço", "Adolescentes e adultos"),
        ("Influenza", "VAC014", "Anual", "Grupos prioritários"),
        ("COVID-19", "VAC015", "Conforme campanha", "População elegível"),
    ]
    for nome, codigo, doses, faixa in seed:
        db.session.add(CatalogoVacina(nome=nome, codigo=codigo, doses=doses, faixa=faixa, ativo=True))
    db.session.commit()


@catalogo_vacinas_bp.get("/")
@login_required
def index():
    _seed_if_empty()
    q = (request.args.get("q") or "").strip()
    query = CatalogoVacina.query
    if q:
        like = f"%{q}%"
        query = query.filter(or_(CatalogoVacina.nome.ilike(like), CatalogoVacina.codigo.ilike(like), CatalogoVacina.faixa.ilike(like)))
    itens = query.order_by(CatalogoVacina.nome.asc()).all()
    return render_template("catalogo_vacinas/index.html", itens=itens, q=q)


@catalogo_vacinas_bp.post("/novo")
@login_required
@requer_permissao("clinical:read")
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