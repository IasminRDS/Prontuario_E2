# -*- coding: utf-8 -*-
"""Registro de consentimento e base legal do tratamento (LGPD).

O model `ConsentimentoLgpd` existia desde o porte do schema, estava registrado
no metadata — e **nenhuma rota o instanciava**. A tabela que documenta a base
legal do tratamento de dado pessoal sensível nunca recebeu uma linha, enquanto
a documentação do sistema listava "registro de consentimento" entre os recursos
de conformidade. Um controle de conformidade que não é escrito por ninguém é
indistinguível de sua ausência — e, pior, aparece como presente no inventário.

**O que esta tela registra não é só consentimento: é a BASE LEGAL.** Em saúde,
a assistência não se apoia no consentimento, e sim na tutela da saúde do
art. 11, II, "f", da Lei 13.709/2018. Registrar a base é o que atende ao art. 37
— manter registro das operações de tratamento — e é o que permite responder ao
titular por que seus dados estão sendo tratados. O consentimento entra apenas
onde ele É a base: pesquisa, contato não assistencial, compartilhamento além do
necessário ao cuidado.

Por isso a tela distingue REGISTRAR de REVOGAR. Só o que se apoia em
consentimento pode ser revogado; oferecer o botão nas demais finalidades faria
o sistema prometer ao titular um controle que a lei não lhe dá ali.
"""
from datetime import datetime

from flask import (
    Blueprint, abort, flash, redirect, render_template, request, url_for,
)
from flask_login import current_user, login_required

from extensions import db
from models.lgpd import ConsentimentoLgpd
from models.paciente import Paciente
from utils.audit import registrar
from utils.rbac import requer_permissao
from utils.security import pode_acessar_paciente

consentimentos_bp = Blueprint("consentimentos", __name__,
                              url_prefix="/pacientes/<int:paciente_id>/consentimentos")

# Versão do termo apresentado ao titular. Muda quando o texto do termo muda: sem
# isto, não há como saber A QUE o titular consentiu, e o registro perde o valor
# probatório que justifica sua existência.
VERSAO_TERMO = "1.0"


def _paciente_no_escopo(paciente_id):
    paciente = Paciente.query.get_or_404(paciente_id)
    if not pode_acessar_paciente(paciente, current_user):
        abort(403)
    return paciente


@consentimentos_bp.get("/")
@login_required
@requer_permissao("patient:read")
def index(paciente_id):
    paciente = _paciente_no_escopo(paciente_id)

    registros = (
        ConsentimentoLgpd.query
        .filter_by(paciente_id=paciente.id)
        .order_by(ConsentimentoLgpd.criado_em.desc())
        .all()
    )

    # A finalidade sem registro é informação, não ausência de informação: é o
    # que o encarregado precisa ver para saber o que ainda falta documentar.
    vigentes = {}
    for r in registros:
        vigentes.setdefault(r.finalidade, r)

    registrar("consentimentos_lgpd", paciente.id, "read",
              f"Consentimentos consultados ({paciente.nome})", commit=True)

    return render_template(
        "consentimentos/index.html",
        paciente=paciente,
        registros=registros,
        vigentes=vigentes,
        finalidades=ConsentimentoLgpd.FINALIDADES,
        versao_termo=VERSAO_TERMO,
    )


@consentimentos_bp.post("/registrar")
@login_required
@requer_permissao("patient:update")
def registrar_consentimento(paciente_id):
    paciente = _paciente_no_escopo(paciente_id)

    finalidade = (request.form.get("finalidade") or "").strip()
    if finalidade not in ConsentimentoLgpd.FINALIDADES:
        flash("Finalidade inválida.", "warning")
        return redirect(url_for("consentimentos.index", paciente_id=paciente.id))

    rotulo, base_legal, por_consentimento = ConsentimentoLgpd.FINALIDADES[finalidade]

    # `concedido` só faz sentido quando a base É o consentimento. Nas demais o
    # registro documenta a base legal aplicada, e não uma escolha do titular.
    concedido = (request.form.get("concedido") == "1") if por_consentimento else True

    registro = ConsentimentoLgpd(
        paciente_id=paciente.id,
        unidade_id=current_user.unidade_id,
        finalidade=finalidade,
        base_legal=base_legal,
        concedido=concedido,
        versao_termo=VERSAO_TERMO,
        # O IP de quem registrou, com o mesmo cuidado do módulo de auditoria:
        # atrás de proxy, `remote_addr` é o do proxy.
        ip=request.headers.get("X-Forwarded-For", request.remote_addr),
        registrado_por=current_user.id,
    )
    db.session.add(registro)
    db.session.flush()

    registrar("consentimentos_lgpd", registro.id, "create",
              f"{rotulo} — base {base_legal}, "
              f"{'concedido' if concedido else 'recusado'} "
              f"(termo {VERSAO_TERMO}), paciente {paciente.nome}")
    db.session.commit()

    flash(f"{rotulo}: registro gravado.", "success")
    return redirect(url_for("consentimentos.index", paciente_id=paciente.id))


@consentimentos_bp.post("/<int:registro_id>/revogar")
@login_required
@requer_permissao("patient:update")
def revogar(paciente_id, registro_id):
    paciente = _paciente_no_escopo(paciente_id)
    registro = ConsentimentoLgpd.query.get_or_404(registro_id)

    if registro.paciente_id != paciente.id:
        abort(404)

    if not registro.revogavel:
        # Recusa explícita, e não botão escondido: quem chega aqui por URL
        # precisa saber POR QUE, e o motivo é jurídico.
        flash("Esta finalidade não se apoia em consentimento — sua base legal "
              "é a tutela da saúde, e revogá-la não teria efeito. A recusa de "
              "tratamento assistencial não é exercida por aqui.", "warning")
        return redirect(url_for("consentimentos.index", paciente_id=paciente.id))

    registro.revogado_em = datetime.utcnow()
    registrar("consentimentos_lgpd", registro.id, "update",
              f"Consentimento revogado — {registro.rotulo}, "
              f"paciente {paciente.nome}")
    db.session.commit()

    flash(f"{registro.rotulo}: consentimento revogado.", "success")
    return redirect(url_for("consentimentos.index", paciente_id=paciente.id))
