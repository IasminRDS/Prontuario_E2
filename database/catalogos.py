# -*- coding: utf-8 -*-
"""Catálogos de referência: exames, vacinas e estabelecimentos de demonstração.

Estas listas viviam dentro de um `_seed_if_empty()` chamado do `GET` do índice
de cada tela. Três problemas nisso:

- **Corrida.** `codigo` é único nos catálogos. Dois acessos simultâneos com a
  tabela vazia veem "vazio" ao mesmo tempo, ambos inserem, e um recebe violação
  de unicidade — um 500 numa requisição de leitura. Com dois workers no
  Procfile, isso é plausível no primeiro acesso depois de um deploy.
- **Semântica.** `GET` precisa ser seguro. Um crawler, um prefetch do navegador
  ou uma sonda de monitoramento passavam a escrever no banco.
- **Encobria a lacuna.** O `flask seed` não populava nada disso; a carga
  preguiçosa escondia o fato.

Carregar aqui resolve os três de uma vez: acontece uma vez, em processo
controlado, e o estado do banco passa a depender só do que foi mandado carregar.
"""
from database.db import db

EXAMES = [
    ("Hemograma completo", "EX001", "Laboratorial"),
    ("Glicemia de jejum", "EX002", "Laboratorial"),
    ("Hemoglobina glicada (HbA1c)", "EX003", "Laboratorial"),
    ("Colesterol total e frações", "EX004", "Laboratorial"),
    ("Triglicerídeos", "EX005", "Laboratorial"),
    ("TSH", "EX006", "Laboratorial"),
    ("T4 livre", "EX007", "Laboratorial"),
    ("Creatinina", "EX008", "Laboratorial"),
    ("Ureia", "EX009", "Laboratorial"),
    ("EAS (Urina tipo I)", "EX010", "Laboratorial"),
    ("Parasitológico de fezes", "EX011", "Laboratorial"),
    ("Beta-HCG", "EX012", "Laboratorial"),
    ("Raio-X de tórax", "EX013", "Imagem"),
    ("Ultrassonografia abdominal", "EX014", "Imagem"),
    ("Eletrocardiograma", "EX015", "Cardiológico"),
]

VACINAS = [
    ("BCG", "VAC001", "Dose única", "Ao nascer"),
    ("Hepatite B", "VAC002", "3 doses", "Ao nascer / adultos"),
    ("Pentavalente", "VAC003", "3 doses + reforço", "2, 4, 6 meses"),
    ("Poliomielite (VIP/VOP)", "VAC004", "3 doses + reforços", "2, 4, 6 meses"),
    ("Rotavírus", "VAC005", "2 doses", "2 e 4 meses"),
    ("Pneumocócica 10v", "VAC006", "2 doses + reforço", "2, 4 e 12 meses"),
    ("Meningocócica C", "VAC007", "2 doses + reforço", "3, 5 e 12 meses"),
    ("Febre Amarela", "VAC008", "1 dose + reforço", "9 meses"),
    ("Tríplice Viral (SCR)", "VAC009", "2 doses", "12 e 15 meses"),
    ("Tetraviral", "VAC010", "1 dose", "15 meses"),
    ("DTP", "VAC011", "Reforços", "15 meses e 4 anos"),
    ("HPV quadrivalente", "VAC012", "2 doses", "9 a 14 anos"),
    ("dT (Dupla adulto)", "VAC013", "3 doses + reforço", "Adolescentes e adultos"),
    ("Influenza", "VAC014", "Anual", "Grupos prioritários"),
    ("COVID-19", "VAC015", "Conforme campanha", "População elegível"),
]

# Estabelecimentos de demonstração. Os códigos CNES são fictícios; a rede real
# entra pelo cadastro em `/unidades/` ou por carga a partir do CNES aberto.
#
# A rede está distribuída por QUATRO municípios e DOIS estados, e isso não é
# enfeite: o comparativo territorial agrega por município, e uma rede inteira
# numa cidade só produz uma tabela de uma linha — que não compara nada e não
# demonstra nada. Com esta distribuição, o filtro por UF também passa a ter o
# que separar.
#
# `Clínica Pública Municipal I` nasceu sem código IBGE, e isso a deixava fora
# de TODA agregação territorial: a junção é com `municipios`, então a unidade
# sumia do relatório sem erro nenhum. Semente que distribui a rede e depois
# esconde um quarto dela é pior do que semente que não distribui — o código foi
# conferido na API de localidades do IBGE.
UNIDADES = [
    ("UBS Central", "UBS", "0000001", "João Pessoa", "PB", "2507507"),
    ("UBS Bairro Norte", "UBS", "0000002", "João Pessoa", "PB", "2507507"),
    ("Clínica Pública Municipal I", "Clínica Pública", "0000003",
     "Campina Grande", "PB", "2504009"),
    ("Hospital Municipal São Lucas", "Hospital", "0000004",
     "João Pessoa", "PB", "2507507"),
    ("UBS Barra", "UBS", "0000005", "Salvador", "BA", "2927408"),
    ("Hospital Geral do Subúrbio", "Hospital", "0000006",
     "Salvador", "BA", "2927408"),
    ("Hospital Municipal de Bom Jesus da Lapa", "Hospital", "0000007",
     "Bom Jesus da Lapa", "BA", "2903904"),
]


def seed_catalogo_exames():
    from models.catalogo_exame import CatalogoExame

    if CatalogoExame.query.count():
        return 0
    for nome, codigo, grupo in EXAMES:
        db.session.add(CatalogoExame(nome=nome, codigo=codigo, grupo=grupo,
                                     ativo=True))
    db.session.commit()
    return len(EXAMES)


def seed_catalogo_vacinas():
    from models.catalogo_vacina import CatalogoVacina

    if CatalogoVacina.query.count():
        return 0
    for nome, codigo, doses, faixa in VACINAS:
        db.session.add(CatalogoVacina(nome=nome, codigo=codigo, doses=doses,
                                      faixa=faixa, ativo=True))
    db.session.commit()
    return len(VACINAS)


def seed_unidades():
    """Só completa a rede; nunca mexe em unidade já cadastrada.

    O `seed_data` cria a primeira unidade antes daqui, então a checagem é por
    CNES e não por "a tabela está vazia".
    """
    from models.unidade_saude import UnidadeSaude

    criadas = 0
    for nome, tipo, cnes, cidade, uf, ibge in UNIDADES:
        existente = UnidadeSaude.query.filter_by(cnes=cnes).first()
        if existente:
            # Preenche a chave territorial quando ela FALTA, e só nesse caso.
            # Não é sobrescrever cadastro: é reparar unidade semeada antes de a
            # semente ter o código, que sem isso ficaria invisível em todo
            # relatório agregado — sem erro, sem aviso, sem linha.
            if ibge and not existente.municipio_ibge:
                existente.municipio_ibge = ibge
            continue
        db.session.add(UnidadeSaude(
            nome=nome, tipo=tipo, cnes=cnes, cidade=cidade, uf=uf,
            municipio_ibge=ibge, ativo=True))
        criadas += 1
    db.session.commit()
    return criadas


def seed_todos():
    return {
        "exames": seed_catalogo_exames(),
        "vacinas": seed_catalogo_vacinas(),
        "unidades": seed_unidades(),
    }
