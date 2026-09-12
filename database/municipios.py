# -*- coding: utf-8 -*-
"""Carga da tabela de municípios.

São 5.570 municípios no Brasil — a lista completa não cabe no repositório e nem
deveria: ela muda, e a fonte é o IBGE. Aqui ficam as 27 capitais, suficientes
para demonstrar e testar, mais o importador que carrega a tabela oficial.

Baixe a relação em https://www.ibge.gov.br/ (Municípios do Brasil) e rode:

    flask municipios-importar caminho/municipios.csv

O CSV precisa ter as colunas `codigo_ibge`, `nome` e `uf` (o cabeçalho é lido
pelo nome, então a ordem não importa).

Duas colunas **opcionais** carregam o denominador: `populacao` e
`populacao_ano`. Sem elas o sistema conta; com elas, calcula taxa por cem mil
habitantes. A estimativa populacional por município sai da mesma origem — o
IBGE —, e o portal de transferência do DATASUS também a publica, na fonte
"Base Populacional" (ver `docs/datasus_levantamento.md`).

O ano é pedido junto porque população é estimativa datada: taxa de 2024 sobre
denominador de 2010 não é comparável com taxa de 2024 sobre denominador de
2024, e nada no número denuncia a mistura.
"""
import csv

from database.db import db
from models.municipio import Municipio, uf_do_codigo

# Capitais, para o sistema nascer utilizável. O código IBGE carrega a UF nos
# dois primeiros dígitos, e `_validar` confere isso na carga — um código trocado
# não passa silenciosamente.
#
# A população é a **estimativa oficial do IBGE para 1º de julho de 2026**,
# obtida da tabela 6579 do SIDRA (variável 9324, "População residente
# estimada"):
#
#     https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/last
#
# O ano viaja junto com o número porque a estimativa é datada: comparar taxa
# calculada sobre denominadores de anos diferentes produz um número de
# aparência normal e significado nenhum. Quando a estimativa nova sair, é esta
# lista que se refaz — e o ano na tela passa a dizer outro.
CAPITAIS = [
    ("1100205", "Porto Velho", "RO", 520379, 2026),
    ("1200401", "Rio Branco", "AC", 390058, 2026),
    ("1302603", "Manaus", "AM", 2327101, 2026),
    ("1400100", "Boa Vista", "RR", 500965, 2026),
    ("1501402", "Belém", "PA", 1396157, 2026),
    ("1600303", "Macapá", "AP", 491987, 2026),
    ("1721000", "Palmas", "TO", 333154, 2026),
    ("2111300", "São Luís", "MA", 1090229, 2026),
    ("2211001", "Teresina", "PI", 908012, 2026),
    ("2304400", "Fortaleza", "CE", 2582360, 2026),
    ("2408102", "Natal", "RN", 783196, 2026),
    ("2507507", "João Pessoa", "PB", 906093, 2026),
    ("2611606", "Recife", "PE", 1588983, 2026),
    ("2704302", "Maceió", "AL", 995134, 2026),
    ("2800308", "Aracaju", "SE", 623328, 2026),
    ("2927408", "Salvador", "BA", 2559945, 2026),
    ("3106200", "Belo Horizonte", "MG", 2415451, 2026),
    ("3205309", "Vitória", "ES", 343935, 2026),
    ("3304557", "Rio de Janeiro", "RJ", 6731133, 2026),
    ("3550308", "São Paulo", "SP", 11911337, 2026),
    ("4106902", "Curitiba", "PR", 1832183, 2026),
    ("4205407", "Florianópolis", "SC", 598370, 2026),
    ("4314902", "Porto Alegre", "RS", 1388791, 2026),
    ("5002704", "Campo Grande", "MS", 970843, 2026),
    ("5103403", "Cuiabá", "MT", 698917, 2026),
    ("5208707", "Goiânia", "GO", 1511709, 2026),
    ("5300108", "Brasília", "DF", 3009996, 2026),
]


def _validar(codigo, uf):
    """A UF declarada precisa bater com a embutida no código.

    É validação de graça: o IBGE codifica a UF nos dois primeiros dígitos, então
    divergência aqui significa linha errada — e uma linha errada na tabela
    territorial contamina todo relatório agregado depois.
    """
    esperada = uf_do_codigo(codigo)
    if esperada is None:
        return f"código '{codigo}' não é um código IBGE de município"
    if uf and uf.upper() != esperada:
        return f"código {codigo} é de {esperada}, mas a linha diz {uf.upper()}"
    return None


