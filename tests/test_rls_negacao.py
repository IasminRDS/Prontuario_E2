# -*- coding: utf-8 -*-
"""Testes de NEGAÇÃO do isolamento territorial.

`test_rls.py` prova que as políticas existem e estão em FORCE. Isso é condição
necessária e não suficiente: política presente que não nega nada passa naquele
teste. Aqui a pergunta é a inversa e é a que importa — **tentando violar o
isolamento, o banco recusa?**

Cada caso escreve um registro de OUTRA unidade e depois tenta alcançá-lo com o
escopo de uma unidade diferente. O êxito do teste é o dado NÃO aparecer.

Estes testes rodam contra o banco diretamente, sem passar pelo filtro em Python
da aplicação. É deliberado: o que se está medindo é a defesa de profundidade, ou
seja, o que sobra quando o filtro da aplicação falha. Um teste que passasse pela
aplicação provaria os dois controles juntos e não distinguiria qual deles
funcionou.
"""
import pytest
import sqlalchemy as sa

from extensions import db
from utils import rls


@pytest.fixture
def postgres(app):
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("RLS só existe em PostgreSQL")
    return True


@pytest.fixture
def duas_unidades(app, postgres):
    """Duas unidades em municípios distintos, com um registro clínico em cada."""
    from models.unidade_saude import UnidadeSaude

    with app.app_context():
        a = UnidadeSaude(nome="Hospital A", tipo="hospital",
                         cidade="Cidade A", uf="BA", ativo=True)
        b = UnidadeSaude(nome="Hospital B", tipo="hospital",
                         cidade="Cidade B", uf="PE", ativo=True)
        db.session.add_all([a, b])
        db.session.commit()
        ids = (a.id, b.id)
    yield ids
    with app.app_context():
        for uid in ids:
            alvo = db.session.get(UnidadeSaude, uid)
            if alvo is not None:
                db.session.delete(alvo)
        db.session.commit()


def _com_escopo(conexao, nivel, unidade_id=None):
    """Publica o escopo na sessão do banco, como a aplicação faz por transação."""
    conexao.exec_driver_sql(f"SET LOCAL app.nivel = '{nivel}'")
    if unidade_id is not None:
        conexao.exec_driver_sql(f"SET LOCAL app.unidade_id = '{unidade_id}'")
    else:
        conexao.exec_driver_sql("SET LOCAL app.unidade_id = ''")


@pytest.mark.parametrize("tabela", [
    "internacoes", "prontuarios", "triagens",
    # As cinco que estavam FORA do RLS até a migration b7f4c2e91a08. São o
    # motivo desta suíte existir: o mecanismo estava certo e não as cobria.
    "cirurgias", "encaminhamentos", "atendimentos_ps",
    "evolucoes_internacao", "itens_prescricao",
])
def test_tabela_clinica_esta_no_escopo(app, postgres, tabela):
    """Toda tabela clínica listada precisa estar sob política.

    Falha aqui significa regressão da correção: alguém removeu `unidade_id` ou
    a tabela saiu da lista derivada do metadata.
    """
    with app.app_context():
        protegidas = set(rls.tabelas_protegidas(db.metadata))
        assert tabela in protegidas, (
            f"{tabela} não está sob política de RLS — o isolamento dela depende "
            "só do filtro em Python")


def _inserir_internacao(conexao, unidade_id):
    return conexao.exec_driver_sql(
        "INSERT INTO internacoes "
        "(paciente_id, leito_id, unidade_id, status, data_entrada, motivo) "
        "SELECT (SELECT min(id) FROM pacientes), (SELECT min(id) FROM leitos), "
        "       %(u)s, 'ativa', now(), 'teste de negacao' "
        "RETURNING id", {"u": unidade_id}).scalar()


