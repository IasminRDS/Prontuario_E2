# -*- coding: utf-8 -*-
"""Minha conta — identificação, troca de senha e verificação em duas etapas.

Porte dos endpoints `/auth/mfa/*` e `/auth/change-password` do backend NestJS.

Regra de ouro do fluxo de MFA: `mfa_ativo` só vira True DEPOIS que o usuário
prova um código válido. Quem escaneia o QR e fecha a aba não fica trancado fora
da própria conta.
"""
import base64
from datetime import datetime
from io import BytesIO

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from extensions import db
from utils.audit import registrar
from utils.rbac import permissoes_de

conta_bp = Blueprint("conta", __name__, url_prefix="/conta")

EMISSOR = "SNPE — Prontuário Eletrônico"
CHAVE_SETUP = "mfa_setup_secret"


def _qrcode_data_uri(uri):
    """PNG do QR em data: URI — evita servir o segredo por uma rota separada."""
    try:
        import qrcode
    except ImportError:
        return None

    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(uri)
    qr.make(fit=True)
    buf = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


@conta_bp.get("/")
@login_required
def index():
    return render_template(
        "conta/index.html",
        permissoes=sorted(permissoes_de(current_user.perfil)),
        setup_pendente=CHAVE_SETUP in session,
    )


@conta_bp.post("/senha")
@login_required
def trocar_senha():
    atual = request.form.get("senha_atual") or ""
    nova = request.form.get("senha_nova") or ""
    confirma = request.form.get("senha_confirma") or ""

    if not current_user.check_password(atual):
        flash("Senha atual incorreta.", "danger")
        return redirect(url_for("conta.index"))
    if len(nova) < 8:
        flash("A nova senha precisa ter ao menos 8 caracteres.", "warning")
        return redirect(url_for("conta.index"))
    if nova != confirma:
        flash("A confirmação não corresponde à nova senha.", "warning")
        return redirect(url_for("conta.index"))
    if nova == atual:
        flash("A nova senha deve ser diferente da atual.", "warning")
        return redirect(url_for("conta.index"))

    current_user.set_password(nova)
    registrar("users", current_user.id, "update", "Senha alterada pelo próprio usuário")
    db.session.commit()

    flash("Senha alterada.", "success")
    return redirect(url_for("conta.index"))


@conta_bp.post("/mfa/setup")
@login_required
def mfa_setup():
    """Gera um segredo provisório e mostra o QR. Nada é persistido ainda."""
    try:
        import pyotp
    except ImportError:
        flash('Dependência ausente: pip install pyotp', "danger")
        return redirect(url_for("conta.index"))

    if current_user.mfa_ativo:
        flash("A verificação em duas etapas já está ativa.", "info")
        return redirect(url_for("conta.index"))

    secret = pyotp.random_base32()
    session[CHAVE_SETUP] = secret

    uri = pyotp.TOTP(secret).provisioning_uri(
        name=current_user.email, issuer_name=EMISSOR
    )

    return render_template(
        "conta/mfa_setup.html",
        secret=secret,
        qrcode=_qrcode_data_uri(uri),
        uri=uri,
    )


@conta_bp.post("/mfa/enable")
@login_required
def mfa_enable():
    """Confirma o setup: só grava o segredo se o código bater."""
    try:
        import pyotp
    except ImportError:
        flash('Dependência ausente: pip install pyotp', "danger")
        return redirect(url_for("conta.index"))

    secret = session.get(CHAVE_SETUP)
    if not secret:
        flash("Sessão de configuração expirada. Comece de novo.", "warning")
        return redirect(url_for("conta.index"))

    codigo = (request.form.get("codigo") or "").strip().replace(" ", "")
    if not pyotp.TOTP(secret).verify(codigo, valid_window=1):
        flash("Código inválido. Confira o app autenticador e tente novamente.", "danger")
        return redirect(url_for("conta.index"))

    current_user.mfa_secret = secret
    current_user.mfa_ativo = True
    current_user.mfa_confirmado_em = datetime.utcnow()
    session.pop(CHAVE_SETUP, None)

    registrar("users", current_user.id, "update", "MFA (TOTP) ativado")
    db.session.commit()

    flash("Verificação em duas etapas ativada.", "success")
    return redirect(url_for("conta.index"))


@conta_bp.post("/mfa/disable")
@login_required
def mfa_disable():
    """Desativar exige a senha — senão bastaria a sessão para derrubar o 2FA."""
    if not current_user.mfa_ativo:
        return redirect(url_for("conta.index"))

    if not current_user.check_password(request.form.get("senha") or ""):
        flash("Senha incorreta. A verificação em duas etapas continua ativa.", "danger")
        return redirect(url_for("conta.index"))

    current_user.mfa_ativo = False
    current_user.mfa_secret = None
    current_user.mfa_confirmado_em = None

    registrar("users", current_user.id, "update", "MFA (TOTP) desativado")
    db.session.commit()

    flash("Verificação em duas etapas desativada.", "warning")
    return redirect(url_for("conta.index"))
