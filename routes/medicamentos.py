# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.medicamento import Medicamento, Prescricao, ItemPrescricao
from models.paciente import Paciente
from models.medico import Medico
from database.db import db
from utils.audit import auditar_aqui
from datetime import datetime
from utils.rbac import requer_permissao

medicamentos_bp = Blueprint('medicamentos', __name__, url_prefix='/medicamentos')


# ── Índice de prescrições (porta de entrada do módulo) ──
@medicamentos_bp.get('/')
@login_required
def index():
    """Todas as prescrições, mais recentes primeiro."""
    termo = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or '').strip()
    pagina = request.args.get('pagina', type=int) or 1

    query = Prescricao.query
    if status in ('ativa', 'suspensa', 'concluida'):
        query = query.filter(Prescricao.status == status)
    if termo:
        like = f'%{termo}%'
        query = query.join(Paciente, Prescricao.paciente_id == Paciente.id).filter(
            Paciente.nome.ilike(like) | Paciente.cpf.ilike(like)
        )

    paginacao = (query.order_by(Prescricao.criado_em.desc())
                 .paginate(page=pagina, per_page=30, error_out=False))

    ids_pac = {p.paciente_id for p in paginacao.items}
    pacientes = ({p.id: p for p in Paciente.query.filter(Paciente.id.in_(ids_pac)).all()}
                 if ids_pac else {})

    return render_template('medicamentos/index.html',
                           paginacao=paginacao,
                           prescricoes=paginacao.items,
                           pacientes=pacientes,
                           termo=termo,
                           status=status,
                           total_catalogo=Medicamento.query.filter_by(ativo=True).count())


# ── Prescrições do paciente ──
@medicamentos_bp.route('/paciente/<int:paciente_id>')
@login_required
@requer_permissao("prescription:read")
def lista_paciente(paciente_id):
    paciente   = Paciente.query.get_or_404(paciente_id)
    prescricoes= (Prescricao.query
                  .filter_by(paciente_id=paciente_id)
                  .order_by(Prescricao.criado_em.desc())
                  .all())
    ativas    = [p for p in prescricoes if p.status == 'ativa']
    historico = [p for p in prescricoes if p.status != 'ativa']
    return render_template('medicamentos/lista.html',
                           paciente=paciente, ativas=ativas, historico=historico)


@medicamentos_bp.route('/prescrever/<int:paciente_id>', methods=['GET', 'POST'])
@medicamentos_bp.route('/prescrever/<int:paciente_id>/<int:prontuario_id>',
                       methods=['GET', 'POST'])
