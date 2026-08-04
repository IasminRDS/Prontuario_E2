# -*- coding: utf-8 -*-
"""Carga da tabela de municípios.

São 5.570 municípios no Brasil — a lista completa não cabe no repositório e nem
deveria: ela muda, e a fonte é o IBGE. Aqui ficam as 27 capitais, suficientes
para demonstrar e testar, mais o importador que carrega a tabela oficial.

Baixe a relação em https://www.ibge.gov.br/ (Municípios do Brasil) e rode:

    flask municipios-importar caminho/municipios.csv

O CSV precisa ter as colunas `codigo_ibge`, `nome` e `uf` (o cabeçalho é lido
pelo nome, então a ordem não importa).
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


def carregar(linhas):
    """Insere ou atualiza municípios. Devolve (gravados, erros)."""
    gravados, erros = 0, []

    for codigo, nome, uf in linhas:
        codigo = (codigo or "").strip()
        nome = (nome or "").strip()
        uf = (uf or "").strip().upper()

        problema = _validar(codigo, uf)
        if problema:
            erros.append(problema)
            continue

        existente = db.session.get(Municipio, codigo)
        if existente:
            existente.nome = nome
            existente.uf = uf
        else:
            db.session.add(Municipio(codigo_ibge=codigo, nome=nome, uf=uf))
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
        linhas = [(l["codigo_ibge"], l["nome"], l["uf"]) for l in leitor]
    return carregar(linhas)
