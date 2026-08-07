# -*- coding: utf-8 -*-
from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    send_file,
    flash,
    redirect,
    url_for,
)
from flask_login import login_required, current_user
from models.paciente import Paciente
from models.prontuario import Prontuario
from models.atendimento import Atendimento
from models.agendamento import Agendamento
from models.triagem import Triagem
from models.exame import ExameSolicitado
from models.encaminhamento import Encaminhamento
from models.vacina import VacinaAplicada
from database.db import db
from datetime import datetime, date
from io import BytesIO, StringIO
import csv


def _hoje():
    """Data de hoje no MESMO fuso em que as colunas são gravadas.

    Os models usam `datetime.utcnow()` como padrão; os relatórios montavam a
    janela com `date.today()`, que é hora local. Em UTC-3, todo registro criado
    entre 21h e meia-noite nasce com data UTC do dia seguinte e ficava FORA da
    janela do próprio dia — o relatório omitia, sem erro nenhum, as últimas três
    horas de movimento de cada dia. Num pronto-socorro, que opera 24h, isso é
    subnotificação sistemática.
    """
    return datetime.utcnow().date()


relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")


@relatorios_bp.route("/")
@login_required
def index():
    return render_template("relatorios/index.html")


# ── 1. Relatório de Pacientes ──
@relatorios_bp.route("/pacientes")
@login_required
def pacientes():
    sexo = request.args.get("sexo", "")
    municipio = request.args.get("municipio", "").strip()
    idade_min = request.args.get("idade_min", "")
    idade_max = request.args.get("idade_max", "")
    tem_cns = request.args.get("tem_cns", "")
    exportar = request.args.get("exportar", "")

    from dateutil.relativedelta import relativedelta

    q = Paciente.query.filter_by(ativo=True)
    if sexo:
        q = q.filter(Paciente.sexo == sexo)
    if municipio:
        q = q.filter(Paciente.municipio.ilike(f"%{municipio}%"))
    if tem_cns == "1":
        q = q.filter(Paciente.cns.isnot(None), Paciente.cns != "")
    elif tem_cns == "0":
        q = q.filter(db.or_(Paciente.cns.is_(None), Paciente.cns == ""))
    if idade_min:
        d_max = _hoje() - relativedelta(years=int(idade_min))
        q = q.filter(Paciente.data_nascimento <= d_max)
    if idade_max:
        d_min = _hoje() - relativedelta(years=int(idade_max) + 1)
        q = q.filter(Paciente.data_nascimento >= d_min)

    q = q.order_by(Paciente.nome)

    # A exportação é a única que legitimamente quer todas as linhas: o arquivo é
    # o produto. A TELA não — carregar 50 mil pacientes para renderizar uma
    # tabela levava 4,6 segundos e crescia linearmente com a base, e ninguém
    # rola 50 mil linhas.
    if exportar == "csv":
        return _csv_pacientes(q.all())

    pagina = q.paginate(
        page=request.args.get("page", 1, type=int),
        per_page=int(current_app.config.get("RELATORIOS_PER_PAGE", 50)),
        error_out=False,
    )

    return render_template(
        "relatorios/pacientes.html",
        pacientes=pagina.items,
        pagina=pagina,
        total_encontrado=pagina.total,
        filtros=dict(
            sexo=sexo,
            municipio=municipio,
            idade_min=idade_min,
            idade_max=idade_max,
            tem_cns=tem_cns,
        ),
    )


