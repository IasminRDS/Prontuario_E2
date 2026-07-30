from datetime import date, datetime

from flask import (
    Blueprint, abort, current_app, flash, jsonify, redirect, render_template,
    request, url_for,
)
from flask_login import login_required, current_user
from sqlalchemy import or_, and_

from database.db import db
from models.atendimento import Atendimento
from models.paciente import Paciente
from models.prontuario import Prontuario
from utils.security import validar_cpf, validar_cns, pode_acessar_paciente
from utils.audit import audit_log, auditar_aqui, registrar
from utils.rbac import requer_permissao

pacientes_bp = Blueprint("pacientes", __name__, url_prefix="/pacientes")


# =========================================================
# Config flags centralizadas (config.py)
# =========================================================
def _is_dev_mode() -> bool:
    return current_app.config.get("FEATURE_DEV_MODE", False)


def _rbac_strict() -> bool:
    return current_app.config.get("FEATURE_RBAC_STRICT", True)


def _allow_create_without_unit() -> bool:
    return current_app.config.get("FEATURE_ALLOW_CREATE_WITHOUT_UNIT", False)


def _bypass_scope() -> bool:
    return current_app.config.get("FEATURE_BYPASS_PACIENTE_SCOPE", False)


def _per_page() -> int:
    return int(current_app.config.get("PACIENTES_PER_PAGE", 20))


# =========================================================
# Helpers
# =========================================================
def _idade_anos(data_nascimento):
    if not data_nascimento:
        return None
    hoje = date.today()
    return hoje.year - data_nascimento.year - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))


def _query_pacientes_escopo():
    q = Paciente.query.filter_by(ativo=True)

    # DEV / bypass explícito
    if _is_dev_mode() or _bypass_scope():
        return q

    # Produção: RBAC estrito
    if current_user.perfil == "admin" or getattr(current_user, "nivel_acesso", "UNIDADE") == "ESTADO":
        return q

    nivel = getattr(current_user, "nivel_acesso", "UNIDADE")

    if nivel == "MUNICIPIO":
        user_ibge = getattr(current_user, "municipio_ibge", None)
        if user_ibge and hasattr(Paciente, "municipio_ibge"):
            return q.filter(Paciente.municipio_ibge == user_ibge)

        if current_user.unidade:
            return q.filter(
                Paciente.municipio == current_user.unidade.municipio,
                Paciente.uf == current_user.unidade.uf
            )
        return q.filter(Paciente.id == -1)

    if nivel == "REGIONAL":
        user_uf = getattr(current_user, "uf", None)
        if user_uf and hasattr(Paciente, "uf"):
            return q.filter(Paciente.uf == user_uf)
        return q.filter(Paciente.id == -1)

    if current_user.unidade:
        return q.filter(
            Paciente.municipio == current_user.unidade.municipio,
            Paciente.uf == current_user.unidade.uf
        )

    if _rbac_strict():
        return q.filter(Paciente.id == -1)
    return q


def _aplicar_filtros(query):
    termo = (request.args.get("q") or "").strip()
    filtro_sexo = (request.args.get("sexo") or "").strip().upper()
    filtro_idade_min = (request.args.get("idade_min") or "").strip()
    filtro_idade_max = (request.args.get("idade_max") or "").strip()
    filtro_municipio = (request.args.get("municipio") or "").strip()
    filtro_tem_cns = (request.args.get("tem_cns") or "").strip()

    if termo:
        like = f"%{termo}%"
        query = query.filter(or_(
            Paciente.nome.ilike(like),
            Paciente.nome_social.ilike(like),
            Paciente.cpf.ilike(like),
            Paciente.cns.ilike(like),
            Paciente.nome_mae.ilike(like),
        ))

    if filtro_sexo in ("M", "F"):
        query = query.filter(Paciente.sexo == filtro_sexo)

    if filtro_municipio:
        query = query.filter(Paciente.municipio.ilike(f"%{filtro_municipio}%"))

    if filtro_tem_cns == "1":
        query = query.filter(and_(Paciente.cns.isnot(None), Paciente.cns != ""))
    elif filtro_tem_cns == "0":
        query = query.filter(or_(Paciente.cns.is_(None), Paciente.cns == ""))

    hoje = date.today()
    if filtro_idade_min.isdigit():
        idade_min = int(filtro_idade_min)
        data_max_nasc = date(hoje.year - idade_min, hoje.month, hoje.day)
        query = query.filter(Paciente.data_nascimento <= data_max_nasc)

    if filtro_idade_max.isdigit():
        idade_max = int(filtro_idade_max)
        data_min_nasc = date(hoje.year - idade_max - 1, hoje.month, hoje.day)
        query = query.filter(Paciente.data_nascimento >= data_min_nasc)

    filtros = {
        "q": termo,
        "filtro_sexo": filtro_sexo,
        "filtro_idade_min": filtro_idade_min,
        "filtro_idade_max": filtro_idade_max,
        "filtro_municipio": filtro_municipio,
        "filtro_tem_cns": filtro_tem_cns,
        "tem_filtro": any([filtro_sexo, filtro_idade_min, filtro_idade_max, filtro_municipio, filtro_tem_cns]),
    }
    return query, filtros


