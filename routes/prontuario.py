from datetime import datetime

from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for,
)
from flask_login import login_required, current_user

from database.db import db
from models.prontuario import Prontuario
from models.paciente import Paciente
from models.medico import Medico
from utils.security import validar_cid10, pode_acessar_prontuario, pode_acessar_paciente
from utils.audit import auditar_aqui, log_auditoria, registrar
from utils.rbac import requer_permissao
from utils.numeros import decimal_de, inteiro_de
from utils.terminologias import descricao_cid

prontuario_bp = Blueprint("prontuario", __name__, url_prefix="/prontuarios")

# Campos SOAP + sinais vitais aceitos pelo formulário.
CAMPOS_TEXTO = ("subjetivo", "objetivo", "avaliacao", "plano",
                "prescricao", "encaminhamento", "pressao_arterial")
CAMPOS_NUM = ("temperatura", "saturacao_o2", "peso", "altura", "glicemia")
CAMPOS_INT = ("frequencia_cardiaca", "frequencia_respiratoria", "retorno_dias")


def _tem_vitais(p):
    return any(
        getattr(p, c) not in (None, "")
        for c in CAMPOS_NUM + CAMPOS_INT + ("pressao_arterial",)
    )


def _medico_do_usuario():
    return Medico.query.filter_by(user_id=current_user.id).first()


def _preencher(p, form):
    """Aplica o formulário no prontuário. Devolve a lista de erros."""
    erros = []

    for campo in CAMPOS_TEXTO:
        if campo in form:
            setattr(p, campo, (form.get(campo) or "").strip() or None)

    # `utils.numeros` e não conversão local: a mesma conversão estava escrita
    # aqui e em `routes/triagem.py` com comportamentos diferentes, e "38,4" era
    # aceito por esta rota e derrubava a triagem inteira.
    for campo in CAMPOS_NUM:
        if campo in form:
            try:
                setattr(p, campo, decimal_de(form.get(campo)))
            except ValueError:
                erros.append(f"{campo.replace('_', ' ')} deve ser numérico")

    for campo in CAMPOS_INT:
        if campo in form:
            try:
                setattr(p, campo, inteiro_de(form.get(campo)))
            except ValueError:
                erros.append(f"{campo.replace('_', ' ')} deve ser inteiro")

    for campo in ("cid_principal", "cid_secundario"):
        if campo not in form:
            continue
        cid = (form.get(campo) or "").strip().upper() or None
        if cid and not validar_cid10(cid):
            erros.append(f"{campo.replace('_', ' ')} não é um CID-10 válido")
        else:
            setattr(p, campo, cid)

    return erros

def to_dict(p):
    return {
        "id": p.id,
        "paciente_id": p.paciente_id,
        "atendimento_id": p.atendimento_id,
        "medico_id": p.medico_id,
        "unidade_id": p.unidade_id,
        "subjetivo": p.subjetivo,
        "objetivo": p.objetivo,
        "avaliacao": p.avaliacao,
        "plano": p.plano,
        "pressao_arterial": p.pressao_arterial,
        "temperatura": p.temperatura,
        "frequencia_cardiaca": p.frequencia_cardiaca,
        "frequencia_respiratoria": p.frequencia_respiratoria,
        "saturacao_o2": p.saturacao_o2,
        "peso": p.peso,
        "altura": p.altura,
        "glicemia": p.glicemia,
        "cid_principal": p.cid_principal,
        "cid_secundario": p.cid_secundario,
        "prescricao": p.prescricao,
        "encaminhamento": p.encaminhamento,
        "retorno_dias": p.retorno_dias,
        "assinado": p.assinado,
        "assinado_em": p.assinado_em.isoformat() if p.assinado_em else None,
        "criado_em": p.criado_em.isoformat() if p.criado_em else None,
        "atualizado_em": p.atualizado_em.isoformat() if p.atualizado_em else None,
    }


def _query_prontuario_escopo():
    q = Prontuario.query

    if current_user.perfil == "admin":
        return q

    if current_user.unidade_id:
        q = q.filter(Prontuario.unidade_id == current_user.unidade_id)
    else:
        q = q.filter(Prontuario.id == -1)

    return q


