from datetime import datetime

from flask import (
    Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for,
)
from flask_login import login_required, current_user
from sqlalchemy import func
from database.db import db
from models.cirurgia import Cirurgia
from models.internacao import EvolucaoInternacao, Internacao, Leito, Setor
from models.medico import Medico
from models.paciente import Paciente
from models.prescricao_hospitalar import PrescricaoHospitalar
from models.unidade import Unidade
from utils.audit import registrar
from utils.rbac import requer_permissao

internacao_bp = Blueprint("internacao", __name__, url_prefix="/internacao")

TIPOS_ALTA = ("melhorado", "curado", "transferencia", "evasao", "obito", "a_pedido")

STATUS_LEITO_LIVRE = "livre"
STATUS_LEITO_OCUPADO = "ocupado"
STATUS_LEITO_HIGIENIZACAO = "em_higienizacao"

STATUS_LEITO = (
    STATUS_LEITO_LIVRE,
    STATUS_LEITO_OCUPADO,
    "reservado",
    STATUS_LEITO_HIGIENIZACAO,
    "interditado",
    "bloqueado",
)
TIPOS_LEITO = ("comum", "isolamento", "uti")


@internacao_bp.route("/leitos", methods=["GET"])
@login_required
def leitos():
    try:
        unidades = Unidade.query.order_by(Unidade.nome.asc()).all()
    except Exception:
        unidades = []

    try:
        setores = Setor.query.order_by(Setor.nome.asc()).all()
    except Exception:
        setores = []

    return render_template("internacao/leitos.html", setores=setores, unidades=unidades)


# =========================================================
# Painel e ficha de internação
# =========================================================
@internacao_bp.get("/")
@login_required
@requer_permissao("internment:write", "clinical:read")
def painel():
    """Mapa de leitos por setor + lista de internações ativas."""
    setores = Setor.query.filter_by(ativo=True).order_by(Setor.nome).all()

    internacoes_ativas = (
        Internacao.query
        .filter_by(status="ativa")
        .order_by(Internacao.data_entrada.desc())
        .all()
    )

    total = Leito.query.filter_by(ativo=True).count()
    ocupados = Leito.query.filter_by(ativo=True, status=STATUS_LEITO_OCUPADO).count()
    livres = Leito.query.filter_by(ativo=True, status=STATUS_LEITO_LIVRE).count()
    higieniz = Leito.query.filter_by(ativo=True, status=STATUS_LEITO_HIGIENIZACAO).count()

    return render_template(
        "internacao/painel.html",
        setores=setores,
        internacoes_ativas=internacoes_ativas,
        total=total,
        ocupados=ocupados,
        livres=livres,
        higieniz=higieniz,
    )


@internacao_bp.get("/<int:id>")
@login_required
@requer_permissao("internment:write", "clinical:read")
def visualizar(id):
    """Ficha da internação: evoluções, prescrições e cirurgias."""
    intern = Internacao.query.get_or_404(id)

    evolucoes = (
        EvolucaoInternacao.query
        .filter_by(internacao_id=intern.id)
        .order_by(EvolucaoInternacao.criado_em.desc())
        .all()
    )
    prescricoes = (
        PrescricaoHospitalar.query
        .filter_by(internacao_id=intern.id)
        .order_by(PrescricaoHospitalar.criado_em.desc())
        .all()
    )
    cirurgias = (
        Cirurgia.query
        .filter_by(internacao_id=intern.id)
        .order_by(Cirurgia.data_agendada.desc())
        .all()
    )

    registrar("internacoes", intern.id, "read",
              f"Ficha de internação aberta (paciente {intern.paciente_id})", commit=True)

    return render_template(
        "internacao/visualizar.html",
        intern=intern,
        evolucoes=evolucoes,
        prescricoes=prescricoes,
        cirurgias=cirurgias,
    )


