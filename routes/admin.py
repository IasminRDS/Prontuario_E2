from flask import (Blueprint, abort, flash, redirect, render_template, request,
                   url_for)
from flask_login import login_required, current_user
from models.user import User
from models.audit_log import AuditLog
from models.unidade_saude import UnidadeSaude
from database.db import db
from utils.rbac import requer_permissao
from utils.security import admin_requerido
from utils.rbac import (RECEPCAO, SUPER_ADMIN, _normalizar,
                        perfis_atribuiveis)
from utils.audit import auditar_aqui
from utils import territorio
from datetime import datetime

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/")
@login_required
@admin_requerido
@requer_permissao("user:manage")
def index():
    usuarios = User.query.order_by(User.nome).all()
    # O alcance territorial de cada conta, na listagem. A tela mostrava a
    # unidade de lotação e mais nada — e lotação não é alcance: um gestor
    # estadual lotado na UBS Central aparecia igualzinho ao recepcionista da
    # mesma UBS, que é justamente a diferença que interessa ver de relance.
    escopos = {u.id: territorio.descrever(u) for u in usuarios}
    total_ativos = sum(1 for u in usuarios if u.ativo)
    total_inativos = sum(1 for u in usuarios if not u.ativo)
    logs_recentes = AuditLog.query.order_by(AuditLog.criado_em.desc()).limit(20).all()
    return render_template(
        "admin/index.html",
        usuarios=usuarios,
        escopos=escopos,
        total_ativos=total_ativos,
        total_inativos=total_inativos,
        logs_recentes=logs_recentes,
    )


# --------------------------------------------------------------------------
# Gestão de contas é a porta pela qual se sai do próprio território.
#
# Duas metades da autorização moram nesta tela: o PERFIL, que diz o que a
# pessoa pode fazer, e o ESCOPO TERRITORIAL, que diz sobre quais registros. Até
# aqui só a primeira aparecia, e a segunda se editava com `UPDATE` no banco —
# o controle que a monografia apresenta como central não tinha tela.
#
# Abrir o escopo numa tela abre uma porta de escalação: um administrador de
# unidade criaria um usuário com alcance estadual e entraria com ele. As três
# verificações abaixo são a fechadura, e valem tanto na criação quanto na
# edição:
#
#   1. o perfil concedido tem de estar em `perfis_atribuiveis` — a regra já
#      existia e só era aplicada à LISTA da tela, nunca ao que chegava no POST;
#   2. o território concedido tem de caber no de quem concede
#      (`utils.territorio`);
#   3. não se edita quem não se poderia criar — sem isto, um administrador
#      trocaria a senha de um SuperAdmin e entraria como ele, sem nunca
#      precisar conceder perfil nenhum.
# --------------------------------------------------------------------------
def _escopo_de_quem_concede():
    """O escopo de quem está concedendo, pela MESMA função que o RLS usa.

    Ler o escopo de outro jeito aqui faria a tela autorizar concessões que o
    banco depois trataria de outra forma — divergência que não gera erro, só
    comportamento inexplicável meses depois.
    """
    from utils.rls import escopo_do_usuario

    return escopo_do_usuario(current_user)


def _concediveis():
    return {p for p, _ in perfis_atribuiveis(current_user.perfil)}


def _perfil_valido(enviado, atual=None):
    """O perfil que chegou no POST, se quem está logado pode concedê-lo."""
    enviado = _normalizar(enviado) or atual
    return enviado if enviado in _concediveis() else None


def _formulario(usuario, escopo):
    return render_template(
        "admin/usuario_form.html",
        usuario=usuario,
        perfis=perfis_atribuiveis(current_user.perfil),
        perfil_atual=_normalizar(usuario.perfil) if usuario else None,
        perfil_padrao=RECEPCAO,
        super_admin=SUPER_ADMIN,
        escopo_proprio=escopo,
        rotulo_do_escopo=territorio.descrever(current_user),
        **territorio.opcoes(escopo),
    )