@prontuario_bp.route("/novo/<int:paciente_id>", methods=["GET", "POST"])
@login_required
@requer_permissao("clinical:write")
def novo(paciente_id):
    """Registro clínico em formato SOAP."""
    paciente = Paciente.query.get_or_404(paciente_id)
    if not pode_acessar_paciente(paciente, current_user):
        abort(403)

    if request.method == "POST":
        p = Prontuario(paciente_id=paciente.id)
        medico = _medico_do_usuario()
        p.medico_id = medico.id if medico else None
        p.unidade_id = current_user.unidade_id
        p.atendimento_id = request.form.get("atendimento_id", type=int)

        erros = _preencher(p, request.form)
        if erros:
            for e in erros:
                flash(e.capitalize() + ".", "warning")
            return render_template("prontuario/form.html", paciente=paciente,
                                   prontuario=p, edicao=False)

        db.session.add(p)
        db.session.flush()

        _gerar_notificacao_se_compulsorio(p)

        # O CID é diagnóstico: registra-se que houve, não qual.
        registrar("prontuarios", p.id, "create",
                  "Prontuário criado"
                  + (" — com CID registrado" if p.cid_principal else ""))
        db.session.commit()

        flash("Prontuário registrado.", "success")
        return redirect(url_for("prontuario.visualizar", id=p.id))

    return render_template("prontuario/form.html", paciente=paciente,
                           prontuario=None, edicao=False)


@prontuario_bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
@requer_permissao("clinical:write")
def editar(id):
    p = Prontuario.query.get_or_404(id)
    if not pode_acessar_prontuario(p, current_user):
        abort(403)

    # Prontuário assinado é documento fechado: nem o autor reescreve.
    if p.assinado:
        flash("Prontuário assinado não pode ser alterado. Registre uma nova evolução.",
              "warning")
        return redirect(url_for("prontuario.visualizar", id=p.id))

    if request.method == "POST":
        erros = _preencher(p, request.form)
        if erros:
            for e in erros:
                flash(e.capitalize() + ".", "warning")
            return render_template("prontuario/form.html", paciente=p.paciente,
                                   prontuario=p, edicao=True)

        p.atualizado_em = datetime.utcnow()
        _gerar_notificacao_se_compulsorio(p)

        registrar("prontuarios", p.id, "update", "Prontuário editado")
        db.session.commit()

        flash("Prontuário atualizado.", "success")
        return redirect(url_for("prontuario.visualizar", id=p.id))

    return render_template("prontuario/form.html", paciente=p.paciente,
                           prontuario=p, edicao=True)


@prontuario_bp.get("/<int:id>/ver")
@login_required
@requer_permissao("clinical:read")
def visualizar(id):
    p = Prontuario.query.get_or_404(id)
    if not pode_acessar_prontuario(p, current_user):
        abort(403)

    registrar("prontuarios", p.id, "read",
              f"Prontuário visualizado (paciente {p.paciente_id})", commit=True)

    return render_template(
        "prontuario/visualizar.html",
        prontuario=p,
        paciente=p.paciente,
        tem_vitais=_tem_vitais(p),
        cid_descricao=descricao_cid(p.cid_principal) if p.cid_principal else None,
    )


@prontuario_bp.get("/paciente/<int:paciente_id>")
@login_required
@requer_permissao("clinical:read")
def historico(paciente_id):
    """Histórico longitudinal — todos os prontuários do paciente."""
    paciente = Paciente.query.get_or_404(paciente_id)
    if not pode_acessar_paciente(paciente, current_user):
        abort(403)

    prontuarios = (
        Prontuario.query
        .filter_by(paciente_id=paciente.id)
        .order_by(Prontuario.criado_em.desc())
        .all()
    )

    registrar("prontuarios", paciente.id, "read",
              "Histórico clínico consultado", commit=True)

    return render_template("prontuario/historico.html",
                           paciente=paciente, prontuarios=prontuarios)


def _gerar_notificacao_se_compulsorio(p):
    """Cria notificação SINAN quando o CID lançado é de notificação obrigatória.

    É o gatilho que o repo1 tem no domínio clínico: o profissional não precisa
    saber quais agravos são notificáveis — o sistema deriva do CID.
    """
    from models.notificacao import NotificacaoCompulsoria, agravo_para_cid

    for cid in (p.cid_principal, p.cid_secundario):
        agravo = agravo_para_cid(cid)
        if not agravo:
            continue
        existe = NotificacaoCompulsoria.query.filter_by(
            prontuario_id=p.id, cid=cid.strip().upper()
        ).first()
        if existe:
            continue
        db.session.add(NotificacaoCompulsoria(
            paciente_id=p.paciente_id,
            prontuario_id=p.id,
            unidade_id=p.unidade_id,
            cid=cid.strip().upper(),
            agravo=agravo,
            status="pendente",
        ))
        break


