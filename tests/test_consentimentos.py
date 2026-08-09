# -*- coding: utf-8 -*-
"""Registro da base legal do tratamento (LGPD).

O model `ConsentimentoLgpd` existia, estava no metadata e **nenhuma rota o
instanciava**: a tabela que documenta a base legal do tratamento de dado
pessoal sensível nunca recebeu uma linha, enquanto o README listava "registro
de consentimento" entre os recursos de conformidade.

O ponto que estes testes guardam não é a mecânica de gravar — é a distinção
jurídica. Em saúde, a assistência NÃO se apoia no consentimento, e sim na tutela
da saúde do art. 11, II, "f". Tratar as duas bases como se fossem uma faria o
sistema oferecer ao titular um controle que a lei não lhe dá ali — e, se ele o
exercesse, a unidade teria de parar de registrar o atendimento.
"""
import pytest

from tests.conftest import PERFIS, autenticar


@pytest.fixture
def recepcao(app, dados_clinicos, sem_csrf):
    return autenticar(app, PERFIS["admin"][1])


@pytest.fixture
def paciente_id(app, recepcao):
    """Paciente no escopo de quem registra — senão a rota recusa com 403."""
    from extensions import db
    from models.paciente import Paciente
    from models.user import User

    with app.app_context():
        usuario = User.query.filter_by(email=PERFIS["admin"][1]).first()
        paciente = Paciente.query.order_by(Paciente.id.asc()).first()
        anterior = (paciente.municipio, paciente.uf)
        if usuario.unidade:
            paciente.municipio = usuario.unidade.municipio
            paciente.uf = usuario.unidade.uf
            db.session.commit()
        alvo = paciente.id

    yield alvo

    with app.app_context():
        p = db.session.get(Paciente, alvo)
        p.municipio, p.uf = anterior
        db.session.commit()


def test_registra_a_base_legal_da_assistencia(app, recepcao, paciente_id):
    """Assistência gera registro de BASE LEGAL, não de consentimento."""
    from models.lgpd import ConsentimentoLgpd

    resposta = recepcao.post(
        f"/pacientes/{paciente_id}/consentimentos/registrar",
        data={"finalidade": "assistencia"}, follow_redirects=True)
    assert resposta.status_code == 200, resposta.get_data(as_text=True)[:300]

    with app.app_context():
        r = (ConsentimentoLgpd.query
             .filter_by(paciente_id=paciente_id, finalidade="assistencia")
             .order_by(ConsentimentoLgpd.id.desc()).first())
        assert r is not None, "a operação de tratamento não foi registrada"
        assert r.base_legal == "tutela_da_saude", (
            f"assistência registrada sob base {r.base_legal!r} — em saúde a "
            "base é a tutela da saúde, não o consentimento")
        assert r.versao_termo, "sem versão do termo não se sabe a QUE se consentiu"
        assert r.unidade_id is not None, "sem unidade o RLS oculta o registro"


def test_consentimento_de_pesquisa_pode_ser_recusado(app, recepcao, paciente_id):
    from models.lgpd import ConsentimentoLgpd

    recepcao.post(f"/pacientes/{paciente_id}/consentimentos/registrar",
                  data={"finalidade": "pesquisa", "concedido": "0"},
                  follow_redirects=True)

    with app.app_context():
        r = (ConsentimentoLgpd.query
             .filter_by(paciente_id=paciente_id, finalidade="pesquisa")
             .order_by(ConsentimentoLgpd.id.desc()).first())
        assert r is not None
        assert r.concedido is False, "a recusa foi gravada como consentimento"
        assert r.base_legal == "consentimento"


def test_assistencia_nao_e_revogavel(app, recepcao, paciente_id):
    """Revogar a tutela da saúde não tem efeito jurídico — e oferecer o botão
    prometeria ao titular um controle que ele não tem ali."""
    from extensions import db
    from models.lgpd import ConsentimentoLgpd

    recepcao.post(f"/pacientes/{paciente_id}/consentimentos/registrar",
                  data={"finalidade": "assistencia"}, follow_redirects=True)
    with app.app_context():
        r = (ConsentimentoLgpd.query
             .filter_by(paciente_id=paciente_id, finalidade="assistencia")
             .order_by(ConsentimentoLgpd.id.desc()).first())
        assert r.revogavel is False
        ident = r.id

    resposta = recepcao.post(
        f"/pacientes/{paciente_id}/consentimentos/{ident}/revogar",
        follow_redirects=True)
    assert "tutela da saúde" in resposta.get_data(as_text=True), (
        "a recusa precisa dizer POR QUE, e o motivo é jurídico")

    with app.app_context():
        assert db.session.get(ConsentimentoLgpd, ident).revogado_em is None, (
            "revogou uma finalidade que não se apoia em consentimento")


def test_consentimento_de_pesquisa_e_revogavel(app, recepcao, paciente_id):
    from extensions import db
    from models.lgpd import ConsentimentoLgpd

    recepcao.post(f"/pacientes/{paciente_id}/consentimentos/registrar",
                  data={"finalidade": "pesquisa", "concedido": "1"},
                  follow_redirects=True)
    with app.app_context():
        r = (ConsentimentoLgpd.query
             .filter_by(paciente_id=paciente_id, finalidade="pesquisa")
             .order_by(ConsentimentoLgpd.id.desc()).first())
        assert r.revogavel is True
        ident = r.id

    recepcao.post(f"/pacientes/{paciente_id}/consentimentos/{ident}/revogar",
                  follow_redirects=True)
    with app.app_context():
        assert db.session.get(ConsentimentoLgpd, ident).revogado_em is not None


def test_finalidade_invalida_e_recusada(app, recepcao, paciente_id):
    """Finalidade fora do vocabulário gravaria base legal indefinida."""
    from models.lgpd import ConsentimentoLgpd

    with app.app_context():
        antes = ConsentimentoLgpd.query.filter_by(paciente_id=paciente_id).count()

    recepcao.post(f"/pacientes/{paciente_id}/consentimentos/registrar",
                  data={"finalidade": "marketing_agressivo"},
                  follow_redirects=True)

    with app.app_context():
        assert ConsentimentoLgpd.query.filter_by(
            paciente_id=paciente_id).count() == antes


def test_registro_de_consentimento_deixa_rastro(app, recepcao, paciente_id):
    """O art. 37 pede registro das operações de tratamento — inclusive desta."""
    from models.audit_log import AuditLog

    with app.app_context():
        antes = AuditLog.query.filter_by(tabela="consentimentos_lgpd",
                                         acao="create").count()

    recepcao.post(f"/pacientes/{paciente_id}/consentimentos/registrar",
                  data={"finalidade": "contato", "concedido": "1"},
                  follow_redirects=True)

    with app.app_context():
        depois = AuditLog.query.filter_by(tabela="consentimentos_lgpd",
                                          acao="create").count()
        assert depois > antes, "registro de base legal sem evento de auditoria"


def test_portal_do_cidadao_mostra_a_base_legal(app, recepcao, paciente_id):
    """Art. 9º: o titular tem direito de saber a finalidade e o fundamento."""
    recepcao.post(f"/pacientes/{paciente_id}/consentimentos/registrar",
                  data={"finalidade": "assistencia"}, follow_redirects=True)

    html = recepcao.get(
        f"/portal-cidadao/?paciente_id={paciente_id}").get_data(as_text=True)
    assert "Por que meus dados são tratados" in html
    assert "Tutela da saúde" in html, (
        "o portal não informa o fundamento do tratamento")
