# -*- coding: utf-8 -*-
from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    send_file,
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
from utils.rbac import requer_permissao
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


# ── 5. Comparativo territorial ────────────────────────────────────────────
#
# Os quatro relatórios acima respondem "quanto esta unidade produziu". Este
# responde outra pergunta: "quanto cada município produziu, comparado aos
# outros". A diferença não é de filtro, é de eixo — aqui a linha é o município,
# e não o registro.
#
# O agrupamento é pelo **código IBGE**, nunca por `cidade` em texto: é o
# argumento que `models/municipio.py` faz por escrito, e é aqui que ele deixa de
# ser teórico. "Feira de Santana" digitado de três jeitos viraria três linhas no
# comparativo, cada uma com um terço do movimento.
#
# O que este relatório NÃO faz, e a tela diz: dividir pela população. Comparar
# por contagem favorece município grande por construção — Salvador sempre terá
# mais atendimentos que Bom Jesus da Lapa, e isso não informa nada sobre
# desempenho. Taxa exigiria o denominador populacional, que o sistema ainda não
# guarda (o levantamento em `docs/datasus_levantamento.md` identificou a base do
# IBGE que o fornece).

# (chave, rótulo, model, coluna de data). A coluna de data é escolhida pelo
# evento que o indicador conta, e não pela data de criação da linha: internação
# conta pela entrada, vacina pela aplicação, exame pela solicitação.
def _indicadores():
    """Importado sob demanda: o módulo já carrega sete models no topo."""
    from models.internacao import Internacao

    return (
        ("atendimentos", "Atendimentos", Atendimento, Atendimento.data_hora),
        ("prontuarios", "Prontuários", Prontuario, Prontuario.criado_em),
        ("triagens", "Triagens", Triagem, Triagem.criado_em),
        ("internacoes", "Internações", Internacao, Internacao.data_entrada),
        ("exames", "Exames", ExameSolicitado, ExameSolicitado.data_solicitacao),
        ("encaminhamentos", "Encaminhamentos", Encaminhamento,
         Encaminhamento.data_solicitacao),
        ("vacinas", "Vacinas", VacinaAplicada, VacinaAplicada.data_aplicacao),
    )


ABRANGENCIAS = (
    ("brasil", "Brasil"),
    ("uf", "Estado"),
    ("municipio", "Município"),
)


def _escopo_do_usuario_legivel():
    """O recorte territorial em vigor, em português, e se ele limita a tela.

    Existe porque o RLS **nega silenciosamente**: um usuário de nível MUNICÍPIO
    que escolher "Brasil" não recebe erro, recebe uma linha só. Sem esta
    explicação na tela, o comparativo pareceria quebrado exatamente para quem
    está protegido como deveria.
    """
    from utils.rls import escopo_do_usuario

    escopo = escopo_do_usuario(current_user)
    nivel = escopo.get("nivel", "UNIDADE")
    rotulos = {
        "SISTEMA": ("todo o país", False),
        "ESTADO": ("o estado %s" % (escopo.get("uf") or "?"), True),
        "REGIONAL": ("a sua região de saúde", True),
        "MUNICIPIO": ("o seu município", True),
        "UNIDADE": ("a sua unidade", True),
    }
    texto, limita = rotulos.get(nivel, ("a sua unidade", True))
    return {
        "nivel": nivel,
        "texto": texto,
        "limita": limita,
        "irresoluvel": escopo.get("irresoluvel", False),
    }


@relatorios_bp.route("/territorio")
@login_required
@requer_permissao("reports:read")
def territorio():
    from sqlalchemy import func

    from models.municipio import Municipio
    from models.unidade_saude import UnidadeSaude

    abrangencia = request.args.get("abrangencia", "brasil")
    if abrangencia not in dict(ABRANGENCIAS):
        abrangencia = "brasil"
    uf = (request.args.get("uf") or "").strip().upper()[:2]
    codigo_ibge = "".join(c for c in (request.args.get("municipio") or "")
                          if c.isdigit())[:7]

    data_ini = request.args.get("data_ini",
                                _hoje().replace(day=1).strftime("%Y-%m-%d"))
    data_fim = request.args.get("data_fim", _hoje().strftime("%Y-%m-%d"))
    try:
        di = datetime.strptime(data_ini, "%Y-%m-%d")
        df = datetime.strptime(data_fim, "%Y-%m-%d").replace(hour=23, minute=59)
    except ValueError:
        di = datetime.utcnow().replace(day=1)
        df = datetime.utcnow()

    def _territorial(consulta):
        """Aplica o recorte escolhido. O do RLS já veio antes, no banco."""
        if abrangencia == "uf" and uf:
            consulta = consulta.filter(Municipio.uf == uf)
        elif abrangencia == "municipio" and codigo_ibge:
            consulta = consulta.filter(Municipio.codigo_ibge == codigo_ibge)
        return consulta

    # Uma consulta agregada por indicador, em vez de uma por município: com 5570
    # municípios possíveis, o laço seria N+1 na sua pior forma.
    linhas = {}
    for chave, _rotulo, model, coluna in _indicadores():
        consulta = (
            db.session.query(
                Municipio.codigo_ibge, Municipio.nome, Municipio.uf,
                Municipio.populacao, Municipio.populacao_ano,
                func.count(model.id),
            )
            # A tabela de fatos é a origem, e não `municipios`, que só entra
            # para dar nome ao agrupamento. Medido: no SQLAlchemy 2.0.23 o SQL
            # sai idêntico com ou sem esta linha — a cadeia de `join` já
            # determina o FROM. Fica porque torna a origem explícita para quem
            # lê, e não porque corrija alguma coisa.
            .select_from(model)
            .join(UnidadeSaude, UnidadeSaude.id == model.unidade_id)
            .join(Municipio,
                  Municipio.codigo_ibge == UnidadeSaude.municipio_ibge)
            .filter(coluna.between(di, df))
            .group_by(Municipio.codigo_ibge, Municipio.nome, Municipio.uf,
                      Municipio.populacao, Municipio.populacao_ano)
        )
        for ibge, nome, sigla, populacao, ano, quantidade in \
                _territorial(consulta).all():
            linha = linhas.setdefault(ibge, {
                "codigo_ibge": ibge, "nome": nome, "uf": sigla, "total": 0,
                "populacao": populacao, "populacao_ano": ano,
            })
            linha[chave] = quantidade
            linha["total"] += quantidade

    colunas = [(chave, rotulo) for chave, rotulo, _m, _c in _indicadores()]
    for linha in linhas.values():
        for chave, _rotulo in colunas:
            linha.setdefault(chave, 0)
        # `None`, e não zero, quando não há denominador. Zero é um valor, e
        # valor errado aqui lê-se como resultado: um município sem população
        # carregada apareceria como o de menor produção do estado.
        linha["por_cem_mil"] = (
            linha["total"] * 100000.0 / linha["populacao"]
            if linha.get("populacao") else None
        )

    # A ordem padrão continua sendo a contagem. Ordenar por taxa por padrão
    # esconderia os municípios sem denominador no fim da lista, que é onde
    # ninguém olha — e a ausência do denominador é justamente o que precisa
    # ser visto para alguém resolver.
    ordem = request.args.get("ordem", "total")
    if ordem == "taxa":
        municipios = sorted(
            linhas.values(),
            key=lambda l: (l["por_cem_mil"] is None,
                           -(l["por_cem_mil"] or 0), l["nome"]))
    else:
        municipios = sorted(linhas.values(),
                            key=lambda l: (-l["total"], l["nome"]))

    sem_denominador = [l for l in linhas.values() if not l.get("populacao")]

    totais = {chave: sum(l[chave] for l in municipios) for chave, _r in colunas}
    totais["total"] = sum(l["total"] for l in municipios)

    if request.args.get("exportar") == "csv":
        buf = StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["Código IBGE", "Município", "UF"]
                   + [rotulo for _c, rotulo in colunas]
                   + ["Total", "População", "Ano da população",
                      "Total por 100 mil hab."])
        for linha in municipios:
            taxa = linha["por_cem_mil"]
            w.writerow([linha["codigo_ibge"], linha["nome"], linha["uf"]]
                       + [linha[chave] for chave, _r in colunas]
                       + [linha["total"],
                          linha.get("populacao") or "",
                          linha.get("populacao_ano") or "",
                          # Célula vazia, e não zero: quem abrir a planilha
                          # somaria zeros como se fossem medições.
                          ("%.1f" % taxa).replace(".", ",") if taxa is not None else ""])
        w.writerow(["", "TOTAL", ""]
                   + [totais[chave] for chave, _r in colunas]
                   + [totais["total"], "", "", ""])
        buf.seek(0)
        return send_file(
            BytesIO(buf.getvalue().encode("utf-8-sig")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"territorio_{_hoje()}.csv",
        )

    # As listas de seleção saem do que EXISTE em `unidades_saude`, e não da
    # tabela de municípios inteira: oferecer 5570 opções, das quais 5568 dariam
    # tela vazia, é oferecer engano.
    ufs = [u for (u,) in db.session.query(UnidadeSaude.uf)
           .filter(UnidadeSaude.uf.isnot(None)).distinct().order_by(UnidadeSaude.uf)]
    opcoes_municipios = (
        db.session.query(Municipio.codigo_ibge, Municipio.nome, Municipio.uf)
        .join(UnidadeSaude, UnidadeSaude.municipio_ibge == Municipio.codigo_ibge)
        .distinct().order_by(Municipio.uf, Municipio.nome).all()
    )

    return render_template(
        "relatorios/territorio.html",
        abrangencias=ABRANGENCIAS,
        abrangencia=abrangencia,
        uf=uf,
        codigo_ibge=codigo_ibge,
        ufs=ufs,
        opcoes_municipios=opcoes_municipios,
        colunas=colunas,
        municipios=municipios,
        totais=totais,
        ordem=ordem,
        sem_denominador=sem_denominador,
        data_ini=data_ini,
        data_fim=data_fim,
        escopo=_escopo_do_usuario_legivel(),
    )
