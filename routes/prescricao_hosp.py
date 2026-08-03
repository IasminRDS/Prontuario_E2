# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.prescricao_hospitalar import PrescricaoHospitalar, ItemPrescricaoHosp, AdministracaoMed
from models.internacao import Internacao
from models.medico import Medico
from models.medicamento import Medicamento
from database.db import db
from utils.audit import audit_log, auditar_aqui
from utils.rbac import requer_permissao
from utils.security import medico_requerido
from datetime import datetime, timedelta

pres_hosp_bp = Blueprint('pres_hosp', __name__, url_prefix='/prescricao-hosp')


@pres_hosp_bp.route('/internacao/<int:internacao_id>')
@login_required
def lista(internacao_id):
    intern    = Internacao.query.get_or_404(internacao_id)
    pres_list = (PrescricaoHospitalar.query
                 .filter_by(internacao_id=internacao_id)
                 .order_by(PrescricaoHospitalar.data_prescricao.desc())
                 .all())
    ativa = next((p for p in pres_list if p.status == 'ativa'), None)
    return render_template('prescricao_hosp/lista.html',
                           intern=intern, pres_list=pres_list, ativa=ativa)


@pres_hosp_bp.route('/nova/<int:internacao_id>', methods=['GET', 'POST'])
@login_required
@medico_requerido
def nova(internacao_id):
    intern   = Internacao.query.get_or_404(internacao_id)
    medico   = Medico.query.filter_by(user_id=current_user.id).first()
    catalogo = Medicamento.query.filter_by(ativo=True).order_by(Medicamento.nome_generico).all()

    if request.method == 'POST':
        try:
            pres = PrescricaoHospitalar(
                internacao_id   = internacao_id,
                # A prescrição é do paciente, não só da internação: sem isto a
                # tela não conseguia dizer de quem ela era.
                paciente_id     = intern.paciente_id,
                medico_id       = medico.id if medico else None,
                unidade_id      = current_user.unidade_id,
                validade_ate    = datetime.utcnow() + timedelta(hours=24),
                dieta           = request.form.get('dieta', '').strip() or None,
                decubito        = request.form.get('decubito', '').strip() or None,
                sinais_vitais   = request.form.get('sinais_vitais', '').strip() or None,
                observacoes     = request.form.get('observacoes', '').strip() or None,
            )
            if 'assinar' in request.form:
                # Não poder assinar não invalida a prescrição: salvamos sem
                # assinatura e dizemos o porquê, em vez de perder o que foi
                # digitado.
                try:
                    pres.assinar()
                except ValueError as erro:
                    flash(f"{erro} A prescrição foi salva sem assinatura.", "warning")
            db.session.add(pres)
            db.session.flush()

            nomes    = request.form.getlist('item_nome')
            doses    = request.form.getlist('item_dose')
            concs    = request.form.getlist('item_concentracao')
            diluicoes= request.form.getlist('item_diluicao')
            vias     = request.form.getlist('item_via')
            vels     = request.form.getlist('item_velocidade')
            freqs    = request.form.getlist('item_frequencia')
            hors     = request.form.getlist('item_horarios')
            durs     = request.form.getlist('item_duracao')
            obs_list = request.form.getlist('item_obs')
            med_ids  = request.form.getlist('item_med_id')

            for i, nome in enumerate(nomes):
                if not nome.strip():
                    continue
                mid = med_ids[i] if i < len(med_ids) and med_ids[i] else None
                item = ItemPrescricaoHosp(
                    prescricao_id  = pres.id,
                    medicamento_id = int(mid) if mid else None,
                    nome_livre     = nome.strip() if not mid else None,
                    dose           = doses[i].strip()    if i < len(doses)    else None,
                    concentracao   = concs[i].strip()    if i < len(concs)    else None,
                    diluicao       = diluicoes[i].strip()if i < len(diluicoes)else None,
                    via            = vias[i].strip()     if i < len(vias)     else None,
                    velocidade     = vels[i].strip()     if i < len(vels)     else None,
                    frequencia     = freqs[i].strip()    if i < len(freqs)    else None,
                    horarios       = hors[i].strip()     if i < len(hors)     else None,
                    duracao        = durs[i].strip()     if i < len(durs)     else None,
                    # A coluna do item chama-se `instrucoes`; o campo do
                    # formulário, `item_obs`. O construtor usava `observacoes`,
                    # que não existe em ItemPrescricaoHosp.
                    instrucoes     = obs_list[i].strip() if i < len(obs_list) else None,
                    ordem          = i,
                )
                db.session.add(item)

            # Suspender prescrição anterior se existir
            ant = PrescricaoHospitalar.query.filter_by(
                internacao_id=internacao_id, status='ativa').first()
            if ant and ant.id != pres.id:
                ant.status = 'suspensa'

            auditar_aqui("prescricoes_hospitalares", "create")
            db.session.commit()
            flash('Prescrição registrada!', 'success')
            return redirect(url_for('pres_hosp.visualizar', id=pres.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {e}', 'danger')

    return render_template('prescricao_hosp/form.html',
                           intern=intern, catalogo=catalogo)


@pres_hosp_bp.route('/<int:id>')
@login_required
def visualizar(id):
    pres = PrescricaoHospitalar.query.get_or_404(id)
    return render_template('prescricao_hosp/visualizar.html', pres=pres)


# Checagem de medicação é ato de enfermagem, e vira registro no prontuário:
# exige a mesma permissão que a farmácia usa para movimentar administração.
@pres_hosp_bp.route('/item/<int:item_id>/administrar', methods=['POST'])
@login_required
@requer_permissao("med-admin:write")
def administrar(item_id):
    item   = ItemPrescricaoHosp.query.get_or_404(item_id)
    status = request.form.get('status', 'administrado')
    obs    = request.form.get('observacoes', '').strip() or None

    adm = AdministracaoMed(
        item_id         = item_id,
        profissional_id = current_user.id,
        status          = status,
        observacoes     = obs,
    )
    db.session.add(adm)
    auditar_aqui("administracoes_med", "create")
    db.session.commit()
    flash(f'{item.nome_exibicao} — {status}.', 'success')
    return redirect(url_for('pres_hosp.visualizar', id=item.prescricao_id))