# =========================================================
# INDEX HTML
# =========================================================
@pacientes_bp.get("/")
@login_required
def index():
    query = _query_pacientes_escopo()
    query, filtros = _aplicar_filtros(query)

    pacientes = query.order_by(Paciente.nome.asc()).paginate(
        page=request.args.get("page", 1, type=int),
        per_page=_per_page(),
        error_out=False
    )

    for p in pacientes.items:
        if not getattr(p, "nome_exibicao", None):
            p.nome_exibicao = p.nome_social or p.nome
        if getattr(p, "idade", None) is None:
            p.idade = _idade_anos(p.data_nascimento)

    auditar_aqui("pacientes", "read")
    return render_template("pacientes/listar.html", pacientes=pacientes, **filtros)


@pacientes_bp.get("/index")
@login_required
def index_alias():
    return index()


@pacientes_bp.get("/listar")
@login_required
def listar_pacientes():
    return index()


# =========================================================
# API JSON
# =========================================================
@pacientes_bp.get("/api")
@login_required
def listar_pacientes_api():
    query = _query_pacientes_escopo()
    query, filtros = _aplicar_filtros(query)
    itens = query.order_by(Paciente.nome.asc()).all()

    auditar_aqui("pacientes", "read")

    return jsonify([{
        "id": p.id,
        "nome": p.nome,
        "nome_social": p.nome_social,
        "cpf": p.cpf,
        "cns": p.cns,
        "data_nascimento": p.data_nascimento.isoformat() if p.data_nascimento else None,
        "sexo": p.sexo,
        "municipio": p.municipio,
        "uf": p.uf,
        "telefone": p.telefone,
        "ativo": p.ativo
    } for p in itens]), 200


# =========================================================
# Busca QR/código
# =========================================================
@pacientes_bp.get("/buscar-codigo")
@login_required
def buscar_codigo():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify({"encontrado": False, "erro": "Código vazio"}), 400

    limpo = q.replace(".", "").replace("-", "").replace("/", "").replace(" ", "")
    paciente = None

    if limpo.isdigit():
        paciente = Paciente.query.filter_by(id=int(limpo)).first()
    if not paciente:
        paciente = Paciente.query.filter_by(cns=limpo).first()
    if not paciente:
        paciente = Paciente.query.filter_by(cpf=limpo).first()

    if not paciente:
        return jsonify({"encontrado": False}), 200

    if _rbac_strict() and not (_is_dev_mode() or _bypass_scope()):
        if not pode_acessar_paciente(paciente, current_user):
            return jsonify({"encontrado": False, "erro": "Sem permissão"}), 403

    return jsonify({
        "encontrado": True,
        "paciente": {
            "id": paciente.id,
            "nome": paciente.nome_social or paciente.nome,
            "cns": paciente.cns,
            "cpf": paciente.cpf,
            "idade": _idade_anos(paciente.data_nascimento),
            "nascimento": paciente.data_nascimento.strftime("%d/%m/%Y") if paciente.data_nascimento else None,
            "sexo": paciente.sexo,
            "alergias": paciente.alergias
        }
    }), 200


# =========================================================
# Telas
# =========================================================
@pacientes_bp.get("/novo")
@login_required
def novo():
    return render_template("pacientes/novo.html")


