# -*- coding: utf-8 -*-
"""Auditoria estática de segurança do SNPE."""
import io
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
RAIZ = pathlib.Path(__file__).parent

from app import app  # noqa: E402

achados = {"CRITICO": [], "ALTO": [], "MEDIO": [], "BAIXO": []}


def add(sev, titulo, detalhe):
    achados[sev].append((titulo, detalhe))


# ---------------------------------------------------------------- 1. Rotas
# Endpoints que PODEM ser públicos por desenho.
PUBLICOS_OK = {
    "static", "auth.login", "auth.login_post", "auth.mfa_verify",
    "auth.mfa_cancelar", "auth.govbr_login", "auth.govbr_callback",
    "auth.govbr_status", "auth.govbr_simulador", "auth.govbr_simulador_post",
    "documentos.verificar",
}

METODOS_ESCRITA = {"POST", "PUT", "PATCH", "DELETE"}

sem_login, escrita_sem_rbac = [], []

for regra in app.url_map.iter_rules():
    ep = regra.endpoint
    if ep in PUBLICOS_OK:
        continue

    view = app.view_functions.get(ep)
    if not view:
        continue

    # flask_login marca a view decorada
    tem_login = getattr(view, "__wrapped__", None) is not None or hasattr(
        view, "__login_required__"
    )
    # heurística mais confiável: procurar o decorator no fonte
    fonte = ""
    try:
        import inspect

        fonte = inspect.getsource(view)
    except Exception:
        pass

    modulo = view.__module__.replace(".", "/") + ".py"
    caminho = RAIZ / modulo
    if caminho.exists():
        txt = io.open(caminho, encoding="utf-8").read()
        # bloco de decorators imediatamente antes do def
        m = re.search(
            r"((?:^@[^\n]*\n)+)def\s+" + re.escape(view.__name__) + r"\s*\(",
            txt,
            re.M,
        )
        decorators = m.group(1) if m else ""
    else:
        decorators = ""

    if "@login_required" not in decorators:
        sem_login.append((ep, str(regra)))

    metodos = regra.methods - {"HEAD", "OPTIONS"}
    if metodos & METODOS_ESCRITA:
        if "requer_permissao" not in decorators and "requer_perfil" not in decorators \
           and "admin_requerido" not in decorators and "medico_requerido" not in decorators:
            escrita_sem_rbac.append((ep, str(regra), sorted(metodos)))

if sem_login:
    add("CRITICO", f"{len(sem_login)} rota(s) sem @login_required",
        "\n".join(f"      {e}  {u}" for e, u in sem_login[:15]))

if escrita_sem_rbac:
    add("ALTO", f"{len(escrita_sem_rbac)} rota(s) de ESCRITA sem RBAC",
        "\n".join(f"      {e}  {u}  {m}" for e, u, m in escrita_sem_rbac[:20]))


# ---------------------------------------------------------------- 2. Jinja |safe
usos_safe = []
for t in (RAIZ / "templates").rglob("*.html"):
    for i, linha in enumerate(io.open(t, encoding="utf-8"), 1):
        if "|safe" in linha or "| safe" in linha:
            usos_safe.append(f"{t.relative_to(RAIZ).as_posix()}:{i}  {linha.strip()[:70]}")
if usos_safe:
    add("MEDIO", f"{len(usos_safe)} uso(s) de |safe (risco de XSS se vier do usuário)",
        "\n".join(f"      {u}" for u in usos_safe))


# ---------------------------------------------------------------- 3. SQL
sql_interp = []
for p in list((RAIZ / "routes").glob("*.py")) + list((RAIZ / "utils").glob("*.py")) + \
         list((RAIZ / "models").glob("*.py")) + list((RAIZ / "services").glob("*.py")):
    txt = io.open(p, encoding="utf-8").read()
    for m in re.finditer(r'(text|execute)\(\s*f["\']', txt):
        sql_interp.append(f"{p.name}: {m.group(0)}")
if sql_interp:
    add("CRITICO", "SQL com f-string (injeção)", "\n".join(f"      {s}" for s in sql_interp))


