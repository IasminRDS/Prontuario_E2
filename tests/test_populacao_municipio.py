# -*- coding: utf-8 -*-
"""O denominador: o que separa contagem de indicador.

Sem população, o sistema só sabia contar — e contagem compara mal. Salvador
terá sempre mais atendimentos que Bom Jesus da Lapa, e disso não se conclui
nada sobre desempenho. O denominador é o que transforma "487 óbitos" em "óbitos
por cem mil habitantes".

O assunto destes casos, porém, não é a divisão: é o **que acontece quando não
há denominador**. Um município sem população carregada não pode virar taxa
zero, porque zero é um valor e valor errado aqui lê-se como resultado — o
município apareceria como o de menor produção do estado, e a conclusão seria
exatamente a oposta da verdade. Ausência tem de continuar ausência o caminho
inteiro: no model, na tela e no CSV.
"""
import io

import pytest

from tests.conftest import PERFIS, SENHA, autenticar
from tests.test_relatorio_territorial import (  # noqa: F401  (fixtures)
    RECIFE, SALVADOR, _corpo_da_tabela, dois_municipios, operador_nacional,
)

POPULACAO_SALVADOR = 2417678      # valor de exemplo, só para exercitar a conta


@pytest.fixture
def salvador_com_populacao(app, dois_municipios):
    """Salvador COM denominador e Recife SEM, para os dois ramos na mesma tela.

    Os dois lados são postos aqui de propósito, inclusive a ausência. A versão
    anterior só carregava Salvador e contava com Recife estar vazio porque a
    semente ainda não trazia população — e quando ela passou a trazer, três
    casos falharam de uma vez. Teste que depende do que a semente por acaso
    não tem mede o acaso.
    """
    from extensions import db
    from models.municipio import Municipio

    original = {}
    with app.app_context():
        for codigo in (SALVADOR[0], RECIFE[0]):
            municipio = db.session.get(Municipio, codigo)
            original[codigo] = (municipio.populacao, municipio.populacao_ano)

        salvador = db.session.get(Municipio, SALVADOR[0])
        salvador.populacao, salvador.populacao_ano = POPULACAO_SALVADOR, 2024

        recife = db.session.get(Municipio, RECIFE[0])
        recife.populacao, recife.populacao_ano = None, None
        db.session.commit()

    yield POPULACAO_SALVADOR

    with app.app_context():
        for codigo, (populacao, ano) in original.items():
            municipio = db.session.get(Municipio, codigo)
            municipio.populacao, municipio.populacao_ano = populacao, ano
        db.session.commit()


# --------------------------------------------------------------- o cálculo
def test_sem_populacao_a_taxa_e_nula_e_nao_zero(app):
    """Zero seria um valor. A ausência precisa se propagar como ausência."""
    from models.municipio import Municipio

    with app.app_context():
        municipio = Municipio(codigo_ibge="2927408", nome="X", uf="BA")
        assert municipio.por_cem_mil(10) is None
        assert municipio.por_cem_mil(0) is None


def test_com_populacao_a_taxa_e_por_cem_mil(app):
    from models.municipio import Municipio

    with app.app_context():
        municipio = Municipio(codigo_ibge="2927408", nome="X", uf="BA",
                              populacao=200000)
        assert municipio.por_cem_mil(10) == pytest.approx(5.0)
        assert municipio.por_cem_mil(0) == pytest.approx(0.0)


# ------------------------------------------------------------------ carga
def _csv(tmp_path, conteudo):
    caminho = tmp_path / "municipios.csv"
    io.open(caminho, "w", encoding="utf-8", newline="").write(conteudo)
    return str(caminho)


def test_importa_populacao_e_ano(app, tmp_path):
    from extensions import db
    from database.municipios import importar_csv
    from models.municipio import Municipio

    caminho = _csv(tmp_path,
                   "codigo_ibge,nome,uf,populacao,populacao_ano\n"
                   "2304400,Fortaleza,CE,2428708,2024\n")
    with app.app_context():
        gravados, erros = importar_csv(caminho)
        assert (gravados, erros) == (1, [])
        municipio = db.session.get(Municipio, "2304400")
        assert municipio.populacao == 2428708
        assert municipio.populacao_ano == 2024


def test_populacao_com_separador_de_milhar_e_aceita(app, tmp_path):
    """A relação do IBGE circula com ponto de milhar. Recusar seria recusar o
    arquivo que as pessoas realmente têm."""
    from extensions import db
    from database.municipios import importar_csv
    from models.municipio import Municipio

    caminho = _csv(tmp_path,
                   "codigo_ibge,nome,uf,populacao\n"
                   "2408102,Natal,RN,751.300\n")
    with app.app_context():
        importar_csv(caminho)
        assert db.session.get(Municipio, "2408102").populacao == 751300


