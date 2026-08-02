from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import or_

from database.db import db
from models.catalogo_exame import CatalogoExame
from utils.rbac import requer_permissao

catalogo_exames_bp = Blueprint("catalogo_exames", __name__, url_prefix="/catalogo-exames")


def _seed_if_empty():
    if CatalogoExame.query.count() > 0:
        return
    seed = [
        ("Hemograma completo", "EX001", "Laboratorial"),
        ("Glicemia de jejum", "EX002", "Laboratorial"),
        ("Hemoglobina glicada (HbA1c)", "EX003", "Laboratorial"),
        ("Colesterol total e frações", "EX004", "Laboratorial"),
        ("Triglicerídeos", "EX005", "Laboratorial"),
        ("TSH", "EX006", "Laboratorial"),
        ("T4 livre", "EX007", "Laboratorial"),
        ("Creatinina", "EX008", "Laboratorial"),
        ("Ureia", "EX009", "Laboratorial"),
        ("EAS (Urina tipo I)", "EX010", "Laboratorial"),
        ("Parasitológico de fezes", "EX011", "Laboratorial"),
        ("Beta-HCG", "EX012", "Laboratorial"),
        ("Raio-X de tórax", "EX013", "Imagem"),
        ("Ultrassonografia abdominal", "EX014", "Imagem"),
        ("Eletrocardiograma", "EX015", "Cardiológico"),
    ]
    for nome, codigo, grupo in seed:
        db.session.add(CatalogoExame(nome=nome, codigo=codigo, grupo=grupo, ativo=True))
    db.session.commit()


@catalogo_exames_bp.get("/")
@login_required
def index():
    _seed_if_empty()
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