@internacao_bp.route("/nova", methods=["GET", "POST"])
@internacao_bp.route("/nova/<int:paciente_id>", methods=["GET", "POST"])
@login_required
@requer_permissao("internment:write")
def nova(paciente_id=None):
    pacientes = Paciente.query.filter_by(ativo=True).order_by(Paciente.nome).all()
    medicos = Medico.query.all()
    # Só leitos livres podem receber internação.
    leitos_livres = (
        Leito.query
        .filter_by(ativo=True, status=STATUS_LEITO_LIVRE)
        .order_by(Leito.numero)
        .all()
    )

    if request.method == "POST":
        leito = Leito.query.get(request.form.get("leito_id", type=int) or 0)
        paciente = Paciente.query.get(request.form.get("paciente_id", type=int) or 0)
        motivo = (request.form.get("motivo") or "").strip()

        if not paciente:
            flash("Selecione o paciente.", "warning")
        elif not leito:
            flash("Selecione o leito.", "warning")
        elif leito.status != STATUS_LEITO_LIVRE:
            # Corrida entre dois operadores no mesmo leito.
            flash(f"O leito {leito.numero} não está mais livre.", "danger")
        elif not motivo:
            flash("Informe o motivo da internação.", "warning")
        else:
            prevista = (request.form.get("data_prevista_alta") or "").strip()
            data_prevista = None
            if prevista:
                try:
                    data_prevista = datetime.fromisoformat(prevista)
                except ValueError:
                    flash("Data prevista de alta inválida.", "warning")
                    return render_template(
                        "internacao/form.html", pacientes=pacientes, medicos=medicos,
                        leitos=leitos_livres, paciente_sel=paciente,
                    )

            intern = Internacao(
                paciente_id=paciente.id,
                leito_id=leito.id,
                medico_id=request.form.get("medico_id", type=int),
                unidade_id=current_user.unidade_id,
                criado_por=current_user.id,
                tipo=(request.form.get("tipo") or "clinica"),
                motivo=motivo,
                hipotese_diag=(request.form.get("hipotese_diag") or "").strip() or None,
                cid_principal=(request.form.get("cid_principal") or "").strip().upper() or None,
                data_prevista_alta=data_prevista,
                aih_numero=(request.form.get("aih_numero") or "").strip() or None,
                observacoes=(request.form.get("observacoes") or "").strip() or None,
                status="ativa",
            )
            db.session.add(intern)

            # Ocupar o leito faz parte da MESMA transação: nunca fica internação
            # sem leito ocupado, nem leito ocupado sem internação.
            leito.status = STATUS_LEITO_OCUPADO
            db.session.flush()

            registrar("internacoes", intern.id, "create",
                      f"Internação de {paciente.nome} no leito {leito.numero}")
            db.session.commit()

            flash(f"{paciente.nome} internado no leito {leito.numero}.", "success")
            return redirect(url_for("internacao.visualizar", id=intern.id))

    return render_template(
        "internacao/form.html",
        pacientes=pacientes,
        medicos=medicos,
        leitos=leitos_livres,
        paciente_sel=Paciente.query.get(paciente_id) if paciente_id else None,
    )


@internacao_bp.route("/<int:id>/evolucao", methods=["GET", "POST"])
@login_required
@requer_permissao("internment:write")
def nova_evolucao(id):
    intern = Internacao.query.get_or_404(id)

    if intern.status != "ativa":
        flash("Internação encerrada não recebe novas evoluções.", "warning")
        return redirect(url_for("internacao.visualizar", id=intern.id))

    if request.method == "POST":
        ev = EvolucaoInternacao(
            internacao_id=intern.id,
            profissional_id=current_user.id,
            tipo=(request.form.get("tipo") or "medica"),
            pressao_arterial=(request.form.get("pressao_arterial") or "").strip() or None,
            subjetivo=(request.form.get("subjetivo") or "").strip() or None,
            objetivo=(request.form.get("objetivo") or "").strip() or None,
            avaliacao=(request.form.get("avaliacao") or "").strip() or None,
            plano=(request.form.get("plano") or "").strip() or None,
        )

        erros = []
        for campo, conv in (
            ("temperatura", float), ("saturacao_o2", float),
            ("frequencia_cardiaca", int), ("frequencia_respiratoria", int),
            ("diurese_ml", int), ("balanco_hidrico", int),
        ):
            bruto = (request.form.get(campo) or "").strip().replace(",", ".")
            if not bruto:
                continue
            try:
                setattr(ev, campo, conv(bruto))
            except ValueError:
                erros.append(campo.replace("_", " "))

        if erros:
            flash(f"Valor inválido em: {', '.join(erros)}.", "warning")
            return render_template("internacao/evolucao_form.html", intern=intern)

        db.session.add(ev)
        registrar("internacoes", intern.id, "create",
                  f"Evolução {ev.tipo} registrada")
        db.session.commit()

        flash("Evolução registrada.", "success")
        return redirect(url_for("internacao.visualizar", id=intern.id))

    return render_template("internacao/evolucao_form.html", intern=intern)


