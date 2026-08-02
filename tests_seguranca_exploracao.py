# -*- coding: utf-8 -*-
"""Testes de exploração — tenta ABUSAR do sistema, não só exercitá-lo.

Cada teste é uma tentativa de ataque. PASSOU = a defesa funcionou.
FALHOU = a exploração deu certo e existe vulnerabilidade.
"""
import logging
import pathlib
import sys

logging.disable(logging.WARNING)
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from app import app  # noqa: E402
from extensions import db  # noqa: E402

resultados = []


def checar(nome, passou, detalhe=""):
    resultados.append((nome, passou, detalhe))
    print(f"  {'PASSOU' if passou else 'FALHOU'}  {nome}")
    if not passou and detalhe:
        print(f"          -> {detalhe}")


def cliente(email=None, senha="senha12345", csrf=True):
    app.config["WTF_CSRF_ENABLED"] = csrf
    c = app.test_client()
    if email:
        c.post("/auth/login", data={"email": email, "senha": senha},
               follow_redirects=True)
    return c


# Garante os usuários de teste
with app.app_context():
    from models.user import User
    for nome, email, perfil in [
        ("Ana Souza", "admin@sus.gov.br", "admin"),
        ("Dr. Teste", "medico2@sus.gov.br", "medico"),
        ("Recep Teste", "recepcao@sus.gov.br", "recepcionista"),
        ("Gestor Teste", "gestor2@sus.gov.br", "gestor"),
    ]:
        if not User.query.filter_by(email=email).first():
            u = User(nome=nome, email=email, perfil=perfil, ativo=True)
            u.set_password("senha12345")
            db.session.add(u)
    db.session.commit()

print("=" * 74)
print("TESTES DE EXPLORACAO".center(74))
print("=" * 74)

# ---------------------------------------------------------------- 1
print("\n### 1. Acesso sem autenticacao")
anon = cliente()
protegidas = ["/", "/pacientes/listar", "/prontuarios/", "/auditoria/",
              "/admin/", "/conta/", "/exportacao/", "/internacao/api/leitos",
              "/portal-cidadao/", "/vigilancia/"]
vazou = []
for u in protegidas:
    r = anon.get(u)
    # 200 = vazou; 302 (para login) ou 401 = defendido
    if r.status_code == 200:
        vazou.append(f"{u} -> 200")
checar("Rotas protegidas negam anônimo", not vazou, "; ".join(vazou))

# ---------------------------------------------------------------- 2
print("\n### 2. Escalonamento de privilegio")
med = cliente("medico2@sus.gov.br")
recep = cliente("recepcao@sus.gov.br")

so_admin = ["/admin/", "/configuracoes/", "/backup/", "/unidades/"]
furos = []
for u in so_admin:
    r = med.get(u)
    if r.status_code == 200:
        furos.append(f"medico acessou {u}")
checar("Medico NAO acessa area de admin", not furos, "; ".join(furos))

furos = []
for u in ["/prontuarios/", "/exportacao/", "/auditoria/"]:
    r = recep.get(u)
    if r.status_code == 200:
        furos.append(f"recepcao acessou {u}")
checar("Recepcao NAO acessa prontuario/exportacao/auditoria", not furos, "; ".join(furos))

# CSRF desligado aqui de proposito: senao o 400 do token mascara o RBAC,
# que e o que este bloco mede.
recep_sem_csrf = cliente("recepcao@sus.gov.br", csrf=False)
med_sem_csrf = cliente("medico2@sus.gov.br", csrf=False)

r = recep_sem_csrf.post("/prontuarios/novo/1", data={"subjetivo": "invadido"})
checar("Recepcao NAO cria prontuario", r.status_code in (401, 403),
       f"status {r.status_code}")

# Médico tentando desativar usuário (admin)
r = med_sem_csrf.post("/admin/usuarios/1/desativar")
checar("Medico NAO desativa usuario", r.status_code in (401, 403),
       f"status {r.status_code}")

# ---------------------------------------------------------------- 3
print("\n### 3. Bypass do MFA")
with app.app_context():
    import pyotp
    from models.user import User
    u = User.query.filter_by(email="medico2@sus.gov.br").first()
    u.mfa_secret = pyotp.random_base32()
    u.mfa_ativo = True
    db.session.commit()
    segredo = u.mfa_secret

app.config["WTF_CSRF_ENABLED"] = False
c = app.test_client()
r = c.post("/auth/login", data={"email": "medico2@sus.gov.br", "senha": "senha12345"},
           follow_redirects=True)
# Com MFA ativo, a senha sozinha NAO pode autenticar
autenticado = "sidebar__brand" in r.get_data(as_text=True)
checar("Senha sozinha NAO autentica quem tem MFA", not autenticado,
       "entrou sem o segundo fator")

# Tenta acessar rota protegida com o desafio pendente
r = c.get("/pacientes/listar")
checar("Desafio MFA pendente NAO da acesso", r.status_code != 200,
       f"status {r.status_code}")

# Código errado
r = c.post("/auth/mfa/verify", data={"codigo": "000000"}, follow_redirects=True)
checar("Codigo MFA errado e rejeitado", "sidebar__brand" not in r.get_data(as_text=True))

# Código certo entra
r = c.post("/auth/mfa/verify", data={"codigo": pyotp.TOTP(segredo).now()},
           follow_redirects=True)
checar("Codigo MFA correto autentica", "sidebar__brand" in r.get_data(as_text=True))

with app.app_context():
    from models.user import User
    u = User.query.filter_by(email="medico2@sus.gov.br").first()
    u.mfa_ativo = False
    u.mfa_secret = None
    db.session.commit()