def test_leitura_cruzada_entre_unidades_e_negada(app, duas_unidades,
                                                 dados_clinicos):
    """Grava com escopo de sistema; tenta ler com escopo de cada unidade."""
    unidade_a, unidade_b = duas_unidades

    with app.app_context():
        with db.engine.begin() as conexao:
            _com_escopo(conexao, "SISTEMA")
            id_b = _inserir_internacao(conexao, unidade_b)

        try:
            with db.engine.begin() as conexao:
                _com_escopo(conexao, "UNIDADE", unidade_a)
                achou = conexao.exec_driver_sql(
                    "SELECT count(*) FROM internacoes WHERE id = %(i)s",
                    {"i": id_b}).scalar()
            assert achou == 0, "unidade A leu internação da unidade B"

            with db.engine.begin() as conexao:
                _com_escopo(conexao, "UNIDADE", unidade_b)
                achou = conexao.exec_driver_sql(
                    "SELECT count(*) FROM internacoes WHERE id = %(i)s",
                    {"i": id_b}).scalar()
            assert achou == 1, (
                "a unidade dona não enxergou o próprio registro — a política "
                "está negando demais, o que é falha de disponibilidade")
        finally:
            with db.engine.begin() as conexao:
                _com_escopo(conexao, "SISTEMA")
                conexao.exec_driver_sql(
                    "DELETE FROM internacoes WHERE id = %(i)s", {"i": id_b})


def test_escopo_ausente_nao_libera_nada(app, duas_unidades, dados_clinicos):
    """Falha fechada: sem escopo, a política não pode liberar."""
    _unidade_a, unidade_b = duas_unidades

    with app.app_context():
        with db.engine.begin() as conexao:
            _com_escopo(conexao, "SISTEMA")
            id_b = _inserir_internacao(conexao, unidade_b)

        try:
            with db.engine.begin() as conexao:
                conexao.exec_driver_sql("SET LOCAL app.nivel = ''")
                conexao.exec_driver_sql("SET LOCAL app.unidade_id = ''")
                achou = conexao.exec_driver_sql(
                    "SELECT count(*) FROM internacoes").scalar()
            assert achou == 0, (
                "sem escopo definido o banco liberou linhas — a política está "
                "falhando ABERTA, que é o pior modo de falha possível")
        finally:
            with db.engine.begin() as conexao:
                _com_escopo(conexao, "SISTEMA")
                conexao.exec_driver_sql(
                    "DELETE FROM internacoes WHERE id = %(i)s", {"i": id_b})


def test_escopo_invalido_nao_libera(app, postgres, dados_clinicos):
    """Nível desconhecido tem de cair no mais restrito, não no mais permissivo."""
    with app.app_context():
        with db.engine.begin() as conexao:
            conexao.exec_driver_sql("SET LOCAL app.nivel = 'ADMINISTRADOR_GERAL'")
            conexao.exec_driver_sql("SET LOCAL app.unidade_id = '1'")
            achou = conexao.exec_driver_sql(
                "SELECT count(*) FROM internacoes").scalar()
        assert achou == 0, "nível inventado liberou leitura"


def test_escopo_nao_sobrevive_a_transacao(app, duas_unidades, dados_clinicos):
    """`SET LOCAL` precisa morrer com a transação, ou vaza pelo pool.

    Sem isso, uma requisição herdaria o escopo da anterior na mesma conexão — e
    o vazamento seria intermitente, dependente de qual conexão o pool entregasse.
    """
    _unidade_a, unidade_b = duas_unidades

    with app.app_context():
        with db.engine.begin() as conexao:
            _com_escopo(conexao, "SISTEMA")
            id_b = _inserir_internacao(conexao, unidade_b)

        try:
            with db.engine.connect() as conexao:
                with conexao.begin():
                    _com_escopo(conexao, "SISTEMA")
                    assert conexao.exec_driver_sql(
                        "SELECT count(*) FROM internacoes WHERE id = %(i)s",
                        {"i": id_b}).scalar() == 1

                # Transação nova, MESMA conexão: o escopo anterior não vale mais.
                with conexao.begin():
                    achou = conexao.exec_driver_sql(
                        "SELECT count(*) FROM internacoes WHERE id = %(i)s",
                        {"i": id_b}).scalar()
                assert achou == 0, (
                    "o escopo SISTEMA sobreviveu à transação e vazou para a "
                    "seguinte na mesma conexão")
        finally:
            with db.engine.begin() as conexao:
                _com_escopo(conexao, "SISTEMA")
                conexao.exec_driver_sql(
                    "DELETE FROM internacoes WHERE id = %(i)s", {"i": id_b})
