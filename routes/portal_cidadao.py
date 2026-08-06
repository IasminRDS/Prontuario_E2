# -*- coding: utf-8 -*-
"""Portal do Cidadão — cartão de vacinas e transparência de acesso (LGPD).

Equivalente à página `/portal-cidadao` do frontend Next. O ponto central é o
direito do titular de saber QUEM acessou seu prontuário (art. 9º da LGPD): a
consulta lê a trilha de auditoria e mostra usuário, ação, data e IP.
"""
from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from models.audit_log import AuditLog
from models.paciente import Paciente
from models.user import User
from models.vacina import Vacina, VacinaAplicada
from utils.audit import registrar
from utils.rbac import requer_permissao
from utils.security import pode_acessar_paciente, query_pacientes_no_escopo

portal_cidadao_bp = Blueprint("portal_cidadao", __name__, url_prefix="/portal-cidadao")

# Tabelas cuja leitura conta como "acesso ao prontuário" do ponto de vista do
# titular. `registro_id` destas tabelas NÃO é o id do paciente (ver
# `_quem_acessou`); só "pacientes" tem essa equivalência.
TABELAS_CLINICAS = ("prontuarios", "pacientes", "exames_solicitados", "internacoes",
                    "triagens", "prescricoes", "atendimentos_ps")


@portal_cidadao_bp.get("/")
@login_required
@requer_permissao("clinical:read")
def index():
    termo = (request.args.get("q") or "").strip()
    paciente_id = request.args.get("paciente_id", type=int)

    pacientes = []
    if termo:
        like = f"%{termo}%"
        pacientes = (
            query_pacientes_no_escopo()
            .filter(
                Paciente.nome.ilike(like)
                | Paciente.cpf.ilike(like)
                | Paciente.cns.ilike(like)
            )
            .order_by(Paciente.nome)
            .limit(20)
            .all()
        )
        if len(pacientes) == 1 and not paciente_id:
            paciente_id = pacientes[0].id

    paciente = None
    if paciente_id:
        paciente = Paciente.query.get(paciente_id)
        # Esta rota lia `Paciente.query.get(...)` direto. Todas as outras que
        # servem o mesmo dado passam por `pode_acessar_paciente` — 8 chamadas em
        # routes/pacientes.py e routes/prontuario.py. Autorização inconsistente
        # entre portas que servem a mesma entidade É a falha: bastava escolher a
        # porta que não conferia e ler, por `?paciente_id=N`, o cartão de vacinas
        # e a trilha de acessos de qualquer cidadão do país.
        if paciente is not None and not pode_acessar_paciente(paciente, current_user):
            abort(403)

    cartao, acessos = [], []

    if paciente:
        cartao = _cartao_vacinas(paciente)
        acessos = _quem_acessou(paciente)
        # Abrir o portal de um paciente é, ele mesmo, um acesso a prontuário.
        registrar("pacientes", paciente.id, "read",
                  "Portal do Cidadão: cartão de vacinas e histórico de acessos",
                  commit=True)

    return render_template(
        "portal_cidadao/index.html",
        termo=termo,
        pacientes=pacientes,
        paciente=paciente,
        cartao=cartao,
        acessos=acessos,
    )


def _cartao_vacinas(paciente):
    """Doses aplicadas agrupadas por imunobiológico, com o esquema previsto."""
    aplicadas = (
        VacinaAplicada.query
        .filter_by(paciente_id=paciente.id)
        .order_by(VacinaAplicada.data_aplicacao.asc())
        .all()
    )

    catalogo = {v.id: v for v in Vacina.query.all()}
    por_vacina = {}

    for a in aplicadas:
        vac = catalogo.get(a.vacina_id)
        chave = a.vacina_id or a.nome_vacina or "—"
        entrada = por_vacina.setdefault(chave, {
            "nome": (vac.nome if vac else None) or a.nome_vacina or "Não identificada",
            "sigla": vac.sigla if vac else None,
            "previstas": vac.doses_total if vac else None,
            "doses": [],
        })
        entrada["doses"].append(a)

    # Vacinas do calendário ainda sem nenhuma dose registrada.
    registradas = {k for k in por_vacina}
    for vac in catalogo.values():
        if vac.id not in registradas and vac.ativo:
            por_vacina[vac.id] = {
                "nome": vac.nome,
                "sigla": vac.sigla,
                "previstas": vac.doses_total,
                "doses": [],
            }

    linhas = list(por_vacina.values())
    # Quem já tem dose aparece primeiro; depois ordem alfabética.
    linhas.sort(key=lambda e: (not e["doses"], e["nome"]))
    return linhas


def _registros_do_paciente(paciente):
    """(tabela, ids) de cada tabela clínica que pertence a este paciente.

    `AuditLog.registro_id` guarda a chave da TABELA AUDITADA, não a do paciente:
    para "prontuarios" é o id do prontuário, para "internacoes" o da internação.
    A consulta anterior comparava `registro_id == paciente.id` para todas elas,
    então a trilha do paciente #5 listava o acesso ao prontuário #5, à internação
    #5 e à triagem #5 — de OUTRAS pessoas. Numa tela cujo propósito é o direito
    do titular saber quem viu o seu prontuário (art. 9º da LGPD), isso é ao mesmo
    tempo dado errado e vazamento: expõe que houve acesso a registro alheio.

    Os ids saem do metadata, não de uma lista à mão: tabela clínica nova entra
    em `TABELAS_CLINICAS` e passa a ser resolvida sozinha.
    """
    from extensions import db

    por_tabela = {}
    for nome in TABELAS_CLINICAS:
        if nome == "pacientes":
            por_tabela[nome] = {paciente.id}
            continue

        tabela = db.metadata.tables.get(nome)
        if tabela is None or "paciente_id" not in tabela.c:
            continue
        ids = db.session.execute(
            db.select(tabela.c.id).where(tabela.c.paciente_id == paciente.id)
        ).scalars().all()
        if ids:
            por_tabela[nome] = set(ids)
    return por_tabela


def _quem_acessou(paciente, limite=100):
    """Trilha de acessos ao prontuário deste paciente."""
    from extensions import db

    por_tabela = _registros_do_paciente(paciente)
    if not por_tabela:
        return []

    condicoes = [
        db.and_(AuditLog.tabela == nome, AuditLog.registro_id.in_(ids))
        for nome, ids in por_tabela.items()
    ]

    logs = (
        AuditLog.query
        .filter(db.or_(*condicoes))
        .order_by(AuditLog.criado_em.desc())
        .limit(limite)
        .all()
    )

    ids = {l.usuario_id for l in logs if l.usuario_id}
    usuarios = (
        {u.id: u for u in User.query.filter(User.id.in_(ids)).all()} if ids else {}
    )

    return [
        {
            "quando": l.criado_em,
            "quem": (usuarios.get(l.usuario_id).nome if usuarios.get(l.usuario_id) else "Sistema"),
            "perfil": (usuarios.get(l.usuario_id).perfil if usuarios.get(l.usuario_id) else "—"),
            "acao": l.acao,
            "descricao": l.descricao,
            "ip": l.ip,
        }
        for l in logs
    ]
