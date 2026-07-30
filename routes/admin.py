from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models.user import User
from models.audit_log import AuditLog
from models.unidade_saude import UnidadeSaude
from database.db import db
from utils.security import admin_requerido
from utils.audit import audit_log, auditar_aqui
from datetime import datetime

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_requerido
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
def novo_usuario():
    unidades = (
        UnidadeSaude.query.filter_by(ativo=True).order_by(UnidadeSaude.nome).all()
    )
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.", "danger")
            return render_template(
                "admin/usuario_form.html", usuario=None, unidades=unidades
            )
        user = User(
            nome=request.form.get("nome", "").strip(),
            email=email,
            perfil=request.form.get("perfil", "recepcionista"),
            unidade_id=request.form.get("unidade_id") or None,
            ativo=True,
        )
        user.set_password(request.form.get("senha", "Mudar@123"))
        db.session.add(user)
        db.session.flush()
        auditar_aqui("users", "create")
        db.session.commit()
        flash(f"Usuário {user.nome} criado com sucesso!", "success")
        return redirect(url_for("admin.index"))
    return render_template("admin/usuario_form.html", usuario=None, unidades=unidades)


@admin_bp.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_requerido
def editar_usuario(id):
    user = User.query.get_or_404(id)
    unidades = Unidade.query.filter_by(ativo=True).order_by(Unidade.nome).all()
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
    return render_template("admin/usuario_form.html", usuario=user, unidades=unidades)


@admin_bp.route("/usuarios/<int:id>/toggle")
@login_required
@admin_requerido
def toggle_usuario(id):
    user = User.query.get_or_404(id)
    if user.id == current_user.id:
        flash("Você não pode desativar sua própria conta.", "warning")
        return redirect(url_for("admin.index"))
    user.ativo = not user.ativo
    acao = "activate" if user.ativo else "delete"
    auditar_aqui("users", acao)
    db.session.commit()
    flash(f'Usuário {"ativado" if user.ativo else "desativado"}.', "info")
    return redirect(url_for("admin.index"))


@admin_bp.route("/auditoria")
@login_required
@admin_requerido
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