def test_populacao_invalida_e_recusada_com_motivo(app, tmp_path):
    """Linha ruim não pode virar denominador: a taxa sairia errada em silêncio."""
    from database.municipios import importar_csv

    caminho = _csv(tmp_path,
                   "codigo_ibge,nome,uf,populacao\n"
                   "2611606,Recife,PE,não informado\n")
    with app.app_context():
        gravados, erros = importar_csv(caminho)
        assert gravados == 0
        assert any("não é um número" in e for e in erros), erros


def test_populacao_zero_e_recusada(app, tmp_path):
    """Zero habitantes não é um denominador — é uma divisão por zero adiada."""
    from database.municipios import importar_csv

    caminho = _csv(tmp_path,
                   "codigo_ibge,nome,uf,populacao\n"
                   "2211001,Teresina,PI,0\n")
    with app.app_context():
        gravados, erros = importar_csv(caminho)
        assert gravados == 0
        assert any("não é utilizável" in e for e in erros), erros


def test_arquivo_sem_a_coluna_nao_apaga_a_populacao_ja_carregada(app, tmp_path):
    """O caso que perde dado sem avisar.

    Carregar a lista simples do IBGE depois da lista com população apagaria o
    denominador, e o relatório voltaria a contar sem dizer que voltou.
    """
    from extensions import db
    from database.municipios import importar_csv
    from models.municipio import Municipio

    com = _csv(tmp_path, "codigo_ibge,nome,uf,populacao,populacao_ano\n"
                         "5002704,Campo Grande,MS,916001,2024\n")
    with app.app_context():
        importar_csv(com)
        assert db.session.get(Municipio, "5002704").populacao == 916001

    sem = tmp_path / "sem.csv"
    io.open(sem, "w", encoding="utf-8", newline="").write(
        "codigo_ibge,nome,uf\n5002704,Campo Grande,MS\n")
    with app.app_context():
        importar_csv(str(sem))
        municipio = db.session.get(Municipio, "5002704")
        assert municipio.populacao == 916001, (
            "a carga sem a coluna apagou o denominador")


# ----------------------------------------------------------------- a tela
def test_a_taxa_aparece_no_relatorio(operador_nacional, salvador_com_populacao):
    corpo = _corpo_da_tabela(
        operador_nacional.get("/relatorios/territorio").get_data(as_text=True))
    linha = next(l for l in corpo.split("<tr>") if SALVADOR[0] in l)
    assert "pop. 2024" in linha, (
        "o ano do denominador não aparece — sem ele a taxa não é comparável")


def test_municipio_sem_denominador_mostra_traco_e_nao_zero(
        operador_nacional, salvador_com_populacao):
    html = operador_nacional.get(
        "/relatorios/territorio").get_data(as_text=True)
    linha = next(l for l in _corpo_da_tabela(html).split("<tr>")
                 if RECIFE[0] in l)
    assert "—" in linha, "município sem população não foi marcado"
    assert "sem população carregada" in linha


def test_a_tela_avisa_quantos_estao_sem_denominador(
        operador_nacional, salvador_com_populacao):
    """O aviso é o que faz alguém carregar a população.

    Sem ele, a coluna de traços passa por detalhe visual e o relatório fica
    meio mudo para sempre.
    """
    html = operador_nacional.get(
        "/relatorios/territorio").get_data(as_text=True)
    assert "sem população carregada" in html
    assert "municipios-importar" in html, (
        "o aviso não diz como resolver")


def test_ordenar_por_taxa_joga_quem_nao_tem_denominador_para_o_fim(
        operador_nacional, salvador_com_populacao):
    """Sem isto, `None` ordenaria antes de qualquer número e os municípios sem
    população encabeçariam o ranking de desempenho."""
    corpo = _corpo_da_tabela(operador_nacional.get(
        "/relatorios/territorio?ordem=taxa").get_data(as_text=True))
    assert corpo.index(SALVADOR[0]) < corpo.index(RECIFE[0])


def test_o_csv_traz_populacao_ano_e_taxa(operador_nacional,
                                         salvador_com_populacao):
    resposta = operador_nacional.get("/relatorios/territorio?exportar=csv")
    csv = resposta.get_data().decode("utf-8-sig")
    assert "População;Ano da população;Total por 100 mil hab." in csv

    linha = next(l for l in csv.splitlines() if l.startswith(SALVADOR[0]))
    assert str(POPULACAO_SALVADOR) in linha
    assert "2024" in linha

    # Recife entra com as três células VAZIAS, não com zero: planilha soma zero
    # como se fosse medição.
    recife = next(l for l in csv.splitlines() if l.startswith(RECIFE[0]))
    assert recife.endswith(";;;"), (
        f"esperava células vazias para município sem denominador: {recife!r}")
