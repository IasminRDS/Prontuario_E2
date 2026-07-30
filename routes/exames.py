# -*- coding: utf-8 -*-
"""Exames — solicitação, coleta, resultado e catálogo de tipos.

Porte de `modules/exames` do backend NestJS (7 endpoints).

Antes deste módulo existir de verdade, as solicitações viviam numa lista de
módulo (`SOLICITACOES = []`): sumiam a cada restart, não eram compartilhadas
entre workers do Gunicorn e nunca tocavam os models `TipoExame`/`ExameSolicitado`,
que já estavam mapeados e sem uso.
"""
from datetime import datetime, timedelta

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from extensions import db
from models.exame import ExameSolicitado, TipoExame
from models.medico import Medico
from models.paciente import Paciente
from utils.audit import registrar
from utils.rbac import requer_permissao

exames_bp = Blueprint("exames", __name__, url_prefix="/exames")

STATUS = ("solicitado", "coletado", "concluido", "cancelado")
URGENCIAS = ("rotina", "prioritario", "urgente")
INTERPRETACOES = ("normal", "alterado", "critico", "inconclusivo")

DIAS_ATRASO = 7


def _medico_do_usuario():
    return Medico.query.filter_by(user_id=current_user.id).first()


def _agrupar_por_categoria(tipos):
    """Agrupa os tipos por categoria, como a tela de solicitação espera.

    Categoria vazia cai em "outros" — o template itera o dict e um None viraria
    um cabeçalho sem rótulo.
    """
    grupos = {}
    for t in tipos:
        grupos.setdefault(t.categoria or "outros", []).append(t)
    return dict(sorted(grupos.items()))



# =========================================================
# Listagens
# =========================================================
@exames_bp.get("/")
@login_required
@requer_permissao("exam:write", "clinical:read")
def index():
    termo = (request.args.get("q") or "").strip()
    status = (request.args.get("status") or "").strip()
    urgencia = (request.args.get("urgencia") or "").strip()
    pagina = request.args.get("pagina", type=int) or 1

    query = ExameSolicitado.query
    if status in STATUS:
        query = query.filter(ExameSolicitado.status == status)
    if urgencia in URGENCIAS:
        query = query.filter(ExameSolicitado.urgencia == urgencia)
    if termo:
        like = f"%{termo}%"
        query = (
            query.join(Paciente, ExameSolicitado.paciente_id == Paciente.id)
            .outerjoin(TipoExame, ExameSolicitado.tipo_exame_id == TipoExame.id)
            .filter(or_(
                Paciente.nome.ilike(like),
                Paciente.cpf.ilike(like),
                TipoExame.nome.ilike(like),
                TipoExame.codigo.ilike(like),
            ))
        )

    # Urgente primeiro; dentro da urgência, o mais antigo primeiro.
    ordem = db.case(
        {"urgente": 0, "prioritario": 1, "rotina": 2},
        value=ExameSolicitado.urgencia,
        else_=9,
    )
    paginacao = (
        query.order_by(ordem, ExameSolicitado.data_solicitacao.asc())
        .paginate(page=pagina, per_page=30, error_out=False)
    )

    return render_template(
        "exames/index.html",
        exames=paginacao.items,
        paginacao=paginacao,
        q=termo,
        status=status,
        urgencia=urgencia,
        status_possiveis=STATUS,
        urgencias=URGENCIAS,
        total_pendentes=ExameSolicitado.query.filter(
            ExameSolicitado.status.in_(("solicitado", "coletado"))
        ).count(),
    )


@exames_bp.get("/pendentes")
@login_required
@requer_permissao("exam:write")
def pendentes():
    """Fila de coleta e de resultado, com destaque para o que atrasou."""
    aguardando_coleta = (
        ExameSolicitado.query
        .filter_by(status="solicitado")
        .order_by(ExameSolicitado.data_solicitacao.asc())
        .all()
    )
    aguardando_resultado = (
        ExameSolicitado.query
        .filter_by(status="coletado")
        .order_by(ExameSolicitado.data_coleta.asc())
        .all()
    )

    return render_template(
        "exames/pendentes.html",
        aguardando_coleta=aguardando_coleta,
        aguardando_resultado=aguardando_resultado,
        corte_atraso=datetime.utcnow() - timedelta(days=DIAS_ATRASO),
        dias_atraso=DIAS_ATRASO,
    )


@exames_bp.get("/paciente/<int:paciente_id>")
@login_required
@requer_permissao("clinical:read")
def lista_paciente(paciente_id):
    paciente = Paciente.query.get_or_404(paciente_id)
    exames = (
        ExameSolicitado.query
        .filter_by(paciente_id=paciente.id)
        .order_by(ExameSolicitado.data_solicitacao.desc())
        .all()
    )

    registrar("exames_solicitados", paciente.id, "read",
              f"Exames do paciente consultados ({paciente.nome})", commit=True)

    return render_template("exames/lista.html", paciente=paciente, exames=exames)