@login_required
@requer_permissao("prescription:create", "prescription:write")
def prescrever(paciente_id, prontuario_id=None):
    paciente = Paciente.query.get_or_404(paciente_id)
    medico   = Medico.query.filter_by(user_id=current_user.id).first()
    catalogo = Medicamento.query.filter_by(ativo=True).order_by(Medicamento.nome_generico).all()

    if request.method == 'POST':
        try:
            pres = Prescricao(
                paciente_id   = paciente_id,
                prontuario_id = prontuario_id,
                medico_id     = medico.id if medico else None,
                unidade_id    = current_user.unidade_id,
                tipo          = request.form.get('tipo', 'ambulatorial'),
                validade_dias = int(request.form['validade_dias']) if request.form.get('validade_dias') else None,
                observacoes   = request.form.get('observacoes','').strip() or None,
                criado_por    = current_user.id,
            )
            db.session.add(pres)
            db.session.flush()

            # Itens: os campos chegam como listas paralelas
            nomes    = request.form.getlist('item_nome')
            doses    = request.form.getlist('item_dose')
            vias     = request.form.getlist('item_via')
            freqs    = request.form.getlist('item_frequencia')
            duracoes = request.form.getlist('item_duracao')
            qtds     = request.form.getlist('item_quantidade')
            insts    = request.form.getlist('item_instrucoes')
            med_ids  = request.form.getlist('item_medicamento_id')

            for i, nome in enumerate(nomes):
                if not nome.strip():
                    continue
                mid = med_ids[i] if i < len(med_ids) and med_ids[i] else None
                item = ItemPrescricao(
                    prescricao_id  = pres.id,
                    unidade_id     = pres.unidade_id,
                    medicamento_id = int(mid) if mid else None,
                    nome_livre     = nome.strip() if not mid else None,
                    dose           = doses[i].strip()    if i < len(doses)    else None,
                    via            = vias[i].strip()     if i < len(vias)     else None,
                    frequencia     = freqs[i].strip()    if i < len(freqs)    else None,
                    duracao        = duracoes[i].strip() if i < len(duracoes) else None,
                    quantidade     = qtds[i].strip()     if i < len(qtds)     else None,
                    instrucoes     = insts[i].strip()    if i < len(insts)    else None,
                )
                db.session.add(item)

            auditar_aqui("prescricoes", "create")
            db.session.commit()
            flash('Prescrição registrada com sucesso!', 'success')
            return redirect(url_for('medicamentos.visualizar', id=pres.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao salvar prescrição: {e}', 'danger')

    return render_template('medicamentos/form.html',
                           paciente=paciente,
                           catalogo=catalogo,
                           prontuario_id=prontuario_id)


@medicamentos_bp.route('/prescricao/<int:id>')
@login_required
@requer_permissao("prescription:read")
def visualizar(id):
    pres = Prescricao.query.get_or_404(id)
    return render_template('medicamentos/visualizar.html', pres=pres)


@medicamentos_bp.route('/prescricao/<int:id>/status', methods=['POST'])
@login_required
@requer_permissao("prescription:write")
def atualizar_status(id):
    pres  = Prescricao.query.get_or_404(id)
    novo  = request.form.get('status')
    if novo in Prescricao.STATUS_LABELS:
        pres.status = novo
        auditar_aqui("prescricoes", "update")
        db.session.commit()
        flash('Status atualizado!', 'success')
    return redirect(url_for('medicamentos.lista_paciente',
                            paciente_id=pres.paciente_id))


# ── Catálogo de medicamentos ──
@medicamentos_bp.route('/catalogo')
@login_required
def catalogo():
    q    = request.args.get('q', '').strip()
    meds = Medicamento.query
    if q:
        meds = meds.filter(db.or_(
            Medicamento.nome_generico.ilike(f'%{q}%'),
            Medicamento.nome_comercial.ilike(f'%{q}%'),
        ))
    meds = meds.order_by(Medicamento.nome_generico).all()
    return render_template('medicamentos/catalogo.html', meds=meds, q=q)


@medicamentos_bp.route('/catalogo/novo', methods=['GET', 'POST'])
@login_required
@requer_permissao("prescription:create")
def novo_medicamento():
    if request.method == 'POST':
        try:
            m = Medicamento(
                nome_generico  = request.form.get('nome_generico','').strip(),
                nome_comercial = request.form.get('nome_comercial','').strip() or None,
                classe         = request.form.get('classe','').strip() or None,
                apresentacao   = request.form.get('apresentacao','').strip() or None,
                via_admin      = request.form.get('via_admin','').strip() or None,
                controlado     = 'controlado' in request.form,
                lista_rename   = request.form.get('lista_rename','').strip().upper() or None,
            )
            db.session.add(m)
            db.session.flush()
            auditar_aqui("medicamentos", "create")
            db.session.commit()
            flash(f'{m.nome_generico} cadastrado!', 'success')
            return redirect(url_for('medicamentos.catalogo'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')
    return render_template('medicamentos/med_form.html')


@medicamentos_bp.route('/buscar')
@login_required
def buscar():
    """API de autocomplete para o formulário de prescrição."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    meds = Medicamento.query.filter(
        Medicamento.ativo == True,
        db.or_(
            Medicamento.nome_generico.ilike(f'%{q}%'),
            Medicamento.nome_comercial.ilike(f'%{q}%'),
        )
    ).limit(10).all()
    return jsonify([{
        'id':           m.id,
        'nome':         m.nome_generico,
        'comercial':    m.nome_comercial or '',
        'apresentacao': m.apresentacao or '',
        'via':          m.via_admin or '',
    } for m in meds])
