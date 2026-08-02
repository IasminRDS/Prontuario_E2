from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from utils.rbac import requer_permissao

pronto_socorro_bp = Blueprint("pronto_socorro", __name__, url_prefix="/pronto-socorro")

# memória local simples (MVP)
FILA_PS = []


@pronto_socorro_bp.get("/")
@login_required
def index():
    # ordena por prioridade (menor número = mais urgente) e depois hora
    ordem = sorted(FILA_PS, key=lambda x: (x["prioridade"], x["entrada_ts"]))
    return render_template("pronto_socorro/index.html", fila=ordem)


@pronto_socorro_bp.post("/novo")
@login_required
@requer_permissao("emergency:write")
def novo():
    nome = (request.form.get("nome") or "").strip()
    motivo = (request.form.get("motivo") or "").strip()
    prioridade = int(request.form.get("prioridade") or 3)

    if not nome:
        flash("Nome é obrigatório.", "warning")
        return redirect(url_for("pronto_socorro.index"))

    FILA_PS.append(
        {
            "id": len(FILA_PS) + 1,
            "nome": nome,
            "motivo": motivo or "N/I",
            "prioridade": prioridade,
            "entrada": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "entrada_ts": datetime.now().timestamp(),
            "status": "Aguardando",
        }
    )
    flash("Paciente adicionado ao Pronto-Socorro.", "success")
    return redirect(url_for("pronto_socorro.index"))


@pronto_socorro_bp.post("/chamar/<int:item_id>")
@login_required
@requer_permissao("emergency:write")
def chamar(item_id):
    for item in FILA_PS:
        if item["id"] == item_id:
            item["status"] = "Em atendimento"
            break
    flash("Paciente chamado.", "info")
    return redirect(url_for("pronto_socorro.index"))


@pronto_socorro_bp.post("/finalizar/<int:item_id>")
@login_required
@requer_permissao("emergency:write")
def finalizar(item_id):
    for item in FILA_PS:
        if item["id"] == item_id:
            item["status"] = "Finalizado"
            break
    flash("Atendimento finalizado.", "success")
    return redirect(url_for("pronto_socorro.index"))
