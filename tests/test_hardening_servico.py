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


def test_nao_verificavel_nao_e_reprovacao(app):
    """O terceiro estado existe e não pode virar `False` numa refatoração.

    Colapsar "não verificável" em "falhou" faz o comando reprovar para sempre
    em qualquer ambiente que não exponha o atributo — e quem convive com um
    portão que sempre reprova aprende a passar por ele sem olhar. A distinção é
    o que mantém a reprovação significando alguma coisa.
    """
    from services.hardening import Achado

    passou = Achado("x", True)
    reprovou = Achado("y", False)
    indefinido = Achado("z", None)

    achados = [passou, reprovou, indefinido]
    assert [a for a in achados if a.ok is False] == [reprovou]
    assert [a for a in achados if a.ok is None] == [indefinido]
    # `not a.ok` é justamente a expressão que confunde os dois — o teste fixa
    # que ela NÃO é a usada para decidir o código de saída.
    assert not indefinido.ok, (
        "se isto falhar, `None` deixou de ser falsy e o comentário sobre por "
        "que não se usa `not a.ok` perdeu o sentido")


def test_journal_ausente_reprova_de_verdade(app, tmp_path, monkeypatch):
    """Sem journal não há o que comparar — isso é falha, não indefinição."""
    from services.hardening import _journal_append_only

    monkeypatch.setenv("ANCORA_JOURNAL", str(tmp_path / "nao_existe.jsonl"))
    achado = _journal_append_only()

    assert achado.ok is False, (
        "journal ausente precisa REPROVAR: não é limitação do ambiente, é "
        "ausência do próprio artefato que se pretende proteger")


def test_indefinido_nao_contamina_o_codigo_de_saida(app, monkeypatch):
    """O contrato operacional: `?` reporta, `FALHA` reprova. Só isso decide.

    Pinar a SEMÂNTICA e não o texto é deliberado. Congelar as mensagens faria
    de toda melhoria de redação uma reprovação, e o hábito de atualizar o
    snapshot sem ler é como um teste deixa de medir. O que não pode mudar em
    silêncio é: quantas verificações reprovam, e com que código o comando sai.
    """
    import services.hardening as hardening
    from services.hardening import Achado

    monkeypatch.setattr(hardening, "verificar", lambda: [
        Achado("passa", True),
        Achado("não dá para saber aqui", None, "sem suporte no SO",
               "chattr +a caminho"),
    ])

    resultado = app.test_cli_runner().invoke(args=["hardening-check"])

    assert resultado.exit_code == 0, (
        "uma verificação NÃO VERIFICÁVEL reprovou o comando — um portão que "
        "reprova para sempre nesta máquina ensina a passar sem olhar")
    assert "?" in resultado.output
    assert "não é aprovação" in resultado.output, (
        "o comando saiu com 0 sem dizer que há verificação não feita — "
        "silêncio aqui é lido como aprovação")


def test_falha_de_verdade_ainda_reprova(app, monkeypatch):
    """O outro lado: o terceiro estado não pode ter amolecido o portão."""
    import services.hardening as hardening
    from services.hardening import Achado

    monkeypatch.setattr(hardening, "verificar", lambda: [
        Achado("passa", True),
        Achado("não dá para saber aqui", None, "sem suporte no SO"),
        Achado("reprova mesmo", False, "isto é uma falha real"),
    ])

    resultado = app.test_cli_runner().invoke(args=["hardening-check"])

    assert resultado.exit_code == 1
    assert "1 verificação(ões) falharam" in resultado.output, (
        "a contagem de falhas passou a incluir o indefinido, ou deixou de "
        "contar a falha real")
