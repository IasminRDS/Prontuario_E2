# -*- coding: utf-8 -*-
"""Comportamento que muda entre SQLite e PostgreSQL.

Em PostgreSQL o primeiro erro aborta a transação inteira: toda consulta seguinte
falha até um rollback. Em SQLite a sessão sobrevive sozinha. Um `except` que
engole o erro sem rollback funciona num e falha em cascata no outro — silenciosa
e com HTTP 200, que é o pior jeito de falhar.
"""
import pytest
import sqlalchemy as sa

from extensions import db


@pytest.fixture
def postgres(app):
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("comportamento específico de PostgreSQL")
        yield


@pytest.mark.postgres
def test_erro_engolido_sem_rollback_envenena_a_sessao(app, postgres):
    """Documenta o mecanismo — é a razão de existir dos rollbacks no código."""
    with app.app_context():
        db.session.execute(sa.text("select 1")).scalar()
        try:
            db.session.execute(sa.text("select coluna_inexistente from pacientes"))
        except Exception:
            pass  # exatamente o que o código fazia antes

        with pytest.raises(Exception, match="(?i)transaction|transação"):
            db.session.execute(sa.text("select count(*) from pacientes")).scalar()

        db.session.rollback()
        assert db.session.execute(sa.text("select count(*) from pacientes")).scalar() >= 0


@pytest.mark.postgres
def test_dashboard_nao_zera_tudo_apos_uma_falha(app, postgres, autenticado_confirmado):
    """Uma consulta com problema não pode derrubar os outros painéis.

    Antes do rollback em `_count`, injetar UMA falha zerava o dashboard inteiro
    e a tela respondia 200 sem nenhum sinal de erro.
    """
    import re
    from unittest.mock import patch

    import routes.dashboard as dashboard

    def valores(html):
        return re.findall(r'class="value">\s*([0-9]+)\s*<', html)

    normais = valores(autenticado_confirmado.get("/").get_data(as_text=True))

    original = dashboard._count
    chamadas = {"n": 0}

    def falha_na_primeira(*args, **kwargs):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            try:
                db.session.execute(sa.text("select inexistente from pacientes"))
            except Exception:
                pass  # sem rollback, imitando o defeito antigo
            return 0
        return original(*args, **kwargs)

    with patch.object(dashboard, "_count", falha_na_primeira):
        resposta = autenticado_confirmado.get("/")

    assert resposta.status_code == 200
    depois = valores(resposta.get_data(as_text=True))
    assert chamadas["n"] > 1, "o dashboard precisa chamar _count mais de uma vez"
    assert depois != ["0"] * len(depois) or normais == ["0"] * len(normais), (
        "uma única falha zerou todos os painéis: a sessão não se recuperou"
    )


@pytest.mark.postgres
@pytest.mark.parametrize("consulta", [
    "func.date sobre DateTime",
    "group_by com func.date",
    "ilike",
    "func.lower + ilike",
])
def test_agregacoes_do_dashboard_rodam_no_postgres(app, postgres, consulta):
    """As agregações ficam dentro de `try/except` que devolve zero.

    Sem exercitá-las fora do `except`, um erro de dialeto viraria "0" na tela em
    vez de falha — e ninguém saberia.
    """
    from datetime import date, timedelta

    from models.atendimento import Atendimento
    from models.paciente import Paciente

    with app.app_context():
        hoje = date.today()
        if consulta == "func.date sobre DateTime":
            Atendimento.query.filter(
                sa.func.date(Atendimento.criado_em) == hoje).count()
        elif consulta == "group_by com func.date":
            db.session.query(sa.func.date(Atendimento.criado_em),
                             sa.func.count(Atendimento.id)) \
                .filter(sa.func.date(Atendimento.criado_em) >= hoje - timedelta(days=7)) \
                .group_by(sa.func.date(Atendimento.criado_em)).all()
        elif consulta == "ilike":
            Paciente.query.filter(Paciente.nome.ilike("%a%")).count()
        else:
            Paciente.query.filter(sa.func.lower(Paciente.nome).ilike("%a%")).count()


def test_migrations_e_models_nao_divergem(app):
    """`flask db check` em forma de teste: schema declarado == schema aplicado."""
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    with app.app_context():
        with db.engine.connect() as conexao:
            contexto = MigrationContext.configure(conexao)
            diferencas = compare_metadata(contexto, db.metadata)

    # `create_all` monta o schema a partir dos models, então divergência aqui
    # significa metadata inconsistente consigo mesma.
    assert not diferencas, f"models divergem do schema aplicado: {diferencas}"
