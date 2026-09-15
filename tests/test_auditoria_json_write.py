# -*- coding: utf-8 -*-
"""Escrita pela API JSON deixa rastro, e na MESMA transação da mutação.

A 9.4.4 do TCC corrigiu a auditoria das rotas de LEITURA. Estas são as de
ESCRITA da API JSON, que tinham dois defeitos distintos e opostos:

**Em `pacientes`, rastro nenhum.** O padrão era `db.session.commit()` e só
depois `auditar_aqui(...)`, que por omissão apenas anexa à sessão. A transação
da escrita já tinha fechado, e o evento era anexado a uma sessão nova que
ninguém confirmava. Criar, alterar e desativar paciente pela API não deixava
rastro algum — verificado disparando a rota, não lendo o código.

**Em `prontuarios`, rastro sem atomicidade.** O decorator `@audit_log` roda
ANTES da view e commita em transação própria. Havia rastro, mas ele registrava
a *intenção*, não o *fato*: se a mutação falhasse depois, a trilha afirmava que
o prontuário fora assinado. É o inverso da garantia que o trabalho declara — "ou
ambas persistem, ou nenhuma persiste". O `auditar_aqui` que vinha depois do
commit era um segundo evento, esse sim perdido: código morto que dava a
impressão de cobertura.

Ambos são da família que esta suíte caça: não geram erro, só deixam de registrar.
"""
import json
from datetime import date

import pytest

from tests.conftest import PERFIS, autenticar


def db_get(modelo, ident):
    from extensions import db

    return db.session.get(modelo, ident)


@pytest.fixture
def admin(app, dados_clinicos):
    return autenticar(app, PERFIS["admin"][1])


@pytest.fixture
def medico(app, dados_clinicos):
    return autenticar(app, PERFIS["medico"][1])


def _contar(app, tabela, acao):
    from models.audit_log import AuditLog

    with app.app_context():
        return AuditLog.query.filter_by(tabela=tabela, acao=acao).count()


def _paciente_id(app):
    from models.paciente import Paciente

    with app.app_context():
        return Paciente.query.order_by(Paciente.id.asc()).first().id


def _prontuario_id(app):
    from models.prontuario import Prontuario

    with app.app_context():
        p = Prontuario.query.order_by(Prontuario.id.asc()).first()
        return p.id if p else None


@pytest.fixture
def paciente_do_medico(app, medico):
    """Um paciente no município da unidade do médico, restaurado ao final.

    O que se mede aqui é a auditoria, não a autorização: com o paciente fora do
    escopo a rota devolve 403 antes de chegar à escrita, e o teste passaria a
    medir o controle errado — ou viraria `skip` e deixaria de medir qualquer
    coisa.

    Alinhar o PACIENTE à unidade, e não elevar o nível do usuário: `ESTADO` sem
    `uf` preenchida é escopo irresolúvel, e o RLS então nega até o INSERT — o
    que é o comportamento correto do sistema e a razão de não servir aqui.
    """
    from extensions import db
    from models.paciente import Paciente
    from models.user import User

    with app.app_context():
        usuario = User.query.filter_by(email=PERFIS["medico"][1]).first()
        unidade = usuario.unidade
        assert unidade is not None, "o médico semeado precisa ter unidade"

        paciente = Paciente.query.order_by(Paciente.id.asc()).first()
        anterior = (paciente.municipio, paciente.uf)
        paciente.municipio, paciente.uf = unidade.municipio, unidade.uf
        db.session.commit()
        alvo = paciente.id

    yield alvo

    with app.app_context():
        paciente = db.session.get(Paciente, alvo)
        paciente.municipio, paciente.uf = anterior
        db.session.commit()


# --- pacientes: não havia rastro nenhum ----------------------------------

def test_criar_paciente_deixa_rastro(app, admin, sem_csrf):
    antes = _contar(app, "pacientes", "create")
    resposta = admin.post("/pacientes/", data=json.dumps({
        "nome": "Auditoria de Escrita JSON",
        "data_nascimento": "1990-01-01",
        "sexo": "F",
    }), content_type="application/json")

    assert resposta.status_code in (200, 201), resposta.get_data(as_text=True)
    assert _contar(app, "pacientes", "create") > antes, (
        "paciente criado e nenhum evento persistiu")


def test_rastro_da_criacao_identifica_o_paciente(app, admin, sem_csrf):
    """Evento sem `registro_id` não responde 'quem foi alterado' — que é a
    pergunta que a trilha existe para responder."""
    from models.audit_log import AuditLog

    resposta = admin.post("/pacientes/", data=json.dumps({
        "nome": "Auditoria Com Identificador",
        "data_nascimento": "1985-03-02",
        "sexo": "M",
    }), content_type="application/json")
    criado = resposta.get_json()["id"]

    with app.app_context():
        evento = (AuditLog.query
                  .filter_by(tabela="pacientes", acao="create")
                  .order_by(AuditLog.id.desc()).first())
        assert evento.registro_id == criado, (
            f"o evento aponta para {evento.registro_id}, não para {criado}")


