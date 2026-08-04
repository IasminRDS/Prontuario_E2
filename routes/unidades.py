from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from sqlalchemy import or_

from database.db import db
from models.unidade_saude import UnidadeSaude
from utils.rbac import requer_permissao

unidades_bp = Blueprint("unidades", __name__, url_prefix="/unidades")


# Cadastro de estabelecimentos é administração da rede, não tela de operação:
# só tinha `@login_required` e qualquer sessão autenticada listava tudo.
@unidades_bp.get("/")
@login_required
@requer_permissao("hospital:manage")
def index():
    q = (request.args.get("q") or "").strip()
    tipo = (request.args.get("tipo") or "").strip()

    query = UnidadeSaude.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                UnidadeSaude.nome.ilike(like),
                UnidadeSaude.cidade.ilike(like),
                UnidadeSaude.cnes.ilike(like),
            )
        )
    if tipo:
        query = query.filter(UnidadeSaude.tipo == tipo)

    itens = query.order_by(UnidadeSaude.nome.asc()).all()
    return render_template("unidades/index.html", itens=itens, q=q, tipo=tipo)


@unidades_bp.post("/novo")
@login_required
@requer_permissao("admin:full")
def novo():
    nome = (request.form.get("nome") or "").strip()
    tipo = (request.form.get("tipo") or "").strip()
    cnes = (request.form.get("cnes") or "").strip()
    cidade = (request.form.get("cidade") or "").strip()
    uf = (request.form.get("uf") or "").strip().upper()

    if not nome or not tipo:
        flash("Nome e tipo são obrigatórios.", "warning")
        return redirect(url_for("unidades.index"))

    if cnes and UnidadeSaude.query.filter_by(cnes=cnes).first():
        flash("Já existe unidade com esse CNES.", "warning")
        return redirect(url_for("unidades.index"))

    db.session.add(
        UnidadeSaude(
            nome=nome,
            tipo=tipo,
            cnes=cnes or None,
            cidade=cidade or None,
            uf=uf or None,
            ativo=True,
        )
    )
    db.session.commit()
    flash("Unidade cadastrada.", "success")
    return redirect(url_for("unidades.index"))
