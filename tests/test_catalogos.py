# -*- coding: utf-8 -*-
"""Catálogos de referência vêm da carga inicial, não de um GET.

Três telas populavam a própria tabela dentro do `GET` do índice. Além de um GET
que escreve violar a semântica de HTTP — crawler, prefetch e sonda de
monitoramento passam a gravar —, `codigo` é único nos catálogos: dois acessos
simultâneos com a tabela vazia colidiam, e um virava 500 numa leitura.
"""
import sqlalchemy as sa

from database.catalogos import seed_todos
from extensions import db

TELAS = ["/catalogo-exames/", "/catalogo-vacinas/", "/unidades/"]


def _contagens(app):
    from models.catalogo_exame import CatalogoExame
    from models.catalogo_vacina import CatalogoVacina
    from models.unidade_saude import UnidadeSaude

    with app.app_context():
        return (CatalogoExame.query.count(),
                CatalogoVacina.query.count(),
                UnidadeSaude.query.count())


def test_a_carga_inicial_popula_os_catalogos(app):
    """Antes, `flask seed` não populava nada disso — a tela é que populava."""
    from models.catalogo_exame import CatalogoExame
    from models.catalogo_vacina import CatalogoVacina

    with app.app_context():
        assert CatalogoExame.query.count() > 0
        assert CatalogoVacina.query.count() > 0


def test_abrir_a_tela_nao_grava_nada(app, autenticado_confirmado):
    antes = _contagens(app)
    for tela in TELAS:
        autenticado_confirmado.get(tela)
    assert _contagens(app) == antes, (
        "uma requisição GET alterou o banco"
    )


def test_carga_e_idempotente(app):
    antes = _contagens(app)
    with app.app_context():
        resultado = seed_todos()
        db.session.commit()
    assert _contagens(app) == antes
    assert resultado == {"exames": 0, "vacinas": 0, "unidades": 0}, (
        f"a carga inseriu de novo: {resultado}"
    )


def test_nao_ha_codigo_de_catalogo_repetido(app):
    """O índice único já garante, mas a carga precisa respeitá-lo sem estourar."""
    with app.app_context():
        for tabela, coluna in [("catalogo_exames", "codigo"),
                               ("catalogo_vacinas", "codigo")]:
            repetidos = db.session.execute(sa.text(
                f'select count(*) from (select "{coluna}" from "{tabela}" '
                f'group by "{coluna}" having count(*) > 1) x')).scalar()
            assert repetidos == 0, f"{tabela} tem código repetido"


def test_nenhuma_rota_get_chama_carga_de_catalogo():
    """Guarda estrutural: o padrão não pode voltar por outra tela."""
    import pathlib
    import re

    raiz = pathlib.Path(__file__).resolve().parent.parent / "routes"
    culpados = []
    for arquivo in sorted(raiz.glob("*.py")):
        texto = arquivo.read_text(encoding="utf-8")
        if re.search(r"def _seed_if_empty\b", texto):
            culpados.append(arquivo.name)
    assert not culpados, (
        "carga preguiçosa dentro de rota voltou em: " + ", ".join(culpados))
