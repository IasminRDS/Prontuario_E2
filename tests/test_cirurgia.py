# -*- coding: utf-8 -*-
"""Agendamento de cirurgia: o dado precisa SOBREVIVER ao POST.

Agendar cirurgia nunca funcionou. Eram dois defeitos empilhados, e cada um
sozinho já bastava para perder o registro:

1. `templates/cirurgia/form.html` era o formulário de INTERNAÇÃO copiado — o
   `page_title` dizia "Registrar Internação". Só `paciente_id` e `observacoes`
   coincidiam com o que a rota lia; leito, motivo e hipótese diagnóstica eram
   descartados, e procedimento, sala, cirurgião e data nunca eram enviados.
2. A rota construía `Cirurgia(...)` com nove argumentos que não são colunas do
   model (`cirurgiao_id`, `procedimento`, `cid`, `carater`, `especialidade`,
   `duracao_prevista`, `codigo_tuss`, `anestesista_id`, `unidade_id`). O
   primeiro levantava `TypeError`, e o `except Exception` da própria rota o
   transformava num aviso amarelo — status 200, nenhuma linha criada.

Um teste que só olhasse o código de resposta teria passado nos dois casos. Por
isso aqui se conta linha e se conferem os campos gravados.
"""
import re

import pytest

from tests.conftest import PERFIS, autenticar


def _token(html):
    achado = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return achado.group(1) if achado else ""


@pytest.fixture
def agendador(app, dados_clinicos):
    """Sessão de médico — `cirurgia.nova` exige `surgery:write` e cadastro."""
    return autenticar(app, PERFIS["medico"][1])


@pytest.fixture
def referencias(app, dados_clinicos):
    from models.cirurgia import SalaCirurgica
    from models.medico import Medico
    from models.paciente import Paciente

    with app.app_context():
        paciente = Paciente.query.order_by(Paciente.id.asc()).first()
        medico = Medico.query.order_by(Medico.id.asc()).first()
        sala = SalaCirurgica.query.order_by(SalaCirurgica.id.asc()).first()
        return {
            "paciente_id": paciente.id,
            "medico_id": medico.id,
            "sala_id": sala.id if sala else None,
        }


@pytest.fixture
def limpar_cirurgias(app):
    """Remove o que o teste criar, para não contaminar contagem alheia."""
    from extensions import db
    from models.cirurgia import Cirurgia

    with app.app_context():
        existentes = {c.id for c in Cirurgia.query.all()}
    yield
    with app.app_context():
        for cir in Cirurgia.query.all():
            if cir.id not in existentes:
                db.session.delete(cir)
        db.session.commit()


def _postar(cliente, campos):
    pagina = cliente.get("/cirurgia/nova").get_data(as_text=True)
    dados = {"csrf_token": _token(pagina)}
    dados.update(campos)
    return cliente.post("/cirurgia/nova", data=dados, follow_redirects=True)


def test_agendar_grava_a_cirurgia_com_os_dados(
        app, agendador, referencias, limpar_cirurgias):
    from models.cirurgia import Cirurgia

    resposta = _postar(agendador, {
        "paciente_id": referencias["paciente_id"],
        "cirurgiao_id": referencias["medico_id"],
        "sala_id": referencias["sala_id"] or "",
        "procedimento": "Colecistectomia videolaparoscopica",
        "data_agendada": "2026-09-01T08:30",
        "observacoes": "jejum de 8h",
    })
    assert resposta.status_code == 200

    with app.app_context():
        cir = (Cirurgia.query
               .filter_by(descricao="Colecistectomia videolaparoscopica")
               .one_or_none())

        assert cir is not None, (
            "o POST respondeu, mas nenhuma cirurgia foi criada — era exatamente "
            "assim que o defeito se apresentava")
        # O procedimento mora em `descricao`, e o cirurgião em `medico_id`: são
        # os nomes do model, e usar outros era a causa do TypeError silencioso.
        assert cir.paciente_id == referencias["paciente_id"]
        assert cir.medico_id == referencias["medico_id"]
        assert cir.observacoes == "jejum de 8h"
        assert cir.status == "agendada"
        assert cir.data_agendada is not None, "a data escolhida não foi gravada"
        assert (cir.data_agendada.year, cir.data_agendada.month,
                cir.data_agendada.day) == (2026, 9, 1)
        assert (cir.data_agendada.hour, cir.data_agendada.minute) == (8, 30)


def test_sem_procedimento_nao_grava(app, agendador, referencias,
                                    limpar_cirurgias):
    """`descricao` é NOT NULL: sem validar, viraria IntegrityError cru na tela."""
    from models.cirurgia import Cirurgia

    with app.app_context():
        antes = Cirurgia.query.count()

    resposta = _postar(agendador, {
        "paciente_id": referencias["paciente_id"],
        "procedimento": "   ",
        "data_agendada": "2026-09-02T10:00",
    })

    with app.app_context():
        assert Cirurgia.query.count() == antes, "gravou sem procedimento"
    assert "Descreva o procedimento" in resposta.get_data(as_text=True)


def test_sem_paciente_nao_grava(app, agendador, limpar_cirurgias):
    from models.cirurgia import Cirurgia

    with app.app_context():
        antes = Cirurgia.query.count()

    resposta = _postar(agendador, {
        "paciente_id": "",
        "procedimento": "Hernioplastia inguinal",
    })

    with app.app_context():
        assert Cirurgia.query.count() == antes, "gravou sem paciente"
    assert "Selecione o paciente" in resposta.get_data(as_text=True)


def test_formulario_e_o_de_cirurgia(agendador):
    """Guarda contra a cópia do formulário de internação voltar."""
    html = agendador.get("/cirurgia/nova").get_data(as_text=True)
    assert "Registrar Internação" not in html
    assert 'name="procedimento"' in html, "o formulário não pede o procedimento"
    assert 'name="leito_id"' not in html, "voltou a ser o formulário de internação"
