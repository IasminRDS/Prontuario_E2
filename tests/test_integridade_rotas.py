# -*- coding: utf-8 -*-
"""Varredura de todas as rotas e templates.

É o teste que segura o tipo de regresso mais comum aqui: template que lê um
atributo inexistente, formulário sem token, link para endpoint que não existe.
Nenhum deles aparece em teste unitário — só renderizando a tela com dado dentro.
"""
import logging
import re
from collections import Counter

import pytest

PARAMETRO = re.compile(r"<(?:[^:<>]+:)?([^<>]+)>")

# Nome do parâmetro na URL -> tabela de onde tirar um id que existe.
TABELA_POR_PARAMETRO = {
    "paciente": "pacientes", "prontuario": "prontuarios", "medico": "medicos",
    "internacao": "internacoes", "triagem": "triagens",
    "exame": "exames_solicitados", "leito": "leitos", "setor": "setores",
    "unidade": "unidades_saude", "usuario": "users", "user": "users",
    "agendamento": "agendamentos", "cirurgia": "cirurgias",
    "encaminhamento": "encaminhamentos", "medicamento": "medicamentos",
    "prescricao": "prescricoes", "item": "itens_estoque", "vacina": "vacinas",
    "notificacao": "notificacoes_compulsorias", "evento": "agenda_eventos",
    "atendimento": "atendimentos", "log": "audit_logs", "envio": "envios_rnds",
    "documento": "documentos_assinados", "consentimento": "consentimentos_lgpd",
    "movimentacao": "mov_estoque", "evolucao": "evolucoes_internacao",
    "sala": "salas_cirurgicas", "regional": "regionais",
    "configuracao": "configuracoes", "tipo": "tipos_exame",
    "catalogo": "catalogo_exames",
}

# Para o parâmetro genérico `id`, a tabela vem do blueprint.
TABELA_POR_BLUEPRINT = {
    "pacientes": "pacientes", "prontuario": "prontuarios", "triagem": "triagens",
    "atendimento": "atendimentos", "internacao": "internacoes", "leitos": "leitos",
    "cirurgia": "cirurgias", "agenda": "agenda_eventos",
    "agendamento": "agendamentos", "encaminhamentos": "encaminhamentos",
    "exames": "exames_solicitados", "catalogo_exames": "catalogo_exames",
    "catalogo_vacinas": "catalogo_vacinas", "vacinas": "vacinas",
    "medicamentos": "medicamentos", "estoque": "itens_estoque",
    "farmacia": "itens_estoque", "faturamento": "faturamento_aih",
    "vigilancia": "notificacoes_compulsorias", "regulacao": "encaminhamentos",
    "rnds": "envios_rnds", "unidades": "unidades_saude", "admin": "users",
    "auditoria": "audit_logs", "configuracoes": "configuracoes",
    "documentos": "documentos_assinados", "ps": "atendimentos_ps",
    "pronto_socorro": "atendimentos_ps",
    "prescricao_hosp": "prescricoes_hospitalares",
    "portal_cidadao": "pacientes",
    "epidemiologia": "notificacoes_compulsorias",
}


def _url_concreta(regra, ids):
    def substituir(achado):
        parametro = achado.group(1)
        base = parametro[:-3] if parametro.endswith("_id") else parametro
        tabela = TABELA_POR_PARAMETRO.get(base)
        if not tabela and base in ("id", "pk"):
            tabela = TABELA_POR_BLUEPRINT.get(regra.endpoint.split(".")[0])
        return str(ids.get(tabela) or 1)

    return PARAMETRO.sub(substituir, str(regra))


def _rotas_get(app):
    return [r for r in sorted(app.url_map.iter_rules(), key=str)
            if "GET" in r.methods and r.endpoint != "static"]