def _populacao(bruto, codigo):
    """Converte o campo de população, ou explica por que recusou.

    Devolve `(valor, problema)`. O valor é `None` quando a coluna não veio —
    que é diferente de zero: zero seria um denominador, e denominador zero
    produz divisão por zero ou taxa absurda. Ausência tem de continuar ausência
    o caminho inteiro.
    """
    # `bruto` chega como texto quando vem de CSV e como inteiro quando vem de
    # CAPITAIS. E o teste é por `is None`, não por `or ""`: com `or`, o inteiro
    # zero viraria "coluna ausente" e passaria como município sem denominador,
    # em vez de ser recusado como o valor inutilizável que é.
    if bruto is None:
        return None, None
    texto = str(bruto).strip().replace(".", "").replace(" ", "")
    if not texto:
        return None, None
    if not texto.isdigit():
        return None, f"município {codigo}: população '{bruto}' não é um número"
    valor = int(texto)
    if valor <= 0:
        return None, f"município {codigo}: população {valor} não é utilizável"
    return valor, None


def carregar(linhas):
    """Insere ou atualiza municípios. Devolve (gravados, erros).

    Cada linha é `(codigo, nome, uf)` ou `(codigo, nome, uf, populacao, ano)`.
    A população é opcional porque a relação do IBGE circula nas duas formas, e
    exigir a coluna impediria carregar a tabela territorial de quem só tem a
    lista de municípios.
    """
    gravados, erros = 0, []

    for linha in linhas:
        codigo, nome, uf = linha[0], linha[1], linha[2]
        bruto_populacao = linha[3] if len(linha) > 3 else None
        bruto_ano = linha[4] if len(linha) > 4 else None

        codigo = (codigo or "").strip()
        nome = (nome or "").strip()
        uf = (uf or "").strip().upper()

        problema = _validar(codigo, uf)
        if problema:
            erros.append(problema)
            continue

        populacao, problema = _populacao(bruto_populacao, codigo)
        if problema:
            erros.append(problema)
            continue

        ano = (str(bruto_ano) or "").strip()
        ano = int(ano) if ano.isdigit() else None

        existente = db.session.get(Municipio, codigo)
        if existente:
            existente.nome = nome
            existente.uf = uf
            # Só sobrescreve o denominador quando o arquivo traz um. Carregar a
            # lista simples do IBGE depois da lista com população apagaria a
            # população — e o relatório voltaria a contar sem dizer que voltou.
            if populacao is not None:
                existente.populacao = populacao
                existente.populacao_ano = ano
        else:
            db.session.add(Municipio(codigo_ibge=codigo, nome=nome, uf=uf,
                                     populacao=populacao, populacao_ano=ano))
        gravados += 1

    db.session.commit()
    return gravados, erros


def seed_capitais():
    """Reaplica as capitais. Idempotente porque `carregar` é upsert.

    A versão anterior desistia se a tabela tivesse qualquer linha. O efeito
    disso só apareceu quando a população entrou na lista: numa base que já
    tinha as capitais — isto é, em toda base existente — o `seed` não
    acrescentava o denominador, e o comparativo territorial continuava
    mostrando "—" sem que nada explicasse por quê. Guarda que impede a semente
    de corrigir a si mesma não protege nada; adia.

    O que reaplicar significa, dito para não surpreender: os nomes, UFs e
    populações DESTES 27 municípios voltam ao valor desta lista. Os outros
    5.543, carregados por `municipios-importar`, não são tocados.
    """
    return carregar(CAPITAIS)


def importar_csv(caminho):
    """Carrega a relação oficial do IBGE."""
    with open(caminho, encoding="utf-8-sig", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        faltando = {"codigo_ibge", "nome", "uf"} - set(leitor.fieldnames or [])
        if faltando:
            raise ValueError(
                f"CSV sem as colunas obrigatórias: {', '.join(sorted(faltando))}")
        linhas = [(l["codigo_ibge"], l["nome"], l["uf"],
                   l.get("populacao"), l.get("populacao_ano"))
                  for l in leitor]
    return carregar(linhas)
