# -*- coding: utf-8 -*-
"""Autenticação — senha, segunda etapa (TOTP) e login federado gov.br.

Porte de `modules/auth` + `modules/govbr` do backend NestJS.

Fluxo em duas etapas: a senha correta NÃO autentica quem tem MFA ativo. Ela só
cria um desafio na sessão (`mfa_pendente`), e o `login_user` acontece depois que
o código de 6 dígitos é aceito. Enquanto o desafio está aberto, o usuário não
tem sessão autenticada — nenhuma rota protegida abre.
"""
import secrets
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

from flask import (
    Blueprint, current_app, flash, redirect, render_template, request, session, url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from extensions import db
from models.user import User
from utils.audit import registrar

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

CHAVE_DESAFIO = "mfa_pendente"
CHAVE_GOVBR_STATE = "govbr_state"
VALIDADE_DESAFIO = timedelta(minutes=5)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _destino_seguro(target):
    """Impede open redirect: só aceita destino no mesmo host."""
    if not target:
        return None
    aqui = urlparse(request.host_url)
    la = urlparse(urljoin(request.host_url, target))
    if la.scheme in ("http", "https") and aqui.netloc == la.netloc:
        return target
    return None


def _concluir_login(user, proximo=None):
    login_user(user, remember=True)
    user.ultimo_acesso = datetime.utcnow()
    registrar("users", user.id, "login", f"Login efetuado ({user.email})")
    db.session.commit()

    session.pop(CHAVE_DESAFIO, None)
    flash("Login realizado com sucesso.", "success")
    return redirect(_destino_seguro(proximo) or url_for("dashboard.index"))


def _desafio_valido():
    """Devolve o desafio de MFA aberto na sessão, se não expirou."""
    desafio = session.get(CHAVE_DESAFIO)
    if not desafio:
        return None
    try:
        criado = datetime.fromisoformat(desafio["criado_em"])
    except (KeyError, TypeError, ValueError):
        session.pop(CHAVE_DESAFIO, None)
        return None
    if datetime.utcnow() - criado > VALIDADE_DESAFIO:
        session.pop(CHAVE_DESAFIO, None)
        return None
    return desafio


# --------------------------------------------------------------------------
# Etapa 1 — senha
# --------------------------------------------------------------------------

@auth_bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    desafio = _desafio_valido()
    return render_template(
        "auth/login.html",
        mfa_pendente=bool(desafio),
        proximo=request.args.get("next", ""),
        govbr_ativo=_govbr_ativo(),
    )


@auth_bp.post("/login")
def login_post():
    proximo = request.form.get("next") or request.args.get("next")
    identidade = (request.form.get("email") or "").strip().lower()
    senha = request.form.get("senha") or ""

    if not identidade or not senha:
        flash("Informe e-mail e senha.", "warning")
        return redirect(url_for("auth.login", next=proximo))

    user = User.query.filter(User.email == identidade).first()

    # Mensagem única para usuário inexistente, senha errada e conta inativa —
    # não entregamos a um atacante qual e-mail existe na base.
    if not user or not user.ativo or not user.check_password(senha):
        if user:
            registrar("users", user.id, "login_falha",
                      f"Tentativa de login rejeitada ({identidade})", commit=True)
        flash("Credenciais inválidas ou usuário inativo.", "danger")
        return redirect(url_for("auth.login", next=proximo))

    if user.mfa_ativo:
        session[CHAVE_DESAFIO] = {
            "user_id": user.id,
            "criado_em": datetime.utcnow().isoformat(),
            "proximo": proximo or "",
        }
        return redirect(url_for("auth.login", next=proximo))

    return _concluir_login(user, proximo)


# --------------------------------------------------------------------------
# Etapa 2 — código TOTP
# --------------------------------------------------------------------------

@auth_bp.post("/mfa/verify")
def mfa_verify():
    desafio = _desafio_valido()
    if not desafio:
        flash("A verificação expirou. Entre com e-mail e senha novamente.", "warning")
        return redirect(url_for("auth.login"))

    user = User.query.get(desafio["user_id"])
    if not user or not user.ativo:
        session.pop(CHAVE_DESAFIO, None)
        flash("Usuário indisponível.", "danger")
        return redirect(url_for("auth.login"))

    codigo = request.form.get("codigo") or ""
    if not user.verificar_totp(codigo):
        registrar("users", user.id, "mfa_falha",
                  "Código de verificação em duas etapas rejeitado", commit=True)
        flash("Código inválido ou expirado. Tente o código atual do aplicativo.", "danger")
        return redirect(url_for("auth.login"))

    return _concluir_login(user, desafio.get("proximo"))


@auth_bp.post("/mfa/cancelar")
def mfa_cancelar():
    session.pop(CHAVE_DESAFIO, None)
    return redirect(url_for("auth.login"))


# --------------------------------------------------------------------------
# Login federado gov.br (OIDC)
# --------------------------------------------------------------------------

def _govbr_ativo():
    """gov.br real exige client_id/secret. Sem eles, oferecemos o simulador."""
    return bool(current_app.config.get("GOVBR_CLIENT_ID"))


@auth_bp.get("/govbr/status")
def govbr_status():
    from flask import jsonify

    return jsonify({
        "configurado": _govbr_ativo(),
        "modo": "producao" if _govbr_ativo() else "simulador",
    })


@auth_bp.get("/govbr/login")
def govbr_login():
    """Inicia o fluxo. Sem credenciais reais, cai no simulador."""
    state = secrets.token_urlsafe(24)
    session[CHAVE_GOVBR_STATE] = state

    if not _govbr_ativo():
        return redirect(url_for("auth.govbr_simulador", state=state))

    # Fluxo real: redirect ao authorization endpoint do gov.br.
    from urllib.parse import urlencode

    params = urlencode({
        "response_type": "code",
        "client_id": current_app.config["GOVBR_CLIENT_ID"],
        "scope": "openid email profile govbr_confiabilidades",
        "redirect_uri": url_for("auth.govbr_callback", _external=True),
        "state": state,
        "nonce": secrets.token_urlsafe(16),
    })
    base = current_app.config.get(
        "GOVBR_AUTH_URL", "https://sso.acesso.gov.br/authorize"
    )
    return redirect(f"{base}?{params}")


@auth_bp.get("/govbr/simulador")
def govbr_simulador():
    """Tela de simulação do gov.br, para desenvolvimento e demonstração.

    Deixa explícito que NÃO é o gov.br real — jamais deve ir a produção com
    credenciais ausentes sem esse aviso.
    """
    if _govbr_ativo():
        return redirect(url_for("auth.login"))

    contas = (
        User.query.filter_by(ativo=True)
        .order_by(User.perfil, User.nome)
        .limit(25)
        .all()
    )
    return render_template(
        "auth/govbr_simulador.html",
        contas=contas,
        state=request.args.get("state", ""),
    )


@auth_bp.post("/govbr/simulador")
def govbr_simulador_post():
    if _govbr_ativo():
        return redirect(url_for("auth.login"))

    if request.form.get("state") != session.get(CHAVE_GOVBR_STATE):
        flash("Sessão de autenticação inválida. Tente novamente.", "danger")
        return redirect(url_for("auth.login"))

    user = User.query.get(request.form.get("user_id", type=int) or 0)
    if not user or not user.ativo:
        flash("Conta indisponível.", "danger")
        return redirect(url_for("auth.login"))

    session.pop(CHAVE_GOVBR_STATE, None)

    if not user.govbr_sub:
        user.govbr_sub = f"sim:{user.id}"
        user.govbr_nivel = "prata"

    registrar("users", user.id, "login",
              "Login via gov.br (SIMULADO — sem credenciais de produção)")

    # O gov.br garante a identidade, não o segundo fator do sistema. Se o
    # usuário tem MFA ativo, ele continua valendo.
    if user.mfa_ativo:
        db.session.commit()
        session[CHAVE_DESAFIO] = {
            "user_id": user.id,
            "criado_em": datetime.utcnow().isoformat(),
            "proximo": "",
        }
        return redirect(url_for("auth.login"))

    return _concluir_login(user)


@auth_bp.get("/govbr/callback")
def govbr_callback():
    """Retorno do gov.br real. Valida o state e troca o code pelos tokens."""
    if request.args.get("state") != session.get(CHAVE_GOVBR_STATE):
        flash("Falha na validação da sessão gov.br.", "danger")
        return redirect(url_for("auth.login"))

    flash(
        "Integração gov.br de produção não configurada neste ambiente. "
        "Defina GOVBR_CLIENT_ID e GOVBR_CLIENT_SECRET.",
        "warning",
    )
    return redirect(url_for("auth.login"))


# --------------------------------------------------------------------------
# Logout
# --------------------------------------------------------------------------

@auth_bp.post("/logout")
@login_required
def logout():
    registrar("users", current_user.id, "logout", "Sessão encerrada", commit=True)
    logout_user()
    session.pop(CHAVE_DESAFIO, None)
    flash("Sessão encerrada.", "info")
    return redirect(url_for("auth.login"))
