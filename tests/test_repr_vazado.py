# -*- coding: utf-8 -*-
"""Objeto Python impresso na tela no lugar do dado.

`{{ u.unidade }}` onde `unidade` é a RELAÇÃO, e não o nome, faz o Jinja chamar
`__repr__`: a tela de administração mostrava **"<UnidadeSaude UBS Central>"** na
coluna de unidade. Não dá erro, não fica em branco, responde 200 — mostra lixo
com cara de dado, que é o pior dos três.

Nenhum detector existente alcança isso. `test_templates_undefined.py` procura
atributo que NÃO existe, e aqui ele existe; a varredura de rotas confere o
código HTTP, e o código era 200; o contrato front/API olha JSON, e isto é HTML.

O que se procura é a assinatura de um `__repr__` vazado:

- `<NomeDaClasse ...>` com o nome de um model do projeto — a forma padrão que
  `def __repr__` produz neste repositório;
- `object at 0x...`, que é o repr de quem não definiu `__repr__` nenhum.

A lista de models sai do metadata, e não escrita à mão: model novo nasce
coberto.
"""
import re

import pytest

from tests.conftest import PERFIS, autenticar

# `object at 0x` é universal; a segunda expressão é montada com os nomes das
# classes do projeto, para não confundir com HTML legítimo como "<Unidade>".
REPR_ANONIMO = re.compile(r"object at 0x[0-9a-fA-F]+")


@pytest.fixture(scope="module")
def classes_do_projeto(app):
    """Nomes das classes mapeadas, para montar a expressão de busca."""
    from extensions import db

    with app.app_context():
        return sorted({m.class_.__name__ for m in db.Model.registry.mappers})


@pytest.fixture(scope="module")
def paginas(app, dados_clinicos, ids_reais):
    """Todo GET renderizado por um perfil que alcança o máximo de telas."""
    from tests.test_integridade_rotas import _rotas_get, _url_concreta

    cliente = autenticar(app, PERFIS["admin"][1])
    coletadas = []
    for regra in _rotas_get(app):
        resposta = cliente.get(_url_concreta(regra, ids_reais))
        if resposta.status_code == 200 and resposta.mimetype == "text/html":
            coletadas.append((regra.endpoint,
                              resposta.get_data(as_text=True)))
    assert coletadas, "nenhuma página renderizou"
    return coletadas


def test_nenhuma_tela_imprime_repr_de_model(paginas, classes_do_projeto):
    """A coluna mostra o nome, não o objeto."""
    padrao = re.compile(r"&lt;(%s)\b[^&]*&gt;|<(%s)\b[^<>]*>"
                        % ("|".join(classes_do_projeto),
                           "|".join(classes_do_projeto)))
    achados = []
    for endpoint, html in paginas:
        encontrado = padrao.search(html)
        if encontrado:
            achados.append("  %s: %s" % (endpoint, encontrado.group(0)[:70]))

    assert not achados, (
        "objeto Python impresso no lugar do dado — a tela responde 200 e "
        "mostra lixo:\n" + "\n".join(achados) +
        "\n\nUse o atributo (`.nome`), não a relação."
    )


def test_nenhuma_tela_imprime_objeto_sem_repr(paginas):
    """`object at 0x7f...` é o repr de quem nem definiu `__repr__`.

    Vale um caso próprio porque essa forma escapa da busca por nome de classe
    quando o objeto não é um model — um `Row`, um `Decimal` embrulhado, um
    objeto de terceiro.
    """
    achados = [
        "  %s: %s" % (endpoint, REPR_ANONIMO.search(html).group(0))
        for endpoint, html in paginas if REPR_ANONIMO.search(html)
    ]
    assert not achados, "objeto sem __repr__ impresso na tela:\n" + "\n".join(achados)
