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


# --- Autorização coerente por entidade -------------------------------------
#
# O defeito: duas rotas escrevem a MESMA entidade exigindo permissões
# diferentes, e o resultado é um perfil que não pode fazer algo por uma porta e
# pode pela outra. Aconteceu duas vezes neste projeto — a classificação de risco
# (gravada por `triagem.nova` sob `triage:write` e por `ps.entrada` sob
# `emergency:write`) e a movimentação de estoque (gravada sob `clinical:read`
# num módulo e `med-admin:write` no outro).
#
# A comparação NÃO é entre os nomes das permissões. Nomes diferentes são
# legítimos: `ps.entrada` é primariamente admissão de urgência e exigir
# `emergency:write` está certo. O que não pode divergir é o CONJUNTO DE PERFIS
# que consegue passar — porque é isso que o usuário sente.
#
# É por medir perfis, e não strings, que este teste depende da concessão de
# `triage:write` ao MEDICO: sem ela, o médico classifica pelo pronto-socorro e
# não pela triagem, e o teste reprova.

# Divergência aceita precisa de razão escrita. Vazio é o estado correto — cada
# entrada aqui é uma dívida, não uma configuração.
AUTORIZACAO_DIVERGENTE_ACEITA = {}


def _entidades_escritas_por_rota(raiz):
    """{Modelo: {frozenset(permissões): {endpoints}}}, por análise estática.

    Construção do objeto no corpo da view é o sinal de escrita. É aproximação
    — não pega escrita por `update()` em massa — mas cobre o caminho normal e
    não depende de executar a rota.
    """
    import ast
    import collections

    from extensions import db

    modelos = {m.class_.__name__ for m in db.Model.registry.mappers}
    mapa = collections.defaultdict(lambda: collections.defaultdict(set))

    for arq in sorted((raiz / "routes").glob("*.py")):
        arvore = ast.parse(arq.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.FunctionDef):
                continue
            permissoes, e_rota = set(), False
            for dec in no.decorator_list:
                alvo = dec.func if isinstance(dec, ast.Call) else dec
                nome = getattr(alvo, "attr", getattr(alvo, "id", ""))
                if nome in ("route", "get", "post", "put", "patch", "delete"):
                    e_rota = True
                if nome == "requer_permissao" and isinstance(dec, ast.Call):
                    for a in dec.args:
                        if isinstance(a, ast.Constant):
                            permissoes.add(a.value)
            if not e_rota:
                continue
            for sub in ast.walk(no):
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Name)
                        and sub.func.id in modelos):
                    mapa[sub.func.id][frozenset(permissoes)].add(
                        f"{arq.stem}.{no.name}")
    return mapa


def _perfis_que_passam(permissoes):
    """Perfis capazes de atravessar `requer_permissao(*permissoes)`.

    Reproduz a semântica de `pode`: QUALQUER uma das permissões basta, e
    `admin:full` é coringa.
    """
    from utils.rbac import ADMIN_FULL, PERFIL_PERMISSOES

    alvo = set(permissoes)
    return frozenset(
        perfil for perfil, concedidas in PERFIL_PERMISSOES.items()
        if ADMIN_FULL in concedidas or not alvo or (alvo & concedidas)
    )


def test_entidade_escrita_por_varias_rotas_tem_a_mesma_autorizacao(raiz, app):
    """Mesma entidade, portas diferentes, mesmo conjunto de perfis."""
    with app.app_context():
        mapa = _entidades_escritas_por_rota(raiz)

    divergentes = {}
    for modelo, por_permissao in mapa.items():
        if len(por_permissao) < 2:
            continue
        perfis = {}
        for permissoes, endpoints in por_permissao.items():
            perfis.setdefault(_perfis_que_passam(permissoes), set()).update(
                f"{e} ({', '.join(sorted(permissoes)) or 'sem permissão'})"
                for e in endpoints)
        if len(perfis) > 1:
            divergentes[modelo] = perfis

    inesperadas = {m: v for m, v in divergentes.items()
                   if m not in AUTORIZACAO_DIVERGENTE_ACEITA}
    assert not inesperadas, (
        "entidade gravada por rotas que admitem perfis diferentes — um perfil "
        "consegue pela porta A e não pela porta B:\n" + "\n".join(
            f"  {m}:\n" + "\n".join(
                f"    {sorted(p)} <- {sorted(rotas)}"
                for p, rotas in v.items())
            for m, v in inesperadas.items()))

    resolvidas = set(AUTORIZACAO_DIVERGENTE_ACEITA) - set(divergentes)
    assert not resolvidas, (
        f"já não divergem — remova de AUTORIZACAO_DIVERGENTE_ACEITA: "
        f"{sorted(resolvidas)}")


