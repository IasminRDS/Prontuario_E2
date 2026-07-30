# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.cirurgia import Cirurgia, SalaCirurgica
from models.internacao import Internacao
from models.paciente import Paciente
from models.medico import Medico
from database.db import db
from utils.audit import audit_log, auditar_aqui
from utils.security import medico_requerido
from datetime import datetime, date

cirurgia_bp = Blueprint('cirurgia', __name__, url_prefix='/cirurgia')


@cirurgia_bp.route('/')
@login_required
def painel():
    hoje   = date.today()
    data_s = request.args.get('data', hoje.strftime('%Y-%m-%d'))
    try:
        data_f = datetime.strptime(data_s, '%Y-%m-%d').date()
    except ValueError:
        data_f = hoje

    cirurgias = (Cirurgia.query
                 .filter(db.func.date(Cirurgia.data_agendada) == data_f)
                 .order_by(Cirurgia.data_agendada)
                 .all())
    salas = SalaCirurgica.query.filter_by(ativa=True).all()

    agendadas   = sum(1 for c in cirurgias if c.status == 'agendada')
    realizadas  = sum(1 for c in cirurgias if c.status == 'realizada')
    canceladas  = sum(1 for c in cirurgias if c.status in ('cancelada','suspensa'))

    return render_template('cirurgia/painel.html',
                           cirurgias=cirurgias, salas=salas,
                           data_s=data_s, data_f=data_f, hoje=hoje,
                           agendadas=agendadas, realizadas=realizadas,
                           canceladas=canceladas)


@cirurgia_bp.route('/nova', methods=['GET', 'POST'])
@cirurgia_bp.route('/nova/<int:paciente_id>', methods=['GET', 'POST'])
@login_required
@medico_requerido
def nova(paciente_id=None):
    pacientes = Paciente.query.filter_by(ativo=True).order_by(Paciente.nome).all()
    medicos   = Medico.query.all()
    salas     = SalaCirurgica.query.filter_by(ativa=True).all()

    if request.method == 'POST':
        try:
            da_str = request.form.get('data_agendada', '').strip()
            data_ag = datetime.strptime(da_str, '%Y-%m-%dT%H:%M') if da_str else None

            cir = Cirurgia(
                paciente_id      = int(request.form['paciente_id']),
                internacao_id    = request.form.get('internacao_id') or None,
                sala_id          = request.form.get('sala_id') or None,
                cirurgiao_id     = request.form.get('cirurgiao_id') or None,
                anestesista_id   = request.form.get('anestesista_id') or None,
                unidade_id       = current_user.unidade_id,
                procedimento     = request.form.get('procedimento', '').strip(),
                codigo_tuss      = request.form.get('codigo_tuss', '').strip() or None,
                cid              = request.form.get('cid', '').strip().upper() or None,
                tipo_anestesia   = request.form.get('tipo_anestesia', '').strip() or None,
                carater          = request.form.get('carater', 'eletiva'),
                especialidade    = request.form.get('especialidade', '').strip() or None,
                data_agendada    = data_ag,
                duracao_prevista = int(request.form['duracao_prevista']) if request.form.get('duracao_prevista') else None,
                observacoes      = request.form.get('observacoes', '').strip() or None,
                criado_por       = current_user.id,
            )
            db.session.add(cir)
            db.session.flush()
            auditar_aqui("cirurgias", "create")
            db.session.commit()
            flash('Cirurgia agendada!', 'success')
            return redirect(url_for('cirurgia.visualizar', id=cir.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')

    paciente_sel = Paciente.query.get(paciente_id) if paciente_id else None
    internacoes  = []
    if paciente_id:
        internacoes = Internacao.query.filter_by(
            paciente_id=paciente_id, status='ativa').all()

    return render_template('cirurgia/form.html',
                           pacientes=pacientes, medicos=medicos,
                           salas=salas, paciente_sel=paciente_sel,
                           internacoes=internacoes)


@cirurgia_bp.route('/<int:id>')
@login_required
def visualizar(id):
    cir = Cirurgia.query.get_or_404(id)
    return render_template('cirurgia/visualizar.html', cir=cir)


@cirurgia_bp.route('/<int:id>/iniciar', methods=['POST'])
@login_required
def iniciar(id):
    cir = Cirurgia.query.get_or_404(id)
    cir.status     = 'em_andamento'
    cir.data_inicio= datetime.utcnow()
    if cir.sala:
        cir.sala.status = 'em_uso'
    auditar_aqui("cirurgias", "update")
    db.session.commit()
    flash('Cirurgia iniciada!', 'success')
    return redirect(url_for('cirurgia.visualizar', id=id))


@cirurgia_bp.route('/<int:id>/finalizar', methods=['GET', 'POST'])
@login_required
@medico_requerido
def finalizar(id):
    cir = Cirurgia.query.get_or_404(id)

    if request.method == 'POST':
        try:
            cir.status         = 'realizada'
            cir.data_fim       = datetime.utcnow()
            cir.relatorio      = request.form.get('relatorio', '').strip() or None
            cir.achados        = request.form.get('achados', '').strip() or None
            cir.intercorrencias= request.form.get('intercorrencias', '').strip() or None
            cir.materiais      = request.form.get('materiais', '').strip() or None
            cir.cid_pos_op     = request.form.get('cid_pos_op', '').strip().upper() or None
            if cir.sala:
                cir.sala.status = 'em_limpeza'
            auditar_aqui("cirurgias", "update")
            db.session.commit()
            flash('Cirurgia finalizada!', 'success')
            return redirect(url_for('cirurgia.visualizar', id=id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')

    return render_template('cirurgia/relatorio_form.html', cir=cir)


@cirurgia_bp.route('/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar(id):
    cir = Cirurgia.query.get_or_404(id)
    motivo = request.form.get('motivo', '').strip()
    cir.status = 'cancelada'
    cir.observacoes = (cir.observacoes or '') + f'\nCancelamento: {motivo}'
    if cir.sala:
        cir.sala.status = 'livre'
    auditar_aqui("cirurgias", "update")
    db.session.commit()
    flash('Cirurgia cancelada.', 'info')
    return redirect(url_for('cirurgia.painel'))
