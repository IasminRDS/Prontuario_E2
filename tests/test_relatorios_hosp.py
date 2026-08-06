# -*- coding: utf-8 -*-
"""O índice de relatórios hospitalares aponta para os relatórios que existem.

O template desta tela era uma cópia esquecida do índice de ESTOQUE: título
"Controle de Estoque", botão "+ Novo Item" e uma tabela de medicamento/OPME. A
rota renderizava sem contexto nenhum, então a tabela vinha vazia e o resultado
era uma tela de estoque em branco dentro da seção de relatórios — e é onde caía
quem clicasse "Voltar" em qualquer um dos três relatórios hospitalares.

O detector de `Undefined` acusava o sintoma (5 variáveis que ninguém fornecia) e
não acusaria mais nada depois da correção: um índice vazio, ou apontado de novo
para o template errado, lê zero variável e passa no detector. Por isso este
teste olha o CONTEÚDO — que os três relatórios da própria blueprint estejam
alcançáveis a partir do índice dela.
"""
import re

import pytest

RELATORIOS = ("rel_hosp.ocupacao", "rel_hosp.producao", "rel_hosp.relatorio_ps")


@pytest.fixture(scope="module")
def indice(app):
    from tests.conftest import PERFIS, autenticar

    cliente = autenticar(app, PERFIS["admin"][1])
    resposta = cliente.get("/relatorios/hospital/")
    assert resposta.status_code == 200, (
        f"o índice devolveu {resposta.status_code}")
    return resposta.get_data(as_text=True)


def test_indice_leva_a_cada_relatorio_hospitalar(app, indice):
    """Um hub que não linka os próprios relatórios é uma tela morta."""
    with app.test_request_context():
        from flask import url_for

        faltando = [nome for nome in RELATORIOS
                    if f'href="{url_for(nome)}"' not in indice]

    assert not faltando, (
        "o índice de relatórios hospitalares não linka: " + ", ".join(faltando))


def test_indice_nao_e_a_tela_de_estoque(indice):
    """Guarda contra a cópia voltar — o defeito original, não o sintoma."""
    assert "Controle de Estoque" not in indice
    assert "+ Novo Item" not in indice
    assert not re.search(r'href="/estoque/(novo|alertas)"', indice), (
        "o índice está oferecendo ações de estoque")


def test_indice_nao_promete_relatorio_indisponivel(indice):
    """`aria-disabled` é o estado para endpoint ausente; com os três no ar, a
    tela não pode exibir nenhum card apagado."""
    assert 'aria-disabled="true"' not in indice
