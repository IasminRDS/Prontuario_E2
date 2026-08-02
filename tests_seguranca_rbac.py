# -*- coding: utf-8 -*-
"""Isola o RBAC: CSRF desligado, para que o 403 (ou a falta dele) seja do RBAC."""
import logging
import pathlib
import sys

logging.disable(logging.WARNING)
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from app import app  # noqa: E402
from extensions import db  # noqa: E402

app.config["WTF_CSRF_ENABLED"] = False

def logar(email):
    c = app.test_client()
    c.post("/auth/login", data={"email": email, "senha": "senha12345"})
    return c

perfis = {
    "recepcao": logar("recepcao@sus.gov.br"),
    "medico": logar("medico2@sus.gov.br"),
    "gestor": logar("gestor2@sus.gov.br"),
}

# (rota, metodo, dados, quem NAO deveria conseguir)
casos = [
    ("/prontuarios/novo/1", "post", {"subjetivo": "x"}, ["recepcao"]),
    ("/prontuarios/", "post", {"paciente_id": 1}, ["recepcao"]),
    ("/pacientes/", "post", {"nome": "Invasor", "data_nascimento": "2000-01-01", "sexo": "M"}, ["gestor"]),
    ("/admin/usuarios/1/desativar", "post", {}, ["recepcao", "medico", "gestor"]),
    ("/admin/usuarios/1/ativar", "post", {}, ["recepcao", "medico", "gestor"]),
    ("/configuracoes/", "post", {"nome_unidade": "X"}, ["recepcao", "medico", "gestor"]),
    ("/triagem/nova", "post", {"paciente_id": 1, "classificacao": "verde"}, ["recepcao"]),
    ("/pronto-socorro/novo", "post", {"nome": "X", "motivo": "y"}, ["recepcao", "gestor"]),
    ("/internacao/api/leitos", "post", {"numero": "X-1", "setor_id": 1}, ["recepcao", "gestor"]),
    ("/agenda/api/eventos", "post", {"paciente_nome": "X", "data": "2026-08-01", "hora": "10:00"}, []),
    ("/cirurgia/1/cancelar", "post", {}, ["recepcao"]),
    ("/exportacao/pacientes.csv", "post", {"escopo": "anonimizado"}, ["medico", "gestor"]),
    ("/vigilancia/1/enviar", "post", {}, ["recepcao"]),
    ("/regulacao/1/parecer", "post", {"decisao": "autorizado"}, ["recepcao", "medico"]),
    ("/estoque/1/editar", "post", {"nome": "X"}, []),
    ("/prontuarios/1", "delete", {}, ["recepcao", "medico", "gestor"]),
]

print("=" * 78)
print("RBAC EM ROTAS DE ESCRITA (CSRF desligado para isolar)".center(78))
print("=" * 78)
print(f"\n{'rota':<38} {'metodo':<7} {'perfil':<10} {'status':<7} veredito")
print("-" * 78)

furos = []
for rota, metodo, dados, proibidos in casos:
    for perfil in proibidos:
        c = perfis[perfil]
        r = getattr(c, metodo)(rota, data=dados)
        bloqueado = r.status_code in (401, 403)
        # 404 tambem e aceitavel (recurso nao existe), 400 = validacao
        aceitavel = bloqueado or r.status_code == 404
        veredito = "ok" if aceitavel else ">>> PASSOU DIRETO"
        if not aceitavel:
            furos.append((rota, metodo, perfil, r.status_code))
        print(f"{rota:<38} {metodo:<7} {perfil:<10} {r.status_code:<7} {veredito}")

print("-" * 78)
if furos:
    print(f"\n{len(furos)} ROTA(S) SEM RBAC EFETIVO:")
    for rota, metodo, perfil, st in furos:
        print(f"  {metodo.upper():<7} {rota:<38} acessivel por '{perfil}' (status {st})")
else:
    print("\nNenhum furo: todo perfil proibido foi barrado.")
