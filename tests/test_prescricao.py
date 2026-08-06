# -*- coding: utf-8 -*-
"""Prescrição ambulatorial: a receita E seus itens precisam sobreviver ao POST.

`templates/medicamentos/form.html` era a triagem copiada — `page_title` dizia
"Triagem — Classificação de Risco". Pedia queixa, escala de dor, discriminadores
e cor de Manchester; a rota lê validade, observações e **oito listas paralelas**
de item (`item_nome`, `item_dose`, `item_via`, ...). Não havia um único campo de
medicamento na tela: prescrever pela interface produzia uma receita vazia.

O detalhe que faz este teste existir são as listas paralelas. A rota casa
`item_dose[i]` com `item_nome[i]` pela POSIÇÃO, então uma linha que deixe de
enviar algum dos campos desloca o índice e a dose de um remédio vai parar em
outro. Um teste de "criou a prescrição?" passaria com os itens embaralhados;
por isso aqui se confere item a item.

`medicamentos.buscar` já existia com a docstring "API de autocomplete para o
formulário de prescrição" — o endpoint foi escrito para esta tela, e a tela
nunca o usou.
"""
import re

import pytest

from tests.conftest import PERFIS, autenticar


def _token(html):
    achado = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return achado.group(1) if achado else ""


@pytest.fixture
def prescritor(app, dados_clinicos):
    """Médico: a rota exige `prescription:create` e cadastro em `medicos`."""
    return autenticar(app, PERFIS["medico"][1])


@pytest.fixture
def paciente_id(app, dados_clinicos):
    from models.paciente import Paciente

    with app.app_context():
        return Paciente.query.order_by(Paciente.id.asc()).first().id


@pytest.fixture
def limpar_prescricoes(app):
    from extensions import db
    from models.medicamento import Prescricao

    with app.app_context():
        existentes = {p.id for p in Prescricao.query.all()}
    yield
    with app.app_context():
        for pres in Prescricao.query.all():
            if pres.id not in existentes:
                db.session.delete(pres)  # itens caem por cascade
        db.session.commit()


def _postar(cliente, paciente_id, campos):
    url = f"/medicamentos/prescrever/{paciente_id}"
    pagina = cliente.get(url).get_data(as_text=True)
    dados = {"csrf_token": _token(pagina)}
    dados.update(campos)
    return cliente.post(url, data=dados, follow_redirects=True)


def test_prescricao_grava_os_itens_na_ordem_certa(
        app, prescritor, paciente_id, limpar_prescricoes):
    """Duas linhas: cada dose tem de ficar com o seu próprio medicamento."""
    from models.medicamento import Prescricao

    resposta = _postar(prescritor, paciente_id, {
        "validade_dias": "30",
        "observacoes": "retorno em 30 dias",
        "item_nome": ["Amoxicilina", "Dipirona"],
        "item_dose": ["500 mg", "1 g"],
        "item_via": ["Oral", "EV"],
        "item_frequencia": ["8/8h", "6/6h"],
        "item_duracao": ["7 dias", "3 dias"],
        "item_quantidade": ["21 comp.", "12 amp."],
        "item_instrucoes": ["tomar com agua", "se dor"],
        "item_medicamento_id": ["", ""],
    })
    assert resposta.status_code == 200

    with app.app_context():
        pres = (Prescricao.query.filter_by(paciente_id=paciente_id)
                .order_by(Prescricao.id.desc()).first())
        assert pres is not None, "o POST respondeu e nenhuma prescrição foi criada"
        assert pres.validade_dias == 30
        assert pres.observacoes == "retorno em 30 dias"
        assert pres.tipo == "ambulatorial", (
            "o formulário não manda `tipo`; o padrão da rota deve valer")

        itens = sorted(pres.itens, key=lambda i: i.id)
        assert len(itens) == 2, f"gravou {len(itens)} itens, esperava 2"

        # O emparelhamento por posição é o ponto: dose, via e frequência têm de
        # continuar com o medicamento da própria linha.
        primeiro, segundo = itens
        assert (primeiro.nome_livre, primeiro.dose, primeiro.via,
                primeiro.frequencia) == ("Amoxicilina", "500 mg", "Oral", "8/8h")
        assert (segundo.nome_livre, segundo.dose, segundo.via,
                segundo.frequencia) == ("Dipirona", "1 g", "EV", "6/6h")
        assert primeiro.duracao == "7 dias" and segundo.duracao == "3 dias"
        assert primeiro.quantidade == "21 comp." and segundo.quantidade == "12 amp."


def test_item_do_catalogo_guarda_o_vinculo_e_nao_o_texto(
        app, prescritor, paciente_id, limpar_prescricoes):
    """Com `item_medicamento_id`, o item aponta para o catálogo e `nome_livre`
    fica nulo — é o que `ItemPrescricao.nome_exibicao` espera."""
    from models.medicamento import Medicamento, Prescricao

    with app.app_context():
        med = Medicamento.query.order_by(Medicamento.id.asc()).first()
        assert med is not None, "nenhum medicamento no catálogo semeado"
        med_id, med_nome = med.id, med.nome_generico

    _postar(prescritor, paciente_id, {
        "item_nome": [med_nome],
        "item_dose": ["1 comp."],
        "item_via": ["Oral"],
        "item_frequencia": ["12/12h"],
        "item_duracao": [""],
        "item_quantidade": [""],
        "item_instrucoes": [""],
        "item_medicamento_id": [str(med_id)],
    })

    with app.app_context():
        pres = (Prescricao.query.filter_by(paciente_id=paciente_id)
                .order_by(Prescricao.id.desc()).first())
        item = pres.itens[0]
        assert item.medicamento_id == med_id
        assert item.nome_livre is None, (
            "item do catálogo não deve duplicar o nome em texto livre")
        assert item.nome_exibicao == med_nome


def test_linha_em_branco_nao_vira_item(app, prescritor, paciente_id,
                                       limpar_prescricoes):
    """O formulário sempre manda ao menos uma linha; vazia, não pode virar item."""
    from models.medicamento import Prescricao

    _postar(prescritor, paciente_id, {
        "item_nome": ["Losartana", "   "],
        "item_dose": ["50 mg", ""],
        "item_via": ["Oral", ""],
        "item_frequencia": ["1x/dia", ""],
        "item_duracao": ["", ""],
        "item_quantidade": ["", ""],
        "item_instrucoes": ["", ""],
        "item_medicamento_id": ["", ""],
    })

    with app.app_context():
        pres = (Prescricao.query.filter_by(paciente_id=paciente_id)
                .order_by(Prescricao.id.desc()).first())
        assert len(pres.itens) == 1, "a linha em branco virou item"
        assert pres.itens[0].nome_livre == "Losartana"


def test_formulario_e_o_de_prescricao(prescritor, paciente_id):
    """Guarda contra a cópia da triagem voltar."""
    html = prescritor.get(
        f"/medicamentos/prescrever/{paciente_id}").get_data(as_text=True)
    assert "Classificação de Risco" not in html
    assert 'name="item_nome"' in html, "o formulário não pede medicamento"
    assert 'name="item_dose"' in html, "o formulário não pede a dose"
    assert 'name="discriminadores"' not in html, "voltou a ser a triagem"
