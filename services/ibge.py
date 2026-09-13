# -*- coding: utf-8 -*-
"""Estatísticas municipais oficiais, pela API de agregados do IBGE.

**A fonte é o IBGE, e não o DATASUS.** A distinção não é preciosismo: o
levantamento em `docs/datasus_levantamento.md` mostrou que os microdados do
DATASUS vêm em `.DBC` — DBF comprimido com PKWare DCL Implode — e exigem
descompressor binário. A API do IBGE entrega JSON por HTTPS, já é usada neste
projeto para a população, e cobre justamente o que falta ao comparativo:
eventos vitais por município.

O que vem de cada tabela do SIDRA:

  6579  População residente estimada        (o denominador)
  2609  Nascidos vivos registrados no ano   (Registro Civil, 2003–2024)
  2654  Óbitos ocorridos no ano             (Registro Civil, 2003–2024)

Registro Civil e não SIM/SINASC: são o mesmo evento contado por outra via — o
cartório, não a notificação em saúde. Os números não coincidem exatamente com
os do DATASUS, e citar um como se fosse o outro seria erro de fonte.

**Nada disto é consultado durante uma requisição.** A carga é por comando, e o
resultado fica no banco: relatório que depende de API externa para renderizar
quebra quando a rede da unidade cai — que é exatamente a rede de uma unidade
de saúde pública.
"""
import requests

BASE = "https://servicodados.ibge.gov.br/api/v3/agregados"
SIDRA = "https://apisidra.ibge.gov.br/values"

TEMPO_LIMITE = 30

# tabela -> (rótulo, variável). A variável é o "quê" dentro da tabela: a mesma
# tabela publica o número absoluto e o percentual, e pegar o errado daria um
# resultado plausível e falso.
TABELA_NASCIDOS = 2609
TABELA_OBITOS = 2654
TABELA_POPULACAO = 6579
VARIAVEL_POPULACAO = 9324


class ErroIBGE(RuntimeError):
    """Falha ao consultar a API. Quem chama decide se aborta ou segue."""


def _lote(codigos, tamanho=200):
    codigos = list(codigos)
    for i in range(0, len(codigos), tamanho):
        yield codigos[i:i + tamanho]


def _agregado(tabela, periodo, codigos):
    """Devolve {codigo_ibge: valor} para uma tabela de agregados.

    Códigos vão em lote porque a API aceita muitos por chamada, e 5.570
    requisições individuais seriam abuso de serviço público além de lentas.
    """
    achados = {}
    for parte in _lote(codigos):
        url = "%s/%s/periodos/%s/variaveis?localidades=N6[%s]" % (
            BASE, tabela, periodo, ",".join(parte))
        try:
            resposta = requests.get(url, timeout=TEMPO_LIMITE)
            resposta.raise_for_status()
            dados = resposta.json()
        except requests.RequestException as erro:
            raise ErroIBGE("tabela %s: %s" % (tabela, erro)) from erro
        except ValueError as erro:
            raise ErroIBGE("tabela %s devolveu resposta não-JSON" % tabela) from erro

        if not dados:
            continue
        for serie in dados[0]["resultados"][0]["series"]:
            codigo = serie["localidade"]["id"]
            bruto = list(serie["serie"].values())[0]
            # "-" e "..." são as marcas do IBGE para dado inexistente e dado
            # não disponível. Virar zero seria transformar ausência em medição.
            achados[codigo] = int(bruto) if str(bruto).isdigit() else None
    return achados


def eventos_vitais(codigos, ano):
    """{codigo: {"nascidos": n, "obitos": n}} para os municípios pedidos."""
    nascidos = _agregado(TABELA_NASCIDOS, ano, codigos)
    obitos = _agregado(TABELA_OBITOS, ano, codigos)
    return {
        codigo: {"nascidos": nascidos.get(codigo), "obitos": obitos.get(codigo)}
        for codigo in codigos
        if nascidos.get(codigo) is not None or obitos.get(codigo) is not None
    }


def populacao(codigos, periodo="last"):
    """{codigo: habitantes}. Usa o SIDRA, que é onde a estimativa é publicada."""
    achados = {}
    for parte in _lote(codigos, 100):
        url = "%s/t/%d/n6/%s/v/%d/p/%s" % (
            SIDRA, TABELA_POPULACAO, ",".join(parte), VARIAVEL_POPULACAO, periodo)
        try:
            resposta = requests.get(url, timeout=TEMPO_LIMITE)
            resposta.raise_for_status()
            linhas = resposta.json()[1:]     # a primeira linha é o cabeçalho
        except requests.RequestException as erro:
            raise ErroIBGE("população: %s" % erro) from erro
        except (ValueError, IndexError) as erro:
            raise ErroIBGE("população: resposta inesperada") from erro

        for linha in linhas:
            valor = linha.get("V")
            if str(valor).isdigit():
                achados[linha["D1C"]] = (int(valor), int(linha["D3N"]))
    return achados