# =========================================================
# Solicitação
# =========================================================
@exames_bp.route("/solicitar/<int:paciente_id>", methods=["GET", "POST"])
@login_required
@requer_permissao("exam:write")
def solicitar(paciente_id):
    """Solicita um ou vários exames de uma vez para o mesmo paciente."""
    paciente = Paciente.query.get_or_404(paciente_id)
    tipos = TipoExame.query.filter_by(ativo=True).order_by(TipoExame.nome).all()

    if request.method == "POST":
        ids = request.form.getlist("tipo_exame_ids")
        if not ids:
            flash("Selecione ao menos um exame.", "warning")
            return render_template("exames/solicitar.html", paciente=paciente,
                                   categorias=_agrupar_por_categoria(tipos),
                                   tipos=tipos, urgencias=URGENCIAS)

        urgencia = (request.form.get("urgencia") or "rotina").strip()
        if urgencia not in URGENCIAS:
            urgencia = "rotina"

        medico = _medico_do_usuario()
        indicacao = (request.form.get("indicacao_clinica") or "").strip() or None
        observacoes = (request.form.get("observacoes") or "").strip() or None

        criados = 0
        for bruto in ids:
            try:
                tipo_id = int(bruto)
            except (TypeError, ValueError):
                continue
            if not db.session.get(TipoExame, tipo_id):
                continue

            db.session.add(ExameSolicitado(
                paciente_id=paciente.id,
                tipo_exame_id=tipo_id,
                medico_id=medico.id if medico else None,
                unidade_id=current_user.unidade_id,
                status="solicitado",
                urgencia=urgencia,
                indicacao_clinica=indicacao,
                observacoes=observacoes,
                criado_por=current_user.id,
            ))
            criados += 1

        if not criados:
            flash("Nenhum exame válido selecionado.", "warning")
            return render_template("exames/solicitar.html", paciente=paciente,
                                   categorias=_agrupar_por_categoria(tipos),
                                   tipos=tipos, urgencias=URGENCIAS)

        registrar("exames_solicitados", paciente.id, "create",
                  f"{criados} exame(s) solicitado(s) — urgência {urgencia}")
        db.session.commit()

        flash(f"{criados} exame(s) solicitado(s).", "success")
        return redirect(url_for("exames.lista_paciente", paciente_id=paciente.id))

    return render_template("exames/solicitar.html", paciente=paciente,
                           categorias=_agrupar_por_categoria(tipos),
                           tipos=tipos, urgencias=URGENCIAS)


@exames_bp.post("/novo")
@login_required
@requer_permissao("exam:write")
def novo():
    """Solicitação rápida a partir do índice."""
    paciente_id = request.form.get("paciente_id", type=int)
    tipo_id = request.form.get("tipo_exame_id", type=int)

    if not paciente_id or not tipo_id:
        flash("Informe o paciente e o tipo de exame.", "warning")
        return redirect(url_for("exames.index"))
    if not db.session.get(Paciente, paciente_id) or not db.session.get(TipoExame, tipo_id):
        flash("Paciente ou tipo de exame inexistente.", "danger")
        return redirect(url_for("exames.index"))

    medico = _medico_do_usuario()
    urgencia = (request.form.get("urgencia") or "rotina").strip()

    e = ExameSolicitado(
        paciente_id=paciente_id,
        tipo_exame_id=tipo_id,
        medico_id=medico.id if medico else None,
        unidade_id=current_user.unidade_id,
        status="solicitado",
        urgencia=urgencia if urgencia in URGENCIAS else "rotina",
        criado_por=current_user.id,
    )
    db.session.add(e)
    db.session.flush()

    registrar("exames_solicitados", e.id, "create", "Exame solicitado")
    db.session.commit()

    flash("Exame solicitado.", "success")
    return redirect(url_for("exames.index"))


# =========================================================
# Coleta, resultado e cancelamento
# =========================================================
@exames_bp.post("/status/<int:exame_id>")
@login_required
@requer_permissao("exam:write")
def alterar_status(exame_id):
    e = ExameSolicitado.query.get_or_404(exame_id)
    novo_status = (request.form.get("status") or "").strip()

    if novo_status not in STATUS:
        flash("Status inválido.", "danger")
        return redirect(request.referrer or url_for("exames.index"))

    anterior = e.status
    e.status = novo_status

    # Marca o instante da transição, para o tempo de resposta ser mensurável.
    if novo_status == "coletado" and not e.data_coleta:
        e.data_coleta = datetime.utcnow()
    elif novo_status == "concluido" and not e.data_resultado:
        e.data_resultado = datetime.utcnow()

    registrar("exames_solicitados", e.id, "update",
              f"Status do exame: {anterior} → {novo_status}")
    db.session.commit()

    flash(f"Exame marcado como {novo_status}.", "success")
    return redirect(request.referrer or url_for("exames.index"))


