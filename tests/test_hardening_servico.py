# -*- coding: utf-8 -*-
"""O verificador de endurecimento — que até aqui não tinha teste algum.

`services/hardening.py` era o arquivo com cobertura ZERO da suíte. Isso importa
porque ele é o instrumento que decide se a fronteira entre garantia da aplicação
e dependência de infraestrutura está de pé.

O teste nasceu de um defeito concreto e caro. A receita que ele prescrevia para
tirar `audit_logs` do papel da aplicação transferia a tabela e concedia INSERT,
mas **não a USAGE na sequência**, que muda de dono junto no `ALTER TABLE OWNER`.
Aplicada a receita, a aplicação parou de conseguir auditar — e as sete
verificações continuaram passando, porque nenhuma perguntava se ela ainda
auditava.

Endurecimento que impede o registro é pior que a lacuna que ele fecha: a trilha
para de crescer, nada acusa, e a ausência de eventos fica indistinguível da
ausência de acessos. É a mesma família de 9.4.2 e 9.4.9 da monografia — o
instrumento de verificação afetado pelo defeito que verifica.
"""
import pytest

from services import hardening


@pytest.fixture
def postgres(app):
    from extensions import db

    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("as verificações consultam catálogos do PostgreSQL")
    return True


def test_verificar_devolve_achados_completos(app, postgres):
    """Todo achado precisa de nome e, quando falha, de como corrigir.

    Achado sem correção transfere ao operador o trabalho de descobrir o comando
    — e é nesse ponto que ele improvisa e quebra outra coisa.
    """
    with app.app_context():
        achados = hardening.verificar()

    assert achados, "o verificador não produziu achado nenhum"
    for a in achados:
        assert a.nome, "achado sem nome"
        if not a.ok:
            assert a.correcao, f"{a.nome}: falha sem instrução de correção"
            assert a.detalhe, f"{a.nome}: falha sem explicação do porquê"


def test_verifica_que_a_aplicacao_ainda_audita(app, postgres):
    """A verificação que faltava, e sem a qual a receita quebrava o sistema."""
    with app.app_context():
        nomes = [a.nome for a in hardening.verificar()]

    assert any("ainda consegue registrar auditoria" in n for n in nomes), (
        "sem esta verificação, endurecer a auditoria pode impedir a auditoria "
        "e as demais continuam passando")


def test_a_receita_de_propriedade_inclui_a_sequencia(app, postgres):
    """Guarda contra a regressão exata que motivou este arquivo.

    `ALTER TABLE ... OWNER TO` leva a sequência junto. Conceder INSERT na tabela
    sem USAGE na sequência produz "permissão negada para sequência" no primeiro
    registro — depois de o operador ter seguido a instrução à risca.
    """
    with app.app_context():
        achados = {a.nome: a for a in hardening.verificar()}

    dono = next((a for n, a in achados.items() if "não pertence ao papel" in n),
                None)
    assert dono is not None, "a verificação de propriedade sumiu"
    assert "SEQUENCE" in dono.correcao.upper(), (
        "a receita concede INSERT e esquece a sequência — foi assim que o "
        "endurecimento passou na própria verificação e parou a auditoria")


def test_todo_achado_e_afirmacao_verificavel(app, postgres):
    """Nome de achado precisa dizer o que está sendo afirmado, não o que se mede.

    "papel sem BYPASSRLS" é afirmação; "checagem 3" não é. O relatório é lido
    por quem não escreveu o código, e é ele que vira evidência de auditoria.
    """
    with app.app_context():
        achados = hardening.verificar()

    for a in achados:
        assert len(a.nome) > 12, f"nome pouco informativo: {a.nome!r}"
        assert not a.nome.lower().startswith(("check", "verificacao ", "teste")), (
            f"nome sem conteúdo: {a.nome!r}")