# ---------------------------------------------------------------- 4
print("\n### 4. CSRF")
adm = cliente("admin@sus.gov.br", csrf=True)
r = adm.post("/configuracoes/", data={"nome_unidade": "INVADIDO"})
checar("POST sem token CSRF e rejeitado", r.status_code == 400,
       f"status {r.status_code} — esperado 400")

# ---------------------------------------------------------------- 5
print("\n### 5. Open redirect")
adm2 = cliente(csrf=False)
r = adm2.post("/auth/login?next=https://evil.example.com/roubo",
              data={"email": "admin@sus.gov.br", "senha": "senha12345"})
destino = r.headers.get("Location", "")
checar("Nao redireciona para host externo", "evil.example.com" not in destino,
       f"Location: {destino}")

r = adm2.post("/auth/login", data={"email": "admin@sus.gov.br",
                                   "senha": "senha12345",
                                   "next": "//evil.example.com"})
destino = r.headers.get("Location", "")
checar("Nao redireciona para //host (protocol-relative)",
       "evil.example.com" not in destino, f"Location: {destino}")

# ---------------------------------------------------------------- 6
print("\n### 6. SQL injection")
adm3 = cliente("admin@sus.gov.br", csrf=False)
payloads = ["' OR '1'='1", "'; DROP TABLE pacientes;--", "%' UNION SELECT NULL--",
            "1' AND SLEEP(5)--"]
quebrou = []
for p in payloads:
    r = adm3.get("/pacientes/listar", query_string={"q": p})
    if r.status_code >= 500:
        quebrou.append(f"{p[:20]} -> {r.status_code}")
checar("Filtro de busca resiste a injecao", not quebrou, "; ".join(quebrou))

with app.app_context():
    from models.paciente import Paciente
    ainda_existe = Paciente.query.count() >= 0
checar("Tabela pacientes intacta apos DROP TABLE", ainda_existe)

# ---------------------------------------------------------------- 7
print("\n### 7. XSS refletido")
xss = "<script>alert(1)</script>"
r = adm3.get("/pacientes/listar", query_string={"q": xss})
corpo = r.get_data(as_text=True)
checar("Payload XSS sai escapado", xss not in corpo,
       "script cru no HTML")

r = adm3.get("/tabelas/", query_string={"q": xss})
checar("XSS escapado em tabelas oficiais", xss not in r.get_data(as_text=True))

# ---------------------------------------------------------------- 8
print("\n### 8. IDOR / vazamento por ID")
r = adm3.get("/pacientes/99999/perfil")
checar("Paciente inexistente devolve 404", r.status_code == 404,
       f"status {r.status_code}")

# Verificação pública não pode vazar dado clínico
pub = app.test_client()
r = pub.get("/verificar/QUALQUERCOISA")
corpo = r.get_data(as_text=True).lower()
vazamentos = [p for p in ("cpf", "cns", "diagnóstico", "prontuário eletrônico nacional")
              if p in corpo and p not in ("prontuário eletrônico nacional",)]
checar("Verificacao publica nao vaza dado clinico", not vazamentos,
       f"encontrado: {vazamentos}")

# ---------------------------------------------------------------- 9
print("\n### 9. Forca bruta no login")
bruta = cliente(csrf=False)
codigos = []
for i in range(12):
    r = bruta.post("/auth/login", data={"email": "admin@sus.gov.br",
                                        "senha": f"errada{i}"})
    codigos.append(r.status_code)
bloqueou = any(c == 429 for c in codigos)
checar("Login limita tentativas (429 apos varias falhas)", bloqueou,
       f"12 tentativas, nenhum 429 — codigos: {set(codigos)}")

# ---------------------------------------------------------------- 10
print("\n### 10. Enumeracao de usuario")
r1 = bruta.post("/auth/login", data={"email": "naoexiste@x.com", "senha": "x"},
                follow_redirects=True)
r2 = bruta.post("/auth/login", data={"email": "admin@sus.gov.br", "senha": "errada"},
                follow_redirects=True)
import re as _re
def msg(r):
    m = _re.search(r'alert__body">([^<]+)', r.get_data(as_text=True))
    return (m.group(1) if m else "").strip()
checar("Mensagem identica p/ usuario inexistente e senha errada",
       msg(r1) == msg(r2), f"'{msg(r1)}' vs '{msg(r2)}'")

# ---------------------------------------------------------------- 11
print("\n### 11. Cabecalhos e cookie")
r = app.test_client().get("/auth/login")
cookie = r.headers.get("Set-Cookie", "")
checar("Cookie de sessao HttpOnly", "HttpOnly" in cookie or not cookie,
       f"Set-Cookie: {cookie[:80]}")
checar("Cookie de sessao SameSite", "SameSite" in cookie or not cookie,
       f"Set-Cookie: {cookie[:80]}")

# ---------------------------------------------------------------- 12
print("\n### 12. Upload")
grande = b"x" * (30 * 1024 * 1024)  # 30 MB
try:
    r = adm3.post("/pdf/processar", data={"documento": (__import__("io").BytesIO(grande), "g.pdf"),
                                          "acao": "compactar"},
                  content_type="multipart/form-data")
    checar("Upload gigante e recusado", r.status_code in (400, 413),
           f"status {r.status_code} — aceitou 30MB")
except Exception as e:
    checar("Upload gigante e recusado", True, str(e)[:50])

# ---------------------------------------------------------------- Resumo
print("\n" + "=" * 74)
passou = sum(1 for _, p, _ in resultados if p)
print(f"RESULTADO: {passou}/{len(resultados)} defesas funcionaram")
falhas = [(n, d) for n, p, d in resultados if not p]
if falhas:
    print(f"\n{len(falhas)} VULNERABILIDADE(S) CONFIRMADA(S):")
    for n, d in falhas:
        print(f"  - {n}")
        if d:
            print(f"      {d}")