@internacao_bp.route("/<int:id>/alta", methods=["GET", "POST"])
@login_required
@requer_permissao("internment:write")
def alta(id):
    intern = Internacao.query.get_or_404(id)

    if intern.status != "ativa":
        flash("Esta internação já foi encerrada.", "info")
        return redirect(url_for("internacao.visualizar", id=intern.id))

    if request.method == "POST":
        tipo_alta = (request.form.get("tipo_alta") or "").strip()
        sumario = (request.form.get("sumario_alta") or "").strip()

        if tipo_alta not in TIPOS_ALTA:
            flash("Selecione o tipo de alta.", "warning")
            return render_template("internacao/alta_form.html", intern=intern,
                                   tipos_alta=TIPOS_ALTA)
        if not sumario:
            flash("O sumário de alta é obrigatório — é o documento que fica no prontuário.",
                  "warning")
            return render_template("internacao/alta_form.html", intern=intern,
                                   tipos_alta=TIPOS_ALTA)

        intern.status = "alta"
        intern.tipo_alta = tipo_alta
        intern.sumario_alta = sumario
        intern.cid_alta = (request.form.get("cid_alta") or "").strip().upper() or None
        intern.data_alta = datetime.utcnow()

        # Leito não volta direto para "livre": passa por higienização.
        if intern.leito:
            intern.leito.status = STATUS_LEITO_HIGIENIZACAO

        registrar("internacoes", intern.id, "update",
                  f"Alta registrada ({tipo_alta}) — leito {intern.leito.numero if intern.leito else '—'} "
                  f"liberado para higienização")
        db.session.commit()

        flash("Alta registrada. O leito foi para higienização.", "success")
        return redirect(url_for("internacao.visualizar", id=intern.id))

    return render_template("internacao/alta_form.html", intern=intern,
                           tipos_alta=TIPOS_ALTA)


@internacao_bp.route("/setores/novo", methods=["GET", "POST"])
@login_required
@requer_permissao("internment:write")
def novo_setor():
    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        if not nome:
            flash("Informe o nome do setor.", "warning")
            return render_template("internacao/setor_form.html")

        setor = Setor(
            nome=nome,
            sigla=(request.form.get("sigla") or "").strip().upper() or None,
            tipo=(request.form.get("tipo") or "enfermaria"),
            andar=(request.form.get("andar") or "").strip() or None,
            responsavel=(request.form.get("responsavel") or "").strip() or None,
            ativo=True,
        )
        db.session.add(setor)
        db.session.flush()

        # Cria os leitos do setor de uma vez, numerados pela sigla.
        qtd = request.form.get("qtd_leitos", type=int) or 0
        tipo_leito = (request.form.get("tipo_leito") or "comum").strip()
        prefixo = setor.sigla or nome[:3].upper()
        for i in range(1, min(qtd, 200) + 1):
            db.session.add(Leito(
                setor_id=setor.id,
                unidade_id=current_user.unidade_id,
                numero=f"{prefixo}-{i:02d}",
                tipo=tipo_leito,
                status=STATUS_LEITO_LIVRE,
                ativo=True,
            ))

        registrar("setores", setor.id, "create",
                  f"Setor {nome} criado com {min(qtd, 200)} leito(s)")
        db.session.commit()

        flash(f"Setor {nome} criado com {min(qtd, 200)} leito(s).", "success")
        return redirect(url_for("internacao.leitos"))

    return render_template("internacao/setor_form.html")


