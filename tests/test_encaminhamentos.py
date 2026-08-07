# -*- coding: utf-8 -*-
"""Solicitação de encaminhamento: o dado precisa SOBREVIVER ao POST.

`templates/encaminhamentos/form.html` era **byte a byte igual** a
`templates/triagem/form.html` — o `page_title` dizia "Triagem — Classificação de
Risco". A tela pedia queixa, escala de dor, discriminadores e cor de Manchester;
a rota lê especialidade, motivo, prioridade, CID e hipótese diagnóstica. Só
`paciente_id` e `observacoes` coincidiam.

O efeito: era impossível encaminhar alguém pela tela. Sem `especialidade` e sem
`motivo` — os dois obrigatórios — a rota parava na validação e devolvia o aviso,
enquanto tudo que a pessoa preenchera (a classificação de risco inteira) ia para
o lixo. Ao contrário do que houve na cirurgia, aqui a ROTA estava correta: todos
os argumentos batiam com colunas reais do model, e por isso a correção foi só do
template.
"""
import re

import pytest

from tests.conftest import PERFIS, autenticar


def _token(html):
    achado = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return achado.group(1) if achado else ""


@pytest.fixture
def solicitante(app, dados_clinicos):
    """Médico: a rota exige `regulation:write`, que a enfermagem não tem."""
    return autenticar(app, PERFIS["medico"][1])


@pytest.fixture
def paciente_id(app, dados_clinicos):
    from models.paciente import Paciente

    with app.app_context():
        return Paciente.query.order_by(Paciente.id.asc()).first().id


@pytest.fixture
def limpar_encaminhamentos(app):
    from extensions import db
    from models.encaminhamento import Encaminhamento

    with app.app_context():
        existentes = {e.id for e in Encaminhamento.query.all()}
    yield
    with app.app_context():
        for enc in Encaminhamento.query.all():
            if enc.id not in existentes:
                db.session.delete(enc)
        db.session.commit()


def _postar(cliente, campos):
    pagina = cliente.get("/encaminhamentos/novo").get_data(as_text=True)
    dados = {"csrf_token": _token(pagina)}
    dados.update(campos)
    return cliente.post("/encaminhamentos/novo", data=dados, follow_redirects=True)


def test_solicitar_grava_o_encaminhamento(app, solicitante, paciente_id,
                                          limpar_encaminhamentos):
    from models.encaminhamento import Encaminhamento

    resposta = _postar(solicitante, {
        "paciente_id": paciente_id,
        "especialidade": "Cardiologia",
        "prioridade": "urgencia",
        "servico_destino": "Ambulatorio de referencia",
        "cid": "i10",
        "hipotese_diagnostica": "Hipertensao de dificil controle",
        "motivo": "Tres anti-hipertensivos em dose plena sem controle pressorico.",
        "observacoes": "paciente trouxe MAPA",
    })
    assert resposta.status_code == 200

    with app.app_context():
        enc = (Encaminhamento.query
               .filter_by(especialidade="Cardiologia")
               .order_by(Encaminhamento.id.desc())
               .first())

        assert enc is not None, "o POST respondeu e nada foi gravado"
        assert enc.paciente_id == paciente_id
        assert enc.prioridade == "urgencia"
        assert enc.servico_destino == "Ambulatorio de referencia"
        # A rota normaliza o CID para maiúsculas.
        assert enc.cid == "I10", f"CID gravado como {enc.cid!r}"
        assert enc.hipotese_diagnostica == "Hipertensao de dificil controle"
        assert enc.motivo.startswith("Tres anti-hipertensivos")
        assert enc.observacoes == "paciente trouxe MAPA"
        assert enc.status == "solicitado"
        # Obrigatória no model; a rota a resolve pela unidade de quem solicita.
        assert enc.unidade_origem_id is not None


def test_prioridade_invalida_cai_em_eletivo(app, solicitante, paciente_id,
                                            limpar_encaminhamentos):
    """A rota só aceita prioridade da lista; qualquer outra vira eletivo."""
    from models.encaminhamento import Encaminhamento

    _postar(solicitante, {
        "paciente_id": paciente_id,
        "especialidade": "Neurologia",
        "prioridade": "inventada",
        "motivo": "Cefaleia refrataria.",
    })

    with app.app_context():
        enc = (Encaminhamento.query.filter_by(especialidade="Neurologia")
               .order_by(Encaminhamento.id.desc()).first())
        assert enc is not None
        assert enc.prioridade == "eletivo"


