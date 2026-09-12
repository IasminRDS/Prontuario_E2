# -*- coding: utf-8 -*-
"""Quem alcança cada relatório, perfil a perfil.

Cinco das seis rotas de `relatorios` tinham apenas `@login_required`. A
consequência, medida e não suposta: **a recepção abria a lista nominal de
pacientes — nome, CPF, CNS, nome da mãe e endereço — e a exportava em CSV.**

Nenhum teste pegava. `test_auditoria_estatica.py` cobra RBAC de rota que
ESCREVE, e relatório só lê; `test_permissoes_por_perfil.py` pergunta se cada
perfil alcança o que a matriz lhe promete, e não o contrário — se alcança o que
ela NÃO lhe promete. A pergunta que faltava é esta.

O critério adotado é um princípio, e não uma lista de exceções: **cada
relatório exige a permissão do domínio que ele consolida.** Daí triagem pedir
`triage:read` — é a atividade do enfermeiro, que já a tem — enquanto a lista
nominal de pacientes pede `reports:read`, porque extração em massa não é o
cadastro individual que `patient:read` cobre.

A matriz abaixo é a especificação executável desse princípio. Ela reprova nos
dois sentidos: perfil que perde acesso devido falha, e perfil que ganha acesso
indevido também.
"""
import pytest

from tests.conftest import PERFIS, autenticar

# rota -> perfis que DEVEM alcançar. Quem não está na lista recebe 403.
# `admin` entra em tudo por `admin:full`, que é o coringa da matriz.
ESPERADO = {
    "/relatorios/": {"admin", "medico", "gestor", "enfermeiro"},
    "/relatorios/pacientes": {"admin", "medico", "gestor"},
    "/relatorios/atendimentos": {"admin", "medico", "gestor"},
    "/relatorios/producao": {"admin", "medico", "gestor"},
    "/relatorios/triagem": {"admin", "medico", "gestor", "enfermeiro"},
    "/relatorios/territorio": {"admin", "medico", "gestor"},
}

CASOS = [(rota, perfil) for rota in ESPERADO for perfil in sorted(PERFIS)]


@pytest.mark.parametrize("rota,perfil", CASOS)
def test_quem_alcanca_cada_relatorio(app, dados_clinicos, rota, perfil):
    cliente = autenticar(app, PERFIS[perfil][1])
    resposta = cliente.get(rota)
    deve_entrar = perfil in ESPERADO[rota]

    if deve_entrar:
        assert resposta.status_code == 200, (
            f"{perfil} deveria alcançar {rota}, recebeu {resposta.status_code}")
    else:
        assert resposta.status_code in (302, 403), (
            f"{perfil} NÃO deveria alcançar {rota}, recebeu "
            f"{resposta.status_code}")


def test_a_exportacao_csv_obedece_a_mesma_regra(app, dados_clinicos):
    """O parâmetro `?exportar=csv` é outro ramo da MESMA rota.

    Vale um caso próprio porque a varredura de rotas exercita a URL sem
    parâmetro, e foi assim que um erro na exportação de atendimentos passou
    despercebido antes. Aqui o que se mede é o inverso: que o ramo da
    exportação não escapa do decorador.
    """
    cliente = autenticar(app, PERFIS["recepcao"][1])
    resposta = cliente.get("/relatorios/pacientes?exportar=csv")
    assert resposta.status_code in (302, 403), (
        "recepção exportou a lista nominal de pacientes em CSV")


def test_anonimo_nao_alcanca_relatorio_nenhum(anonimo):
    """O piso. `requer_permissao` devolve 401 a quem não se identificou, e o
    Flask-Login redireciona antes disso — os dois são aceitáveis, entrar não."""
    for rota in ESPERADO:
        resposta = anonimo.get(rota)
        assert resposta.status_code in (302, 401), (
            f"anônimo alcançou {rota}: {resposta.status_code}")