@pytest.fixture(scope="module")
def varredura(app, ids_reais):
    """Percorre todo GET autenticado uma vez e guarda o resultado."""
    from tests.conftest import PERFIS, autenticar

    class Coletor(logging.Handler):
        def __init__(self):
            super().__init__()
            self.mensagens = []

        def emit(self, registro):
            try:
                self.mensagens.append(registro.getMessage())
            except Exception:
                pass

    coletor = Coletor()
    coletor.setLevel(logging.WARNING)
    app.logger.addHandler(coletor)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    cliente = autenticar(app, PERFIS["admin"][1])
    assert cliente.get("/pacientes/").status_code == 200, (
        "a varredura precisa estar autenticada; deslogada ela só mede a tela de login"
    )

    falhas, paginas = [], {}
    for regra in _rotas_get(app):
        url = _url_concreta(regra, ids_reais)
        try:
            resposta = cliente.get(url)
        except Exception as exc:
            falhas.append((url, f"{type(exc).__name__}: {exc}"))
            continue
        if resposta.status_code >= 500:
            falhas.append((url, f"status {resposta.status_code}"))
        elif resposta.status_code == 200 and resposta.content_type.startswith("text/html"):
            paginas[url] = resposta.get_data(as_text=True)

    app.logger.removeHandler(coletor)
    return {"falhas": falhas, "paginas": paginas, "avisos": coletor.mensagens}


def test_nenhuma_rota_get_quebra(varredura):
    assert not varredura["falhas"], "rotas com erro:\n" + "\n".join(
        f"  {url} — {motivo}" for url, motivo in varredura["falhas"])


def test_varredura_renderizou_telas_de_verdade(varredura, app):
    """Guarda contra o teste acima virar tautologia.

    Se a autenticação ou os dados quebrarem, quase nada renderiza e a varredura
    passa sem ter exercitado coisa alguma.
    """
    total = len(_rotas_get(app))
    assert len(varredura["paginas"]) > total * 0.6, (
        f"só {len(varredura['paginas'])} de {total} rotas renderizaram HTML"
    )


def test_nenhum_link_para_endpoint_inexistente(varredura):
    mortos = Counter()
    for mensagem in varredura["avisos"]:
        achado = re.search(r"url_for\('([^']+)'\) falhou", mensagem)
        if achado:
            mortos[achado.group(1)] += 1
    assert not mortos, f"url_for para endpoint inexistente: {dict(mortos)}"


FORMULARIO = re.compile(r"<form\b([^>]*)>(.*?)</form>", re.I | re.S)
METODO_POST = re.compile(r"method\s*=\s*[\"']?post", re.I)


def test_todo_formulario_post_renderizado_tem_csrf(varredura):
    """Formulário POST sem token devolve 400 — é botão morto, não proteção."""
    sem_token = []
    for url, html in varredura["paginas"].items():
        for achado in FORMULARIO.finditer(html):
            atributos, corpo = achado.group(1), achado.group(2)
            if METODO_POST.search(atributos) and "csrf_token" not in corpo:
                acao = re.search(r"action\s*=\s*[\"']([^\"']*)[\"']", atributos)
                sem_token.append(f"{acao.group(1) if acao else url} (tela {url})")
    assert not sem_token, "formulários sem csrf_token:\n" + "\n".join(
        f"  {x}" for x in sem_token)


def test_todo_template_compila(app):
    """Pega erro de sintaxe em tela que a varredura não alcança."""
    import pathlib

    raiz = pathlib.Path(app.root_path) / "templates"
    erros = []
    for arquivo in sorted(raiz.rglob("*.html")):
        relativo = arquivo.relative_to(raiz).as_posix()
        try:
            app.jinja_env.get_template(relativo)
        except Exception as exc:
            erros.append(f"  {relativo}: {type(exc).__name__}: {exc}")
    assert not erros, "templates com erro de sintaxe:\n" + "\n".join(erros)


