# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.estoque import ItemEstoque, MovEstoque
from database.db import db
from utils.numeros import decimal_de
from utils.audit import auditar_aqui
from datetime import datetime, date
from utils.rbac import requer_permissao
from utils.seguranca_http import limitar

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

    # O seletor "Todas categorias" existia na tela e nunca teve opção nenhuma:
    # a rota filtra por categoria e não passava a lista para preenchê-lo. Sai da
    # base e não de uma constante, porque a categoria é texto livre no model.
    categorias = sorted(
        v[0] for v in ItemEstoque.query
        .with_entities(ItemEstoque.categoria)
        .filter_by(unidade_id=uid, ativo=True)
        .distinct().all()
        if v[0]
    )

    return render_template('estoque/index.html', itens=itens, q=q, cat=cat,
                           categorias=categorias,
                           criticos=criticos, total_itens=total_itens,
                           criticos_n=criticos_n, zerados_n=zerados_n)

@estoque_bp.route('/novo', methods=['GET', 'POST'])
@login_required
@requer_permissao("med-admin:write")
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
                # `decimal_de` aceita a vírgula decimal; `float()` direto não.
                # No MESMO arquivo, `editar` já trocava a vírgula por ponto e
                # esta rota não: cadastrar item com "10,5" caía no `except`
                # genérico abaixo e virava "Erro: could not convert string to
                # float" na tela, enquanto editar o mesmo item aceitava.
                quantidade=decimal_de(request.form.get('quantidade')) or 0,
                estoque_minimo=decimal_de(request.form.get('estoque_minimo')) or 10,
                estoque_maximo=decimal_de(request.form.get('estoque_maximo')),
                preco_unitario=decimal_de(request.form.get('preco_unitario')),
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
    # `item=None` explícito: o mesmo template serve cadastro e edição, e é por
    # ele que a tela decide entre campo vazio e valor gravado. Omitir aqui faria
    # o Jinja tratar como indefinido — que é falso, e funcionaria por acidente
    # até alguém trocar a comparação.
    return render_template('estoque/form.html', item=None)

# Mesma permissão que `novo` e `movimentar` deste módulo — era a única escrita
# de estoque sem nenhuma.
@estoque_bp.route('/<int:item_id>/editar', methods=['GET', 'POST'])
@login_required
@requer_permissao("med-admin:write")
def editar(item_id):
    """Edita o cadastro do item.

    A QUANTIDADE não é editável aqui de propósito: saldo só muda por
    movimentação, que deixa rastro em mov_estoque. Editar o número direto
    apagaria o histórico.
    """
    item = ItemEstoque.query.get_or_404(item_id)

    if request.method == 'POST':
        campos_texto = ('nome', 'categoria', 'apresentacao', 'unidade_medida',
                        'codigo_interno', 'lote_atual')
        alteracoes = []

        for campo in campos_texto:
            if campo not in request.form:
                continue
            novo = (request.form.get(campo) or '').strip() or None
            if getattr(item, campo) != novo:
                alteracoes.append(campo)
                setattr(item, campo, novo)

        if not item.nome:
            flash('O nome do item é obrigatório.', 'warning')
            return render_template('estoque/form.html', item=item)

        for campo in ('estoque_minimo', 'estoque_maximo', 'preco_unitario'):
            if campo not in request.form:
                continue
            bruto = (request.form.get(campo) or '').strip().replace(',', '.')
            if not bruto:
                if getattr(item, campo) is not None:
                    alteracoes.append(campo)
                    setattr(item, campo, None)
                continue
            try:
                valor = float(bruto)
            except ValueError:
                flash(f'{campo.replace("_", " ").capitalize()} deve ser numérico.', 'warning')
                return render_template('estoque/form.html', item=item)
            if getattr(item, campo) != valor:
                alteracoes.append(campo)
                setattr(item, campo, valor)

        validade = (request.form.get('validade') or '').strip()
        if 'validade' in request.form:
            nova = None
            if validade:
                try:
                    nova = datetime.strptime(validade, '%Y-%m-%d').date()
                except ValueError:
                    flash('Data de validade inválida.', 'warning')
                    return render_template('estoque/form.html', item=item)
            if item.validade != nova:
                alteracoes.append('validade')
                item.validade = nova

        if 'ativo' in request.form:
            ativo = request.form.get('ativo') in ('1', 'on', 'true')
            if item.ativo != ativo:
                alteracoes.append('ativo')
                item.ativo = ativo

        if alteracoes:
            auditar_aqui('itens_estoque', 'update',
                         f'Campos alterados em {item.nome}: '
                         f'{", ".join(sorted(set(alteracoes)))}')
            db.session.commit()
            flash(f'{item.nome} atualizado.', 'success')
        else:
            flash('Nenhuma alteração a salvar.', 'info')

        return redirect(url_for('estoque.index'))

    return render_template('estoque/form.html', item=item)


@estoque_bp.route('/<int:id>/movimentar', methods=['GET', 'POST'])
@login_required
@requer_permissao("med-admin:write")
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
# Autocomplete de item de estoque — mesma razão.
@limitar(maximo=300, janela_segundos=300)
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
