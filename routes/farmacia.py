# -*- coding: utf-8 -*-
"""Farmácia — visão do estoque pela ótica da dispensação.

Compartilha os models `ItemEstoque`/`MovEstoque` com o módulo de estoque; a
diferença é o recorte: aqui só entram itens da categoria medicamento, e a
movimentação padrão é saída por dispensação.

O módulo tinha template e nenhuma rota.
"""
from datetime import date, datetime

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from extensions import db
from models.estoque import ItemEstoque, MovEstoque
from utils.audit import registrar
from utils.rbac import requer_permissao

farmacia_bp = Blueprint("farmacia", __name__, url_prefix="/farmacia")

TIPOS_MOV = ("entrada", "saida", "ajuste", "perda", "dispensacao")


@farmacia_bp.get("/")
@login_required
@requer_permissao("med-admin:write", "clinical:read")
def index():
    termo = (request.args.get("q") or "").strip()
    categoria = (request.args.get("categoria") or "").strip()
    somente_ativos = request.args.get("ativos", "1") != "0"

    query = ItemEstoque.query
    if somente_ativos:
        query = query.filter(ItemEstoque.ativo.is_(True))
    if categoria:
        query = query.filter(ItemEstoque.categoria == categoria)
    else:
        # Recorte do módulo: farmácia trata medicamento e insumo.
        query = query.filter(ItemEstoque.categoria.in_(("medicamento", "insumo")))
    if termo:
        like = f"%{termo}%"
        query = query.filter(or_(
            ItemEstoque.nome.ilike(like),
            ItemEstoque.apresentacao.ilike(like),
            ItemEstoque.codigo_interno.ilike(like),
        ))

    itens = query.order_by(ItemEstoque.nome).all()

    hoje = date.today()
    abaixo_minimo = sum(
        1 for i in itens
        if i.quantidade is not None and i.estoque_minimo is not None
        and i.quantidade <= i.estoque_minimo
    )
    vencidos = sum(1 for i in itens if i.validade and i.validade < hoje)

    categorias = sorted(
        v[0]
        for v in ItemEstoque.query.with_entities(ItemEstoque.categoria).distinct().all()
        if v[0]
    )

    return render_template(
        "farmacia/index.html",
        itens=itens,
        q=termo,
        categoria=categoria,
        categorias=categorias,
        ativos=somente_ativos,
        # O template lê os filtros por um dict único.
        filtros={"q": termo, "categoria": categoria, "ativos": somente_ativos},
        abaixo_minimo=abaixo_minimo,
        vencidos=vencidos,
        hoje=hoje,
        tipos_mov=TIPOS_MOV,
    )


@farmacia_bp.route("/item/<int:item_id>/movimentar", methods=["GET", "POST"])
@login_required
@requer_permissao("med-admin:write")
def movimentar(item_id):
    item = ItemEstoque.query.get_or_404(item_id)

    if request.method == "POST":
        tipo = (request.form.get("tipo") or "").strip()
        bruto = (request.form.get("quantidade") or "").strip().replace(",", ".")

        if tipo not in TIPOS_MOV:
            flash("Tipo de movimentação inválido.", "danger")
            return render_template("farmacia/movimentar.html", item=item,
                                   tipos_mov=TIPOS_MOV)
        try:
            quantidade = float(bruto)
        except ValueError:
            flash("Quantidade deve ser numérica.", "warning")
            return render_template("farmacia/movimentar.html", item=item,
                                   tipos_mov=TIPOS_MOV)
        if quantidade <= 0:
            flash("A quantidade deve ser maior que zero.", "warning")
            return render_template("farmacia/movimentar.html", item=item,
                                   tipos_mov=TIPOS_MOV)

        anterior = float(item.quantidade or 0)
        entra = tipo == "entrada"
        delta = quantidade if entra else -quantidade
        posterior = anterior + delta

        # Estoque negativo não existe fisicamente: bloqueia em vez de "corrigir".
        if posterior < 0:
            flash(
                f"Saldo insuficiente: há {anterior:g} {item.unidade_medida or 'un'} "
                f"em estoque.",
                "danger",
            )
            return render_template("farmacia/movimentar.html", item=item,
                                   tipos_mov=TIPOS_MOV)

        mov = MovEstoque(
            item_id=item.id,
            unidade_id=current_user.unidade_id,
            usuario_id=current_user.id,
            tipo=tipo,
            quantidade=quantidade,
            quantidade_anterior=anterior,
            quantidade_posterior=posterior,
            motivo=(request.form.get("motivo") or "").strip() or None,
            lote=(request.form.get("lote") or "").strip() or None,
            fornecedor=(request.form.get("fornecedor") or "").strip() or None,
            nota_fiscal=(request.form.get("nota_fiscal") or "").strip() or None,
            criado_em=datetime.utcnow(),
        )
        item.quantidade = posterior

        db.session.add(mov)
        registrar("itens_estoque", item.id, "update",
                  f"{tipo} de {quantidade:g} {item.unidade_medida or 'un'} "
                  f"em {item.nome} ({anterior:g} → {posterior:g})")
        db.session.commit()

        flash(
            f"{tipo.capitalize()} registrada. Saldo de {item.nome}: "
            f"{posterior:g} {item.unidade_medida or 'un'}.",
            "success",
        )
        return redirect(url_for("farmacia.index"))

    movimentacoes = (
        MovEstoque.query
        .filter_by(item_id=item.id)
        .order_by(MovEstoque.criado_em.desc())
        .limit(30)
        .all()
    )
    return render_template("farmacia/movimentar.html", item=item,
                           movimentacoes=movimentacoes, tipos_mov=TIPOS_MOV)
