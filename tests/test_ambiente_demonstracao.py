# -*- coding: utf-8 -*-
"""O ambiente que a banca vê, e que nenhum teste olhava.

`database/seeds.py` e `services/seed_volume.py` não tinham um único caso. Foi
assim que três defeitos sobreviveram até alguém abrir as telas:

- os 46 leitos nasciam todos em `Unidade.query.first()`, que é a **UBS Central**
  — uma unidade básica de saúde com UTI e maternidade, enquanto os três
  hospitais da rede apareciam com zero leitos;
- `seed-volume` não podia ser repetido: o CPF vinha do índice do laço, que
  recomeça em zero, e a segunda execução estourava o `UNIQUE` com uma
  `IntegrityError` crua;
- triagem, prontuário, agenda e exames ficavam **vazios**, porque
  `gerar_clinicas` cobre só as cinco tabelas do backfill que a motivou.

Nenhum dos três gera erro em teste de rota: as telas respondem 200 e mostram
lista vazia, que é indistinguível de "ainda não houve atendimento".
"""
import pytest


# ------------------------------------------------------- leitos e unidades
def test_leito_nasce_em_hospital_e_nao_em_unidade_basica(app):
    """Unidade básica de saúde não interna, e o cadastro diz qual é qual.

    Mede o banco semeado, e não a constante: o defeito não era a lista de
    setores, era a unidade escolhida para recebê-los.
    """
    from extensions import db
    from models.internacao import Leito
    from models.unidade_saude import UnidadeSaude
    from database.seeds import TIPOS_COM_LEITO

    with app.app_context():
        por_tipo = dict(
            db.session.query(UnidadeSaude.tipo, db.func.count(Leito.id))
            .join(Leito, Leito.unidade_id == UnidadeSaude.id)
            .group_by(UnidadeSaude.tipo).all())

    assert por_tipo, "nenhum leito semeado — a internação não é demonstrável"
    fora = {t: n for t, n in por_tipo.items() if t not in TIPOS_COM_LEITO}
    assert not fora, (
        f"leito em unidade que não interna: {fora}. Uma UBS com UTI é a "
        "primeira coisa que quem conhece o SUS repara na tela de ocupação")


def test_todo_hospital_da_rede_tem_leito(app):
    """Hospital com zero leitos deixa o painel de ocupação sem o que mostrar."""
    from extensions import db
    from models.internacao import Leito
    from models.unidade_saude import UnidadeSaude
    from database.seeds import TIPOS_COM_LEITO

    with app.app_context():
        hospitais = (UnidadeSaude.query
                     .filter(UnidadeSaude.tipo.in_(TIPOS_COM_LEITO)).all())
        vazios = [h.nome for h in hospitais
                  if not db.session.query(Leito.id)
                  .filter(Leito.unidade_id == h.id).first()]

    assert hospitais, "nenhum hospital na rede de demonstração"
    assert not vazios, f"hospital sem leito nenhum: {vazios}"


def test_numero_do_leito_diz_de_que_hospital_e(app):
    """`CM-01` em três hospitais é indistinguível na tela de ocupação.

    O setor é catálogo da rede — o model não tem `unidade_id` —, então é o
    número do leito que precisa carregar a unidade.
    """
    from models.internacao import Leito

    with app.app_context():
        numeros = [n for (n,) in Leito.query.with_entities(Leito.numero).all()]

    assert len(numeros) == len(set(numeros)), (
        "há leitos com o mesmo número em hospitais diferentes")


# ------------------------------------------------- o que limpar precisa saber
def _modelos_escritos(fonte):
    """Modelos em que os geradores inserem, lidos da própria fonte."""
    import re

    return set(re.findall(r"_inserir\(\s*([A-Z]\w+)", fonte)) | set(
        re.findall(r"db\.session\.execute\(\s*([A-Z]\w+)\.__table__\.insert", fonte))


def test_limpar_alcanca_tudo_que_os_geradores_escrevem():
    """Limpeza que deixa resto faz a execução seguinte medir um banco desconhecido.

    Estrutural de propósito, e não um caso por tabela: a lista de geradores
    cresce, e o que precisa continuar verdadeiro é a RELAÇÃO entre o que se
    escreve e o que se apaga. Foi acrescentando quatro tabelas ao gerador que
    isto apareceu — `limpar` continuaria apagando cinco.
    """
    import pathlib

    fonte = (pathlib.Path(__file__).resolve().parent.parent / "services"
             / "seed_volume.py").read_text(encoding="utf-8")

    geradores, _, faxina = fonte.partition("def limpar(")
    escritos = _modelos_escritos(geradores)
    apagados = set(__import__("re").findall(r"\(([A-Z]\w+), \"", faxina)) | set(
        __import__("re").findall(r"sa\.delete\(([A-Z]\w+)\)", faxina))

    assert escritos, "não encontrei os modelos escritos pelos geradores"
    esquecidos = escritos - apagados
    assert not esquecidos, (
        f"os geradores escrevem em {sorted(esquecidos)} e `limpar` não apaga: "
        "`--limpar` promete devolver o banco ao estado anterior")


# ------------------------------------------------------ repetir o comando
@pytest.fixture
def sem_sinteticos(app):
    """Só roda se o banco não tiver sintéticos de outra origem.

    Evita que este caso apague dado que não criou — e evita medir uma contagem
    que outro teste esteja mexendo.
    """
    from models.paciente import Paciente
    from services.seed_volume import MARCA

    with app.app_context():
        if Paciente.query.filter(Paciente.nome.like(f"%[{MARCA}]%")).first():
            pytest.skip("já há pacientes sintéticos neste banco")
    return True


def test_seed_volume_pode_ser_repetido(app, sem_sinteticos):
    """O defeito: o documento vinha do índice do laço, que recomeça em zero.

    Duas execuções produziam exatamente os mesmos CPFs, o `UNIQUE` estourava, e
    o operador via uma `IntegrityError` crua que não dizia o que fazer. O comando
    existe para PÔR VOLUME, e pôr mais volume é a operação natural de repeti-lo.
    """
    from extensions import db
    from models.paciente import Paciente
    from services import seed_volume as sv

    criados = []
    try:
        with app.app_context():
            primeira = sv.gerar(pacientes=3)
            segunda = sv.gerar(pacientes=3)

            sinteticos = Paciente.query.filter(
                Paciente.nome.like(f"%[{sv.MARCA}]%")).all()
            criados = [p.id for p in sinteticos]
            documentos = [p.cpf for p in sinteticos]

        assert primeira["ja_existiam"] == 0
        assert segunda["ja_existiam"] == 3, (
            "a segunda execução não viu os cadastros da primeira e recomeçaria "
            "a numeração do zero")
        assert len(documentos) == 6
        assert len(set(documentos)) == 6, (
            f"documento repetido entre execuções: {documentos}")
    finally:
        if criados:
            with app.app_context():
                db.session.execute(
                    Paciente.__table__.delete().where(
                        Paciente.__table__.c.id.in_(criados)))
                db.session.commit()