# Rota de escrita legitimamente guardada por permissão de leitura. Cada entrada
# precisa de razão, e a razão precisa ser de NATUREZA — não "ainda não arrumei".
ESCRITA_SOB_LEITURA_ACEITA = {
    # Estes três respondem POST porque recebem payload de formulário, não
    # porque mutam estado: leem dado clínico e devolvem um arquivo. A auditoria
    # que gravam é do tipo `read`. Exigir permissão de escrita aqui impediria o
    # Gestor de emitir relatório sobre dado que ele já pode ver.
    "pdf.atestado",
    "pdf.processar_pdf",
    "pdf.reorganizar",
    # Agenda e agendamento gravavam sob `patient:read` por não existir nome
    # para a função. `schedule:write` foi criado e concedido a Recepção, Médico
    # e Enfermeiro; a dívida saiu daqui em vez de envelhecer.
}


def test_permissao_de_leitura_nao_protege_rota_de_escrita(app, raiz):
    """`clinical:read` guardando um POST concede escrita a quem só deveria ler.

    Os casos reais: três rotas de estoque gravavam sob `clinical:read` — o
    Gestor, perfil de leitura e relatório, movimentava estoque, e o
    Farmacêutico, de quem é a função, não conseguia; o catálogo de vacinas
    destoava do de exames, que já usava `exam:write`; e o envio à RNDS estava
    sob `reports:read`, o que permitia ao Gestor publicar documento clínico na
    rede nacional.

    A lista de exceções reprova nos dois sentidos, como as demais deste projeto.
    """
    falhas = set()
    for regra in app.url_map.iter_rules():
        if regra.endpoint == "static" or not (regra.methods & METODOS_ESCRITA):
            continue
        decoradores = _decoradores(app, regra.endpoint, raiz)
        for argumentos in re.findall(r"requer_permissao\(([^)]*)\)", decoradores):
            nomes = re.findall(r'"([^"]+)"', argumentos)
            if nomes and all(n.endswith(":read") for n in nomes):
                falhas.add(regra.endpoint)

    inesperadas = falhas - ESCRITA_SOB_LEITURA_ACEITA
    assert not inesperadas, (
        "rota de escrita guardada só por permissão de leitura — quem só pode "
        "ler consegue gravar:\n  " + "\n  ".join(sorted(inesperadas)))

    resolvidas = ESCRITA_SOB_LEITURA_ACEITA - falhas
    assert not resolvidas, (
        f"já não gravam sob permissão de leitura — remova de "
        f"ESCRITA_SOB_LEITURA_ACEITA: {sorted(resolvidas)}")


# --- Vocabulário de permissões vivo ----------------------------------------

def test_toda_permissao_exigida_existe_na_matriz(raiz):
    """String de permissão é contrato sem tipo: um erro de digitação não falha.

    `pode()` compara contra o conjunto concedido; nome inexistente simplesmente
    não pertence a ninguém, e a rota passa a negar TODO perfil que não tenha o
    coringa administrativo. O sintoma é 403 para o usuário certo, sem erro em
    log nenhum.
    """
    import ast

    from utils.rbac import TODAS_PERMISSOES

    desconhecidas = set()
    for arq in sorted((raiz / "routes").glob("*.py")):
        for no in ast.walk(ast.parse(arq.read_text(encoding="utf-8"))):
            if not isinstance(no, ast.Call):
                continue
            nome = getattr(no.func, "id", getattr(no.func, "attr", ""))
            if nome not in ("requer_permissao", "pode"):
                continue
            for a in no.args:
                if isinstance(a, ast.Constant) and a.value not in TODAS_PERMISSOES:
                    desconhecidas.add(f"{arq.name}: {a.value!r}")

    for tpl in sorted((raiz / "templates").rglob("*.html")):
        for achado in re.finditer(r"pode\(\s*['\"]([^'\"]+)['\"]",
                                  tpl.read_text(encoding="utf-8")):
            if achado.group(1) not in TODAS_PERMISSOES:
                desconhecidas.add(f"{tpl.name}: {achado.group(1)!r}")

    assert not desconhecidas, (
        "permissão exigida que não existe na matriz — nega todo mundo em "
        "silêncio:\n  " + "\n  ".join(sorted(desconhecidas)))