@internacao_bp.route("/api/leitos", methods=["GET"])
@login_required
def api_listar_leitos():
    """Lista os leitos ativos, opcionalmente de um setor.

    A versão anterior lia `PRAGMA table_info(leitos)` para descobrir quais
    colunas existiam e montar o SELECT como string. Além de só funcionar em
    SQLite, era introspecção desnecessária: o model `Leito` já declara as
    colunas, e o ORM gera o SQL certo para qualquer dialeto.
    """
    setor_id = request.args.get("setor_id", type=int)

    # outerjoin: leito sem setor ainda aparece na lista.
    query = (
        db.session.query(Leito, Setor.nome)
        .outerjoin(Setor, Leito.setor_id == Setor.id)
        .filter(Leito.ativo.is_(True))
    )
    if setor_id:
        query = query.filter(Leito.setor_id == setor_id)

    linhas = query.order_by(Leito.numero.asc()).all()

    return jsonify([
        {
            "id": leito.id,
            "numero": leito.numero or "",
            "tipo": leito.tipo or "",
            "status": leito.status or "",
            "setor_id": leito.setor_id,
            "setor": setor_nome or "",
        }
        for leito, setor_nome in linhas
    ]), 200


@internacao_bp.route("/api/leitos", methods=["POST"])
@login_required
@requer_permissao("internment:write")
def api_criar_leito():
    dados = request.get_json(silent=True) or request.form or {}

    numero = (dados.get("numero") or "").strip()
    if not numero:
        return jsonify({"ok": False, "erro": "Campo 'numero' é obrigatório."}), 400

    try:
        setor_id = int(dados.get("setor_id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erro": "Campo 'setor_id' é obrigatório."}), 400

    if not db.session.get(Setor, setor_id):
        return jsonify({"ok": False, "erro": "Setor inválido."}), 400

    tipo = (dados.get("tipo") or "comum").strip().lower()
    if tipo not in TIPOS_LEITO:
        tipo = "comum"

    status = (dados.get("status") or STATUS_LEITO_LIVRE).strip().lower()
    if status not in STATUS_LEITO:
        status = STATUS_LEITO_LIVRE

    # Duplicidade por setor + número, sem diferenciar maiúsculas.
    duplicado = (
        Leito.query
        .filter(
            func.lower(Leito.numero) == numero.lower(),
            Leito.setor_id == setor_id,
            Leito.ativo.is_(True),
        )
        .first()
    )
    if duplicado:
        return jsonify({
            "ok": False,
            "erro": "Já existe leito com esse número neste setor.",
        }), 400

    leito = Leito(
        numero=numero,
        setor_id=setor_id,
        unidade_id=current_user.unidade_id,
        tipo=tipo,
        status=status,
        observacoes=(dados.get("observacoes") or "").strip() or None,
        ativo=True,
    )
    db.session.add(leito)

    # flush() atribui a PK pela sequência do próprio banco. Substitui o
    # `last_insert_rowid()`, que é função exclusiva do SQLite.
    db.session.flush()

    registrar("leitos", leito.id, "create",
              f"Leito {leito.numero} criado no setor #{setor_id}")
    db.session.commit()

    return jsonify({
        "ok": True,
        "id": leito.id,
        "msg": "Leito criado com sucesso.",
    }), 201


@internacao_bp.route("/api/leitos/<int:leito_id>/status", methods=["POST"])
@login_required
@requer_permissao("internment:write")
def api_status_leito(leito_id):
    dados = request.get_json(silent=True) or request.form or {}
    status = (dados.get("status") or "").strip().lower()

    if status not in STATUS_LEITO:
        return jsonify({"ok": False, "erro": "Status inválido."}), 400

    leito = db.session.get(Leito, leito_id)
    if not leito:
        return jsonify({"ok": False, "erro": "Leito não encontrado."}), 404
    if not leito.ativo:
        return jsonify({"ok": False, "erro": "Leito inativo."}), 400

    # Leito ocupado tem internação ativa atrás: mudar o status por aqui
    # descolaria os dois. A liberação correta é pela alta.
    if leito.status == STATUS_LEITO_OCUPADO and status != STATUS_LEITO_OCUPADO:
        internacao_ativa = Internacao.query.filter_by(
            leito_id=leito.id, status="ativa"
        ).first()
        if internacao_ativa:
            return jsonify({
                "ok": False,
                "erro": "Leito com internação ativa. Registre a alta para liberá-lo.",
            }), 409

    anterior = leito.status
    leito.status = status

    registrar("leitos", leito.id, "update",
              f"Status do leito {leito.numero}: {anterior} → {status}")
    db.session.commit()

    return jsonify({"ok": True, "msg": "Status atualizado com sucesso."}), 200