@pacientes_bp.get("/qrscan")
@login_required
def qrscan():
    return render_template("pacientes/qrscan.html")


# =========================================================
# Telas HTML do paciente
# =========================================================
@pacientes_bp.get("/<int:id>/perfil")
@login_required
@requer_permissao("patient:read")
def perfil(id):
    """Sumário do paciente: dados, atendimentos e prontuários.

    Equivale ao `/pacientes/[id]` do frontend Next. Abrir esta tela é acesso a
    prontuário e por isso entra na trilha de auditoria.
    """
    paciente = Paciente.query.get_or_404(id)

    if _rbac_strict() and not (_is_dev_mode() or _bypass_scope()):
        if not pode_acessar_paciente(paciente, current_user):
            abort(403)

    atendimentos = (
        Atendimento.query
        .filter_by(paciente_id=paciente.id)
        .order_by(Atendimento.data_hora.desc())
        .limit(50)
        .all()
    )
    prontuarios = (
        Prontuario.query
        .filter_by(paciente_id=paciente.id)
        .order_by(Prontuario.criado_em.desc())
        .limit(50)
        .all()
    )

    registrar("pacientes", paciente.id, "read",
              f"Sumário do paciente aberto ({paciente.nome})", commit=True)

    return render_template(
        "pacientes/perfil.html",
        paciente=paciente,
        atendimentos=atendimentos,
        prontuarios=prontuarios,
    )


@pacientes_bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
@requer_permissao("patient:update")
def editar(id):
    paciente = Paciente.query.get_or_404(id)

    if _rbac_strict() and not (_is_dev_mode() or _bypass_scope()):
        if not pode_acessar_paciente(paciente, current_user):
            abort(403)

    if request.method == "POST":
        campos_texto = (
            "nome", "nome_social", "rg", "sexo", "raca_cor", "nome_mae", "nome_pai",
            "telefone", "telefone2", "email", "cep", "logradouro", "numero",
            "complemento", "bairro", "municipio", "uf", "tipo_sanguineo",
            "alergias", "observacoes",
        )

        cpf = _so_digitos(request.form.get("cpf"))
        cns = _so_digitos(request.form.get("cns"))

        if cpf and not validar_cpf(cpf):
            flash("CPF inválido.", "warning")
            return render_template("pacientes/form.html", paciente=paciente)
        if cns and not validar_cns(cns):
            flash("CNS inválido.", "warning")
            return render_template("pacientes/form.html", paciente=paciente)

        # Unicidade: outro paciente já com o mesmo CPF.
        if cpf:
            duplicado = Paciente.query.filter(
                Paciente.cpf == cpf, Paciente.id != paciente.id
            ).first()
            if duplicado:
                flash(f"Já existe paciente com este CPF: {duplicado.nome}.", "danger")
                return render_template("pacientes/form.html", paciente=paciente)

        alteracoes = []
        for campo in campos_texto:
            if campo not in request.form:
                continue
            novo = (request.form.get(campo) or "").strip() or None
            if campo == "uf" and novo:
                novo = novo.upper()
            if getattr(paciente, campo) != novo:
                alteracoes.append(campo)
                setattr(paciente, campo, novo)

        for campo, valor in (("cpf", cpf), ("cns", cns)):
            if getattr(paciente, campo) != (valor or None):
                alteracoes.append(campo)
                setattr(paciente, campo, valor or None)

        nascimento = (request.form.get("data_nascimento") or "").strip()
        if nascimento:
            try:
                nova_data = date.fromisoformat(nascimento)
            except ValueError:
                flash("Data de nascimento inválida.", "warning")
                return render_template("pacientes/form.html", paciente=paciente)
            if paciente.data_nascimento != nova_data:
                alteracoes.append("data_nascimento")
                paciente.data_nascimento = nova_data

        if alteracoes:
            paciente.atualizado_em = datetime.utcnow()
            registrar("pacientes", paciente.id, "update",
                      f"Campos alterados: {', '.join(sorted(set(alteracoes)))}")
            db.session.commit()
            flash("Cadastro atualizado.", "success")
        else:
            flash("Nenhuma alteração a salvar.", "info")

        return redirect(url_for("pacientes.perfil", id=paciente.id))

    return render_template("pacientes/form.html", paciente=paciente)


