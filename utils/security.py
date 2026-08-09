from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user
import re

# ===============================
# Validações
# ===============================
_CPF_RE = re.compile(r"^\d{11}$")
_CNS_RE = re.compile(r"^\d{15}$")
_IBGE_RE = re.compile(r"^\d{7}$")
_CID10_RE = re.compile(r"^[A-TV-Z][0-9][0-9AB](\.[0-9A-KXZ]{1,2})?$")


def validar_cpf(cpf: str) -> bool:
    cpf = (cpf or "").strip().replace(".", "").replace("-", "")
    return bool(_CPF_RE.fullmatch(cpf))


def validar_cns(cns: str) -> bool:
    return bool(_CNS_RE.fullmatch((cns or "").strip()))


def validar_ibge(cod: str) -> bool:
    return bool(_IBGE_RE.fullmatch((cod or "").strip()))


def validar_cid10(cid: str) -> bool:
    return bool(_CID10_RE.fullmatch((cid or "").strip().upper()))


# ===============================
# Controle por perfil (já usado)
# ===============================
def perfil_requerido(*perfis):
    """Autorização por PERFIL, para o caso em que não há permissão granular.

    Compara nomes NORMALIZADOS. A versão anterior comparava a string crua do
    banco contra literais em minúsculo, enquanto `utils.rbac` normaliza por
    apelido — de modo que um usuário gravado como "Medico" (a forma canônica de
    `PERFIS`) passava pelo RBAC e era barrado aqui, e um gravado como "medico"
    fazia o contrário. Duas linguagens de autorização convivendo já é ruim; que
    discordassem sobre o mesmo usuário era o defeito.
    """
    from utils.rbac import ADMINISTRADOR, SUPER_ADMIN, _normalizar

    alvo = {_normalizar(p) for p in perfis} | {SUPER_ADMIN}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("auth.login"))
            atual = _normalizar(getattr(current_user, "perfil", None))
            # O administrador seguia liberado incondicionalmente pelo `!=
            # "admin"` do final da condição antiga. Mantido, mas explícito.
            if atual not in alvo and atual != ADMINISTRADOR:
                flash("Você não tem permissão para acessar esta área.", "danger")
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def medico_requerido(f):
    return perfil_requerido("medico", "admin")(f)


def admin_requerido(f):
    return perfil_requerido("admin")(f)


# ===============================
# Escopo territorial
# ===============================
def pode_acessar_paciente(paciente, usuario):
    # `perfil == "admin"` liberava tudo. Pelo mapa de utils/rbac.py, "admin" é
    # alias de ADMINISTRADOR — "Admin dentro do próprio hospital" —, então um
    # administrador de hospital lia o prontuário de qualquer cidadão do país. O
    # próprio rbac.py define SuperAdmin como "o único perfil autorizado a
    # atravessar o isolamento por hospital"; aqui o código passa a cumprir isso.
    #
    # O escopo continua sendo respeitado pelo administrador via `nivel_acesso`:
    # quem precisa enxergar além da unidade recebe MUNICIPIO, REGIONAL, ESTADO
    # ou SISTEMA no cadastro, que é onde essa decisão deve morar.
    from utils.rbac import is_super_admin

    if is_super_admin(usuario.perfil):
        return True

    nivel = getattr(usuario, "nivel_acesso", "UNIDADE")

    if nivel in ("ESTADO", "SISTEMA"):
        return True

    # MUNICIPIO: preferir municipio_ibge
    if nivel == "MUNICIPIO":
        user_ibge = getattr(usuario, "municipio_ibge", None)
        pac_ibge = getattr(paciente, "municipio_ibge", None)
        if user_ibge and pac_ibge:
            return str(user_ibge) == str(pac_ibge)

        # fallback por unidade->municipio/uf
        if usuario.unidade:
            return (
                paciente.municipio == usuario.unidade.municipio
                and paciente.uf == usuario.unidade.uf
            )
        return False

    # REGIONAL: fallback por UF (até mapear regional no paciente)
    if nivel == "REGIONAL":
        if getattr(usuario, "uf", None) and getattr(paciente, "uf", None):
            return usuario.uf == paciente.uf
        return False

    # UNIDADE: por município/UF da unidade
    if nivel == "UNIDADE":
        if usuario.unidade:
            return (
                paciente.municipio == usuario.unidade.municipio
                and paciente.uf == usuario.unidade.uf
            )
        return False

    return False


def query_pacientes_no_escopo(usuario=None):
    """Query de pacientes já restrita ao escopo territorial do usuário.

    Mora AQUI, ao lado de `pode_acessar_paciente`, e não dentro de um blueprint.
    A regra vivia em `routes/pacientes.py`; o portal do cidadão, que serve o
    mesmo dado por outra rota, não a importou e passou a permitir busca
    nacional. Regra de autorização que mora perto de UMA rota é regra que a
    próxima rota esquece — e o esquecimento não gera erro, gera dado a mais.

    As duas funções deste módulo respondem à mesma pergunta em formas
    diferentes: `pode_acessar_paciente` decide sobre UM registro já carregado;
    esta restringe o CONJUNTO antes de carregar. Mantê-las juntas é o que torna
    possível notar quando divergem.
    """
    from flask import current_app
    from flask_login import current_user

    from models.paciente import Paciente
    from utils.rbac import is_super_admin

    u = usuario if usuario is not None else current_user
    q = Paciente.query.filter_by(ativo=True)

    if current_app.config.get("FEATURE_DEV_MODE", False) or \
            current_app.config.get("FEATURE_BYPASS_PACIENTE_SCOPE", False):
        return q

    if is_super_admin(getattr(u, "perfil", None)) or getattr(
            u, "nivel_acesso", "UNIDADE") in ("ESTADO", "SISTEMA"):
        return q

    nivel = getattr(u, "nivel_acesso", "UNIDADE")

    if nivel == "MUNICIPIO":
        user_ibge = getattr(u, "municipio_ibge", None)
        if user_ibge and hasattr(Paciente, "municipio_ibge"):
            return q.filter(Paciente.municipio_ibge == user_ibge)
        if getattr(u, "unidade", None):
            return q.filter(Paciente.municipio == u.unidade.municipio,
                            Paciente.uf == u.unidade.uf)
        return q.filter(Paciente.id == -1)

    if nivel == "REGIONAL":
        if getattr(u, "uf", None):
            return q.filter(Paciente.uf == u.uf)
        return q.filter(Paciente.id == -1)

    if getattr(u, "unidade", None):
        return q.filter(Paciente.municipio == u.unidade.municipio,
                        Paciente.uf == u.unidade.uf)

    # Falha fechada: escopo irresolúvel não libera nada.
    if current_app.config.get("FEATURE_RBAC_STRICT", True):
        return q.filter(Paciente.id == -1)
    return q


def pode_acessar_prontuario(prontuario, usuario):
    if usuario.perfil == "admin":
        return True

    nivel = getattr(usuario, "nivel_acesso", "UNIDADE")
    if nivel == "ESTADO":
        return True

    if nivel in ("UNIDADE", "MUNICIPIO"):
        if usuario.unidade_id and prontuario.unidade_id:
            return usuario.unidade_id == prontuario.unidade_id
        return False

    if nivel == "REGIONAL":
        unidade = getattr(prontuario, "unidade", None)
        return bool(
            unidade
            and getattr(usuario, "regional_id", None)
            and unidade.regional_id == usuario.regional_id
        )

    return False
