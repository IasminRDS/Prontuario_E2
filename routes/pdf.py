import os
import uuid
from werkzeug.utils import secure_filename
from flask import Blueprint, send_file, abort, request, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

from models.prontuario import Prontuario
from models.paciente import Paciente
from models.medico import Medico
from models.encaminhamento import Encaminhamento
from services.pdf_service import gerar_prontuario, gerar_receituario, gerar_atestado
from services.pdf_encaminhamento import gerar_encaminhamento
from services.pdf_manager import PDFManager
from utils.audit import registrar
from utils.rbac import requer_permissao

pdf_bp = Blueprint('pdf', __name__, url_prefix='/pdf')

@pdf_bp.route('/prontuario/<int:id>')
@login_required
def prontuario(id):
    p = Prontuario.query.get_or_404(id)
    paciente = p.paciente
    medico   = p.medico
    unidade  = p.unidade
    buf = gerar_prontuario(p, paciente, medico, unidade)
    registrar("prontuarios", id, "read", "PDF do prontuário gerado", commit=True)
    nome = f'prontuario_{paciente.nome.split()[0].lower()}_{id}.pdf'
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=False, download_name=nome)

@pdf_bp.route('/receituario/<int:id>')
@login_required
def receituario(id):
    p = Prontuario.query.get_or_404(id)
    if not p.prescricao:
        abort(400, 'Prontuário sem prescrição registrada.')
    paciente = p.paciente
    medico   = p.medico
    unidade  = p.unidade
    buf = gerar_receituario(p, paciente, medico, unidade)
    registrar("prontuarios", id, "read", "PDF do receituário gerado", commit=True)
    nome = f'receituario_{paciente.nome.split()[0].lower()}_{id}.pdf'
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=False, download_name=nome)

@pdf_bp.route('/atestado/<int:paciente_id>', methods=['GET', 'POST'])
@login_required
@requer_permissao("clinical:read")
def atestado(paciente_id):
    paciente = Paciente.query.get_or_404(paciente_id)
    medico   = Medico.query.filter_by(user_id=current_user.id).first()
    unidade  = current_user.unidade

    if request.method == 'POST':
        dias = int(request.form.get('dias', 1))
        cid  = request.form.get('cid', '').strip().upper() or None
        obs  = request.form.get('observacao', '').strip() or None
        buf  = gerar_atestado(paciente, medico, unidade, dias, cid, obs)
        registrar("pacientes", paciente_id, "read", "PDF de atestado gerado", commit=True)
        nome = f'atestado_{paciente.nome.split()[0].lower()}.pdf'
        return send_file(buf, mimetype='application/pdf',
                         as_attachment=False, download_name=nome)

    return render_template('pdf/atestado_form.html', paciente=paciente)

@pdf_bp.route('/encaminhamento/<int:id>')
@login_required
def encaminhamento(id):
    enc      = Encaminhamento.query.get_or_404(id)
    paciente = enc.paciente
    medico   = enc.medico
    unidade  = enc.unidade_origem
    buf = gerar_encaminhamento(enc, paciente, medico, unidade)
    registrar("encaminhamentos", id, "read", "PDF de encaminhamento gerado", commit=True)
    nome = f'encaminhamento_{enc.especialidade.lower().replace(" ","_")}_{id}.pdf'
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=False, download_name=nome)


@pdf_bp.route('/alta/<int:internacao_id>')
@login_required
def alta_hospitalar(internacao_id):
    from models.internacao import Internacao
    from services.pdf_alta import gerar_alta

    intern = Internacao.query.get_or_404(internacao_id)
    buf = gerar_alta(intern, intern.paciente, intern.medico, intern.unidade)
    registrar("internacoes", internacao_id, "read", "PDF sumário de alta gerado", commit=True)
    nome = f"alta_{intern.paciente.nome.split()[0].lower()}_{internacao_id}.pdf"
    return send_file(buf, mimetype='application/pdf',
                     as_attachment=False, download_name=nome)