def test_nenhum_formulario_aninhado():
    """<form> dentro de <form> é HTML inválido: o navegador descarta o interno."""
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parent.parent / "templates"
    aninhados = []
    for arquivo in sorted(raiz.rglob("*.html")):
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        # Ignora comentários Jinja, que podem citar a tag no texto.
        texto = re.sub(r"\{#.*?#\}", "", texto, flags=re.S)
        profundidade = 0
        for achado in re.finditer(r"<form\b|</form>", texto, re.I):
            if achado.group(0).lower().startswith("<form"):
                profundidade += 1
                if profundidade > 1:
                    linha = texto[:achado.start()].count("\n") + 1
                    aninhados.append(f"  {arquivo.name}:{linha}")
            else:
                profundidade = max(0, profundidade - 1)
    assert not aninhados, "formulários aninhados:\n" + "\n".join(aninhados)


# Template que nenhuma rota renderiza é peso morto que engana: alguém abre o
# arquivo, conclui que a tela existe, e ela nunca foi ligada. Doze deles
# acumularam-se assim — entre eles um `pacientes/index.html` de 169 linhas que
# convivia com o `pacientes/listar.html` que a rota de fato usa, e um par de
# `relatorio_form.html` copiado para duas pastas erradas.
#
# A lista abaixo existe para o caso legítimo: template criado junto com a rota
# que ainda vai ligá-lo. Entrar nela exige justificar por quê.
TEMPLATES_SEM_ROTA_ACEITOS = set()


def test_nenhum_template_orfao():
    """Todo template é renderizado por alguém, ou herdado por outro template."""
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parent.parent
    templates = raiz / "templates"

    codigo = ""
    for pasta in ("routes", "utils", "services"):
        for arquivo in (raiz / pasta).rglob("*.py"):
            codigo += arquivo.read_text(encoding="utf-8", errors="replace")
    codigo += (raiz / "app.py").read_text(encoding="utf-8", errors="replace")

    # `extends`, `include`, `import` e `from` referenciam template sem rota.
    referenciados = set()
    for arquivo in templates.rglob("*.html"):
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        referenciados.update(
            m.group(1) for m in
            re.finditer(r"{%-?\s*(?:extends|include|import|from)\s+['\"]([^'\"]+)",
                        texto))

    # O casamento é por caminho ENTRE ASPAS, e não por substring solta. Com
    # substring, `templates/404.html` parecia referenciado porque o código cita
    # `errors/404.html`, que o contém — dois órfãos ficaram escondidos assim,
    # e o detector passava. Um verificador com casamento frouxo não acusa
    # menos: acusa errado, e a diferença só aparece quando alguém confere.
    citados = set(re.findall(r"['\"]([\w/.-]+\.html)['\"]", codigo))

    orfaos = []
    for arquivo in sorted(templates.rglob("*.html")):
        rel = arquivo.relative_to(templates).as_posix()
        if rel in referenciados or rel in TEMPLATES_SEM_ROTA_ACEITOS:
            continue
        if rel not in citados:
            orfaos.append(f"  templates/{rel}")

    assert not orfaos, (
        "template que nenhuma rota renderiza e nenhum outro herda — ou ligue, "
        "ou apague:\n" + "\n".join(orfaos))