def _so_digitos(valor):
    return "".join(c for c in (valor or "") if c.isdigit()) or None


# =========================================================
# CRUD JSON
# =========================================================
@pacientes_bp.get("/<int:paciente_id>")
@login_required
def obter_paciente(paciente_id):
    p = Paciente.query.get_or_404(paciente_id)

    if _rbac_strict() and not (_is_dev_mode() or _bypass_scope()):
        if not pode_acessar_paciente(p, current_user):
            return jsonify({"erro": "Sem permissão para acessar este paciente"}), 403

    auditar_aqui("pacientes", "read")
    return jsonify({
        "id": p.id,
        "nome": p.nome,
        "nome_social": p.nome_social,
        "cpf": p.cpf,
        "cns": p.cns,
        "rg": p.rg,
        "data_nascimento": p.data_nascimento.isoformat() if p.data_nascimento else None,
        "sexo": p.sexo,
        "raca_cor": p.raca_cor,
        "nome_mae": p.nome_mae,
        "nome_pai": p.nome_pai,
        "telefone": p.telefone,
        "telefone2": p.telefone2,
        "email": p.email,
        "cep": p.cep,
        "logradouro": p.logradouro,
        "numero": p.numero,
        "complemento": p.complemento,
        "bairro": p.bairro,
        "municipio": p.municipio,
        "uf": p.uf,
        "municipio_ibge": getattr(p, "municipio_ibge", None),
        "tipo_sanguineo": p.tipo_sanguineo,
        "alergias": p.alergias,
        "observacoes": p.observacoes,
        "ativo": p.ativo,
        "criado_em": p.criado_em.isoformat() if p.criado_em else None,
        "atualizado_em": p.atualizado_em.isoformat() if p.atualizado_em else None,
    }), 200


@pacientes_bp.post("/")
@login_required
def criar_paciente():
    data = request.get_json(silent=True) or {}

    nome = (data.get("nome") or "").strip()
    cpf = (data.get("cpf") or "").strip().replace(".", "").replace("-", "")
    cns = (data.get("cns") or "").strip()
    data_nascimento = data.get("data_nascimento")
    sexo = data.get("sexo")

    # NOVAS VALIDAÇÕES PARA NÃO QUEBRAR O BANCO
    if not nome:
        return jsonify({"erro": "Nome é obrigatório"}), 400
    if not data_nascimento:
        return jsonify({"erro": "Data de nascimento é obrigatória"}), 400
    if not sexo:
        return jsonify({"erro": "Sexo é obrigatório"}), 400
    if cpf and not validar_cpf(cpf):
        return jsonify({"erro": "CPF inválido (11 dígitos)"}), 400
    if cns and not validar_cns(cns):
        return jsonify({"erro": "CNS inválido (15 dígitos)"}), 400

    if cpf and Paciente.query.filter_by(cpf=cpf).first():
        return jsonify({"erro": "CPF já cadastrado"}), 409
    if cns and Paciente.query.filter_by(cns=cns).first():
        return jsonify({"erro": "CNS já cadastrado"}), 409

    municipio = data.get("municipio")
    uf = data.get("uf")
    municipio_ibge = data.get("municipio_ibge")

    if current_user.perfil != "admin":
        if current_user.unidade:
            municipio = current_user.unidade.municipio
            uf = current_user.unidade.uf
            if not municipio_ibge:
                municipio_ibge = getattr(current_user, "municipio_ibge", None)
        elif not (_is_dev_mode() or _allow_create_without_unit()):
            return jsonify({"erro": "Usuário sem unidade vinculada"}), 403
        else:
            municipio = municipio or "N/I"
            uf = uf or "N/I"

    p = Paciente(
        nome=nome,
        nome_social=data.get("nome_social"),
        cns=cns or None,
        cpf=cpf or None,
        rg=data.get("rg"),
        data_nascimento=data_nascimento,
        sexo=sexo,
        raca_cor=data.get("raca_cor"),
        nome_mae=data.get("nome_mae"),
        nome_pai=data.get("nome_pai"),
        telefone=data.get("telefone"),
        telefone2=data.get("telefone2"),
        email=data.get("email"),
        cep=data.get("cep"),
        logradouro=data.get("logradouro"),
        numero=data.get("numero"),
        complemento=data.get("complemento"),
        bairro=data.get("bairro"),
        municipio=municipio,
        uf=uf,
        municipio_ibge=municipio_ibge if hasattr(Paciente, "municipio_ibge") else None,
        tipo_sanguineo=data.get("tipo_sanguineo"),
        alergias=data.get("alergias"),
        observacoes=data.get("observacoes"),
        criado_por=current_user.id,
        ativo=True
    )

    db.session.add(p)
    db.session.commit()

    auditar_aqui("pacientes", "create")
    return jsonify({"mensagem": "Paciente criado com sucesso", "id": p.id}), 201


