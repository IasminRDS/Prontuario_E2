# -*- coding: utf-8 -*-
"""Os números citados nos documentos são os medidos hoje.

`AGENTS.md` diz que todo número citado é medido, não estimado, e o gerador do
resumo diz que divergência entre README, monografia e resumo "é defeito, não
versão". As duas regras dependiam de alguém lembrar de remedir — e número
herdado de uma versão anterior parece verdade porque já esteve.

O gatilho deste arquivo foi banal e por isso convincente: acrescentar quatro
casos de teste numa sessão deixou sete afirmações desatualizadas em quatro
arquivos, e acrescentar um relatório deixou outras tantas. Nenhuma falhava em
nada; só passavam a estar erradas.

O que se mede aqui é o que é barato e inequívoco — rotas, telas, tabelas,
módulos e funções de teste. O **número de casos** não é medido: obtê-lo exigiria
coletar a suíte de dentro da própria suíte. Para ele vale a segunda regra, que é
a de consistência: os quatro documentos têm de dizer o mesmo, e a divergência
entre eles é o que se acusa.
"""
import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent

DOCUMENTOS = {
    "README.md": RAIZ / "README.md",
    "docs/TCC.md": RAIZ / "docs" / "TCC.md",
    "scripts/gerar_resumo_pdf.py": RAIZ / "scripts" / "gerar_resumo_pdf.py",
    # Entrou depois dos outros três, e a omissão foi instrutiva: os slides
    # citam as mesmas contagens e ficaram defasados sem que nada acusasse,
    # justamente porque ninguém pensa no gerador de slides ao acrescentar um
    # teste.
    "scripts/gerar_defesa_pptx.py": RAIZ / "scripts" / "gerar_defesa_pptx.py",
}


def _texto(nome):
    return DOCUMENTOS[nome].read_text(encoding="utf-8", errors="replace")


def _inteiro(texto, padrao, onde):
    achado = re.search(padrao, texto)
    assert achado, f"não encontrei o número de {onde} (padrão {padrao!r})"
    return int(achado.group(1))


# ---------------------------------------------------------------- medições
def _rotas_medidas(app):
    regras = [r for r in app.url_map.iter_rules() if r.endpoint != "static"]
    return {
        "total": len(regras),
        "get": len([r for r in regras if "GET" in r.methods]),
        "mutacao": len([r for r in regras
                        if r.methods & {"POST", "PUT", "DELETE", "PATCH"}]),
    }


def _telas_medidas():
    return len(list((RAIZ / "templates").rglob("*.html")))


def _funcoes_de_teste_medidas():
    total = 0
    for arquivo in (RAIZ / "tests").glob("*.py"):
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        total += len(re.findall(r"^\s*def test_", texto, re.M))
    return total


def _arquivos_de_teste_medidos():
    return len(list((RAIZ / "tests").glob("test_*.py")))


# ------------------------------------------------------------------ testes
def test_rotas_citadas_conferem(app):
    medido = _rotas_medidas(app)

    readme = _inteiro(_texto("README.md"), r"\|\s*Rotas\s*\|\s*(\d+)\s*\|", "rotas no README")
    assert readme == medido["total"], (
        f"README diz {readme} rotas; medido {medido['total']}")

    tcc = re.search(
        r"Rotas expostas \| (\d+) — (\d+) aceitam GET; (\d+), método de mutação",
        _texto("docs/TCC.md"))
    assert tcc, "não encontrei a linha de rotas na monografia"
    assert [int(g) for g in tcc.groups()] == [
        medido["total"], medido["get"], medido["mutacao"]], (
        f"monografia diz {tcc.groups()}; medido "
        f"{medido['total']}, {medido['get']}, {medido['mutacao']}")

    resumo = re.search(r'"<b>(\d+)</b> \((\d+) GET, (\d+) mutação\)"',
                       _texto("scripts/gerar_resumo_pdf.py"))
    assert resumo, "não encontrei a linha de rotas no gerador do resumo"
    assert [int(g) for g in resumo.groups()] == [
        medido["total"], medido["get"], medido["mutacao"]], (
        f"resumo diz {resumo.groups()}; medido "
        f"{medido['total']}, {medido['get']}, {medido['mutacao']}")

    slides = re.search(r'"(\d+) — (\d+) aceitam GET; (\d+), mutação"',
                       _texto("scripts/gerar_defesa_pptx.py"))
    assert slides, "não encontrei a linha de rotas no gerador dos slides"
    assert [int(g) for g in slides.groups()] == [
        medido["total"], medido["get"], medido["mutacao"]], (
        f"slides dizem {slides.groups()}; medido "
        f"{medido['total']}, {medido['get']}, {medido['mutacao']}")


