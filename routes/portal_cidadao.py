# -*- coding: utf-8 -*-
"""Portal do Cidadão — cartão de vacinas e transparência de acesso (LGPD).

Equivalente à página `/portal-cidadao` do frontend Next. O ponto central é o
direito do titular de saber QUEM acessou seu prontuário (art. 9º da LGPD): a
consulta lê a trilha de auditoria e mostra usuário, ação, data e IP.
"""
from flask import Blueprint, render_template, request
from flask_login import login_required

from models.audit_log import AuditLog
from models.paciente import Paciente
from models.user import User
from models.vacina import Vacina, VacinaAplicada
from utils.audit import registrar
from utils.rbac import requer_permissao

portal_cidadao_bp = Blueprint("portal_cidadao", __name__, url_prefix="/portal-cidadao")

# Tabelas cuja leitura conta como "acesso ao prontuário" do ponto de vista do titular.
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
            Paciente.query
            .filter(Paciente.ativo.is_(True))
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

    paciente = Paciente.query.get(paciente_id) if paciente_id else None
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


def _quem_acessou(paciente, limite=100):
    """Trilha de acessos ao prontuário deste paciente."""
    logs = (
        AuditLog.query
        .filter(AuditLog.tabela.in_(TABELAS_CLINICAS))
        .filter(AuditLog.registro_id == paciente.id)
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
