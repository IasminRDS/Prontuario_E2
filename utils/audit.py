# utils/audit.py
from datetime import datetime
from functools import wraps

from flask import request
from flask_login import current_user

from extensions import db
from models.audit_log import AuditLog


def registrar(tabela, registro_id, acao, detalhes, commit=False):
    """Grava um evento de auditoria.

    Por padrão apenas anexa à sessão corrente (sem commit) para que o log caia na
    MESMA transação da mutação que o originou — é isso que dá atomicidade: ou a
    escrita clínica e a auditoria persistem juntas, ou nenhuma das duas.

    Use ``commit=True`` só em leituras/consultas, onde não há transação de escrita
    em curso para carregar o log.
    """
    usuario_id = getattr(current_user, "id", None) if current_user.is_authenticated else None
    ip = request.headers.get("X-Forwarded-For", request.remote_addr) if request else None

    log = AuditLog(
        tabela=tabela,
        registro_id=registro_id,
        acao=acao,
        descricao=detalhes,
        usuario_id=usuario_id,
        ip=ip,
        criado_em=datetime.utcnow(),
    )

    # Encadeia no último elo da trilha. Sob concorrência real dois writers podem
    # ler o mesmo `hash_anterior`; a verificação trata isso como ramificação, não
    # como violação. Para serialização estrita seria preciso um lock na tabela.
    anterior = (
        AuditLog.query
        .order_by(AuditLog.id.desc())
        .with_entities(AuditLog.hash_atual)
        .first()
    )
    log.hash_anterior = anterior[0] if anterior else None
    log.hash_atual = log.calcular_hash()

    db.session.add(log)

    if commit:
        db.session.commit()

    return log


def verificar_integridade(limite=None):
    """Recalcula a cadeia de hashes e devolve as inconsistências encontradas.

    Retorna (total_verificado, lista_de_problemas). Cada problema traz o id do
    registro e o motivo — elo rompido, hash recalculado divergente ou registro
    sem hash (gravado antes do encadeamento existir).
    """
    query = AuditLog.query.order_by(AuditLog.id.asc())
    if limite:
        query = query.limit(limite)

    problemas = []
    esperado_anterior = None
    total = 0

    for log in query.all():
        total += 1

        if not log.hash_atual:
            problemas.append({
                "id": log.id,
                "motivo": "registro sem hash (anterior ao encadeamento)",
            })
            esperado_anterior = None
            continue

        if esperado_anterior is not None and log.hash_anterior != esperado_anterior:
            problemas.append({
                "id": log.id,
                "motivo": "elo rompido: hash_anterior não corresponde ao registro precedente",
            })

        recalculado = log.calcular_hash()
        if recalculado != log.hash_atual:
            problemas.append({
                "id": log.id,
                "motivo": "conteúdo alterado após a gravação (hash divergente)",
            })

        esperado_anterior = log.hash_atual

    return total, problemas


def auditar_aqui(tabela, acao, descricao=None, commit=False):
    """Audita a operação corrente de dentro do corpo da view.

    Existe para substituir os `audit_log(...)()` espalhados pelas rotas: aquilo
    era uma fábrica de decorator sendo invocada inline — na melhor hipótese não
    auditava nada, na pior levantava TypeError.

    O `registro_id` sai dos parâmetros da rota, como o decorator fazia.
    """
    args = request.view_args or {}
    registro_id = (
        args.get("id")
        or args.get("prontuario_id")
        or args.get("paciente_id")
        or args.get("item_id")
        or args.get("internacao_id")
        or args.get("exame_id")
        or args.get("evento_id")
        or args.get("leito_id")
    )
    return registrar(
        tabela,
        registro_id,
        acao,
        descricao or f"{acao} em {tabela} via {request.endpoint}",
        commit=commit,
    )


def audit_log(acao_default="update", tabela_default="desconhecido"):
    """Decorator: audita a chamada de uma rota.

    ATENÇÃO: é uma fábrica de decorator — precisa ser aplicada com @, nunca
    chamada inline. `audit_log(...)` solto no corpo da função não audita nada.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            registro_id = kwargs.get("prontuario_id") or kwargs.get("id")
            registrar(
                tabela_default,
                registro_id,
                acao_default,
                f"Endpoint: {request.endpoint}",
                commit=True,
            )
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def log_auditoria(tabela, acao):
    """Decorator equivalente, com tabela/ação explícitas."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            registro_id = kwargs.get("prontuario_id") or (request.view_args or {}).get("id")
            registrar(
                tabela,
                registro_id,
                acao,
                f"Acesso à rota: {request.path}",
                commit=True,
            )
            return f(*args, **kwargs)
        return decorated_function
    return decorator
