# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.agendamento import Agendamento
from models.paciente import Paciente
from models.medico import Medico
from database.db import db
from utils.audit import audit_log, auditar_aqui
from datetime import datetime, date, timedelta
from utils.rbac import requer_permissao

agendamento_bp = Blueprint('agendamento', __name__, url_prefix='/agendamento')


@agendamento_bp.route('/')
@login_required
def index():
    hoje      = date.today()
    data_str  = request.args.get('data', hoje.strftime('%Y-%m-%d'))
    status    = request.args.get('status', '')
    medico_id = request.args.get('medico_id', '', type=str)

    try:
        data_filtro = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        data_filtro = hoje

    q = Agendamento.query.filter(
        db.func.date(Agendamento.data_hora) == data_filtro,
        Agendamento.unidade_id == current_user.unidade_id
    )
    if status:
        q = q.filter(Agendamento.status == status)
    if medico_id:
        q = q.filter(Agendamento.medico_id == int(medico_id))

    agendamentos = q.order_by(Agendamento.data_hora).all()
    medicos      = Medico.query.all()

    dia_ant  = (data_filtro - timedelta(days=1)).strftime('%Y-%m-%d')
    dia_prox = (data_filtro + timedelta(days=1)).strftime('%Y-%m-%d')

    return render_template('agendamento/index.html',
                           agendamentos=agendamentos,
                           data_filtro=data_filtro,
                           data_str=data_str,
                           dia_ant=dia_ant,
                           dia_prox=dia_prox,
                           medicos=medicos,
                           filtro_status=status,
                           filtro_medico=medico_id,
                           hoje=hoje)


@agendamento_bp.route('/novo', methods=['GET', 'POST'])
@agendamento_bp.route('/novo/<int:paciente_id>', methods=['GET', 'POST'])
@login_required
@requer_permissao("patient:read")
def novo(paciente_id=None):
    pacientes = Paciente.query.filter_by(ativo=True).order_by(Paciente.nome).all()
    medicos   = Medico.query.all()

    if request.method == 'POST':
        try:
            data_hora_str = request.form.get('data_hora', '')
            data_hora     = datetime.strptime(data_hora_str, '%Y-%m-%dT%H:%M')

            ag = Agendamento(
                paciente_id = int(request.form['paciente_id']),
                medico_id   = request.form.get('medico_id') or None,
                unidade_id  = current_user.unidade_id,
                data_hora   = data_hora,
                tipo        = request.form.get('tipo', 'consulta'),
                status      = 'agendado',
                observacoes = request.form.get('observacoes', '').strip() or None,
                criado_por  = current_user.id,
            )
            db.session.add(ag)
            db.session.flush()
            auditar_aqui("agendamentos", "create")
            db.session.commit()
            flash('Agendamento criado com sucesso!', 'success')
            return redirect(url_for('agendamento.index',
                                    data=data_hora.strftime('%Y-%m-%d')))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro ao agendar: {e}', 'danger')

    paciente_sel = Paciente.query.get(paciente_id) if paciente_id else None
    return render_template('agendamento/form.html',
                           pacientes=pacientes,
                           medicos=medicos,
                           paciente_sel=paciente_sel,
                           agendamento=None)


@agendamento_bp.route('/<int:id>/status', methods=['POST'])
@login_required
@requer_permissao("patient:read")
def atualizar_status(id):
    ag          = Agendamento.query.get_or_404(id)
    novo_status = request.form.get('status')
    motivo      = request.form.get('motivo_cancel', '').strip() or None

    if novo_status in Agendamento.STATUS_LABELS:
        ag.status = novo_status
        if motivo:
            ag.motivo_cancel = motivo
        auditar_aqui("agendamentos", "update")
        db.session.commit()
        flash(f'Status atualizado para {ag.status_label[0]}.', 'success')

    return redirect(url_for('agendamento.index',
                            data=ag.data_hora.strftime('%Y-%m-%d')))


@agendamento_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_permissao("patient:read")
def editar(id):
    ag        = Agendamento.query.get_or_404(id)
    pacientes = Paciente.query.filter_by(ativo=True).order_by(Paciente.nome).all()
    medicos   = Medico.query.all()

    if request.method == 'POST':
        try:
            data_hora  = datetime.strptime(request.form['data_hora'], '%Y-%m-%dT%H:%M')
            ag.paciente_id = int(request.form['paciente_id'])
            ag.medico_id   = request.form.get('medico_id') or None
            ag.data_hora   = data_hora
            ag.tipo        = request.form.get('tipo', ag.tipo)
            ag.observacoes = request.form.get('observacoes', '').strip() or None
            auditar_aqui("agendamentos", "update")
            db.session.commit()
            flash('Agendamento atualizado!', 'success')
            return redirect(url_for('agendamento.index',
                                    data=data_hora.strftime('%Y-%m-%d')))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')

    return render_template('agendamento/form.html',
                           agendamento=ag,
                           pacientes=pacientes,
                           medicos=medicos,
                           paciente_sel=ag.paciente)


@agendamento_bp.route('/api/horarios')
@login_required
def api_horarios():
    data_str = request.args.get('data', date.today().strftime('%Y-%m-%d'))
    try:
        d = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify([])
    ags = Agendamento.query.filter(
        db.func.date(Agendamento.data_hora) == d,
        Agendamento.unidade_id == current_user.unidade_id
    ).order_by(Agendamento.data_hora).all()
    return jsonify([{
        'id':       a.id,
        'paciente': a.paciente.nome_exibicao,
        'hora':     a.data_hora.strftime('%H:%M'),
        'tipo':     a.tipo_label,
        'status':   a.status,
    } for a in ags])