# Rotas que NÃO devem ser alcançáveis pela navegação, com o motivo de cada uma.
# É o espelho de `TEMPLATES_SEM_ROTA_ACEITOS`: lá, tela sem rota; aqui, rota sem
# tela. As duas listas juntas são o que impede o sistema de acumular pontas
# soltas — nenhuma delas quebra nada, e é justamente por isso que sobrevivem.
ROTAS_SEM_PORTA_ACEITAS = {
    # --- Interface programável (JSON), consumida por cliente e não por link ---
    "pacientes.listar_pacientes_api",
    "prontuario.criar_prontuario",
    "prontuario.atualizar_prontuario",
    "prontuario.excluir_prontuario",
    "prontuario.assinar_prontuario",
    "atendimento.criar_atendimento",
    "auth.govbr_status",
    # --- Chamadas assíncronas do próprio front, montadas em JavaScript -------
    # `test_contrato_front_api.py` é quem garante que estas existem e respondem
    # o que o JS lê; aqui elas entram porque não têm (nem devem ter) link.
    "agenda.api_listar_eventos",
    "agenda.api_criar_evento",
    "agenda.api_status_evento",
    "agendamento.api_horarios",
    "estoque.api_buscar",
    "internacao.api_listar_leitos",
    "internacao.api_criar_leito",
    "internacao.api_status_leito",
    "medicamentos.buscar",
    "pacientes.buscar",
    "pacientes.buscar_codigo",
    # Entrou aqui quando o autocomplete de terminologia saiu de dentro de
    # `prontuario/form.html` e virou `static/js/terminologia.js`, ligado por
    # `data-terminologia` nos quinze campos de CID e de procedimento. A tela de
    # consulta (`terminologia.index`) continua ligada por link; é só a rota
    # JSON que passou a ser chamada por JavaScript.
    "terminologia.api",
    "pacientes.atualizar_paciente",
    "pacientes.desativar_paciente",
    # --- Compatibilidade: URL antiga que redireciona para a tela nova --------
    "leitos.index",
    "pacientes.index_alias",
}

_ENDPOINT = re.compile(r"""url_for\(\s*['"]([a-zA-Z_0-9.]+)['"]""")
# O menu lateral registra o endpoint como string simples, sem `url_for`.
_ENDPOINT_NAV = re.compile(r"""_i\(\s*['"]([a-zA-Z_0-9.]+)['"]""")


def test_nenhuma_rota_sem_porta_de_entrada(app):
    """Toda rota é alcançável por link, formulário, menu ou `fetch`.

    Rota que existe e ninguém alcança passa em todos os outros testes: responde
    200, não quebra nada, e nenhum usuário consegue usá-la. Foi assim que o
    cadastro de usuário, a criação de setor e o cancelamento de cirurgia
    ficaram inacessíveis pela interface.

    A comparação é por FUNÇÃO e não por endpoint: `add_url_rule` com
    `endpoint=` cria apelidos para a mesma tela, e basta um deles estar citado
    para a tela estar ligada.
    """
    import pathlib

    raiz = pathlib.Path(__file__).resolve().parent.parent

    citados = set()
    alvos = list((raiz / "templates").rglob("*.html"))
    alvos += list((raiz / "static").rglob("*.js"))
    for pasta in ("routes", "utils", "services"):
        alvos += list((raiz / pasta).rglob("*.py"))
    alvos.append(raiz / "app.py")
    for arquivo in alvos:
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        citados.update(_ENDPOINT.findall(texto))
        citados.update(_ENDPOINT_NAV.findall(texto))

    # Apelidos: agrupa os endpoints que compartilham a mesma função de view.
    por_funcao = {}
    for endpoint, funcao in app.view_functions.items():
        por_funcao.setdefault(funcao, set()).add(endpoint)
    apelidos = {}
    for endpoints in por_funcao.values():
        for endpoint in endpoints:
            apelidos[endpoint] = endpoints

    sem_porta = []
    for regra in sorted(app.url_map.iter_rules(), key=str):
        endpoint = regra.endpoint
        if endpoint == "static" or endpoint in ROTAS_SEM_PORTA_ACEITAS:
            continue
        if apelidos.get(endpoint, {endpoint}) & citados:
            continue
        metodos = ",".join(sorted(regra.methods - {"HEAD", "OPTIONS"}))
        sem_porta.append(f"  {endpoint} [{metodos}] {regra}")

    assert not sem_porta, (
        "rota que nenhuma tela alcança — ou ligue, ou apague, ou declare em "
        "ROTAS_SEM_PORTA_ACEITAS com o motivo:\n" + "\n".join(sem_porta))