def test_atualizar_paciente_deixa_rastro(app, cliente_super, sem_csrf):
    # SuperAdmin: o alvo é o rastro da escrita, não a autorização. O `admin`
    # (Administrador) só edita paciente da própria unidade, e o paciente semeado
    # cai fora — devolveria 403 antes de chegar à escrita, medindo o controle
    # errado. Alcance nacional é do perfil SuperAdmin.
    antes = _contar(app, "pacientes", "update")
    alvo = _paciente_id(app)
    resposta = cliente_super.put(f"/pacientes/{alvo}", data=json.dumps(
        {"observacoes": "anotação de teste"}), content_type="application/json")

    assert resposta.status_code == 200, resposta.get_data(as_text=True)
    assert _contar(app, "pacientes", "update") > antes


# --- prontuários: havia rastro, faltava atomicidade ----------------------

def test_criar_prontuario_deixa_rastro(app, medico, paciente_do_medico, sem_csrf):
    antes = _contar(app, "prontuarios", "create")
    resposta = medico.post("/prontuarios/", data=json.dumps({
        "paciente_id": paciente_do_medico,
        "queixa_principal": "Cefaleia ha tres dias",
        "conduta": "Analgesia e retorno em sete dias",
    }), content_type="application/json")

    assert resposta.status_code in (200, 201), resposta.get_data(as_text=True)
    assert _contar(app, "prontuarios", "create") > antes


def test_assinar_prontuario_deixa_rastro(app, medico, paciente_do_medico,
                                         sem_csrf):
    alvo = _prontuario_id(app)
    if alvo is None:
        pytest.skip("sem prontuário semeado")

    antes = _contar(app, "prontuarios", "sign")
    resposta = medico.post(f"/prontuarios/{alvo}/assinar")

    assert resposta.status_code == 200, resposta.get_data(as_text=True)
    # Assinar duas vezes é no-op declarado pela rota; só exigimos rastro quando
    # a assinatura de fato aconteceu.
    if "já estava assinado" not in resposta.get_data(as_text=True):
        assert _contar(app, "prontuarios", "sign") > antes


# --- a data que só um dos dois bancos aceitava ---------------------------
#
# Achado de tabela: a rota entregava `data_nascimento` como string crua ao
# model. O driver do PostgreSQL converte por conta própria; o do SQLite recusa
# com TypeError. Criar paciente pela API funcionava num banco e falhava no
# outro, e em nenhum dos dois a data era validada.

def test_criar_paciente_converte_a_data(app, admin, sem_csrf):
    from models.paciente import Paciente

    resposta = admin.post("/pacientes/", data=json.dumps({
        "nome": "Data Convertida",
        "data_nascimento": "1974-11-30",
        "sexo": "F",
    }), content_type="application/json")
    assert resposta.status_code in (200, 201), resposta.get_data(as_text=True)

    with app.app_context():
        p = db_get(Paciente, resposta.get_json()["id"])
        assert p.data_nascimento == date(1974, 11, 30)


@pytest.mark.parametrize("valor", ["30/11/1974", "1974-13-01", "ontem", ""])
def test_data_invalida_e_recusada_com_mensagem(app, admin, sem_csrf, valor):
    """Sem isto a data inválida chegava ao banco e o erro saía como 500 do
    driver, com o texto em inglês e o SQL inteiro na resposta."""
    resposta = admin.post("/pacientes/", data=json.dumps({
        "nome": "Data Invalida",
        "data_nascimento": valor,
        "sexo": "F",
    }), content_type="application/json")

    assert resposta.status_code == 400, resposta.get_data(as_text=True)
    assert "ata de nascimento" in resposta.get_json()["erro"]


# --- detector estático: impede o padrão de voltar ------------------------

def test_nenhuma_rota_audita_depois_de_fechar_a_transacao():
    """Auditoria depois do `commit`, sem `commit=True`, é evento descartado.

    Detector e não revisão: o defeito não gera erro, e reapareceu em duas
    blueprints distintas escritas em momentos diferentes. Enquanto o padrão for
    escrevível, ele volta.
    """
    import pathlib
    import re

    raiz = pathlib.Path(__file__).resolve().parent.parent
    chamada = re.compile(r"\b(auditar_aqui|registrar)\s*\(")
    commit = re.compile(r"db\.session\.commit\(\)")

    infratores = []
    for caminho in sorted((raiz / "routes").glob("*.py")):
        linhas = caminho.read_text(encoding="utf-8").splitlines()
        ultimo_commit = None
        for n, linha in enumerate(linhas, 1):
            if commit.search(linha):
                ultimo_commit = n
            if chamada.search(linha):
                trecho = "\n".join(linhas[n - 1:n + 3])
                if (ultimo_commit is not None
                        and 0 < n - ultimo_commit <= 5
                        and "commit=True" not in trecho):
                    infratores.append(f"routes/{caminho.name}:{n}")

    assert not infratores, (
        "auditoria chamada logo após o commit, sem commit=True — o evento é "
        "anexado a uma sessão que ninguém confirma: " + ", ".join(infratores))
