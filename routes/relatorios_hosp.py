# -*- coding: utf-8 -*-
from flask import Blueprint, render_template, request, send_file
from flask_login import login_required, current_user
from models.internacao import Internacao, Setor, Leito
from models.cirurgia import Cirurgia
from models.pronto_socorro import AtendimentoPS
from models.faturamento import AIH
from database.db import db
from datetime import datetime, date
from io import BytesIO, StringIO
import csv

rel_hosp_bp = Blueprint("rel_hosp", __name__, url_prefix="/relatorios/hospital")


@rel_hosp_bp.route("/")
@login_required
def index():
    return render_template("relatorios_hosp/index.html")


@rel_hosp_bp.route("/ocupacao")
@login_required
def ocupacao():
    setores = Setor.query.filter_by(ativo=True).all()
    total = sum(s.total_leitos for s in setores)
    ocupados = sum(s.leitos_ocupados for s in setores)
    taxa = round(ocupados / total * 100) if total else 0
    internacoes_mes = Internacao.query.filter(
        Internacao.data_entrada >= date.today().replace(day=1),
        Internacao.unidade_id == current_user.unidade_id,
    ).count()
    permanencia_media = None
    altas = Internacao.query.filter(
        Internacao.status == "alta",
        Internacao.unidade_id == current_user.unidade_id,
        Internacao.data_alta >= date.today().replace(day=1),
    ).all()
    if altas:
        permanencia_media = round(sum(i.dias_internado for i in altas) / len(altas), 1)
    return render_template(
        "relatorios_hosp/ocupacao.html",
        setores=setores,
        total=total,
        ocupados=ocupados,
        taxa=taxa,
        internacoes_mes=internacoes_mes,
        permanencia_media=permanencia_media,
        altas=altas,
    )


@rel_hosp_bp.route("/producao")
@login_required
def producao():
    data_ini = request.args.get(
        "data_ini", date.today().replace(day=1).strftime("%Y-%m-%d")
    )
    data_fim = request.args.get("data_fim", date.today().strftime("%Y-%m-%d"))
    exportar = request.args.get("exportar", "")
    try:
        di = datetime.strptime(data_ini, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59)
    except ValueError:
        di = datetime.now().replace(day=1)
        df = datetime.now()

    uid = current_user.unidade_id
    internacoes = Internacao.query.filter(
        Internacao.data_entrada.between(di, df), Internacao.unidade_id == uid
    ).count()
    altas = Internacao.query.filter(
        Internacao.data_alta.between(di, df),
        Internacao.unidade_id == uid,
        Internacao.status == "alta",
    ).count()
    cirurgias = Cirurgia.query.filter(
        Cirurgia.data_agendada.between(di, df)
    ).count()
    cir_realizadas = Cirurgia.query.filter(
        Cirurgia.data_agendada.between(di, df),
        Cirurgia.status == "realizada",
    ).count()
    ps_total = AtendimentoPS.query.filter(
        AtendimentoPS.data_chegada.between(di, df)
    ).count()
    ps_internados = AtendimentoPS.query.filter(
        AtendimentoPS.data_chegada.between(di, df),
        AtendimentoPS.status == "internado",
    ).count()
    obitos = Internacao.query.filter(
        Internacao.data_alta.between(di, df),
        Internacao.unidade_id == uid,
        Internacao.status == "obito",
    ).count()

    dados = [
        ("Internações", internacoes),
        ("Altas hospitalares", altas),
        ("Cirurgias agendadas", cirurgias),
        ("Cirurgias realizadas", cir_realizadas),
        ("Atendimentos PS", ps_total),
        ("PS → Internação", ps_internados),
        ("Óbitos", obitos),
    ]

    if exportar == "csv":
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["Indicador", "Quantidade", "Período"])
        for label, val in dados:
            w.writerow([label, val, f"{data_ini} a {data_fim}"])
        buf.seek(0)
        return send_file(
            BytesIO(buf.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"producao_hospitalar_{date.today()}.csv",
        )

    return render_template(
        "relatorios_hosp/producao.html",
        dados=dados,
        data_ini=data_ini,
        data_fim=data_fim,
    )


@rel_hosp_bp.route("/ps")
@login_required
def relatorio_ps():
    data_ini = request.args.get(
        "data_ini", date.today().replace(day=1).strftime("%Y-%m-%d")
    )
    data_fim = request.args.get("data_fim", date.today().strftime("%Y-%m-%d"))
    exportar = request.args.get("exportar", "")
    try:
        di = datetime.strptime(data_ini, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59)
    except ValueError:
        di = datetime.now().replace(day=1)
        df = datetime.now()

    # AtendimentoPS não tem vínculo com unidade no model — o filtro territorial
    # não é aplicável aqui.
    ats = (
        AtendimentoPS.query.filter(AtendimentoPS.data_chegada.between(di, df))
        .order_by(AtendimentoPS.data_chegada.desc())
        .all()
    )

    por_cor = {}
    por_desfecho = {}
    for a in ats:
        por_cor[a.classificacao] = por_cor.get(a.classificacao, 0) + 1
        if a.desfecho:
            por_desfecho[a.desfecho] = por_desfecho.get(a.desfecho, 0) + 1

    tempos = [a.tempo_total_min for a in ats if a.tempo_total_min is not None]
    tempo_medio = round(sum(tempos) / len(tempos)) if tempos else None

    if exportar == "csv":
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(
            [
                "Data entrada",
                "Paciente",
                "Classificação",
                "Modo chegada",
                "Status",
                "Desfecho",
                "Tempo (min)",
            ]
        )
        for a in ats:
            w.writerow(
                [
                    a.data_chegada.strftime("%d/%m/%Y %H:%M"),
                    a.paciente.nome_exibicao,
                    a.classificacao,
                    a.modo_chegada,
                    a.status,
                    a.desfecho or "",
                    a.tempo_total_min or "",
                ]
            )
        buf.seek(0)
        return send_file(
            BytesIO(buf.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"relatorio_ps_{date.today()}.csv",
        )

    return render_template(
        "relatorios_hosp/ps.html",
        ats=ats,
        por_cor=por_cor,
        por_desfecho=por_desfecho,
        tempo_medio=tempo_medio,
        data_ini=data_ini,
        data_fim=data_fim,
    )
