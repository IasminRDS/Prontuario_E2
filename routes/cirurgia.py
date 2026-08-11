# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.cirurgia import Cirurgia, SalaCirurgica
from models.internacao import Internacao
from models.paciente import Paciente
from models.medico import Medico
from database.db import db
from utils.audit import auditar_aqui
from utils.security import medico_requerido, validar_cid10
from datetime import datetime, date
from utils.rbac import requer_permissao

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
@requer_permissao("surgery:write")
def nova(paciente_id=None):
    pacientes = Paciente.query.filter_by(ativo=True).order_by(Paciente.nome).all()
    medicos   = Medico.query.all()
    salas     = SalaCirurgica.query.filter_by(ativa=True).all()

    if request.method == 'POST':
        # Esta rota construía `Cirurgia` com nove argumentos que não são colunas
        # do model (`cirurgiao_id`, `procedimento`, `cid`, `carater`,
        # `especialidade`, `duracao_prevista`, `codigo_tuss`, `anestesista_id`,
        # `unidade_id`). O primeiro deles levantava TypeError, o `except` abaixo
        # o transformava num aviso amarelo, e agendar cirurgia nunca funcionou —
        # nenhuma linha era criada. Os nomes agora são os do model:
        # `descricao` guarda o procedimento e `medico_id` é o cirurgião
        # principal.
        paciente_id_sel = request.form.get('paciente_id', type=int)
        procedimento = (request.form.get('procedimento') or '').strip()

        da_str = (request.form.get('data_agendada') or '').strip()
        try:
            data_ag = datetime.strptime(da_str, '%Y-%m-%dT%H:%M') if da_str else None
        except ValueError:
            data_ag = None

        # `descricao` é NOT NULL: sem validar aqui, o formulário vazio viraria
        # um IntegrityError exibido cru para quem está agendando.
        if not paciente_id_sel:
            flash('Selecione o paciente.', 'warning')
        elif not procedimento:
            flash('Descreva o procedimento.', 'warning')
        elif da_str and data_ag is None:
            flash('Data do agendamento inválida.', 'warning')
        else:
            try:
                cir = Cirurgia(
                    paciente_id   = paciente_id_sel,
                    medico_id     = request.form.get('cirurgiao_id', type=int),
                    sala_id       = request.form.get('sala_id', type=int),
                    internacao_id = request.form.get('internacao_id', type=int),
                    unidade_id    = current_user.unidade_id,
                    descricao     = procedimento,
                    data_agendada = data_ag,
                    status        = 'agendada',
                    observacoes   = (request.form.get('observacoes') or '').strip() or None,
                    criado_por    = current_user.id,
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
@requer_permissao("surgery:write")
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
@requer_permissao("surgery:write")
def finalizar(id):
    cir = Cirurgia.query.get_or_404(id)

    if request.method == 'POST':
        cid = request.form.get('cid_pos_op', '').strip().upper() or None
        # O CID vem digitado. Sem conferir o formato, o laudo carrega um código
        # que nenhuma tabela reconhece — e o relatório operatório é justamente
        # o documento que vai para o faturamento e para a auditoria.
        if cid and not validar_cid10(cid):
            flash('CID pós-operatório inválido.', 'warning')
            return render_template('cirurgia/relatorio_form.html', cir=cir)
        try:
            cir.status         = 'realizada'
            cir.data_fim       = datetime.utcnow()
            cir.relatorio      = request.form.get('relatorio', '').strip() or None
            cir.achados        = request.form.get('achados', '').strip() or None
            cir.intercorrencias= request.form.get('intercorrencias', '').strip() or None
            cir.materiais      = request.form.get('materiais', '').strip() or None
            cir.cid_pos_op     = cid
            if cir.sala:
                cir.sala.status = 'em_limpeza'
            auditar_aqui("cirurgias", "update")
            db.session.commit()
            flash('Cirurgia finalizada!', 'success')
            return redirect(url_for('cirurgia.visualizar', id=id))
        except Exception as e:
            # REGISTRA antes de degradar. Foi um `except` como este que exibiu
            # como aviso amarelo, por tempo indeterminado, o TypeError que fazia
            # o agendamento de cirurgia nunca criar uma linha (TCC, 9.4.6).
            from flask import current_app

            current_app.logger.exception(
                "falha ao finalizar a cirurgia %s", cir.id)
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')

    return render_template('cirurgia/relatorio_form.html', cir=cir)


@cirurgia_bp.route('/<int:id>/cancelar', methods=['POST'])
@login_required
@requer_permissao("surgery:write")
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