@prontuario_bp.get("/")
@login_required
@requer_permissao("clinical:read")
def listar_prontuarios():
    """Índice de prontuários.

    A listagem tinha só `@login_required`: qualquer sessão autenticada — a
    recepção, inclusive — via o índice clínico inteiro. Prontuário exige
    `clinical:read`, que a recepção não tem.

    Devolve HTML para o navegador e JSON para quem pede JSON (`Accept:
    application/json` ou `?formato=json`). Antes respondia SEMPRE JSON, então o
    item "Prontuário" do menu jogava o operador numa parede de texto cru.
    """
    q = _query_prontuario_escopo()

    paciente_id = request.args.get("paciente_id", type=int)
    cid = (request.args.get("cid") or "").strip().upper()
    termo = (request.args.get("q") or "").strip()

    if paciente_id:
        q = q.filter(Prontuario.paciente_id == paciente_id)
    if cid:
        q = q.filter(
            (Prontuario.cid_principal == cid) | (Prontuario.cid_secundario == cid)
        )
    if termo:
        like = f"%{termo}%"
        q = q.join(Paciente, Prontuario.paciente_id == Paciente.id).filter(
            Paciente.nome.ilike(like)
            | Paciente.cpf.ilike(like)
            | Paciente.cns.ilike(like)
        )

    itens = q.order_by(Prontuario.criado_em.desc()).all()

    # `commit=True` aqui, e não só no ramo HTML abaixo: em rota de leitura não
    # existe transação de escrita para carregar o log, e a sessão é descartada
    # no fim da requisição. O commit vivia dentro do `if not quer_json`, então
    # quem consultasse a lista de prontuários em JSON — a mesma URL, com
    # `?formato=json` ou `Accept: application/json` — não deixava rastro nenhum.
    auditar_aqui("prontuarios", "list", commit=True)

    quer_json = (
        request.args.get("formato") == "json"
        or request.accept_mimetypes.best == "application/json"
    )
    if not quer_json:
        pacientes = {}
        ids = {p.paciente_id for p in itens}
        if ids:
            pacientes = {
                x.id: x for x in Paciente.query.filter(Paciente.id.in_(ids)).all()
            }
        return render_template(
            "prontuario/index.html",
            prontuarios=itens[:200],
            total=len(itens),
            pacientes=pacientes,
            termo=termo,
            cid=cid,
        )

    return (
        jsonify(
            [
                {
                    "id": p.id,
                    "paciente_id": p.paciente_id,
                    "atendimento_id": p.atendimento_id,
                    "medico_id": p.medico_id,
                    "unidade_id": p.unidade_id,
                    "subjetivo": p.subjetivo,
                    "objetivo": p.objetivo,
                    "avaliacao": p.avaliacao,
                    "plano": p.plano,
                    "cid_principal": p.cid_principal,
                    "cid_secundario": p.cid_secundario,
                    "assinado": p.assinado,
                    "assinado_em": p.assinado_em.isoformat() if p.assinado_em else None,
                    "criado_em": p.criado_em.isoformat() if p.criado_em else None,
                }
                for p in itens
            ]
        ),
        200,
    )


@prontuario_bp.get("/<int:prontuario_id>")
@login_required
@log_auditoria("prontuarios", "view")
def obter_prontuario(prontuario_id):
    p = Prontuario.query.get_or_404(prontuario_id)
    if not pode_acessar_prontuario(p, current_user):
        return jsonify({"erro": "Sem permissão"}), 403

    return jsonify(to_dict(p)), 200


@prontuario_bp.post("/")
@login_required
@requer_permissao("clinical:write")
def criar_prontuario():
    data = request.get_json(silent=True) or {}

    paciente_id = data.get("paciente_id")
    if not paciente_id:
        return jsonify({"erro": "paciente_id é obrigatório"}), 400

    paciente = Paciente.query.get(paciente_id)
    if not paciente:
        return jsonify({"erro": "Paciente não encontrado"}), 404

    if not pode_acessar_paciente(paciente, current_user):
        return (
            jsonify({"erro": "Sem permissão para criar prontuário para este paciente"}),
            403,
        )

    cid_principal = (data.get("cid_principal") or "").strip().upper()
    cid_secundario = (data.get("cid_secundario") or "").strip().upper()

    if cid_principal and not validar_cid10(cid_principal):
        return jsonify({"erro": "CID principal inválido"}), 400
    if cid_secundario and not validar_cid10(cid_secundario):
        return jsonify({"erro": "CID secundário inválido"}), 400

    medico_id = data.get("medico_id")
    if current_user.perfil == "medico":
        # tenta vincular automaticamente ao medico do usuário logado
        m = Medico.query.filter_by(user_id=current_user.id).first()
        if m:
            medico_id = m.id

    novo = Prontuario(
        paciente_id=paciente_id,
        atendimento_id=data.get("atendimento_id"),
        medico_id=medico_id,
        unidade_id=current_user.unidade_id,  # trava na unidade do usuário
        subjetivo=data.get("subjetivo"),
        objetivo=data.get("objetivo"),
        avaliacao=data.get("avaliacao"),
        plano=data.get("plano"),
        pressao_arterial=data.get("pressao_arterial"),
        temperatura=data.get("temperatura"),
        frequencia_cardiaca=data.get("frequencia_cardiaca"),
        frequencia_respiratoria=data.get("frequencia_respiratoria"),
        saturacao_o2=data.get("saturacao_o2"),
        peso=data.get("peso"),
        altura=data.get("altura"),
        glicemia=data.get("glicemia"),
        cid_principal=cid_principal or None,
        cid_secundario=cid_secundario or None,
        prescricao=data.get("prescricao"),
        encaminhamento=data.get("encaminhamento"),
        retorno_dias=data.get("retorno_dias"),
    )

    db.session.add(novo)
    # `flush` e não `commit`: o id fica disponível para a auditoria sem fechar a
    # transação, então o evento e a escrita persistem juntos ou não persistem.
    db.session.flush()
    registrar("prontuarios", novo.id, "create",
              f"Prontuário criado via {request.endpoint}")
    db.session.commit()

    return jsonify({"mensagem": "Prontuário criado com sucesso", "id": novo.id}), 201


