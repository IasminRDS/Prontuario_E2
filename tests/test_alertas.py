# -*- coding: utf-8 -*-
"""Central de alertas operacionais."""
from unittest.mock import patch

import pytest


def test_recepcao_nao_acessa(clientes):
    """A tela agrega estoque, fila de urgência e notificações compulsórias.

    A recepção tem `patient:read`, não `reports:read` — antes via tudo isso
    porque a rota exigia apenas autenticação.
    """
    assert clientes["recepcao"].get("/alertas/").status_code in (401, 403)


@pytest.mark.parametrize("perfil", ["admin", "medico", "gestor"])
def test_quem_tem_reports_read_acessa(clientes, perfil):
    assert clientes[perfil].get("/alertas/").status_code == 200


def test_tela_vazia_diz_que_esta_vazia(autenticado_confirmado):
    """"Nenhuma pendência" e "a tela quebrou" não podem ser a mesma página.

    Sem estado vazio, as duas situações renderizavam em branco e não havia como
    distingui-las — foi exatamente o que aconteceu quando o RLS escondeu tudo.
    """
    import routes.alertas as alertas

    with patch.object(alertas, "_pronto_socorro", return_value=[]), \
         patch.object(alertas, "_internacao", return_value=[]), \
         patch.object(alertas, "_estoque", return_value=[]), \
         patch.object(alertas, "_exames", return_value=[]), \
         patch.object(alertas, "_vigilancia", return_value=[]):
        resposta = autenticado_confirmado.get("/alertas/")

    assert resposta.status_code == 200
    assert "Nenhuma pendência operacional" in resposta.get_data(as_text=True)


def test_alerta_existente_e_renderizado(autenticado_confirmado):
    import routes.alertas as alertas

    falso = [alertas._alerta(alertas.CRITICO, "Título de teste",
                             "Descrição de teste", None, 3)]
    with patch.object(alertas, "_estoque", return_value=falso):
        html = autenticado_confirmado.get("/alertas/").get_data(as_text=True)

    assert "Título de teste" in html
    assert "Descrição de teste" in html
    assert "Nenhuma pendência operacional" not in html


def test_severidade_aparece_na_tela(autenticado_confirmado):
    """Crítico e informativo não podem ter a mesma cara.

    A rota classifica cada alerta; a tela ignorava a classificação, e um
    estoque zerado aparecia igual a um aviso.
    """
    import routes.alertas as alertas

    critico = [alertas._alerta(alertas.CRITICO, "Estoque zerado", "reponha já")]
    atencao = [alertas._alerta(alertas.ATENCAO, "Exame atrasado", "verifique")]
    with patch.object(alertas, "_estoque", return_value=critico), \
         patch.object(alertas, "_exames", return_value=atencao):
        html = autenticado_confirmado.get("/alertas/").get_data(as_text=True)

    assert "badge--red" in html, "alerta crítico sem destaque de severidade"
    assert "badge--amber" in html
    assert "Crítico" in html and "Atenção" in html


def test_alerta_com_destino_oferece_o_caminho(autenticado_confirmado):
    """Alerta sem link obriga o operador a procurar a tela certa no menu."""
    import routes.alertas as alertas

    falso = [alertas._alerta(alertas.CRITICO, "Com destino", "vá resolver",
                             "/estoque/", 1)]
    with patch.object(alertas, "_estoque", return_value=falso):
        html = autenticado_confirmado.get("/alertas/").get_data(as_text=True)

    assert 'href="/estoque/"' in html
    assert "Resolver" in html


def test_alerta_sem_destino_nao_mostra_botao_morto(autenticado_confirmado):
    import routes.alertas as alertas

    falso = [alertas._alerta(alertas.ATENCAO, "Sem destino", "sem link", None)]
    with patch.object(alertas, "_estoque", return_value=falso), \
         patch.object(alertas, "_pronto_socorro", return_value=[]), \
         patch.object(alertas, "_internacao", return_value=[]), \
         patch.object(alertas, "_exames", return_value=[]), \
         patch.object(alertas, "_vigilancia", return_value=[]):
        html = autenticado_confirmado.get("/alertas/").get_data(as_text=True)

    assert "Sem destino" in html
    assert "Resolver" not in html


def test_resumo_por_severidade_aparece(autenticado_confirmado):
    import routes.alertas as alertas

    dois = [alertas._alerta(alertas.CRITICO, "Um", "x"),
            alertas._alerta(alertas.CRITICO, "Dois", "y")]
    with patch.object(alertas, "_estoque", return_value=dois), \
         patch.object(alertas, "_pronto_socorro", return_value=[]), \
         patch.object(alertas, "_internacao", return_value=[]), \
         patch.object(alertas, "_exames", return_value=[]), \
         patch.object(alertas, "_vigilancia", return_value=[]):
        html = autenticado_confirmado.get("/alertas/").get_data(as_text=True)

    assert "stat__value" in html, "o resumo por severidade não foi renderizado"


def test_uma_fonte_com_erro_nao_derruba_as_outras(autenticado_confirmado):
    """O módulo promete isolamento entre fontes — este teste cobra a promessa.

    A falha é injetada na CONSULTA, dentro da fonte, e não substituindo a
    função inteira: substituir a função pularia o `try/except` que se quer
    testar, e o teste passaria sem provar nada.

    Em PostgreSQL isto também exercita o rollback: sem ele, a transação ficaria
    abortada e as fontes seguintes falhariam em cascata.
    """
    import models.estoque as estoque_mod
    import routes.alertas as alertas

    falso = [alertas._alerta(alertas.ATENCAO, "Sobrevivente", "segue de pé")]

    class EstoqueQuebrado:
        class query:  # noqa: N801 — imita a interface do Flask-SQLAlchemy
            @staticmethod
            def filter(*_a, **_kw):
                raise RuntimeError("consulta de estoque falhou")

        ativo = quantidade = estoque_minimo = validade = None

    with patch.object(estoque_mod, "ItemEstoque", EstoqueQuebrado), \
         patch.object(alertas, "_vigilancia", return_value=falso):
        resposta = autenticado_confirmado.get("/alertas/")

    assert resposta.status_code == 200, "uma fonte quebrada derrubou a tela"
    assert "Sobrevivente" in resposta.get_data(as_text=True), (
        "a falha de uma fonte apagou as outras"
    )
