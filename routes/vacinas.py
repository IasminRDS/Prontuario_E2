# -*- coding: utf-8 -*-
"""Vacinas — catálogo de imunobiológicos e cartão de vacinas do cidadão.

O módulo tinha 3 templates e nenhuma rota. O cartão consolidado também aparece
no Portal do Cidadão; aqui é a visão do profissional, que além de consultar
registra e corrige doses.
"""
from datetime import date, datetime

from flask import (
    Blueprint, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import or_

from extensions import db
from models.paciente import Paciente
from models.vacina import Vacina, VacinaAplicada
from utils.audit import registrar
from utils.rbac import requer_permissao

vacinas_bp = Blueprint("vacinas", __name__, url_prefix="/vacinas")


@vacinas_bp.get("/")
@login_required
@requer_permissao("clinical:read")
def index():
    """Busca o cidadão para abrir o cartão."""
    termo = (request.args.get("q") or "").strip()
    pacientes = []
    if termo:
        like = f"%{termo}%"
        pacientes = (
            Paciente.query
            .filter(Paciente.ativo.is_(True))
            .filter(or_(
                Paciente.nome.ilike(like),
                Paciente.cpf.ilike(like),
                Paciente.cns.ilike(like),
            ))
            .order_by(Paciente.nome)
            .limit(30)
            .all()
        )
        if len(pacientes) == 1:
            return redirect(url_for("vacinas.cartao", paciente_id=pacientes[0].id))

    return render_template("vacinas/index.html", pacientes=pacientes, q=termo)


@vacinas_bp.get("/cartao/<int:paciente_id>")
@login_required
@requer_permissao("clinical:read")
def cartao(paciente_id):
    """Cartão de vacinas: doses aplicadas x esquema previsto."""
    paciente = Paciente.query.get_or_404(paciente_id)

    aplicadas = (
        VacinaAplicada.query
        .filter_by(paciente_id=paciente.id)
        .order_by(VacinaAplicada.data_aplicacao.desc())
        .all()
    )
    catalogo = Vacina.query.filter_by(ativo=True).order_by(Vacina.nome).all()

    # Doses por imunobiológico, para o template mostrar o esquema.
    por_vacina = {}
    for a in aplicadas:
        por_vacina.setdefault(a.vacina_id, []).append(a)

    esquema = []
    for v in catalogo:
        doses = por_vacina.get(v.id, [])
        esquema.append({
            "vacina": v,
            "doses": doses,
            "aplicadas": len(doses),
            "previstas": v.doses_total or 1,
            "completo": len(doses) >= (v.doses_total or 1),
        })

    registrar("pacientes", paciente.id, "read",
              f"Cartão de vacinas consultado ({paciente.nome})", commit=True)

    return render_template(
        "vacinas/cartao.html",
        paciente=paciente,
        doses=aplicadas,
        catalogo=catalogo,
        esquema=esquema,
        hoje=date.today(),
    )


@vacinas_bp.post("/cartao/<int:paciente_id>/dose")
@login_required
@requer_permissao("clinical:write", "exam:write")
def registrar_dose(paciente_id):
    paciente = Paciente.query.get_or_404(paciente_id)

    vacina = db.session.get(Vacina, request.form.get("vacina_id", type=int) or 0)
    if not vacina:
        flash("Selecione o imunobiológico.", "warning")
        return redirect(url_for("vacinas.cartao", paciente_id=paciente.id))

    quando = (request.form.get("data_aplicacao") or "").strip()
    data_aplicacao = datetime.utcnow()
    if quando:
        try:
            data_aplicacao = datetime.fromisoformat(quando)
        except ValueError:
            flash("Data de aplicação inválida.", "warning")
            return redirect(url_for("vacinas.cartao", paciente_id=paciente.id))

    if data_aplicacao.date() > date.today():
        flash("Não é possível registrar dose com data futura.", "warning")
        return redirect(url_for("vacinas.cartao", paciente_id=paciente.id))

    aplicadas = VacinaAplicada.query.filter_by(
        paciente_id=paciente.id, vacina_id=vacina.id
    ).count()

    dose = VacinaAplicada(
        paciente_id=paciente.id,
        vacina_id=vacina.id,
        nome_vacina=vacina.nome,
        dose=(request.form.get("dose") or "").strip() or f"{aplicadas + 1}ª dose",
        data_aplicacao=data_aplicacao,
        unidade=(current_user.unidade.nome if current_user.unidade else None),
        profissional=current_user.nome,
        observacao=(request.form.get("observacao") or "").strip() or None,
    )
    db.session.add(dose)

    registrar("vacinas_aplicadas", paciente.id, "create",
              f"{dose.dose} de {vacina.nome} aplicada")
    db.session.commit()

    flash(f"{dose.dose} de {vacina.nome} registrada.", "success")
    return redirect(url_for("vacinas.cartao", paciente_id=paciente.id))


@vacinas_bp.post("/dose/<int:id>/excluir")
@login_required
@requer_permissao("clinical:write")
def excluir_dose(id):
    """Remove uma dose lançada por engano.

    Registro clínico não se apaga em silêncio: exige motivo, e o motivo fica na
    trilha de auditoria mesmo depois da linha sair da tabela.
    """
    dose = VacinaAplicada.query.get_or_404(id)
    paciente_id = dose.paciente_id

    motivo = (request.form.get("motivo") or "").strip()
    if not motivo:
        flash("Informe o motivo da exclusão — ele fica registrado na auditoria.",
              "warning")
        return redirect(url_for("vacinas.cartao", paciente_id=paciente_id))

    registrar("vacinas_aplicadas", paciente_id, "delete",
              f"Dose removida ({dose.nome_vacina} — {dose.dose}): {motivo}")
    db.session.delete(dose)
    db.session.commit()

    flash("Dose removida.", "info")
    return redirect(url_for("vacinas.cartao", paciente_id=paciente_id))


# =========================================================
# Catálogo de imunobiológicos
# =========================================================
@vacinas_bp.get("/catalogo")
@login_required
@requer_permissao("clinical:read")
def catalogo():
    termo = (request.args.get("q") or "").strip()

    query = Vacina.query
    if termo:
        like = f"%{termo}%"
        query = query.filter(or_(Vacina.nome.ilike(like), Vacina.sigla.ilike(like)))

    return render_template("vacinas/catalogo.html",
                           vacinas=query.order_by(Vacina.nome).all(), q=termo)


@vacinas_bp.route("/catalogo/nova", methods=["GET", "POST"])
@login_required
@requer_permissao("admin:full")
def nova_vacina():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        if not nome:
            flash("Informe o nome do imunobiológico.", "warning")
            return render_template("vacinas/vacina_form.html")

        if Vacina.query.filter(db.func.lower(Vacina.nome) == nome.lower()).first():
            flash(f"Já existe imunobiológico chamado {nome}.", "danger")
            return render_template("vacinas/vacina_form.html")

        v = Vacina(
            nome=nome,
            sigla=(request.form.get("sigla") or "").strip().upper() or None,
            doses_total=request.form.get("doses_total", type=int) or 1,
            intervalo_dias=request.form.get("intervalo_dias", type=int),
            fabricante=(request.form.get("fabricante") or "").strip() or None,
            lote=(request.form.get("lote") or "").strip() or None,
            ativo=True,
        )

        validade = (request.form.get("validade") or "").strip()
        if validade:
            try:
                v.validade = date.fromisoformat(validade)
            except ValueError:
                flash("Data de validade inválida.", "warning")
                return render_template("vacinas/vacina_form.html")

        db.session.add(v)
        db.session.flush()

        registrar("vacinas", v.id, "create", f"Imunobiológico cadastrado: {nome}")
        db.session.commit()

        flash("Imunobiológico cadastrado.", "success")
        return redirect(url_for("vacinas.catalogo"))

    return render_template("vacinas/vacina_form.html")
