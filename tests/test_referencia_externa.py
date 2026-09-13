# -*- coding: utf-8 -*-
"""A referência externa do município, e por que ela fica separada.

O comparativo media a produção DESTA REDE por município. Isso responde "onde
minha rede trabalhou mais" — não responde "como minha rede se situa no
município", que é a pergunta de gestão. Falta o termo externo: quanto o
município inteiro produz, de todas as redes.

**Duas naturezas, duas tabelas.** A produção interna é isolada por unidade
(RLS), restrita ao período escolhido e contada por esta aplicação. O evento
vital é do município inteiro, de um ano fechado, apurado por outra instituição.
Na mesma linha, com a mesma aparência, os dois se leriam como comparáveis — e a
diferença entre eles é justamente a informação. Por isso o teste abaixo exige
que a fonte e o ano apareçam na tela: número externo sem procedência não é
comparável com nada.

Nada aqui vai à rede. A carga é por `flask municipios-ibge`, e o que se testa é
o que ficou no banco — relatório que consulta API externa para renderizar
quebra quando a rede da unidade cai, que é a rede de uma unidade pública.
"""
import pytest

from tests.test_relatorio_territorial import (  # noqa: F401  (fixtures)
    RECIFE, SALVADOR, _corpo_da_tabela, dois_municipios, operador_nacional,
)

NASCIDOS = 23484      # Salvador, 2024, IBGE/Registro Civil
OBITOS = 17880


@pytest.fixture
def salvador_com_vitais(app, dois_municipios):
    """Carrega a referência externa de Salvador e desfaz ao final."""
    from extensions import db
    from models.municipio import Municipio

    with app.app_context():
        m = db.session.get(Municipio, SALVADOR[0])
        original = (m.nascidos_vivos, m.obitos, m.vitais_ano, m.vitais_fonte)
        m.nascidos_vivos, m.obitos = NASCIDOS, OBITOS
        m.vitais_ano, m.vitais_fonte = 2024, "IBGE/Registro Civil"
        db.session.commit()
    yield
    with app.app_context():
        m = db.session.get(Municipio, SALVADOR[0])
        (m.nascidos_vivos, m.obitos, m.vitais_ano, m.vitais_fonte) = original
        db.session.commit()


def _pagina(cliente):
    return cliente.get("/relatorios/territorio").get_data(as_text=True)


def test_a_referencia_externa_aparece(operador_nacional, salvador_com_vitais):
    html = _pagina(operador_nacional)
    assert str(NASCIDOS) in html, "nascidos vivos não aparecem"
    assert str(OBITOS) in html, "óbitos não aparecem"


def test_a_fonte_e_o_ano_aparecem_junto_do_numero(operador_nacional,
                                                  salvador_com_vitais):
    """Número externo sem procedência não é comparável com nada.

    E a fonte precisa ser dita com precisão: Registro Civil e SIM/SINASC contam
    os mesmos fatos por vias diferentes, com totais que não coincidem. Chamar
    um de outro seria erro de fonte, não de digitação.
    """
    html = _pagina(operador_nacional)
    assert "IBGE/Registro Civil" in html
    assert "2024" in html
    assert "não é o SIM/SINASC" in html.lower() or "Não é o SIM/SINASC" in html


def test_a_referencia_nao_entra_na_tabela_de_producao(operador_nacional,
                                                      salvador_com_vitais):
    """O número do município não pode virar mais uma coluna da produção.

    É o ponto inteiro desta funcionalidade: misturado às colunas de
    atendimentos e internações, o evento vital do município seria somado ao
    total da rede — e o total passaria a não significar coisa alguma.
    """
    corpo = _corpo_da_tabela(_pagina(operador_nacional))
    assert str(NASCIDOS) not in corpo, (
        "a referência externa vazou para a tabela de produção da rede")


def test_municipio_sem_referencia_mostra_traco(operador_nacional,
                                               salvador_com_vitais):
    """Recife fica sem carga de propósito: ausência é '—', nunca zero."""
    html = _pagina(operador_nacional)
    assert "—" in html


def test_a_secao_some_quando_nao_ha_fonte_carregada(operador_nacional):
    """Sem `flask municipios-ibge`, a seção inteira não aparece.

    Cabeçalho de "referência externa" sobre uma tabela de traços anuncia um
    dado que não existe.
    """
    html = _pagina(operador_nacional)
    assert "Referência externa do município" not in html
