# -*- coding: utf-8 -*-
"""O contrato entre o JavaScript do front e as rotas JSON.

Mesma classe de defeito que `test_templates_undefined.py` pega no Jinja, uma
camada acima. Lá, `{{ obj.campo_inexistente }}` rende string vazia sem erro;
aqui, `fetch()` para uma URL que não existe devolve 404, o `.json()` rejeita e a
rejeição morre num `catch` vazio ou numa promessa não tratada. Nos dois casos a
tela não acusa nada e simplesmente deixa de funcionar — foi assim que o
autocomplete de paciente ficou morto em seis formulários clínicos e na busca do
topo, chamando uma `/pacientes/buscar` que nunca foi escrita.

São duas verificações de natureza diferente:

- a **URL existe** é automática e vale para todo `fetch` do projeto: rota nova
  que o front invente já nasce coberta;
- o **corpo tem as chaves que o front lê** precisa da tabela `CONTRATOS`, porque
  não dá para inferir com segurança, por expressão regular, qual variável do
  JavaScript carrega a resposta.
"""
import pathlib
import re
from datetime import date

import pytest

from tests.conftest import PERFIS, autenticar

RAIZ = pathlib.Path(__file__).resolve().parent.parent

FETCH = re.compile(r"""fetch\(\s*[`'"]([^`'"]+)[`'"]""")
# `${...}` (template string) e `{{ ... }}` (Jinja) são valores de execução;
# viram um id qualquer só para o caminho poder ser casado com o url_map.
INTERPOLACAO = re.compile(r"\$\{[^}]*\}|\{\{[^}]*\}\}")

METODOS = ("GET", "POST", "PUT", "DELETE", "PATCH")

# Chaves que o front lê de cada resposta. Chave que sumir do payload é campo que
# vira `undefined` no template string e aparece escrito "undefined" na tela.
# `{termo}` é substituído pelo nome de um paciente que existe de fato — buscar
# por uma constante devolveria lista vazia e o teste passaria sem ver payload.
CONTRATOS = {
    "/pacientes/buscar?q={termo}": {
        "id", "nome", "cns", "idade", "data_nascimento",
    },
}


def _fetches_do_front():
    """(arquivo, linha, url) de todo fetch() em template ou script próprio."""
    for padrao in ("templates/**/*.html", "static/**/*.js"):
        for arquivo in sorted(RAIZ.glob(padrao)):
            if arquivo.name.endswith(".min.js"):
                continue
            texto = arquivo.read_text(encoding="utf-8", errors="replace")
            for numero, linha in enumerate(texto.splitlines(), 1):
                for url in FETCH.findall(linha):
                    yield arquivo.relative_to(RAIZ).as_posix(), numero, url


def test_todo_fetch_aponta_para_rota_existente(app):
    """URL que o front chama tem de casar com o url_map, em algum método."""
    adaptador = app.url_map.bind("localhost")
    quebradas = []

    for arquivo, linha, url in _fetches_do_front():
        if url.startswith("http"):
            continue  # serviço externo (ViaCEP); não é rota nossa
        caminho = INTERPOLACAO.sub("1", url).split("?")[0].split("#")[0]
        if not caminho.startswith("/"):
            continue

        casou = False
        for metodo in METODOS:
            try:
                adaptador.match(caminho, method=metodo)
                casou = True
                break
            except Exception:
                continue
        if not casou:
            quebradas.append(f"  {arquivo}:{linha} -> {url}")

    assert not quebradas, (
        "fetch para rota que não existe — o 404 vira rejeição silenciosa e a "
        "tela só deixa de funcionar:\n" + "\n".join(quebradas)
    )


@pytest.fixture(scope="module")
def cliente_api(app, dados_clinicos):
    """Admin: o alvo aqui é a FORMA do payload, não o escopo territorial.

    Com um perfil de unidade, o paciente semeado cairia fora do escopo (o
    município dele não é o da unidade de teste) e a lista viria vazia — o teste
    passaria sem nunca olhar uma linha.
    """
    return autenticar(app, PERFIS["admin"][1])


@pytest.fixture(scope="module")
def termo(app, dados_clinicos):
    """Nome de um paciente que existe, para a busca devolver alguma coisa."""
    from models.paciente import Paciente

    with app.app_context():
        paciente = (Paciente.query.filter_by(ativo=True)
                    .order_by(Paciente.id.asc()).first())
        assert paciente is not None, "nenhum paciente semeado"
        assert len(paciente.nome) >= 2, (
            f"nome semeado {paciente.nome!r} é curto demais para o piso de 2")
        return paciente.nome


