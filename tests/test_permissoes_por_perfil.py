# -*- coding: utf-8 -*-
"""O que cada perfil alcança, medido pela resposta e não pela matriz.

A varredura de `test_integridade_rotas` autentica como administrador, que
detém o coringa `admin:full` — ela prova que a tela renderiza, nunca que a
autorização discrimina. Este arquivo faz a pergunta que aquela não faz: com o
perfil X, esta tela responde 200 ou 403?

Existe porque um aperto de permissão passou pela suíte inteira sem que nada
exercitasse o caso restringido. Suíte verde sobre um usuário coringa mede a
renderização, não o controle.
"""
import pytest

# (rota, perfil, espera_acesso). `True` é "precisa continuar entrando",
# `False` é "precisa ser barrado" — e os dois lados importam: uma restrição que
# barra quem deveria passar é indisponibilidade clínica, não segurança.
CASOS = [
    # Leitura de triagem passou a exigir `triage:read`.
    ("/triagem/", "medico", True),
    ("/triagem/", "recepcao", False),
    ("/triagem/", "gestor", False),
    # Agendar passou a exigir `schedule:write`; a Recepção é quem agenda.
    ("/agendamento/novo", "recepcao", True),
    ("/agendamento/novo", "gestor", False),
    # Estoque saiu de `clinical:read` para `med-admin:write`. A inversão era
    # completa: o Gestor movimentava e o Farmacêutico, de quem é a função, não.
    ("/estoque/novo", "farmaceutico", True),
    ("/estoque/novo", "gestor", False),
    ("/estoque/novo", "medico", False),
    # Classificação de risco: o enfermeiro sempre pôde, o médico passou a poder
    # pelas DUAS portas — é a decisão registrada em 9.4.18.
    ("/triagem/nova", "enfermeiro", True),
    ("/triagem/nova", "medico", True),
    ("/triagem/nova", "recepcao", False),
    # Envio à RNDS saiu de `reports:read`: o Gestor acompanha a fila e não
    # publica mais documento clínico na rede nacional.
    ("/rnds/", "gestor", True),
    ("/rnds/", "medico", True),
]


@pytest.mark.parametrize("rota,perfil,espera_acesso", CASOS)
def test_perfil_alcanca_o_que_a_matriz_promete(clientes, perfil, rota,
                                               espera_acesso, dados_clinicos):
    resposta = clientes[perfil].get(rota, follow_redirects=False)

    if espera_acesso:
        assert resposta.status_code != 403, (
            f"{perfil} foi BARRADO em {rota} — a restrição pegou quem deveria "
            f"passar (status {resposta.status_code})")
    else:
        assert resposta.status_code == 403, (
            f"{perfil} ENTROU em {rota} com status {resposta.status_code}; "
            "a permissão não está discriminando")