# ---------------------------------------------------------------- 4. Config
cfg = app.config
if not cfg.get("SESSION_COOKIE_HTTPONLY"):
    add("ALTO", "SESSION_COOKIE_HTTPONLY desligado", "      JS consegue ler o cookie de sessão")
if cfg.get("SESSION_COOKIE_SAMESITE") not in ("Lax", "Strict"):
    add("ALTO", "SESSION_COOKIE_SAMESITE fraco", f"      valor: {cfg.get('SESSION_COOKIE_SAMESITE')}")
if not cfg.get("WTF_CSRF_ENABLED", True):
    add("CRITICO", "CSRF desabilitado", "      WTF_CSRF_ENABLED=False")
if not cfg.get("SESSION_COOKIE_SECURE"):
    add("MEDIO", "SESSION_COOKIE_SECURE desligado no ambiente atual",
        "      correto em dev (HTTP); confirmar que ProductionConfig liga")
if cfg.get("PERMANENT_SESSION_LIFETIME") and cfg["PERMANENT_SESSION_LIFETIME"].days > 7:
    add("MEDIO", "Sessão muito longa", f"      {cfg['PERMANENT_SESSION_LIFETIME']}")


# ---------------------------------------------------------------- 5. Headers
resp = app.test_client().get("/auth/login")
headers_esperados = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "impede clickjacking",
    "Content-Security-Policy": "limita origem de script",
    "Referrer-Policy": "não vazar URL de prontuário no Referer",
}
faltando = [f"{h} ({motivo})" for h, motivo in headers_esperados.items() if h not in resp.headers]
if faltando:
    add("MEDIO", f"{len(faltando)} header(s) de segurança ausente(s)",
        "\n".join(f"      {h}" for h in faltando))


# ---------------------------------------------------------------- 6. Senha
seg = io.open(RAIZ / "utils" / "security.py", encoding="utf-8").read()
user_py = io.open(RAIZ / "models" / "user.py", encoding="utf-8").read()
if "generate_password_hash" not in user_py:
    add("CRITICO", "Senha possivelmente sem hash", "      generate_password_hash ausente em models/user.py")
if not re.search(r"len\(\s*\w*senha\w*\s*\)\s*[<>]=?\s*\d", io.open(RAIZ / "routes" / "conta.py", encoding="utf-8").read()):
    add("BAIXO", "Sem verificação de tamanho mínimo de senha em algum fluxo", "      conferir criação de usuário no admin")

admin_py = io.open(RAIZ / "routes" / "admin.py", encoding="utf-8").read()
if "Mudar@123" in admin_py:
    add("MEDIO", "Senha padrão fixa ao criar usuário",
        "      routes/admin.py usa 'Mudar@123' como default, sem forçar troca no 1º acesso")


# ---------------------------------------------------------------- 7. Brute force
auth_py = io.open(RAIZ / "routes" / "auth.py", encoding="utf-8").read()
if "limiter" not in auth_py.lower() and "ratelimit" not in auth_py.lower():
    add("ALTO", "Login sem limite de tentativas",
        "      /auth/login aceita tentativas ilimitadas — força bruta e enumeração por tempo")


# ---------------------------------------------------------------- 8. Upload
pdf_py = io.open(RAIZ / "routes" / "pdf.py", encoding="utf-8").read()
if "MAX_CONTENT_LENGTH" not in str(cfg.keys()) and not cfg.get("MAX_CONTENT_LENGTH"):
    add("MEDIO", "Upload sem limite de tamanho",
        "      MAX_CONTENT_LENGTH não definido; /pdf/processar e /importacao/csv aceitam arquivo de qualquer tamanho")


# ---------------------------------------------------------------- Relatório
print("=" * 74)
print("AUDITORIA ESTATICA DE SEGURANCA".center(74))
print("=" * 74)
total = sum(len(v) for v in achados.values())
for sev in ("CRITICO", "ALTO", "MEDIO", "BAIXO"):
    if not achados[sev]:
        continue
    print(f"\n### {sev} ({len(achados[sev])})")
    for titulo, detalhe in achados[sev]:
        print(f"\n  [{sev}] {titulo}")
        if detalhe:
            print(detalhe)
print(f"\n{'=' * 74}\nTOTAL: {total} achado(s)")
