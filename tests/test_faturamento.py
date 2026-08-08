# -*- coding: utf-8 -*-
"""AIH e APAC: os campos que a tela pede precisam SOBREVIVER ao POST.

As duas telas pediam 34 campos que os models não tinham. Quem preenchia via a
mensagem de sucesso e perdia o que digitou — o defeito que
`test_contrato_formularios.py` cataloga. O schema foi decidido em
`e2f7b48c9d13`; estes testes verificam o que de fato ficou gravado, e não o
código de resposta, que já era 200 antes.
"""
import pytest

from tests.conftest import PERFIS, autenticar


@pytest.fixture
def admin(app, dados_clinicos, sem_csrf):
    return autenticar(app, PERFIS["admin"][1])


@pytest.fixture
def paciente_id(app):
    from models.paciente import Paciente

    with app.app_context():
        return Paciente.query.order_by(Paciente.id.asc()).first().id


def test_aih_grava_os_campos_novos(app, admin, paciente_id):
    from models.faturamento import AIH

    resposta = admin.post("/faturamento/aih/nova", data={
        "paciente_id": paciente_id,
        "procedimento_principal": "0408050063",
        "cid_principal": "s72.0",
        "competencia": "2026/08",
        "tipo_aih": "1",
        "carater_internacao": "02",
        "cid_secundario": "e11.9",
        "procedimento_secundario": "0408050128",
        "data_internacao": "2026-08-01",
        "data_saida": "2026-08-06",
        "motivo_saida": "alta melhorado",
        "valor_sh": "1200,50",
        "valor_sp": "300,50",
        "observacoes": "fratura de femur",
        "status": "aberta",
    }, follow_redirects=True)
    assert resposta.status_code == 200, resposta.get_data(as_text=True)[:400]

    with app.app_context():
        aih = AIH.query.order_by(AIH.id.desc()).first()
        assert aih is not None, "o POST respondeu e nada foi gravado"
        assert aih.competencia == "2026/08"
        assert aih.tipo_aih == "1"
        assert aih.carater_internacao == "02"
        assert aih.cid_secundario == "E11.9", "o CID secundário não foi normalizado"
        assert aih.procedimento_secundario == "0408050128"
        assert aih.data_internacao.isoformat() == "2026-08-01"
        assert aih.data_saida.isoformat() == "2026-08-06"
        assert aih.motivo_saida == "alta melhorado"
        assert float(aih.valor_sh) == 1200.50
        assert float(aih.valor_sp) == 300.50
        assert aih.observacoes == "fratura de femur"
        # Derivados, não digitados.
        assert aih.dias_permanencia == 5
        assert float(aih.valor_total) == 1501.00, (
            "o total precisa ser a soma de SH e SP, senão os três divergem")


@pytest.mark.parametrize("competencia", ["2026-8", "ago/26", "2026/13", "26/08"])
def test_competencia_malformada_e_recusada(app, admin, paciente_id, competencia):
    """Competência é o recorte pelo qual o SUS fecha o mês.

    Aceitar formato livre faria o relatório agrupar em silêncio coisas que não
    são a mesma competência — e agrupamento errado não parece erro.
    """
    from models.faturamento import AIH

    with app.app_context():
        antes = AIH.query.count()

    resposta = admin.post("/faturamento/aih/nova", data={
        "paciente_id": paciente_id,
        "procedimento_principal": "0408050063",
        "competencia": competencia,
    }, follow_redirects=True)

    with app.app_context():
        assert AIH.query.count() == antes, f"gravou com competência {competencia!r}"
    assert "Competência inválida" in resposta.get_data(as_text=True)


def test_saida_antes_da_internacao_e_recusada(app, admin, paciente_id):
    """Sem esta guarda, `dias_permanencia` sairia negativo."""
    from models.faturamento import AIH

    with app.app_context():
        antes = AIH.query.count()

    resposta = admin.post("/faturamento/aih/nova", data={
        "paciente_id": paciente_id,
        "procedimento_principal": "0408050063",
        "data_internacao": "2026-08-10",
        "data_saida": "2026-08-01",
    }, follow_redirects=True)

    with app.app_context():
        assert AIH.query.count() == antes
    assert "anterior à internação" in resposta.get_data(as_text=True)


def test_apac_grava_os_campos_novos(app, admin, paciente_id):
    from models.faturamento import APAC

    resposta = admin.post("/faturamento/apac/nova", data={
        "paciente_id": paciente_id,
        "procedimento_principal": "0304010030",
        "cid_principal": "c50.9",
        "competencia": "2026/08",
        "tipo": "continuidade",
        "justificativa": "quimioterapia adjuvante",
        "data_inicio": "2026-08-01",
        "data_fim": "2026-10-31",
        "quantidade": "3",
        "status": "ativa",
    }, follow_redirects=True)
    assert resposta.status_code == 200, resposta.get_data(as_text=True)[:400]

    with app.app_context():
        apac = APAC.query.order_by(APAC.id.desc()).first()
        assert apac is not None, "o POST respondeu e nada foi gravado"
        assert apac.competencia == "2026/08"
        assert apac.tipo == "continuidade"
        assert apac.justificativa == "quimioterapia adjuvante"
        # O template mandava `cid` e `procedimento`, que a rota nunca leu: eram
        # apelidos dos campos que já existiam, não colunas faltando.
        assert apac.cid_principal == "C50.9"
        assert apac.procedimento_principal == "0304010030"


def test_filtro_por_competencia_recorta_a_lista(app, admin, paciente_id):
    """O campo existia no filtro e a rota nunca leu o parâmetro."""
    from extensions import db
    from models.faturamento import AIH

    with app.app_context():
        db.session.add_all([
            AIH(paciente_id=paciente_id, procedimento_principal="A",
                competencia="2026/01", valor_total=100),
            AIH(paciente_id=paciente_id, procedimento_principal="B",
                competencia="2026/02", valor_total=250),
        ])
        db.session.commit()

    html = admin.get("/faturamento/aih?competencia=2026/01").get_data(as_text=True)
    assert "2026/01" in html
    assert "2026/02" not in html, "o filtro por competência não recortou a lista"
