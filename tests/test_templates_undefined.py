# -*- coding: utf-8 -*-
"""Caça atributos e variáveis que os templates leem e ninguém fornece.

Esta é a classe de defeito mais traiçoeira do projeto: o Jinja renderiza
`{{ obj.campo_que_nao_existe }}` como string vazia, sem erro nenhum. A tela
parece funcionar e simplesmente não mostra o dado. Foi assim que o nome do
medicamento, o procedimento da cirurgia e o estoque mínimo sumiram das telas
sem que nada acusasse.

O teste troca o `Undefined` do Jinja por um que registra cada acesso, renderiza
todas as rotas GET com dado semeado e compara o resultado com a lista de
pendências conhecidas abaixo. Achado novo reprova; achado corrigido também
reprova, para a lista não apodrecer.
"""
import traceback
from collections import Counter

import pytest
from jinja2 import Undefined

from tests.conftest import PERFIS, autenticar

# Pendências conhecidas, cada uma com o motivo de ainda não ter sido corrigida.
# Formato: "arquivo do template" -> {nomes acessados}
#
# Reduzir esta lista é trabalho pendente; aumentá-la exige justificar por quê.
PENDENCIAS = {
    # A AIH da tela tem sete campos que o model não possui. Completar exige
    # decidir o schema de faturamento — não é renomeação.
    "templates/faturamento/aih_form.html": {
        "competencia", "cid_secundario", "procedimento_secundario",
        "dias_permanencia", "valor_sh", "valor_sp", "observacoes", "comp_atual",
    },
    "templates/faturamento/aih_lista.html": {"comp"},
    "templates/faturamento/apac_form.html": {"comp_atual"},
    # Telas de relatório e formulários cujas rotas não passam o contexto que o
    # template espera.
    "templates/internacao/form.html": {"leitos_livres"},
    "templates/encaminhamentos/painel.html": {"filtro_esp"},
    "templates/exames/catalogo.html": {"meds"},
    "templates/exames/pendentes.html": {"exames"},
    "templates/medicamentos/catalogo.html": {"tipos"},
    "templates/ps/historico.html": {"data_s", "ats"},
    "templates/ps/painel.html": {"ORDEM_CORES"},
    # `Atendimento` não tem `status` — tem `tipo`. Definir o que a coluna
    # deveria significar é decisão de produto.
    "templates/pacientes/perfil.html": {"status"},
    "templates/relatorios/atendimentos.html": {"status"},
}


def _origem_do_template():
    """Arquivo do template a partir da pilha.

    O Jinja compila cada template num código cujo `co_filename` é o caminho do
    .html. A LINHA não serve — é a do código gerado, não a do arquivo.
    """
    for quadro in reversed(traceback.extract_stack()):
        if quadro.filename.endswith(".html"):
            caminho = quadro.filename.replace("\\", "/")
            corte = caminho.find("/templates/")
            return caminho[corte + 1:] if corte != -1 else caminho
    return "?"


@pytest.fixture(scope="module")
def acessos_indefinidos(app, ids_reais):
    """Renderiza todas as rotas GET e devolve {template: {nomes}}."""
    registro = Counter()

    class UndefinedQueDelata(Undefined):
        def _anotar(self):
            registro[(_origem_do_template(), str(self._undefined_name))] += 1
            return ""

        def __str__(self):
            return self._anotar()

        def __html__(self):
            return self._anotar()

        def __iter__(self):
            self._anotar()
            return iter(())

        def __bool__(self):
            return False

        def __len__(self):
            return 0

    from tests.test_integridade_rotas import _rotas_get, _url_concreta

    anterior = app.jinja_env.undefined
    app.jinja_env.undefined = UndefinedQueDelata
    try:
        cliente = autenticar(app, PERFIS["admin"][1])
        assert cliente.get("/pacientes/").status_code == 200, "login falhou"
        for regra in _rotas_get(app):
            try:
                cliente.get(_url_concreta(regra, ids_reais))
            except Exception:
                pass
    finally:
        app.jinja_env.undefined = anterior

    encontrados = {}
    for (template, nome), _n in registro.items():
        encontrados.setdefault(template, set()).add(nome)
    return encontrados


def test_nenhum_acesso_indefinido_novo(acessos_indefinidos):
    novos = []
    for template, nomes in sorted(acessos_indefinidos.items()):
        inesperados = nomes - PENDENCIAS.get(template, set())
        for nome in sorted(inesperados):
            novos.append(f"  {template}: {nome}")
    assert not novos, (
        "template lendo algo que ninguém fornece — renderiza vazio, sem erro:\n"
        + "\n".join(novos)
    )


def test_pendencias_conhecidas_nao_apodrecem(acessos_indefinidos):
    """Item corrigido precisa sair da lista, senão ela vira decoração."""
    resolvidos = []
    for template, nomes in sorted(PENDENCIAS.items()):
        ainda = acessos_indefinidos.get(template, set())
        for nome in sorted(nomes - ainda):
            resolvidos.append(f"  {template}: {nome}")
    assert not resolvidos, (
        "já foi corrigido — remova de PENDENCIAS:\n" + "\n".join(resolvidos))
