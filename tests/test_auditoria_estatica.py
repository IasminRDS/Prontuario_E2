# -*- coding: utf-8 -*-
"""Invariantes de arquitetura — lidas do código, não de uma requisição.

São as regras que o AGENTS.md declara e que só um teste estrutural sustenta:
rota nova nasce protegida, SQL não se monta com f-string, cabeçalho de segurança
não some numa refatoração.
"""
import re

import pytest

RAIZ_PROJETO = None  # preenchido pelo fixture `raiz`

# Endpoints públicos por desenho: login, o fluxo gov.br e a verificação de
# documento por código (que não pode exigir sessão para funcionar).
PUBLICOS = {
    "static", "auth.login", "auth.login_post", "auth.mfa_verify",
    "auth.mfa_cancelar", "auth.govbr_login", "auth.govbr_callback",
    "auth.govbr_status", "auth.govbr_simulador", "auth.govbr_simulador_post",
    "documentos.verificar",
}

METODOS_ESCRITA = {"POST", "PUT", "PATCH", "DELETE"}

DECORADORES_RBAC = ("requer_permissao", "requer_perfil", "admin_requerido",
                    "medico_requerido")

# Escritas sobre a própria conta: a autorização é "ser o dono da sessão", que
# `@login_required` já garante. Exigir permissão aqui impediria o usuário de
# trocar a própria senha ou configurar o próprio MFA. Manter a lista curta e
# explícita é o que separa exceção pensada de rota esquecida.
AUTOSSERVICO = {
    "auth.logout",
    "conta.trocar_senha",
    "conta.mfa_setup",
    "conta.mfa_enable",
    "conta.mfa_disable",
}


@pytest.fixture(scope="module")
def raiz():
    import pathlib

    return pathlib.Path(__file__).resolve().parent.parent


def _decoradores(app, endpoint, raiz):
    """Bloco de decorators imediatamente acima do `def` da view."""
    view = app.view_functions.get(endpoint)
    if not view:
        return ""
    caminho = raiz / (view.__module__.replace(".", "/") + ".py")
    if not caminho.exists():
        return ""
    texto = caminho.read_text(encoding="utf-8")
    # Aceita comentário entre decorators — é Python válido, e uma linha de
    # comentário no meio do bloco não pode fazer o teste concluir que a rota
    # está desprotegida.
    achado = re.search(
        r"((?:^(?:@[^\n]*|[ \t]*#[^\n]*)\n)+)def\s+"
        + re.escape(view.__name__) + r"\s*\(",
        texto, re.M)
    return achado.group(1) if achado else ""


def test_toda_rota_exige_autenticacao(app, raiz):
    sem_login = [
        f"{r.endpoint} ({r})"
        for r in app.url_map.iter_rules()
        if r.endpoint not in PUBLICOS
        and "@login_required" not in _decoradores(app, r.endpoint, raiz)
    ]
    assert not sem_login, "rotas sem @login_required:\n" + "\n".join(
        f"  {x}" for x in sem_login)


def test_toda_rota_de_escrita_exige_permissao(app, raiz):
    """`@login_required` diz que há sessão; não diz que ela pode escrever."""
    sem_rbac = []
    for regra in app.url_map.iter_rules():
        if regra.endpoint in PUBLICOS or regra.endpoint in AUTOSSERVICO:
            continue
        if not (regra.methods - {"HEAD", "OPTIONS"}) & METODOS_ESCRITA:
            continue
        decoradores = _decoradores(app, regra.endpoint, raiz)
        if not any(d in decoradores for d in DECORADORES_RBAC):
            sem_rbac.append(f"{regra.endpoint} ({regra})")

    assert not sem_rbac, "rotas de escrita sem RBAC:\n" + "\n".join(
        f"  {x}" for x in sem_rbac)


def test_nenhum_sql_montado_com_f_string(raiz):
    """Interpolação em SQL é injeção esperando entrada de usuário."""
    suspeitos = []
    for pasta in ("routes", "utils", "models", "services", "database"):
        for arquivo in (raiz / pasta).glob("*.py"):
            texto = arquivo.read_text(encoding="utf-8")
            for achado in re.finditer(r'(?:text|execute)\(\s*f["\']', texto):
                linha = texto[:achado.start()].count("\n") + 1
                suspeitos.append(f"{pasta}/{arquivo.name}:{linha}")
    assert not suspeitos, "SQL com f-string:\n" + "\n".join(f"  {x}" for x in suspeitos)


@pytest.mark.parametrize("cabecalho", [
    "X-Content-Type-Options",
    "X-Frame-Options",
    "Content-Security-Policy",
    "Referrer-Policy",
])
def test_cabecalhos_de_seguranca_presentes(anonimo, cabecalho):
    assert cabecalho in anonimo.get("/auth/login").headers


def test_configuracao_de_sessao_segura(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] in ("Lax", "Strict")
    assert app.config["PERMANENT_SESSION_LIFETIME"].days <= 7


def test_producao_liga_cookie_secure():
    """Em dev o cookie roda sem Secure (HTTP); em produção não pode."""
    from config import ProductionConfig

    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert ProductionConfig.DEBUG is False


def test_pool_cabe_no_limite_do_servidor(app):
    """(pool_size + max_overflow) x workers precisa caber no max_connections.

    O Procfile sobe 2 workers e cada um abre o próprio pool; um Postgres padrão
    oferece ~97 conexões úteis.
    """
    opcoes = app.config["SQLALCHEMY_ENGINE_OPTIONS"]
    if "pool_size" not in opcoes:
        pytest.skip("SQLite não usa pool dimensionável")
    por_worker = opcoes["pool_size"] + opcoes["max_overflow"]
    assert por_worker * 2 <= 97, (
        f"{por_worker} conexões por worker x 2 workers estoura o max_connections"
    )


def test_uso_de_safe_em_template_e_consciente(raiz):
    """`|safe` desliga o escape do Jinja: cada uso precisa ser deliberado.

    Hoje só o arquivo de ícones usa, com SVG do próprio projeto. Se aparecer em
    outro lugar, é para revisar antes de aceitar.
    """
    usos = []
    for arquivo in (raiz / "templates").rglob("*.html"):
        for numero, linha in enumerate(
                arquivo.read_text(encoding="utf-8").splitlines(), 1):
            if "|safe" in linha or "| safe" in linha:
                usos.append(f"{arquivo.relative_to(raiz).as_posix()}:{numero}")
    inesperados = [u for u in usos if not u.startswith("templates/_icons.html")]
    assert not inesperados, "novo uso de |safe para revisar:\n" + "\n".join(
        f"  {x}" for x in inesperados)
