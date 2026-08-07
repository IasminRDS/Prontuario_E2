# -*- coding: utf-8 -*-
"""O que sai nos CSVs — a camada que ninguém tinha conferido.

Mesmo raciocínio do `test_pdf_conteudo.py`: o arquivo é o produto entregue ao
usuário, e ninguém tinha olhado o que sai dentro dele. Um CSV mal formado não
gera erro no servidor — ele baixa, abre torto, e a pessoa conclui que o sistema
exportou errado os dados.

Duas propriedades decidem se o arquivo abre no Excel em português:

**BOM (`utf-8-sig`).** Sem ele o Excel lê UTF-8 como Latin-1 e todo acento
vira sujeira: "João" aparece como "JoÃ£o".

**Delimitador `;`.** O separador de listas do Windows em pt-BR é o ponto e
vírgula. Com vírgula, o Excel joga a linha inteira na coluna A — o arquivo
"abre", e é justamente por isso que passa despercebido.

O próprio sistema já decidiu a favor do `;`: é o que `importacao/modelo.csv`
gera e o que `importacao.csv_importar` lê de volta. Um relatório com vírgula não
volta para dentro do sistema que o produziu.
"""
import csv
import io

import pytest

from tests.conftest import PERFIS, autenticar


@pytest.fixture
def gestor(app, dados_clinicos, sem_csrf):
    return autenticar(app, PERFIS["admin"][1])


# TODA URL que devolve CSV. A lista é à mão de propósito: o ramo de exportação
# depende de `?exportar=csv`, e a varredura de rotas só visita a URL sem o
# parâmetro. Foi essa exata lacuna que deixou o relatório de atendimentos
# devolvendo 500 na exportação sem ninguém notar.
EXPORTACOES = [
    ("GET", "/relatorios/pacientes?exportar=csv"),
    ("GET", "/relatorios/atendimentos?exportar=csv"),
    ("GET", "/relatorios/producao?exportar=csv"),
    ("GET", "/relatorios/triagem?exportar=csv"),
    ("GET", "/relatorios/hospital/producao?exportar=csv"),
    ("GET", "/relatorios/hospital/ps?exportar=csv"),
    ("GET", "/importacao/modelo.csv"),
    ("POST", "/exportacao/pacientes.csv"),
    ("POST", "/exportacao/auditoria.csv"),
]


def _baixar(cliente, metodo, url):
    if metodo == "GET":
        return cliente.get(url)
    # A exportação identificada exige o aceite explícito; sem ele a rota
    # recusa — e recusar é o comportamento correto, não o que se mede aqui.
    return cliente.post(url, data={"escopo": "anonimizado", "ciente": "1"})


@pytest.mark.parametrize("metodo,url", EXPORTACOES)
def test_csv_abre_no_excel_pt_br(gestor, metodo, url):
    resposta = _baixar(gestor, metodo, url)
    assert resposta.status_code == 200, f"{url} devolveu {resposta.status_code}"

    bruto = resposta.get_data()
    assert bruto.startswith(b"\xef\xbb\xbf"), (
        f"{url}: sem BOM — o Excel vai ler UTF-8 como Latin-1 e quebrar o acento")

    texto = bruto.decode("utf-8-sig")
    primeira = texto.splitlines()[0] if texto.splitlines() else ""
    assert ";" in primeira, (
        f"{url}: cabeçalho sem ';' — com vírgula o Excel pt-BR joga a linha "
        f"inteira na coluna A. Cabeçalho: {primeira[:120]!r}")


@pytest.mark.parametrize("metodo,url", EXPORTACOES)
def test_csv_tem_cabecalho_e_colunas_coerentes(gestor, metodo, url):
    """Linha de dado com mais campos que o cabeçalho desalinha tudo à direita."""
    resposta = _baixar(gestor, metodo, url)
    texto = resposta.get_data().decode("utf-8-sig")
    linhas = list(csv.reader(io.StringIO(texto), delimiter=";"))
    assert linhas, f"{url}: arquivo vazio"

    cabecalho = linhas[0]
    assert len(cabecalho) > 1, f"{url}: cabeçalho com uma coluna só: {cabecalho}"
    assert all(c.strip() for c in cabecalho), (
        f"{url}: coluna sem nome no cabeçalho: {cabecalho}")

    for numero, linha in enumerate(linhas[1:], start=2):
        if not any(c.strip() for c in linha):
            continue
        assert len(linha) == len(cabecalho), (
            f"{url}: linha {numero} tem {len(linha)} campos e o cabeçalho tem "
            f"{len(cabecalho)}")


def test_export_de_pacientes_traz_o_paciente_semeado(gestor, app):
    """Arquivo bem formado e vazio de conteúdo é o pior resultado: parece OK."""
    from models.paciente import Paciente

    with app.app_context():
        nome = Paciente.query.order_by(Paciente.id.asc()).first().nome

    texto = _baixar(gestor, "GET",
                    "/relatorios/pacientes?exportar=csv").get_data().decode("utf-8-sig")
    assert nome in texto, f"{nome!r} não saiu no CSV de pacientes"


# Telas que oferecem o botão "Exportar CSV".
TELAS_COM_BOTAO = [
    "/relatorios/pacientes",
    "/relatorios/atendimentos",
    "/relatorios/producao",
    "/relatorios/triagem",
    "/relatorios/hospital/producao",
    "/relatorios/hospital/ps",
]


@pytest.mark.parametrize("tela", TELAS_COM_BOTAO)
def test_botao_exportar_csv_leva_a_um_csv(gestor, tela):
    """O link precisa funcionar com a tela aberta SEM filtro.

    Os seis botões montavam a URL como `request.url ~ "&exportar=csv"`. Sem `?`
    na origem — que é o caso ao chegar pelo índice de relatórios — o `&` vira
    parte do caminho e o link dá 404. O botão existia, era visível, e nenhuma
    exportação funcionava no primeiro clique.
    """
    import re

    html = gestor.get(tela).get_data(as_text=True)
    links = re.findall(r'href="([^"]*exportar=csv[^"]*)"', html)
    assert links, f"{tela}: nenhum link de exportação na página"

    for link in links:
        alvo = link
        if "://" in alvo:
            alvo = "/" + alvo.split("://", 1)[1].split("/", 1)[1]
        resposta = gestor.get(alvo)
        assert resposta.status_code == 200, (
            f"{tela}: o botão aponta para {alvo!r}, que devolveu "
            f"{resposta.status_code}")
        assert "csv" in resposta.content_type, (
            f"{tela}: o botão devolveu {resposta.content_type}, não um CSV")