@pytest.mark.parametrize("faltando,aviso", [
    ("especialidade", "Informe a especialidade"),
    ("motivo", "motivo do encaminhamento"),
])
def test_campo_obrigatorio_ausente_nao_grava(app, solicitante, paciente_id,
                                             limpar_encaminhamentos,
                                             faltando, aviso):
    from models.encaminhamento import Encaminhamento

    campos = {
        "paciente_id": paciente_id,
        "especialidade": "Ortopedia",
        "motivo": "Dor lombar cronica.",
    }
    campos[faltando] = ""

    with app.app_context():
        antes = Encaminhamento.query.count()

    resposta = _postar(solicitante, campos)

    with app.app_context():
        assert Encaminhamento.query.count() == antes, f"gravou sem {faltando}"
    assert aviso in resposta.get_data(as_text=True)


def test_formulario_e_o_de_encaminhamento(solicitante):
    """Guarda contra a cópia da triagem voltar."""
    html = solicitante.get("/encaminhamentos/novo").get_data(as_text=True)
    assert "Classificação de Risco" not in html
    assert 'name="especialidade"' in html, "o formulário não pede a especialidade"
    assert 'name="motivo"' in html, "o formulário não pede o motivo"
    assert 'name="discriminadores"' not in html, "voltou a ser a triagem"


# --- vocabulário de prioridade -------------------------------------------
#
# O vocabulário já esteve escrito em cinco lugares com três conteúdos: a rota
# gravava `prioritario`, o model não sabia rotulá-lo e o painel o exibia cru e
# cinza, e o PDF conhecia um `urgente` que a rota nunca grava — de modo que o
# encaminhamento de emergência era impresso como "EMERGENCIA", sem acento, pelo
# fallback de `.upper()`. Nenhuma dessas divergências gera erro: elas apenas
# exibem a informação errada, que é a classe de defeito que esta suíte caça.

def _consumidores():
    """Cada mapa que precisa cobrir o vocabulário, e como se lê seu rótulo."""
    from routes.regulacao import PRIORIDADES as REGULACAO
    from services.pdf_encaminhamento import (PRIORIDADE_CORES,
                                             PRIORIDADE_LABELS as PDF_LABELS)

    return {
        "regulação (badge da fila)": REGULACAO,
        "PDF (rótulo impresso)": PDF_LABELS,
        "PDF (cor impressa)": PRIORIDADE_CORES,
    }


def test_todo_consumidor_cobre_o_vocabulario_gravado(app):
    """Nenhum mapa pode ficar para trás quando uma prioridade for acrescentada.

    Reprova nos dois sentidos: chave que a rota grava e o consumidor não conhece,
    e chave que o consumidor conhece e a rota nunca grava — a segunda é o que
    deixou `urgente` no PDF por tempo indeterminado, parecendo cobertura.
    """
    from models.encaminhamento import Encaminhamento
    from routes.encaminhamentos import PRIORIDADES

    gravadas = set(PRIORIDADES)
    assert gravadas == set(Encaminhamento.PRIORIDADE_LABELS), (
        "o model deixou de rotular alguma prioridade que a rota grava")

    for nome, mapa in _consumidores().items():
        assert set(mapa) == gravadas, (
            f"{nome}: conhece {sorted(set(mapa) - gravadas)} a mais e "
            f"{sorted(gravadas - set(mapa))} a menos que a rota grava")


def test_ordem_de_gravidade_e_a_mesma_nas_duas_filas(app):
    """Encaminhamento e regulação mostram a mesma fila; ordená-las diferente
    faria o mesmo caso aparecer em posições distintas conforme a tela."""
    from routes.encaminhamentos import ORDEM_DE_GRAVIDADE as FILA_SOLICITANTE
    from routes.regulacao import ORDEM_DE_GRAVIDADE as FILA_REGULADOR

    assert FILA_SOLICITANTE == FILA_REGULADOR
    assert FILA_SOLICITANTE["emergencia"] < FILA_SOLICITANTE["urgencia"]
    assert FILA_SOLICITANTE["urgencia"] < FILA_SOLICITANTE["prioritario"]
    assert FILA_SOLICITANTE["prioritario"] < FILA_SOLICITANTE["eletivo"]


def test_rotulo_de_prioridade_nunca_sai_cru(app, dados_clinicos):
    """`prioridade_label` devolvendo a chave crua é o sintoma visível: o painel
    exibe "prioritario" em minúscula e cinza, no meio de rótulos acentuados."""
    from models.encaminhamento import Encaminhamento
    from routes.encaminhamentos import PRIORIDADES

    with app.app_context():
        for chave in PRIORIDADES:
            enc = Encaminhamento(prioridade=chave)
            rotulo, tom = enc.prioridade_label
            assert rotulo != chave, f"{chave} sai cru no painel"
            assert tom != "cinza", f"{chave} cai no tom de fallback"