@pdf_bp.route('/qrcode/paciente/<int:paciente_id>')
@login_required
def qrcode_paciente(paciente_id):
    """QR Code com o CNS/CPF do paciente, para leitura rápida na recepção."""
    from io import BytesIO

    try:
        import qrcode
    except ImportError:
        abort(503, 'Dependência ausente: pip install "qrcode[pil]"')

    pac = Paciente.query.get_or_404(paciente_id)
    qr = qrcode.QRCode(version=1, box_size=8, border=3)
    qr.add_data(pac.cns or pac.cpf or str(pac.id))
    qr.make(fit=True)

    buf = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype='image/png',
                     download_name=f'qr_{pac.nome.split()[0].lower()}.png')


# ==========================================
# ROTAS DE FERRAMENTAS PDF AVANÇADAS
# ==========================================

@pdf_bp.route('/ferramentas')
@login_required
def ferramentas():
    return render_template('pdf/ferramentas.html')

@pdf_bp.route('/processar', methods=['POST'])
@login_required
@requer_permissao("clinical:read")
def processar_pdf():
    arquivo = request.files.get('documento')
    acao = request.form.get('acao')
    
    if not arquivo or arquivo.filename == '':
        flash("Nenhum arquivo enviado.", "danger")
        return redirect(url_for('pdf.ferramentas'))

    os.makedirs('instance', exist_ok=True)
    
    nome_seguro = secure_filename(arquivo.filename)
    nome_temporario = f"temp_{uuid.uuid4().hex}_{nome_seguro}"
    caminho_temp = os.path.join('instance', nome_temporario)
    caminho_saida = os.path.join('instance', f"proc_{nome_temporario}")
    
    arquivo.save(caminho_temp)

    try:
        nome_download = request.form.get('nome_final', 'documento_processado').strip()
        if not nome_download.endswith('.pdf'):
            nome_download += '.pdf'

        if acao == 'compactar':
            nivel = request.form.get('nivel_compactacao', 'medio')
            PDFManager.compactar_pdf(caminho_temp, caminho_saida, nivel)
            registrar("pdf_tools", None, "process", f"Ferramenta PDF: {acao}", commit=True)

        elif acao == 'proteger':
            senha = request.form.get('senha_pdf')
            permitir_impressao = request.form.get('permitir_impressao') == 'sim'
            PDFManager.proteger_pdf(caminho_temp, caminho_saida, senha, permitir_impressao)
            registrar("pdf_tools", None, "process", f"Ferramenta PDF: {acao}", commit=True)

        return send_file(caminho_saida, as_attachment=True, download_name=nome_download)
        
    except Exception as e:
        flash(f"Erro ao processar PDF: {e}", "danger")
        return redirect(url_for('pdf.ferramentas'))
    finally:
        if os.path.exists(caminho_temp):
            os.remove(caminho_temp)

@pdf_bp.route('/reorganizar', methods=['GET', 'POST'])
@login_required
@requer_permissao("clinical:read")
def reorganizar():
    if request.method == 'GET':
        return render_template('pdf/reorganizar.html')
        
    arquivo = request.files.get('documento')
    ordem = request.form.get('ordem_paginas')
    
    if not arquivo or arquivo.filename == '' or not ordem:
        flash("Arquivo ou ordem de páginas inválidos.", "danger")
        return redirect(url_for('pdf.reorganizar'))
        
    os.makedirs('instance', exist_ok=True)
    nome_seguro = secure_filename(arquivo.filename)
    nome_temp = f"temp_{uuid.uuid4().hex}_{nome_seguro}"
    caminho_temp = os.path.join('instance', nome_temp)
    caminho_saida = os.path.join('instance', f"reorg_{nome_seguro}")
    
    arquivo.save(caminho_temp)
    
    try:
        # Converte a string de texto para uma lista de números
        nova_ordem = [int(x) for x in ordem.split(',')]
        
        PDFManager.reorganizar_pdf(caminho_temp, caminho_saida, nova_ordem)
        registrar("pdf_tools", None, "process", "Ferramenta PDF: reorganizar", commit=True)
        
        return send_file(caminho_saida, as_attachment=True, download_name=f"novo_{nome_seguro}")
    except Exception as e:
        flash(f"Erro ao reorganizar PDF.", "danger")
        return redirect(url_for('pdf.reorganizar'))
    finally:
        if os.path.exists(caminho_temp):
            os.remove(caminho_temp)