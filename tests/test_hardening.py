# -*- coding: utf-8 -*-
"""Regressões dos achados de ALTO impacto da auditoria de produção.

Cada teste aqui corresponde a uma falha que existiu e foi corrigida. O caso
NEGATIVO é o que importa em todos: provar que a porta fecha, não que ela abre.
"""
import os

import pytest

from tests.conftest import PERFIS, autenticar


# ------------------------------------------------ 1. configuração segura
def test_producao_exige_cookie_seguro():
    from config import ProductionConfig

    assert ProductionConfig.SESSION_COOKIE_SECURE is True
    assert ProductionConfig.SESSION_COOKIE_HTTPONLY is True
    assert ProductionConfig.SESSION_COOKIE_SAMESITE == "Lax"
    assert ProductionConfig.DEBUG is False


def test_app_env_ausente_ou_invalida_falha_em_vez_de_cair_em_dev(monkeypatch):
    """O recuo silencioso para dev punha DEBUG=True e cookie sem Secure em
    produção sempre que APP_ENV faltasse ou viesse escrita errado."""
    from config import get_config_class

    for valor in (None, "", "   ", "production", "PRODUÇÃO", "prd", "test"):
        if valor is None:
            monkeypatch.delenv("APP_ENV", raising=False)
        else:
            monkeypatch.setenv("APP_ENV", valor)
        with pytest.raises(RuntimeError):
            get_config_class()


def test_app_env_valida_resolve(monkeypatch):
    from config import DevelopmentConfig, ProductionConfig, get_config_class

    monkeypatch.setenv("APP_ENV", "prod")
    assert get_config_class() is ProductionConfig
    monkeypatch.setenv("APP_ENV", " DEV ")
    assert get_config_class() is DevelopmentConfig


# ------------------------------------------------ 2. ferramentas de PDF
def test_saida_do_pdf_nao_usa_nome_previsivel():
    """`reorg_{nome_do_arquivo}` fazia dois usuários com "laudo.pdf" gravarem no
    mesmo caminho: um baixava o documento clínico do outro."""
    fonte = (
        __import__("pathlib").Path("routes/pdf.py").read_text(encoding="utf-8")
    )
    assert 'f"reorg_{nome_seguro}"' not in fonte, (
        "caminho de saída derivado do nome enviado pelo usuário")
    assert 'f"reorg_{nome_temp}"' in fonte, (
        "a saída precisa herdar o identificador único da entrada")


def test_ferramentas_de_pdf_nao_deixam_arquivo_para_tras(app, tmp_path):
    """O `finally` só apagava a entrada; o processado ficava em `instance/`."""
    import pathlib

    fonte = pathlib.Path("routes/pdf.py").read_text(encoding="utf-8")
    # Os dois `finally` devem varrer entrada E saída.
    assert fonte.count("for caminho in (caminho_temp, caminho_saida):") == 2, (
        "algum caminho de processamento ainda não remove o arquivo de saída")


# ------------------------------------------------ 3. portal do cidadão
@pytest.fixture
def paciente_de_outra_unidade(app, dados_clinicos):
    """Paciente fora do escopo territorial dos usuários de teste."""
    from datetime import date

    from extensions import db
    from models.paciente import Paciente

    with app.app_context():
        p = Paciente(nome="Fora do Escopo", ativo=True,
                     data_nascimento=date(1980, 1, 1), sexo="F",
                     municipio="Municipio Distante", uf="AC")
        db.session.add(p)
        db.session.commit()
        pid = p.id
    yield pid
    with app.app_context():
        alvo = db.session.get(Paciente, pid)
        if alvo is not None:
            db.session.delete(alvo)
            db.session.commit()


def test_portal_nega_paciente_fora_do_escopo(app, paciente_de_outra_unidade):
    """CASO NEGATIVO: perfil clínico de unidade não alcança paciente de outra.

    Era a falha: `Paciente.query.get(paciente_id)` sem checagem nenhuma, e
    qualquer `clinical:read` lia o cartão de vacinas e a trilha de acessos de
    qualquer cidadão por `?paciente_id=N`.
    """
    cliente = autenticar(app, PERFIS["medico"][1])
    resposta = cliente.get(
        f"/portal-cidadao/?paciente_id={paciente_de_outra_unidade}")
    assert resposta.status_code == 403, (
        f"portal devolveu {resposta.status_code} para paciente fora do escopo")


def test_trilha_de_acesso_nao_mistura_pacientes(app, dados_clinicos):
    """`registro_id` é a chave da tabela auditada, não a do paciente.

    Comparar `registro_id == paciente.id` para "prontuarios", "internacoes" etc.
    fazia a trilha do paciente #5 listar acessos ao prontuário #5 de OUTRA
    pessoa — dado errado numa tela de transparência LGPD, e vazamento.
    """
    from models.paciente import Paciente
    from routes.portal_cidadao import _registros_do_paciente

    with app.app_context():
        paciente = Paciente.query.order_by(Paciente.id.asc()).first()
        por_tabela = _registros_do_paciente(paciente)

        assert por_tabela.get("pacientes") == {paciente.id}
        for nome, ids in por_tabela.items():
            if nome == "pacientes":
                continue
            from extensions import db
            tabela = db.metadata.tables[nome]
            donos = db.session.execute(
                db.select(tabela.c.paciente_id).where(tabela.c.id.in_(ids))
            ).scalars().all()
            assert set(donos) == {paciente.id}, (
                f"{nome} trouxe registro de outro paciente: {set(donos)}")


# ------------------------------------------------ 4. auditoria de leitura
@pytest.mark.parametrize("url,tabela", [
    ("/pacientes/", "pacientes"),
    ("/pacientes/api", "pacientes"),
    ("/prontuarios/?formato=json", "prontuarios"),
])
def test_leitura_de_dado_clinico_deixa_rastro(app, dados_clinicos, url, tabela):
    """LGPD art. 37: a leitura precisa ficar registrada de fato.

    `auditar_aqui(commit=False)` só faz `db.session.add`; em rota de leitura não
    há transação de escrita para carregar o log, e não existe hook global de
    commit — o único `after_request` do projeto só aplica cabeçalhos. O evento
    era descartado no fim da requisição.
    """
    from models.audit_log import AuditLog

    cliente = autenticar(app, PERFIS["admin"][1])

    with app.app_context():
        antes = AuditLog.query.filter_by(tabela=tabela).count()

    assert cliente.get(url).status_code == 200

    with app.app_context():
        depois = AuditLog.query.filter_by(tabela=tabela).count()

    assert depois > antes, (
        f"GET {url} não gravou auditoria em {tabela}: {antes} -> {depois}")
