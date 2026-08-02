# -*- coding: utf-8 -*-
"""Defesas de plataforma: cabeçalhos de segurança e limite de tentativas.

Ficam separadas das regras de negócio porque valem para a aplicação inteira,
não para um domínio específico.
"""
import time
from collections import defaultdict, deque
from functools import wraps

from flask import abort, request

# ============================================================================
# Cabeçalhos de segurança
# ============================================================================

CABECALHOS = {
    # Impede o navegador de "adivinhar" o tipo do conteúdo. Sem isto, um upload
    # de texto pode ser interpretado como script.
    "X-Content-Type-Options": "nosniff",
    # Impede que o sistema seja embutido num iframe de outro site (clickjacking:
    # a vítima acha que clica num lugar e clica em outro, autenticada).
    "X-Frame-Options": "DENY",
    # Não vaza a URL do prontuário no Referer ao clicar num link externo. A URL
    # carrega o id do paciente — é dado clínico.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Desliga APIs que o sistema não usa.
    "Permissions-Policy": "geolocation=(), microphone=(), payment=(), usb=()",
}

# CSP: 'unsafe-inline' é necessário enquanto houver <script> e style= inline nos
# templates herdados. Restringir mais exige removê-los primeiro — está anotado
# como dívida, não como decisão final.
CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://vlibras.gov.br; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https://vlibras.gov.br; "
    "font-src 'self' data:; "
    "connect-src 'self' https://vlibras.gov.br; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def registrar_cabecalhos(app):
    @app.after_request
    def aplicar(resposta):
        for nome, valor in CABECALHOS.items():
            resposta.headers.setdefault(nome, valor)
        resposta.headers.setdefault("Content-Security-Policy", CSP)

        # HSTS só faz sentido sob HTTPS; em HTTP local ele quebraria o acesso.
        if request.is_secure:
            resposta.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return resposta


# ============================================================================
# Limite de tentativas (proteção contra força bruta)
# ============================================================================

# Janela deslizante em memória: chave -> deque de timestamps.
#
# Serve para um processo. Com vários workers do Gunicorn, cada um tem a sua
# contagem, então o limite efetivo é (limite x nº de workers). Para limite
# global e preciso é preciso um armazenamento compartilhado (Redis) — o que
# está aqui já eleva muito o custo do ataque sem adicionar dependência.
_tentativas = defaultdict(deque)


def _chave_cliente(sufixo=""):
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?")
    ip = ip.split(",")[0].strip()
    return f"{ip}:{request.endpoint}:{sufixo}"


def limitar(maximo=8, janela_segundos=300, sufixo_form=None):
    """Bloqueia com 429 após `maximo` chamadas na janela.

    `sufixo_form` inclui um campo do formulário na chave (ex.: "email"), para
    que o ataque a uma conta específica seja contado separadamente do tráfego
    normal do mesmo IP.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            sufixo = ""
            if sufixo_form:
                sufixo = (request.form.get(sufixo_form) or "").strip().lower()[:120]

            chave = _chave_cliente(sufixo)
            agora = time.monotonic()
            registros = _tentativas[chave]

            # Descarta o que saiu da janela.
            while registros and agora - registros[0] > janela_segundos:
                registros.popleft()

            if len(registros) >= maximo:
                espera = int(janela_segundos - (agora - registros[0]))
                abort(429, description=(
                    f"Muitas tentativas. Tente novamente em {max(espera, 1)} segundo(s)."
                ))

            registros.append(agora)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def limpar_tentativas(sufixo=""):
    """Zera o contador — chamar após autenticação bem-sucedida.

    Sem isto, quem erra a senha algumas vezes e acerta continuaria consumindo a
    janela e seria bloqueado no meio do expediente.
    """
    _tentativas.pop(_chave_cliente(sufixo), None)
