# -*- coding: utf-8 -*-
"""RBAC granular por permissão (`recurso:ação`).

Porte direto de `backend/src/shared/rbac/permissions.ts` do monorepo NestJS. O
backend é a autoridade: toda rota é protegida por `@requer_permissao(...)`. O
template apenas ESPELHA a decisão via `pode(...)` para esconder controles — nunca
é a fonte de verdade.

Perfis legados em minúsculo (`admin`, `medico`, `enfermeiro`, `recepcionista`)
continuam funcionando: `_normalizar` os traduz para os nomes canônicos.
"""
from functools import wraps

from flask import abort
from flask_login import current_user

# --- Permissões --------------------------------------------------------------

PATIENT_READ = "patient:read"
PATIENT_CREATE = "patient:create"
PATIENT_UPDATE = "patient:update"
TRIAGE_READ = "triage:read"
TRIAGE_WRITE = "triage:write"
ENCOUNTER_WRITE = "encounter:write"
CLINICAL_READ = "clinical:read"
CLINICAL_WRITE = "clinical:write"
PRESCRIPTION_READ = "prescription:read"
PRESCRIPTION_CREATE = "prescription:create"
PRESCRIPTION_WRITE = "prescription:write"
INTERNMENT_WRITE = "internment:write"
EMERGENCY_WRITE = "emergency:write"
EXAM_WRITE = "exam:write"
SURGERY_WRITE = "surgery:write"
MED_ADMIN_WRITE = "med-admin:write"
REPORTS_READ = "reports:read"
SURVEILLANCE_READ = "surveillance:read"
SURVEILLANCE_WRITE = "surveillance:write"
REGULATION_READ = "regulation:read"
REGULATION_WRITE = "regulation:write"
REGULATION_DECIDE = "regulation:decide"
AUDIT_READ = "audit:read"
USER_MANAGE = "user:manage"
HOSPITAL_MANAGE = "hospital:manage"
ADMIN_FULL = "admin:full"

TODAS_PERMISSOES = frozenset({
    PATIENT_READ, PATIENT_CREATE, PATIENT_UPDATE,
    TRIAGE_READ, TRIAGE_WRITE,
    ENCOUNTER_WRITE, CLINICAL_READ, CLINICAL_WRITE,
    PRESCRIPTION_READ, PRESCRIPTION_CREATE, PRESCRIPTION_WRITE,
    INTERNMENT_WRITE, EMERGENCY_WRITE, EXAM_WRITE, SURGERY_WRITE, MED_ADMIN_WRITE,
    REPORTS_READ,
    SURVEILLANCE_READ, SURVEILLANCE_WRITE,
    REGULATION_READ, REGULATION_WRITE, REGULATION_DECIDE,
    AUDIT_READ, USER_MANAGE, HOSPITAL_MANAGE, ADMIN_FULL,
})

# --- Perfis ------------------------------------------------------------------

SUPER_ADMIN = "SuperAdmin"
ADMINISTRADOR = "Administrador"
MEDICO = "Medico"
ENFERMEIRO = "Enfermeiro"
FARMACEUTICO = "Farmaceutico"
RECEPCAO = "Recepcao"
GESTOR = "Gestor"

PERFIS = (SUPER_ADMIN, ADMINISTRADOR, MEDICO, ENFERMEIRO, FARMACEUTICO, RECEPCAO, GESTOR)

# Nomes legados do banco Flask -> nome canônico.
_ALIASES = {
    "superadmin": SUPER_ADMIN,
    "super_admin": SUPER_ADMIN,
    "admin": ADMINISTRADOR,
    "administrador": ADMINISTRADOR,
    "medico": MEDICO,
    "médico": MEDICO,
    "enfermeiro": ENFERMEIRO,
    "enfermeira": ENFERMEIRO,
    "farmaceutico": FARMACEUTICO,
    "farmacêutico": FARMACEUTICO,
    "recepcao": RECEPCAO,
    "recepção": RECEPCAO,
    "recepcionista": RECEPCAO,
    "gestor": GESTOR,
}

PERFIL_PERMISSOES = {
    # Operador da plataforma: atravessa o isolamento por hospital.
    SUPER_ADMIN: {ADMIN_FULL, HOSPITAL_MANAGE},
    # Admin dentro do próprio hospital.
    ADMINISTRADOR: {ADMIN_FULL},
    MEDICO: {
        PATIENT_READ, PATIENT_UPDATE,
        CLINICAL_READ, CLINICAL_WRITE, ENCOUNTER_WRITE,
        PRESCRIPTION_READ, PRESCRIPTION_CREATE, PRESCRIPTION_WRITE,
        TRIAGE_READ,
        INTERNMENT_WRITE, EMERGENCY_WRITE, EXAM_WRITE, SURGERY_WRITE,
        REPORTS_READ,
        SURVEILLANCE_READ, SURVEILLANCE_WRITE,
        REGULATION_READ, REGULATION_WRITE,
    },
    ENFERMEIRO: {
        PATIENT_READ,
        TRIAGE_READ, TRIAGE_WRITE,
        CLINICAL_READ,
        PRESCRIPTION_READ,
        EMERGENCY_WRITE, EXAM_WRITE, INTERNMENT_WRITE, MED_ADMIN_WRITE,
        SURVEILLANCE_READ, SURVEILLANCE_WRITE,
        REGULATION_READ,
    },
    FARMACEUTICO: {PATIENT_READ, PRESCRIPTION_READ, MED_ADMIN_WRITE},
    RECEPCAO: {PATIENT_READ, PATIENT_CREATE, PATIENT_UPDATE},
    GESTOR: {
        PATIENT_READ, CLINICAL_READ,
        AUDIT_READ, REPORTS_READ,
        SURVEILLANCE_READ, SURVEILLANCE_WRITE,
        REGULATION_READ, REGULATION_DECIDE,
    },
}


def _normalizar(perfil):
    if not perfil:
        return None
    p = str(perfil).strip()
    if p in PERFIL_PERMISSOES:
        return p
    return _ALIASES.get(p.lower())


def permissoes_de(perfil):
    """Conjunto de permissões concedidas a um perfil."""
    return set(PERFIL_PERMISSOES.get(_normalizar(perfil), set()))


def is_super_admin(perfil):
    """Único perfil autorizado a atravessar o isolamento por hospital."""
    return _normalizar(perfil) == SUPER_ADMIN


def permissoes_do_usuario(usuario=None):
    u = usuario if usuario is not None else current_user
    if not getattr(u, "is_authenticated", False):
        return set()
    return permissoes_de(getattr(u, "perfil", None))


def pode(*permissoes, usuario=None):
    """True se o usuário tem QUALQUER uma das permissões.

    `admin:full` concede tudo — é o coringa, igual ao `grantsAll` do backend.
    Sem argumentos, responde apenas "está autenticado?".
    """
    concedidas = permissoes_do_usuario(usuario)
    if not concedidas:
        return False
    if ADMIN_FULL in concedidas:
        return True
    if not permissoes:
        return True
    return any(p in concedidas for p in permissoes)


def requer_permissao(*permissoes):
    """Decorator de rota. 401 se anônimo, 403 se autenticado sem permissão."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not getattr(current_user, "is_authenticated", False):
                abort(401)
            if not pode(*permissoes):
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def requer_perfil(*perfis):
    """Decorator para autorização por PERFIL, quando não há permissão granular."""
    alvo = {_normalizar(p) for p in perfis}

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not getattr(current_user, "is_authenticated", False):
                abort(401)
            atual = _normalizar(getattr(current_user, "perfil", None))
            if atual != SUPER_ADMIN and atual not in alvo:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator
