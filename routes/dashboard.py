from datetime import date, timedelta, datetime

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from database.db import db
from models.paciente import Paciente

try:
    from models.atendimento import Atendimento
except Exception:
    Atendimento = None

try:
    from models.triagem import Triagem
except Exception:
    Triagem = None

try:
    from models.agendamento import Agendamento
except Exception:
    Agendamento = None



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


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/")


def _degradar(padrao):
    """Devolve `padrao` depois de recuperar a sessão do banco.

    Cada painel deste dashboard tolera a própria falha e mostra zero. Isso só
    funciona se a sessão continuar utilizável: em PostgreSQL, um erro aborta a
    transação inteira, e sem o rollback os painéis SEGUINTES falham em cascata —
    a tela responde 200 com tudo zerado, sem nenhum sinal de erro. Em SQLite a
    sessão sobrevive sozinha, e foi por isso que a falta passou despercebida.
    """
    db.session.rollback()
    return padrao


def _count(model, coluna_data=None, hoje_only=False, inicio=None):
    if model is None:
        return 0
    try:
        q = model.query
        if coluna_data is not None:
            if hoje_only:
                q = q.filter(func.date(coluna_data) == _hoje())
            elif inicio is not None:
                q = q.filter(func.date(coluna_data) >= inicio)
        return int(q.count())
    except Exception:
        return _degradar(0)


def _serie_atendimentos_7dias():
    fim = _hoje()
    dias = [fim - timedelta(days=i) for i in range(6, -1, -1)]
    labels = [d.strftime("%d/%m") for d in dias]
    valores = [0] * 7

    if Atendimento is None:
        return labels, valores

    col = getattr(Atendimento, "data_atendimento", None) or getattr(Atendimento, "criado_em", None)
    if col is None:
        return labels, valores

    try:
        rows = (
            db.session.query(func.date(col).label("d"), func.count(Atendimento.id))
            .filter(func.date(col) >= dias[0], func.date(col) <= fim)
            .group_by(func.date(col))
            .all()
        )
        mapa = {}
        for d, c in rows:
            if isinstance(d, str):
                d = datetime.strptime(d, "%Y-%m-%d").date()
            mapa[d] = int(c or 0)
        valores = [mapa.get(d, 0) for d in dias]
    except Exception:
        _degradar(None)

    return labels, valores


def _pacientes_por_sexo():
    try:
        rows = (
            db.session.query(Paciente.sexo, func.count(Paciente.id))
            .group_by(Paciente.sexo)
            .all()
        )
        m = f = o = 0
        for sexo, c in rows:
            s = (sexo or "").upper()
            if s == "M":
                m += int(c or 0)
            elif s == "F":
                f += int(c or 0)
            else:
                o += int(c or 0)
        return [m, f, o]
    except Exception:
        return _degradar([0, 0, 0])


@dashboard_bp.get("/")
@login_required
def index():
    total_pacientes = _count(Paciente)
    atendimentos_hoje = _count(
        Atendimento,
        getattr(Atendimento, "data_atendimento", None) or getattr(Atendimento, "criado_em", None),
        hoje_only=True
    )
    atendimentos_mes = _count(
        Atendimento,
        getattr(Atendimento, "data_atendimento", None) or getattr(Atendimento, "criado_em", None),
        inicio=_hoje().replace(day=1)
    )
    agenda_hoje = _count(
        Agendamento,
        getattr(Agendamento, "data_agendamento", None) or getattr(Agendamento, "data", None) or getattr(Agendamento, "criado_em", None),
        hoje_only=True
    )
    triagens_hoje = _count(
        Triagem,
        getattr(Triagem, "data_triagem", None) or getattr(Triagem, "criado_em", None),
        hoje_only=True
    )

    labels_7dias, dados_7dias = _serie_atendimentos_7dias()
    pacientes_sexo = _pacientes_por_sexo()

    return render_template(
        "dashboard/index.html",
        data_hoje=_hoje().strftime("%d/%m/%Y"),
        total_pacientes=total_pacientes,
        atendimentos_hoje=atendimentos_hoje,
        atendimentos_mes=atendimentos_mes,
        agenda_hoje=agenda_hoje,
        triagens_hoje=triagens_hoje,
        pendentes_total=0,
        pendencias_texto="0 exames · 0 enc.",
        labels_7dias=labels_7dias,
        dados_7dias=dados_7dias,
        pacientes_sexo=pacientes_sexo,
    )