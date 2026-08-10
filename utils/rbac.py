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
# Agendar não é atender nem cadastrar paciente. Existia como lacuna: as rotas de
# agenda e agendamento gravavam sob `patient:read` — permissão de LEITURA — por
# não haver nome para a função. Quem agenda é a Recepção; o clínico agenda
# retorno, e por isso Médico e Enfermeiro também recebem.
SCHEDULE_WRITE = "schedule:write"
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
    ENCOUNTER_WRITE, SCHEDULE_WRITE, CLINICAL_READ, CLINICAL_WRITE,
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

# Rótulo de tela para cada perfil. Fica aqui, e não no gabarito, porque a lista
# escrita à mão no formulário de usuário oferecia QUATRO dos sete — Farmacêutico
# e Gestor existiam na matriz, tinham permissões próprias e não havia como criar
# usuário com eles. É a mesma replicação de regra da seção 9.4.14 da monografia,
# desta vez entre a matriz e um `{% for %}`.
ROTULOS_PERFIL = {
    SUPER_ADMIN: "Operador da plataforma",
    ADMINISTRADOR: "Administrador",
    MEDICO: "Médico(a)",
    ENFERMEIRO: "Enfermeiro(a)",
    FARMACEUTICO: "Farmacêutico(a)",
    RECEPCAO: "Recepcionista",
    GESTOR: "Gestor(a)",
}


def perfis_atribuiveis(atribuidor=None):
    """Perfis que a tela de usuários pode oferecer.

    `SuperAdmin` atravessa o isolamento por hospital, então só um SuperAdmin o
    concede — administrador de hospital que pudesse criá-lo escaparia do próprio
    escopo territorial pela porta de gestão de contas.
    """
    concedidos = [p for p in PERFIS if p != SUPER_ADMIN]
    if _normalizar(atribuidor) == SUPER_ADMIN:
        concedidos.insert(0, SUPER_ADMIN)
    return [(p, ROTULOS_PERFIL[p]) for p in concedidos]

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
    # Admin dentro do próprio hospital. `ADMIN_FULL` é coringa e já
    # concederia tudo — `USER_MANAGE` aparece explícito porque a matriz
    # é documento de governança: quem a lê precisa ver QUEM administra
    # contas sem ter de saber que existe um coringa.
    ADMINISTRADOR: {ADMIN_FULL, USER_MANAGE},
    MEDICO: {
        PATIENT_READ, PATIENT_UPDATE,
        CLINICAL_READ, CLINICAL_WRITE, ENCOUNTER_WRITE, SCHEDULE_WRITE,
        PRESCRIPTION_READ, PRESCRIPTION_CREATE, PRESCRIPTION_WRITE,
        # `TRIAGE_WRITE`: a concessão foi decidida acreditando-se que havia
        # norma profissional em contrário. NÃO HÁ. A Resolução Cofen 661/2021
        # (que revogou a 423/2012, citada em toda parte como se vigente fosse)
        # diz "NO ÂMBITO DA EQUIPE DE ENFERMAGEM, a classificação de Risco (...)
        # é privativa do Enfermeiro" — e não menciona médicos, porque o conselho
        # de enfermagem não regula outra profissão. A norma separa enfermeiro de
        # TÉCNICO de enfermagem.
        #
        # Isto tem consequência para esta matriz, e ela é o inverso da que se
        # supunha: o problema não é o Médico ter a permissão, é NÃO HAVER perfil
        # de técnico de enfermagem. Enquanto ENFERMEIRO for perfil único, a
        # distinção que a norma exige depende de a organização não dar esse
        # perfil a técnico — controle administrativo, não técnico.
        #
        # O que sustenta a concessão são razões de projeto: em unidade pequena
        # sem enfermeiro de plantão, negar produz paciente na fila SEM
        # classificação de risco, e é ela que ordena o painel do PS; a trilha já
        # registra a autoria, então a segregação acrescenta pouco; e negar
        # empurra para o registro por terceiro, que faz a trilha mentir sobre
        # quem classificou.
        TRIAGE_READ, TRIAGE_WRITE,
        INTERNMENT_WRITE, EMERGENCY_WRITE, EXAM_WRITE, SURGERY_WRITE,
        REPORTS_READ,
        SURVEILLANCE_READ, SURVEILLANCE_WRITE,
        REGULATION_READ, REGULATION_WRITE,
    },
    ENFERMEIRO: {
        PATIENT_READ, SCHEDULE_WRITE,
        TRIAGE_READ, TRIAGE_WRITE,
        CLINICAL_READ,
        PRESCRIPTION_READ,
        EMERGENCY_WRITE, EXAM_WRITE, INTERNMENT_WRITE, MED_ADMIN_WRITE,
        SURVEILLANCE_READ, SURVEILLANCE_WRITE,
        REGULATION_READ,
    },
    FARMACEUTICO: {PATIENT_READ, PRESCRIPTION_READ, MED_ADMIN_WRITE},
    RECEPCAO: {PATIENT_READ, PATIENT_CREATE, PATIENT_UPDATE, SCHEDULE_WRITE},
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


def registrar_negacao(permissoes, motivo):
    """Log de negação de acesso, com o que permite investigar depois.

    Negação isolada é rotina — alguém clicou onde não devia. Negação em série,
    do mesmo usuário ou do mesmo IP, é tentativa de mapear o que o sistema
    expõe, e é o indicador MAIS PRECOCE de acesso indevido que existe: aparece
    antes de qualquer dado vazar. Sem este registro, o primeiro sinal seria o
    incidente já consumado.

    Vai para o log da aplicação e não para `audit_logs` de propósito: a trilha
    de auditoria registra o que ACONTECEU com dado clínico, e aqui nada
    aconteceu. Misturar as duas coisas polui a trilha que responde ao titular.
    """
    from flask import current_app, request

    current_app.logger.warning(
        "ACESSO NEGADO: usuario=%s perfil=%s ip=%s rota=%s exigia=%s (%s)",
        getattr(current_user, "id", None),
        getattr(current_user, "perfil", None),
        request.headers.get("X-Forwarded-For", request.remote_addr),
        request.endpoint,
        ",".join(permissoes) if permissoes else "-",
        motivo,
    )


def requer_permissao(*permissoes):
    """Decorator de rota. 401 se anônimo, 403 se autenticado sem permissão."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not getattr(current_user, "is_authenticated", False):
                registrar_negacao(permissoes, "sessão anônima")
                abort(401)
            if not pode(*permissoes):
                registrar_negacao(permissoes, "perfil sem a permissão")
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