@prontuario_bp.put("/<int:prontuario_id>")
@login_required
@requer_permissao("clinical:write")
def atualizar_prontuario(prontuario_id):
    p = Prontuario.query.get_or_404(prontuario_id)

    if not pode_acessar_prontuario(p, current_user):
        return jsonify({"erro": "Sem permissão para editar este prontuário"}), 403

    if p.assinado and current_user.perfil != "admin":
        return jsonify({"erro": "Prontuário assinado não pode ser editado"}), 409

    data = request.get_json(silent=True) or {}

    cid_principal = (data.get("cid_principal", p.cid_principal) or "").strip().upper()
    cid_secundario = (
        (data.get("cid_secundario", p.cid_secundario) or "").strip().upper()
    )

    if cid_principal and not validar_cid10(cid_principal):
        return jsonify({"erro": "CID principal inválido"}), 400
    if cid_secundario and not validar_cid10(cid_secundario):
        return jsonify({"erro": "CID secundário inválido"}), 400

    p.subjetivo = data.get("subjetivo", p.subjetivo)
    p.objetivo = data.get("objetivo", p.objetivo)
    p.avaliacao = data.get("avaliacao", p.avaliacao)
    p.plano = data.get("plano", p.plano)
    p.pressao_arterial = data.get("pressao_arterial", p.pressao_arterial)
    p.temperatura = data.get("temperatura", p.temperatura)
    p.frequencia_cardiaca = data.get("frequencia_cardiaca", p.frequencia_cardiaca)
    p.frequencia_respiratoria = data.get(
        "frequencia_respiratoria", p.frequencia_respiratoria
    )
    p.saturacao_o2 = data.get("saturacao_o2", p.saturacao_o2)
    p.peso = data.get("peso", p.peso)
    p.altura = data.get("altura", p.altura)
    p.glicemia = data.get("glicemia", p.glicemia)
    p.cid_principal = cid_principal or None
    p.cid_secundario = cid_secundario or None
    p.prescricao = data.get("prescricao", p.prescricao)
    p.encaminhamento = data.get("encaminhamento", p.encaminhamento)
    p.retorno_dias = data.get("retorno_dias", p.retorno_dias)

    auditar_aqui("prontuarios", "update")
    db.session.commit()

    return jsonify({"mensagem": "Prontuário atualizado com sucesso"}), 200


@prontuario_bp.post("/<int:prontuario_id>/assinar")
@login_required
@requer_permissao("clinical:write")
def assinar_prontuario(prontuario_id):
    p = Prontuario.query.get_or_404(prontuario_id)

    if not pode_acessar_prontuario(p, current_user):
        return jsonify({"erro": "Sem permissão para assinar este prontuário"}), 403

    if current_user.perfil not in ("medico", "admin"):
        return jsonify({"erro": "Apenas médico/admin pode assinar prontuário"}), 403

    if p.assinado:
        return jsonify({"mensagem": "Prontuário já estava assinado"}), 200

    p.assinar()
    auditar_aqui("prontuarios", "sign")
    db.session.commit()

    return jsonify({"mensagem": "Prontuário assinado com sucesso"}), 200


@prontuario_bp.delete("/<int:prontuario_id>")
@login_required
@requer_permissao("admin:full")
def excluir_prontuario(prontuario_id):
    if current_user.perfil != "admin":
        return jsonify({"erro": "Apenas admin pode excluir prontuário"}), 403

    p = Prontuario.query.get_or_404(prontuario_id)
    # Auditar ANTES do delete: depois dele o objeto já não tem o que descrever, e
    # exclusão de prontuário sem rastro é justamente o que não pode acontecer.
    auditar_aqui("prontuarios", "delete",
                 f"Prontuário {prontuario_id} do paciente {p.paciente_id} excluído")
    db.session.delete(p)
    db.session.commit()

    return jsonify({"mensagem": "Prontuário excluído com sucesso"}), 200