def _csv_pacientes(pacientes):
    buf = StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(
        [
            "Nome",
            "Nome Social",
            "CNS",
            "CPF",
            "Data Nasc.",
            "Idade",
            "Sexo",
            "Raça/Cor",
            "Telefone",
            "Município",
            "UF",
            "Alergias",
        ]
    )
    for p in pacientes:
        w.writerow(
            [
                p.nome,
                p.nome_social or "",
                p.cns or "",
                p.cpf or "",
                p.data_nascimento.strftime("%d/%m/%Y"),
                p.idade,
                p.sexo,
                p.raca_cor or "",
                p.telefone or "",
                p.municipio or "",
                p.uf or "",
                p.alergias or "",
            ]
        )
    buf.seek(0)
    return send_file(
        BytesIO(buf.getvalue().encode("utf-8-sig")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"pacientes_{_hoje()}.csv",
    )


# ── 2. Relatório de Atendimentos ──
@relatorios_bp.route("/atendimentos")
@login_required
def atendimentos():
    data_ini = request.args.get(
        "data_ini", _hoje().replace(day=1).strftime("%Y-%m-%d")
    )
    data_fim = request.args.get("data_fim", _hoje().strftime("%Y-%m-%d"))
    tipo = request.args.get("tipo", "")
    exportar = request.args.get("exportar", "")

    try:
        di = datetime.strptime(data_ini, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59)
    except ValueError:
        di = datetime.now().replace(day=1)
        df = datetime.now()

    q = Atendimento.query.filter(Atendimento.data_hora.between(di, df))
    if tipo:
        q = q.filter(Atendimento.tipo == tipo)
    ats = q.order_by(Atendimento.data_hora.desc()).all()

    if exportar == "csv":
        buf = StringIO()
        w = csv.writer(buf, delimiter=";")
        # Sem coluna "Status": `Atendimento` não tem esse campo — tem `tipo`.
        # No template o Jinja renderizava vazio e ninguém percebia; aqui o
        # `csv.writer` levantava AttributeError e a exportação inteira devolvia
        # 500. A varredura de rotas não pegava porque só exercita a URL sem o
        # `?exportar=csv`, e é o parâmetro que decide o ramo.
        w.writerow(["Data", "Paciente", "Tipo", "Médico", "Unidade"])
        for a in ats:
            w.writerow(
                [
                    a.data_hora.strftime("%d/%m/%Y %H:%M"),
                    a.paciente.nome_exibicao,
                    a.tipo,
                    a.medico.nome if a.medico else "",
                    a.unidade.nome if a.unidade else "",
                ]
            )
        buf.seek(0)
        return send_file(
            BytesIO(buf.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"atendimentos_{_hoje()}.csv",
        )

    # Totais por tipo
    totais_tipo = {}
    for a in ats:
        totais_tipo[a.tipo] = totais_tipo.get(a.tipo, 0) + 1

    return render_template(
        "relatorios/atendimentos.html",
        atendimentos=ats,
        totais_tipo=totais_tipo,
        data_ini=data_ini,
        data_fim=data_fim,
        tipo=tipo,
    )


# ── 3. Relatório de Produção ──
@relatorios_bp.route("/producao")
@login_required
def producao():
    data_ini = request.args.get(
        "data_ini", _hoje().replace(day=1).strftime("%Y-%m-%d")
    )
    data_fim = request.args.get("data_fim", _hoje().strftime("%Y-%m-%d"))
    exportar = request.args.get("exportar", "")

    try:
        di = datetime.strptime(data_ini, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59)
    except ValueError:
        di = datetime.now().replace(day=1)
        df = datetime.now()

    uid = current_user.unidade_id

    total_at = Atendimento.query.filter(Atendimento.data_hora.between(di, df)).count()
    total_pront = Prontuario.query.filter(Prontuario.criado_em.between(di, df)).count()
    total_ag = Agendamento.query.filter(
        Agendamento.data_hora.between(di, df), Agendamento.unidade_id == uid
    ).count()
    total_tri = Triagem.query.filter(
        Triagem.criado_em.between(di, df), Triagem.unidade_id == uid
    ).count()
    total_exam = ExameSolicitado.query.filter(
        ExameSolicitado.data_solicitacao.between(di, df),
        ExameSolicitado.unidade_id == uid,
    ).count()
    total_enc = Encaminhamento.query.filter(
        Encaminhamento.data_solicitacao.between(di, df),
        Encaminhamento.unidade_origem_id == uid,
    ).count()
    total_vac = VacinaAplicada.query.filter(
        VacinaAplicada.data_aplicacao.between(di, df)
    ).count()
    novos_pac = Paciente.query.filter(Paciente.criado_em.between(di, df)).count()

    # Faltas e cancelamentos de agendamento
    faltas = Agendamento.query.filter(
        Agendamento.data_hora.between(di, df),
        Agendamento.status.in_(["cancelado", "falta"]),
        Agendamento.unidade_id == uid,
    ).count()

    if exportar == "csv":
        buf = StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["Indicador", "Quantidade"])
        for label, val in [
            ("Atendimentos", total_at),
            ("Prontuários", total_pront),
            ("Agendamentos", total_ag),
            ("Triagens", total_tri),
            ("Exames solicitados", total_exam),
            ("Encaminhamentos", total_enc),
            ("Vacinas aplicadas", total_vac),
            ("Novos pacientes", novos_pac),
            ("Faltas/Cancelamentos", faltas),
        ]:
            w.writerow([label, val])
        buf.seek(0)
        return send_file(
            BytesIO(buf.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"producao_{_hoje()}.csv",
        )

    return render_template(
        "relatorios/producao.html",
        data_ini=data_ini,
        data_fim=data_fim,
        total_at=total_at,
        total_pront=total_pront,
        total_ag=total_ag,
        total_tri=total_tri,
        total_exam=total_exam,
        total_enc=total_enc,
        total_vac=total_vac,
        novos_pac=novos_pac,
        faltas=faltas,
    )


# ── 4. Relatório de Triagem ──
@relatorios_bp.route("/triagem")
@login_required
def triagem():
    data_ini = request.args.get(
        "data_ini", _hoje().replace(day=1).strftime("%Y-%m-%d")
    )
    data_fim = request.args.get("data_fim", _hoje().strftime("%Y-%m-%d"))
    exportar = request.args.get("exportar", "")

    try:
        di = datetime.strptime(data_ini, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59)
    except ValueError:
        di = datetime.now().replace(day=1)
        df = datetime.now()

    triagens = (
        Triagem.query.filter(
            Triagem.criado_em.between(di, df),
            Triagem.unidade_id == current_user.unidade_id,
        )
        .order_by(Triagem.criado_em.desc())
        .all()
    )

    por_cor = {}
    for t in triagens:
        por_cor[t.classificacao] = por_cor.get(t.classificacao, 0) + 1

    if exportar == "csv":
        buf = StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(
            [
                "Data",
                "Paciente",
                "Classificação",
                "Queixa",
                "PA",
                "Temp.",
                "SpO2",
                "Dor",
            ]
        )
        for t in triagens:
            w.writerow(
                [
                    t.criado_em.strftime("%d/%m/%Y %H:%M"),
                    t.paciente.nome_exibicao,
                    t.classificacao,
                    t.queixa_principal or "",
                    t.pressao_arterial or "",
                    t.temperatura or "",
                    t.saturacao_o2 or "",
                    t.dor_escala if t.dor_escala is not None else "",
                ]
            )
        buf.seek(0)
        return send_file(
            BytesIO(buf.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"triagem_{_hoje()}.csv",
        )

    return render_template(
        "relatorios/triagem.html",
        triagens=triagens,
        por_cor=por_cor,
        data_ini=data_ini,
        data_fim=data_fim,
    )


# Produção por unidade: mesmo relatório, com o recorte territorial do usuário
# já aplicado por `_escopo_unidade()`. Existe como endpoint próprio porque a
# tela inicial de relatórios linka os dois separadamente.
relatorios_bp.add_url_rule(
    "/producao/unidade", endpoint="producao_unidade", view_func=producao
)
