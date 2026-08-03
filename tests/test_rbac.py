# -*- coding: utf-8 -*-
"""RBAC: o backend é a autoridade, não o template.

O CSRF fica desligado nestes testes de propósito — com ele ligado, um 400 de
token responderia antes do controle de permissão e mascararia exatamente o que
se quer medir.
"""
import pytest

# (rota, método, dados, perfis que NÃO deveriam conseguir)
CASOS_ESCRITA = [
    ("/prontuarios/novo/1", "post", {"subjetivo": "x"}, ["recepcao"]),
    ("/prontuarios/", "post", {"paciente_id": 1}, ["recepcao"]),
    ("/pacientes/", "post",
     {"nome": "Invasor", "data_nascimento": "2000-01-01", "sexo": "M"}, ["gestor"]),
    ("/admin/usuarios/1/desativar", "post", {}, ["recepcao", "medico", "gestor"]),
    ("/admin/usuarios/1/ativar", "post", {}, ["recepcao", "medico", "gestor"]),
    ("/configuracoes/", "post", {"nome_unidade": "X"},
     ["recepcao", "medico", "gestor"]),
    ("/triagem/nova", "post", {"paciente_id": 1, "classificacao": "verde"},
     ["recepcao"]),
    ("/pronto-socorro/novo", "post", {"nome": "X", "motivo": "y"},
     ["recepcao", "gestor"]),
    ("/internacao/api/leitos", "post", {"numero": "X-1", "setor_id": 1},
     ["recepcao", "gestor"]),
    ("/cirurgia/1/cancelar", "post", {}, ["recepcao"]),
    ("/exportacao/pacientes.csv", "post", {"escopo": "anonimizado"},
     ["medico", "gestor"]),
    ("/vigilancia/1/enviar", "post", {}, ["recepcao"]),
    ("/regulacao/1/parecer", "post", {"decisao": "autorizado"},
     ["recepcao", "medico"]),
    ("/prontuarios/1", "delete", {}, ["recepcao", "medico", "gestor"]),
]

# Achata para um caso de teste por (rota, perfil) — assim a falha aponta o par
# exato em vez de derrubar a matriz inteira.
PARES = [
    pytest.param(rota, metodo, dados, perfil,
                 id=f"{metodo}:{rota}:{perfil}")
    for rota, metodo, dados, proibidos in CASOS_ESCRITA
    for perfil in proibidos
]


@pytest.mark.parametrize("rota,metodo,dados,perfil", PARES)
def test_perfil_proibido_e_barrado(clientes, sem_csrf, rota, metodo, dados, perfil):
    resposta = getattr(clientes[perfil], metodo)(rota, data=dados)
    # 404 também é aceitável: o recurso pode não existir neste banco.
    assert resposta.status_code in (401, 403, 404), (
        f"{metodo.upper()} {rota} acessível por '{perfil}' "
        f"(status {resposta.status_code})"
    )


LEITURAS_SO_ADMIN = ["/admin/", "/configuracoes/", "/backup/", "/unidades/"]


@pytest.mark.parametrize("rota", LEITURAS_SO_ADMIN)
def test_medico_nao_acessa_area_de_admin(clientes, rota):
    assert clientes["medico"].get(rota).status_code != 200


@pytest.mark.parametrize("rota", ["/prontuarios/", "/auditoria/"])
def test_recepcao_nao_acessa_area_clinica(clientes, rota):
    assert clientes["recepcao"].get(rota).status_code != 200


def test_recepcao_acessa_exportacao_por_desenho(clientes):
    """`/exportacao/` declara `@requer_perfil("Administrador", "Recepcao")`.

    Fica registrado como decisão explícita, não como esquecimento: se alguém
    concluir que a recepção não deve exportar dado de paciente, é este teste que
    precisa mudar junto com o decorador.
    """
    assert clientes["recepcao"].get("/exportacao/").status_code == 200


def test_admin_acessa_o_que_lhe_cabe(clientes):
    for rota in LEITURAS_SO_ADMIN:
        assert clientes["admin"].get(rota).status_code == 200, rota
