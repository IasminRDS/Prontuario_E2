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
CAPITAIS = [
    ("1100205", "Porto Velho", "RO"),
    ("1200401", "Rio Branco", "AC"),
    ("1302603", "Manaus", "AM"),
    ("1400100", "Boa Vista", "RR"),
    ("1501402", "Belém", "PA"),
    ("1600303", "Macapá", "AP"),
    ("1721000", "Palmas", "TO"),
    ("2111300", "São Luís", "MA"),
    ("2211001", "Teresina", "PI"),
    ("2304400", "Fortaleza", "CE"),
    ("2408102", "Natal", "RN"),
    ("2507507", "João Pessoa", "PB"),
    ("2611606", "Recife", "PE"),
    ("2704302", "Maceió", "AL"),
    ("2800308", "Aracaju", "SE"),
    ("2927408", "Salvador", "BA"),
    ("3106200", "Belo Horizonte", "MG"),
    ("3205309", "Vitória", "ES"),
    ("3304557", "Rio de Janeiro", "RJ"),
    ("3550308", "São Paulo", "SP"),
    ("4106902", "Curitiba", "PR"),
    ("4205407", "Florianópolis", "SC"),
    ("4314902", "Porto Alegre", "RS"),
    ("5002704", "Campo Grande", "MS"),
    ("5103403", "Cuiabá", "MT"),
    ("5208707", "Goiânia", "GO"),
    ("5300108", "Brasília", "DF"),
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
    texto = (bruto or "").strip().replace(".", "").replace(" ", "")
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
    """Idempotente: só insere o que falta."""
    if Municipio.query.count():
        return 0, []
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
