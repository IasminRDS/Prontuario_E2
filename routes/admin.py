from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.user import User
from models.audit_log import AuditLog
from models.unidade_saude import UnidadeSaude
from database.db import db
from utils.rbac import requer_permissao
from utils.security import admin_requerido
from utils.rbac import SUPER_ADMIN, _normalizar, perfis_atribuiveis
from utils.audit import audit_log, auditar_aqui
from datetime import datetime

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_requerido
@requer_permissao("user:manage")
def index():
    usuarios = User.query.order_by(User.nome).all()
    total_ativos = sum(1 for u in usuarios if u.ativo)
    total_inativos = sum(1 for u in usuarios if not u.ativo)
    logs_recentes = AuditLog.query.order_by(AuditLog.criado_em.desc()).limit(20).all()
    return render_template(
        "admin/index.html",
        usuarios=usuarios,
        total_ativos=total_ativos,
        total_inativos=total_inativos,
        logs_recentes=logs_recentes,
    )


@admin_bp.route("/usuarios/novo", methods=["GET", "POST"])
@login_required
@admin_requerido
@requer_permissao("user:manage")
def novo_usuario():
    unidades = (
        UnidadeSaude.query.filter_by(ativo=True).order_by(UnidadeSaude.nome).all()
    )
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.", "danger")
            return render_template(
                "admin/usuario_form.html", usuario=None, unidades=unidades,
                perfis=perfis_atribuiveis(current_user.perfil), perfil_atual=None
            )
        senha = (request.form.get("senha") or "").strip()
        if len(senha) < 8:
            # Sem senha padrão fixa: 'Mudar@123' em todo cadastro é uma
            # credencial conhecida por qualquer um que leia o repositório.
            flash("Defina uma senha inicial de ao menos 8 caracteres.", "warning")
            return render_template(
                "admin/usuario_form.html", usuario=None, unidades=unidades,
                perfis=perfis_atribuiveis(current_user.perfil), perfil_atual=None
            )

        perfil = request.form.get("perfil", "recepcionista")
        unidade_id = request.form.get("unidade_id") or None

        # Usuário com nível de acesso UNIDADE (o padrão) e sem unidade vinculada
        # não enxerga registro clínico nenhum: o Row-Level Security compara
        # `unidade_id` com NULL, que nunca é verdadeiro. Antes do RLS isso
        # passava despercebido; agora é um cadastro nascido inutilizável.
        if not unidade_id and _normalizar(perfil) != SUPER_ADMIN:
            flash("Selecione a unidade do usuário: sem ela, ele não terá acesso "
                  "a nenhum registro clínico.", "warning")
            return render_template(
                "admin/usuario_form.html", usuario=None, unidades=unidades,
                perfis=perfis_atribuiveis(current_user.perfil), perfil_atual=None
            )

        user = User(
            nome=request.form.get("nome", "").strip(),
            email=email,
            perfil=perfil,
            unidade_id=unidade_id,
            ativo=True,
        )
        user.set_password(senha)
        db.session.add(user)
        db.session.flush()
        auditar_aqui("users", "create")
        db.session.commit()
        flash(f"Usuário {user.nome} criado com sucesso!", "success")
        return redirect(url_for("admin.index"))
    return render_template("admin/usuario_form.html", usuario=None, unidades=unidades,
                perfis=perfis_atribuiveis(current_user.perfil), perfil_atual=None)


@admin_bp.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_requerido
@requer_permissao("user:manage")
def editar_usuario(id):
    user = User.query.get_or_404(id)
    unidades = UnidadeSaude.query.filter_by(ativo=True).order_by(UnidadeSaude.nome).all()
    if request.method == "POST":
        user.nome = request.form.get("nome", "").strip()
        user.perfil = request.form.get("perfil", user.perfil)
        user.unidade_id = request.form.get("unidade_id") or None
        user.ativo = "ativo" in request.form
        nova_senha = request.form.get("senha", "").strip()
        if nova_senha:
            user.set_password(nova_senha)
        auditar_aqui("users", "update")
        db.session.commit()
        flash("Usuário atualizado!", "success")
        return redirect(url_for("admin.index"))
    return render_template("admin/usuario_form.html", usuario=user,
                           unidades=unidades,
                           perfis=perfis_atribuiveis(current_user.perfil),
                           perfil_atual=_normalizar(user.perfil))


# `toggle_usuario` vivia aqui e foi removido: `ativar_usuario` e
# `desativar_usuario` o substituíram — e o fizeram de propósito, como diz a
# docstring de `ativar_usuario`, para o clique dizer o que faz. Ele continuava
# registrado, respondendo em GET, sem tela nenhuma apontando para ele. Rota de
# mutação alcançável por GET e não referenciada é superfície sem dono.


@admin_bp.post("/usuarios/<int:id>/ativar")
@login_required
@admin_requerido
@requer_permissao("user:manage")
def ativar_usuario(id):
    """Reativa a conta. Explícito em vez de toggle: o clique diz o que faz."""
    user = User.query.get_or_404(id)
    if user.ativo:
        flash("A conta já está ativa.", "info")
        return redirect(url_for("admin.index"))

    user.ativo = True
    auditar_aqui("users", "activate", f"Conta reativada ({user.email})")
    db.session.commit()
    flash(f"Conta de {user.nome} reativada.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.post("/usuarios/<int:id>/desativar")
@login_required
@admin_requerido
@requer_permissao("user:manage")
def desativar_usuario(id):
    """Desativa a conta. Nunca a própria — evita o admin se trancar fora."""
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash("Você não pode desativar sua própria conta.", "warning")
        return redirect(url_for("admin.index"))
    if not user.ativo:
        flash("A conta já está inativa.", "info")
        return redirect(url_for("admin.index"))

    user.ativo = False
    auditar_aqui("users", "deactivate", f"Conta desativada ({user.email})")
    db.session.commit()
    flash(f"Conta de {user.nome} desativada.", "info")
    return redirect(url_for("admin.index"))


# Leitura da trilha é `audit:read`, e não gestão de usuário: são competências
# distintas, e o Gestor tem a primeira sem ter a segunda.
@admin_bp.route("/auditoria")
@login_required
@admin_requerido
@requer_permissao("audit:read")
def auditoria():
    page = request.args.get("page", 1, type=int)
    tabela = request.args.get("tabela", "")
    acao = request.args.get("acao", "")
    usuario = request.args.get("usuario", "")

    q = AuditLog.query
    if tabela:
        q = q.filter(AuditLog.tabela == tabela)
    if acao:
        q = q.filter(AuditLog.acao == acao)
    if usuario:
        u = User.query.filter(User.nome.ilike(f"%{usuario}%")).first()
        if u:
            q = q.filter(AuditLog.usuario_id == u.id)

    logs = q.order_by(AuditLog.criado_em.desc()).paginate(page=page, per_page=50)
    tabelas = db.session.query(AuditLog.tabela).distinct().all()
    return render_template(
        "admin/auditoria.html",
        logs=logs,
        tabelas=[t[0] for t in tabelas],
        filtro_tabela=tabela,
        filtro_acao=acao,
        filtro_usuario=usuario,
    )
