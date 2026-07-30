# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.estoque import ItemEstoque, MovEstoque
from database.db import db
from utils.audit import audit_log, auditar_aqui
from utils.security import admin_requerido
from datetime import datetime, date

estoque_bp = Blueprint('estoque', __name__, url_prefix='/estoque')

@estoque_bp.route('/')
@login_required
def index():
    q = request.args.get('q', '').strip()
    cat = request.args.get('categoria', '')
    criticos = request.args.get('criticos', '')
    uid = current_user.unidade_id
    query = ItemEstoque.query.filter_by(unidade_id=uid, ativo=True)
    if q:   query = query.filter(ItemEstoque.nome.ilike(f'%{q}%'))
    if cat: query = query.filter_by(categoria=cat)
    itens = query.order_by(ItemEstoque.nome).all()
    if criticos:
        itens = [i for i in itens if i.abaixo_minimo]
    total_itens = len(itens)
    criticos_n  = sum(1 for i in itens if i.abaixo_minimo)
    zerados_n   = sum(1 for i in itens if i.quantidade <= 0)
    return render_template('estoque/index.html', itens=itens, q=q, cat=cat,
                           criticos=criticos, total_itens=total_itens,
                           criticos_n=criticos_n, zerados_n=zerados_n)

@estoque_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if request.method == 'POST':
        try:
            val_str = request.form.get('validade', '').strip()
            item = ItemEstoque(
                unidade_id=current_user.unidade_id,
                nome=request.form['nome'].strip(),
                categoria=request.form.get('categoria', 'medicamento'),
                apresentacao=request.form.get('apresentacao', '').strip() or None,
                unidade_medida=request.form.get('unidade_medida', 'un'),
                codigo_interno=request.form.get('codigo_interno', '').strip() or None,
                lote_atual=request.form.get('lote_atual', '').strip() or None,
                validade=datetime.strptime(val_str, '%Y-%m-%d').date() if val_str else None,
                quantidade=float(request.form.get('quantidade', 0)),
                estoque_minimo=float(request.form.get('estoque_minimo', 10)),
                estoque_maximo=float(request.form['estoque_maximo']) if request.form.get('estoque_maximo') else None,
                preco_unitario=float(request.form['preco_unitario']) if request.form.get('preco_unitario') else None,
            )
            db.session.add(item)
            db.session.flush()
            if item.quantidade > 0:
                db.session.add(MovEstoque(
                    item_id=item.id, unidade_id=current_user.unidade_id,
                    usuario_id=current_user.id, tipo='entrada',
                    quantidade=item.quantidade, quantidade_anterior=0,
                    quantidade_posterior=item.quantidade, motivo='Cadastro inicial'))
            auditar_aqui("itens_estoque", "create")
            db.session.commit()
            flash(f'{item.nome} cadastrado!', 'success')
            return redirect(url_for('estoque.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')
    return render_template('estoque/form.html')

@estoque_bp.route('/<int:id>/movimentar', methods=['GET', 'POST'])
@login_required
def movimentar(id):
    item = ItemEstoque.query.get_or_404(id)
    if request.method == 'POST':
        try:
            tipo = request.form['tipo']
            qtd  = float(request.form['quantidade'])
            ant  = item.quantidade
            if tipo in ('saida', 'perda', 'vencimento'):
                if qtd > item.quantidade:
                    flash('Quantidade insuficiente.', 'danger')
                    return redirect(url_for('estoque.movimentar', id=id))
                item.quantidade -= qtd
            elif tipo == 'ajuste':
                item.quantidade = qtd
            else:
                item.quantidade += qtd
            lote = request.form.get('lote', '').strip() or None
            if lote and tipo == 'entrada':
                item.lote_atual = lote
            db.session.add(MovEstoque(
                item_id=item.id, unidade_id=current_user.unidade_id,
                usuario_id=current_user.id, tipo=tipo, quantidade=qtd,
                quantidade_anterior=ant, quantidade_posterior=item.quantidade,
                motivo=request.form.get('motivo', '').strip() or None,
                lote=lote,
                fornecedor=request.form.get('fornecedor', '').strip() or None,
                nota_fiscal=request.form.get('nota_fiscal', '').strip() or None))
            auditar_aqui("itens_estoque", "update")
            db.session.commit()
            flash(f'Registrado! Estoque: {item.quantidade} {item.unidade_medida}', 'success')
            return redirect(url_for('estoque.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')
    historico = item.movimentacoes.order_by(MovEstoque.criado_em.desc()).limit(20).all()
    return render_template('estoque/movimentar.html', item=item, historico=historico)

@estoque_bp.route('/alertas')
@login_required
def alertas():
    uid = current_user.unidade_id
    itens = ItemEstoque.query.filter_by(unidade_id=uid, ativo=True).all()
    criticos = [i for i in itens if i.quantidade <= i.estoque_minimo]
    hoje = date.today()
    vencendo = [i for i in itens if i.validade and (i.validade - hoje).days <= 30 and i.quantidade > 0]
    return render_template('estoque/alertas.html', criticos=criticos, vencendo=vencendo)

@estoque_bp.route('/api/buscar')
@login_required
def api_buscar():
    q = request.args.get('q', '').strip()
    itens = ItemEstoque.query.filter(
        ItemEstoque.unidade_id == current_user.unidade_id,
        ItemEstoque.ativo == True,
        ItemEstoque.nome.ilike(f'%{q}%')
    ).limit(10).all()
    return jsonify([{'id':i.id,'nome':i.nome,'quantidade':i.quantidade,
                     'unidade_medida':i.unidade_medida,'apresentacao':i.apresentacao or ''}
                    for i in itens])