@exames_bp.route("/<int:id>/resultado", methods=["GET", "POST"])
@login_required
@requer_permissao("exam:write")
def registrar_resultado(id):
    e = ExameSolicitado.query.get_or_404(id)

    if e.status == "cancelado":
        flash("Exame cancelado não recebe resultado.", "warning")
        return redirect(url_for("exames.lista_paciente", paciente_id=e.paciente_id))

    if request.method == "POST":
        texto = (request.form.get("resultado_texto") or "").strip()
        valor = (request.form.get("resultado_valor") or "").strip()

        if not texto and not valor:
            flash("Informe o resultado — em texto ou como valor.", "warning")
            return render_template("exames/resultado.html", exame=e,
                                   interpretacoes=INTERPRETACOES)

        interpretacao = (request.form.get("interpretacao") or "").strip()

        e.resultado_texto = texto or None
        e.resultado_valor = valor or None
        e.resultado_unidade = (request.form.get("resultado_unidade") or "").strip() or None
        e.valor_referencia = (request.form.get("valor_referencia") or "").strip() or None
        e.interpretacao = interpretacao if interpretacao in INTERPRETACOES else None
        e.status = "concluido"
        e.data_resultado = datetime.utcnow()
        if not e.data_coleta:
            e.data_coleta = e.data_solicitacao

        registrar("exames_solicitados", e.id, "update",
                  "Resultado registrado"
                  + (f" — {e.interpretacao}" if e.interpretacao else ""))
        db.session.commit()

        flash("Resultado registrado.", "success")
        return redirect(url_for("exames.lista_paciente", paciente_id=e.paciente_id))

    return render_template("exames/resultado.html", exame=e,
                           interpretacoes=INTERPRETACOES)


@exames_bp.post("/<int:id>/cancelar")
@login_required
@requer_permissao("exam:write")
def cancelar(id):
    e = ExameSolicitado.query.get_or_404(id)

    if e.status == "concluido":
        flash("Exame com resultado não pode ser cancelado.", "warning")
        return redirect(request.referrer or url_for("exames.index"))

    motivo = (request.form.get("motivo") or "").strip()
    e.status = "cancelado"
    if motivo:
        prefixo = f"{e.observacoes} | " if e.observacoes else ""
        e.observacoes = f"{prefixo}Cancelado: {motivo}"

    registrar("exames_solicitados", e.id, "update",
              f"Exame cancelado{f': {motivo}' if motivo else ''}")
    db.session.commit()

    flash("Exame cancelado.", "info")
    return redirect(request.referrer or url_for("exames.index"))


# =========================================================
# Catálogo de tipos de exame
# =========================================================
@exames_bp.get("/catalogo")
@login_required
@requer_permissao("exam:write", "clinical:read")
def catalogo():
    termo = (request.args.get("q") or "").strip()
    categoria = (request.args.get("categoria") or "").strip()

    query = TipoExame.query
    if termo:
        like = f"%{termo}%"
        query = query.filter(or_(
            TipoExame.nome.ilike(like), TipoExame.codigo.ilike(like)
        ))
    if categoria:
        query = query.filter(TipoExame.categoria == categoria)

    tipos = query.order_by(TipoExame.nome).all()
    categorias = sorted(
        v[0]
        for v in TipoExame.query.with_entities(TipoExame.categoria).distinct().all()
        if v[0]
    )

    return render_template("exames/catalogo.html", tipos=tipos, q=termo,
                           categoria=categoria, categorias=categorias)


@exames_bp.route("/catalogo/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("exam:write")
def novo_tipo():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        codigo = (request.form.get("codigo") or "").strip().upper()

        if not nome or not codigo:
            flash("Nome e código são obrigatórios.", "warning")
            return render_template("exames/tipo_form.html")

        if TipoExame.query.filter_by(codigo=codigo).first():
            flash(f"Já existe tipo de exame com o código {codigo}.", "danger")
            return render_template("exames/tipo_form.html")

        tipo = TipoExame(
            nome=nome,
            codigo=codigo,
            categoria=(request.form.get("categoria") or "").strip() or "laboratorial",
            instrucoes=(request.form.get("instrucoes") or "").strip() or None,
            ativo=True,
        )
        db.session.add(tipo)
        db.session.flush()

        registrar("tipos_exame", tipo.id, "create", f"Tipo de exame criado: {nome}")
        db.session.commit()

        flash("Tipo de exame cadastrado.", "success")
        return redirect(url_for("exames.catalogo"))

    return render_template("exames/tipo_form.html")