def test_telas_citadas_conferem():
    medido = _telas_medidas()
    citados = {
        "README.md": _inteiro(_texto("README.md"),
                              r"\|\s*Templates\s*\|\s*(\d+)\s*\|", "telas"),
        "docs/TCC.md": _inteiro(_texto("docs/TCC.md"),
                                r"Telas \(\*templates\*\) \| (\d+)", "telas"),
        "scripts/gerar_resumo_pdf.py": _inteiro(
            _texto("scripts/gerar_resumo_pdf.py"),
            r'"Telas \(templates\)", "<b>(\d+)</b>"', "telas"),
    }
    divergentes = {k: v for k, v in citados.items() if v != medido}
    assert not divergentes, (
        f"{medido} templates no repositório; documentos dizem {divergentes}")


def test_tabelas_colunas_e_chaves_conferem(app):
    """As três saem da mesma linha da monografia, e as três envelhecem juntas:
    uma migration que acrescente coluna muda duas delas de uma vez."""
    from extensions import db

    with app.app_context():
        tabelas = db.metadata.sorted_tables
        medido = (len(tabelas),
                  sum(len(t.columns) for t in tabelas),
                  sum(len(t.foreign_keys) for t in tabelas))

    achado = re.search(
        r"Tabelas no modelo de dados \| (\d+), com (\d+) colunas e (\d+) chaves",
        _texto("docs/TCC.md"))
    assert achado, "não encontrei a linha do modelo de dados na monografia"
    assert tuple(int(g) for g in achado.groups()) == medido, (
        f"monografia diz {achado.groups()}; medido {medido}")


def test_migracoes_citadas_conferem():
    """Contagem que só muda quando alguém cria migration — e é exatamente aí
    que ninguém lembra de atualizar o número."""
    medido = len([a for a in (RAIZ / "migrations" / "versions").glob("*.py")])

    readme = _inteiro(_texto("README.md"),
                      r"\|\s*Migrations\s*\|\s*(\d+)", "migrations no README")
    tcc = _inteiro(_texto("docs/TCC.md"),
                   r"Migrações de esquema versionadas \| (\d+)", "migrações")
    assert readme == medido, f"README diz {readme} migrations; medido {medido}"
    assert tcc == medido, f"monografia diz {tcc} migrações; medido {medido}"


def test_modulos_citados_conferem(app):
    medido = len(app.blueprints)
    citado = _inteiro(_texto("README.md"),
                      r"\|\s*Módulos \(blueprints\)\s*\|\s*(\d+)\s*\|", "módulos")
    assert citado == medido, f"README diz {citado} módulos; medido {medido}"


def test_funcoes_e_arquivos_de_teste_conferem():
    funcoes, arquivos = _funcoes_de_teste_medidas(), _arquivos_de_teste_medidos()

    readme = re.search(r"(\d+) funções → (\d+) casos, em (\d+) arquivos",
                       _texto("README.md"))
    assert readme, "não encontrei a linha de testes no README"
    assert int(readme.group(1)) == funcoes, (
        f"README diz {readme.group(1)} funções de teste; medido {funcoes}")
    assert int(readme.group(3)) == arquivos, (
        f"README diz {readme.group(3)} arquivos de teste; medido {arquivos}")


def test_os_documentos_dizem_o_mesmo_numero_de_casos():
    """O único número não medido aqui — resta exigir que não divirjam.

    Coletar a suíte de dentro da suíte para contar casos seria recursão cara e
    frágil. Consistência entre os quatro é a garantia possível, e é exatamente a
    que o gerador do resumo declara em sua docstring.
    """
    casos = {
        "README.md": _inteiro(_texto("README.md"),
                              r"\d+ funções → (\d+) casos", "casos"),
        "docs/TCC.md": _inteiro(_texto("docs/TCC.md"),
                                r"Casos de teste automatizados \| (\d+),", "casos"),
        "scripts/gerar_resumo_pdf.py": _inteiro(
            _texto("scripts/gerar_resumo_pdf.py"),
            r'"<b>(\d+)</b> casos, em \d+ funções', "casos"),
        "scripts/gerar_defesa_pptx.py": _inteiro(
            _texto("scripts/gerar_defesa_pptx.py"),
            r'"(\d+), em \d+ funções e \d+ arquivos"', "casos"),
    }
    assert len(set(casos.values())) == 1, (
        "os documentos discordam sobre o número de casos de teste: "
        f"{casos}")


@pytest.mark.parametrize("nome", sorted(DOCUMENTOS))
def test_o_documento_existe_e_foi_lido(nome):
    """Sem isto, renomear um arquivo transformaria os testes acima em silêncio."""
    assert DOCUMENTOS[nome].exists(), f"{nome} não existe mais"
    assert _texto(nome).strip(), f"{nome} está vazio"