def test_toda_permissao_da_matriz_guarda_alguma_coisa(raiz):
    """O sentido inverso: nome concedido a perfil que não protege rota alguma.

    Quatro das 26 permissões estavam nesta situação — `triage:read`,
    `prescription:read`, `prescription:write` e `encounter:write`. A matriz é
    documento de governança: quem a lia concluía que a Recepção não enxergava a
    fila de triagem, quando na verdade QUALQUER sessão autenticada enxergava,
    porque nenhuma rota exigia o nome. Vocabulário morto faz a matriz descrever
    um sistema que não é este.
    """
    import ast

    from utils.rbac import ADMIN_FULL, TODAS_PERMISSOES

    exigidas = set()
    for arq in sorted((raiz / "routes").glob("*.py")):
        for no in ast.walk(ast.parse(arq.read_text(encoding="utf-8"))):
            if isinstance(no, ast.Call) and getattr(
                    no.func, "id", getattr(no.func, "attr", "")) in (
                        "requer_permissao", "pode"):
                exigidas |= {a.value for a in no.args
                             if isinstance(a, ast.Constant)}
    for tpl in sorted((raiz / "templates").rglob("*.html")):
        exigidas |= set(re.findall(r"pode\(\s*['\"]([^'\"]+)['\"]",
                                   tpl.read_text(encoding="utf-8")))

    # `admin:full` é coringa: concede sem ser exigido, por desenho.
    mortas = TODAS_PERMISSOES - exigidas - {ADMIN_FULL}
    assert not mortas, (
        "permissão declarada na matriz que nenhuma rota ou tela exige — ou "
        "aplique onde deveria valer, ou remova do vocabulário:\n  "
        + "\n  ".join(sorted(mortas)))


# --- Mutação que escapa da leitura por construção de objeto -----------------

# Rotas que mutam em massa e por isso não são vistas pelo detector de entidade
# (que enxerga `Modelo(...)`). Cada uma precisa de razão, porque o custo de
# estar aqui é ficar fora daquela conferência de autorização.
MUTACAO_EM_MASSA_ACEITA = set()


def test_mutacao_em_massa_declarada(raiz):
    """`query.update()` e `query.delete()` não constroem objeto.

    O detector de coerência de autorização por entidade lê construção de
    objeto — está dito na docstring dele que é aproximação. Este teste fecha a
    aproximação pelo outro lado: se aparecer mutação em massa numa rota, ela
    precisa ser declarada, porque a autorização dela ninguém está conferindo.
    """
    import ast

    achados = set()
    for arq in sorted((raiz / "routes").glob("*.py")):
        arvore = ast.parse(arq.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.FunctionDef):
                continue
            for sub in ast.walk(no):
                if (isinstance(sub, ast.Call)
                        and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr in ("update", "delete")
                        and isinstance(sub.func.value, ast.Call)):
                    achados.add(f"{arq.stem}.{no.name}")

    inesperadas = achados - MUTACAO_EM_MASSA_ACEITA
    assert not inesperadas, (
        "mutação em massa numa rota — fica fora da conferência de autorização "
        "por entidade:\n  " + "\n  ".join(sorted(inesperadas)))

    resolvidas = MUTACAO_EM_MASSA_ACEITA - achados
    assert not resolvidas, (
        f"já não fazem mutação em massa — remova de "
        f"MUTACAO_EM_MASSA_ACEITA: {sorted(resolvidas)}")