@admin_bp.route("/usuarios/novo", methods=["GET", "POST"])
@login_required
@admin_requerido
@requer_permissao("user:manage")
def novo_usuario():
    escopo = _escopo_de_quem_concede()
    if request.method == "POST":
        # Os campos territoriais são lidos um a um, e não com `request.form`
        # inteiro, de propósito: `test_contrato_formularios` compara
        # estaticamente o que a tela envia com o que a rota lê, e desiste da
        # comparação quando vê o dicionário usado em atacado. Passar
        # `request.form` adiante desligaria o detector nesta tela — que é
        # justamente a que ganhou quatro campos novos.
        pretendido = {
            "unidade_id": request.form.get("unidade_id"),
            "municipio_ibge": request.form.get("municipio_ibge"),
            "regional_id": request.form.get("regional_id"),
            "uf": request.form.get("uf"),
        }
        nivel = request.form.get("nivel_acesso")

        email = request.form.get("email", "").strip().lower()
        if User.query.filter_by(email=email).first():
            flash("E-mail já cadastrado.", "danger")
            return _formulario(None, escopo)

        senha = (request.form.get("senha") or "").strip()
        if len(senha) < 8:
            # Sem senha padrão fixa: 'Mudar@123' em todo cadastro é uma
            # credencial conhecida por qualquer um que leia o repositório.
            flash("Defina uma senha inicial de ao menos 8 caracteres.", "warning")
            return _formulario(None, escopo)

        perfil = _perfil_valido(request.form.get("perfil"))
        if perfil is None:
            # A restrição vivia só no `{% for %}` da tela. Um POST montado à
            # mão com `perfil=SuperAdmin` passava direto — e SuperAdmin
            # atravessa todo o isolamento territorial pelo perfil, o que
            # tornaria decorativo qualquer cuidado com o escopo logo abaixo.
            flash("Perfil de acesso inválido ou fora do que você pode conceder.",
                  "danger")
            return _formulario(None, escopo)

        if perfil == SUPER_ADMIN:
            # Operador da plataforma atravessa o isolamento pelo PERFIL —
            # `escopo_do_usuario` decide por ele antes de olhar `nivel_acesso`.
            # Pedir escopo territorial aqui seria pedir um dado que nada lê.
            campos = dict(territorio.SEM_TERRITORIO)
        else:
            campos, erro = territorio.resolver(nivel, pretendido, escopo)
            if erro:
                flash(erro, "warning")
                return _formulario(None, escopo)

        user = User(nome=request.form.get("nome", "").strip(), email=email,
                    perfil=perfil, ativo=True, **campos)
        user.set_password(senha)
        db.session.add(user)
        db.session.flush()
        auditar_aqui("users", "create")
        db.session.commit()
        flash(f"Usuário {user.nome} criado com sucesso!", "success")
        return redirect(url_for("admin.index"))
    return _formulario(None, escopo)


@admin_bp.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_requerido
@requer_permissao("user:manage")
def editar_usuario(id):
    user = User.query.get_or_404(id)
    escopo = _escopo_de_quem_concede()

    # Quem não pode CRIAR um SuperAdmin também não pode editar um. Sem esta
    # linha a defesa do perfil seria contornável pelo caminho mais curto: abrir
    # o SuperAdmin existente, definir uma senha nova e entrar como ele — sem
    # precisar conceder perfil nenhum.
    if _normalizar(user.perfil) not in _concediveis():
        abort(403)
    # E o mesmo pelo território: administrador de unidade que editasse usuário
    # de outra unidade poderia trazê-lo para a sua, ou ler o que ele alcança
    # pela via de trocar-lhe a senha.
    #
    # Compara o ALCANCE do alvo, e não a lotação dele. A primeira versão desta
    # linha era `if user.unidade_id and not contido(...)`: quem não tem lotação
    # escapava da verificação inteira, e gestor estadual é exatamente esse caso
    # — alcance de UF, unidade nenhuma. Sem a guarda certa, bastava abrir o
    # cadastro e definir uma senha nova.
    if not territorio.contido(territorio.territorio_do_usuario(user), escopo):
        abort(403)

    if request.method == "POST":
        pretendido = {
            "unidade_id": request.form.get("unidade_id"),
            "municipio_ibge": request.form.get("municipio_ibge"),
            "regional_id": request.form.get("regional_id"),
            "uf": request.form.get("uf"),
        }
        nivel = request.form.get("nivel_acesso")

        perfil = _perfil_valido(request.form.get("perfil"), _normalizar(user.perfil))
        if perfil is None:
            flash("Perfil de acesso inválido ou fora do que você pode conceder.",
                  "danger")
            return _formulario(user, escopo)

        if perfil == SUPER_ADMIN:
            campos = dict(territorio.SEM_TERRITORIO)
        else:
            campos, erro = territorio.resolver(nivel, pretendido, escopo)
            if erro:
                flash(erro, "warning")
                return _formulario(user, escopo)

        user.nome = request.form.get("nome", "").strip()
        user.perfil = perfil
        for campo, valor in campos.items():
            setattr(user, campo, valor)
        user.ativo = "ativo" in request.form
        nova_senha = request.form.get("senha", "").strip()
        if nova_senha:
            user.set_password(nova_senha)
        auditar_aqui("users", "update")
        db.session.commit()
        flash("Usuário atualizado!", "success")
        return redirect(url_for("admin.index"))
    return _formulario(user, escopo)


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