@pytest.mark.parametrize("modelo,esperadas", sorted(CONTRATOS.items()))
def test_payload_tem_as_chaves_que_o_front_le(cliente_api, termo, modelo, esperadas):
    url = modelo.format(termo=termo)
    resposta = cliente_api.get(url)
    assert resposta.status_code == 200, f"{url} devolveu {resposta.status_code}"
    assert "application/json" in resposta.headers.get("Content-Type", ""), (
        f"{url} não devolveu JSON")

    corpo = resposta.get_json()
    assert isinstance(corpo, list), f"{url} devolveu {type(corpo).__name__}"
    assert corpo, (
        f"{url} não trouxe nenhuma linha com o dado semeado — sem linha, este "
        "teste não prova nada sobre as chaves"
    )

    for linha in corpo:
        faltando = esperadas - set(linha)
        assert not faltando, (
            f"{url}: o front lê {sorted(faltando)} e o payload não traz — "
            f"vira 'undefined' na tela. Payload: {sorted(linha)}"
        )


def test_autocomplete_de_paciente_calcula_a_idade(cliente_api, termo):
    """`idade` é derivada; se voltar nula com data de nascimento presente, a
    sugestão mostra 'null anos' e ninguém percebe pelo status 200."""
    corpo = cliente_api.get(f"/pacientes/buscar?q={termo}").get_json()
    com_data = [p for p in corpo if p.get("data_nascimento")]
    assert com_data, "nenhum paciente semeado tem data de nascimento"
    for p in com_data:
        assert isinstance(p["idade"], int), (
            f"paciente {p['id']} tem data de nascimento e idade={p['idade']!r}")


@pytest.fixture(scope="module")
def pacientes_de_nome(app, dados_clinicos):
    """Dois pacientes: um com nome social, outro sem, para cobrir os dois ramos.

    Criados e removidos aqui de propósito. Linha extra em `pacientes` que
    sobrevivesse ao módulo entraria na varredura do teste de deduplicação, que
    roda depois deste na ordem alfabética. Vão sem CPF e sem CNS para não
    disputar as colunas UNIQUE com ninguém.
    """
    from extensions import db
    from models.paciente import Paciente

    with app.app_context():
        com = Paciente(nome="Reginaldo Vieira Castro",
                       nome_social="Regina Vieira Castro",
                       data_nascimento=date(1990, 3, 14), sexo="F", ativo=True)
        sem = Paciente(nome="Anselmo Pires Tavares", nome_social=None,
                       data_nascimento=date(1985, 7, 2), sexo="M", ativo=True)
        db.session.add_all([com, sem])
        db.session.commit()
        ids = (com.id, sem.id)

    yield ids

    with app.app_context():
        for pid in ids:
            alvo = db.session.get(Paciente, pid)
            if alvo is not None:
                db.session.delete(alvo)
        db.session.commit()


def test_autocomplete_responde_com_o_nome_social(cliente_api, pacientes_de_nome):
    """Nome social é o nome de tratamento (Decreto 8.727/2016).

    A busca casa com o nome de registro — quem procura por ele encontra —, mas a
    sugestão tem de exibir o nome pelo qual a pessoa é chamada, ou a equipe lê a
    tela em voz alta e usa o nome errado.
    """
    corpo = cliente_api.get("/pacientes/buscar?q=Reginaldo").get_json()
    assert corpo, "buscar pelo nome de registro não encontrou o paciente"
    assert corpo[0]["nome"] == "Regina Vieira Castro", (
        f"a sugestão veio com {corpo[0]['nome']!r}, não com o nome social")


def test_autocomplete_cai_no_nome_de_registro_sem_nome_social(
        cliente_api, pacientes_de_nome):
    """Sem nome social, o campo não pode vir nulo e apagar a sugestão."""
    corpo = cliente_api.get("/pacientes/buscar?q=Anselmo").get_json()
    assert corpo, "paciente sem nome social não foi encontrado"
    assert corpo[0]["nome"] == "Anselmo Pires Tavares"


def test_autocomplete_exige_dois_caracteres(cliente_api):
    """Sem piso, `q` vazio devolveria a base inteira numa rota de sugestão."""
    for curto in ("", "a"):
        corpo = cliente_api.get(f"/pacientes/buscar?q={curto}").get_json()
        assert corpo == [], f"q={curto!r} devolveu {len(corpo)} linhas"


def test_autocomplete_nao_atende_anonimo(anonimo):
    """A rota expõe nome e CNS: sessão é obrigatória."""
    resposta = anonimo.get("/pacientes/buscar?q=silva")
    assert resposta.status_code != 200, "autocomplete respondeu a anônimo"