@pacientes_bp.put("/<int:paciente_id>")
@login_required
def atualizar_paciente(paciente_id):
    p = Paciente.query.get_or_404(paciente_id)

    if _rbac_strict() and not (_is_dev_mode() or _bypass_scope()):
        if not pode_acessar_paciente(p, current_user):
            return jsonify({"erro": "Sem permissão para editar este paciente"}), 403

    data = request.get_json(silent=True) or {}

    novo_cpf = (data.get("cpf", p.cpf) or "").strip().replace(".", "").replace("-", "")
    novo_cns = (data.get("cns", p.cns) or "").strip()

    if novo_cpf and not validar_cpf(novo_cpf):
        return jsonify({"erro": "CPF inválido"}), 400
    if novo_cns and not validar_cns(novo_cns):
        return jsonify({"erro": "CNS inválido"}), 400

    cpf_dup = Paciente.query.filter(Paciente.cpf == novo_cpf, Paciente.id != p.id).first() if novo_cpf else None
    if cpf_dup:
        return jsonify({"erro": "CPF já utilizado por outro paciente"}), 409

    cns_dup = Paciente.query.filter(Paciente.cns == novo_cns, Paciente.id != p.id).first() if novo_cns else None
    if cns_dup:
        return jsonify({"erro": "CNS já utilizado por outro paciente"}), 409

    p.nome = data.get("nome", p.nome)
    p.nome_social = data.get("nome_social", p.nome_social)
    p.cpf = novo_cpf or None
    p.cns = novo_cns or None
    p.rg = data.get("rg", p.rg)
    p.data_nascimento = data.get("data_nascimento", p.data_nascimento)
    p.sexo = data.get("sexo", p.sexo)
    p.raca_cor = data.get("raca_cor", p.raca_cor)
    p.nome_mae = data.get("nome_mae", p.nome_mae)
    p.nome_pai = data.get("nome_pai", p.nome_pai)
    p.telefone = data.get("telefone", p.telefone)
    p.telefone2 = data.get("telefone2", p.telefone2)
    p.email = data.get("email", p.email)
    p.cep = data.get("cep", p.cep)
    p.logradouro = data.get("logradouro", p.logradouro)
    p.numero = data.get("numero", p.numero)
    p.complemento = data.get("complemento", p.complemento)
    p.bairro = data.get("bairro", p.bairro)
    p.tipo_sanguineo = data.get("tipo_sanguineo", p.tipo_sanguineo)
    p.alergias = data.get("alergias", p.alergias)
    p.observacoes = data.get("observacoes", p.observacoes)
    p.ativo = data.get("ativo", p.ativo)

    if current_user.perfil == "admin":
        p.municipio = data.get("municipio", p.municipio)
        p.uf = data.get("uf", p.uf)
        if hasattr(Paciente, "municipio_ibge"):
            p.municipio_ibge = data.get("municipio_ibge", getattr(p, "municipio_ibge", None))

    db.session.commit()
    auditar_aqui("pacientes", "update")
    return jsonify({"mensagem": "Paciente atualizado com sucesso"}), 200


@pacientes_bp.delete("/<int:paciente_id>")
@login_required
def desativar_paciente(paciente_id):
    p = Paciente.query.get_or_404(paciente_id)

    if current_user.perfil != "admin":
        return jsonify({"erro": "Apenas admin pode desativar paciente"}), 403

    p.ativo = False
    db.session.commit()
    auditar_aqui("pacientes", "delete")
    return jsonify({"mensagem": "Paciente desativado com sucesso"}), 200