# -*- coding: utf-8 -*-
"""Campo de código oficial que não consulta a terminologia.

Mesma família dos outros detectores: o defeito não gera erro, apenas deixa de
funcionar — e aqui o prejuízo não aparece na tela de quem digita, e sim meses
depois, na hora de agregar.

O catálogo SIGTAP era servido por `/tabelas/api/sigtap` desde sempre e
**nenhuma tela o chamava**; o de CID-10 alcançava um formulário, enquanto onze
pediam CID. Os campos aceitavam texto livre com um código de exemplo no
`placeholder` — o que pede um código e aceita qualquer coisa.

É o argumento que `models/municipio.py` faz por escrito sobre `cidade`/`uf`:
texto livre "funciona numa unidade e falha numa federação". Vale inteiro para o
procedimento, com o agravante de que a AIH é o documento que alimenta o SIHSUS
— procedimento errado é AIH que não fatura e agregação que não fecha.

A lista `LIVRE_POR_DECISAO` reprova **nos dois sentidos**: campo novo sem
terminologia falha, e justificativa para campo que já foi ligado também. Sem
isso a lista vira decoração.
"""
import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TEMPLATES = RAIZ / "templates"

# Prefixo do atributo `name` -> terminologia que o campo deve consultar.
ESPERADO = {
    "cid": "cid10",
    "procedimento": "sigtap",
}

# Campo que é texto livre de propósito. Cada entrada precisa de razão escrita.
LIVRE_POR_DECISAO = {
    ("cirurgia/form.html", "procedimento"):
        "É a descrição da cirurgia ('Colecistectomia videolaparoscópica'), "
        "mapeada para Cirurgia.descricao — nome do procedimento, não código de "
        "faturamento. Trocar por código SIGTAP mudaria o significado do campo.",
}

ENTRADA = re.compile(r"<input\b[^>]*>", re.S)
NOME = re.compile(r'name="([^"]+)"')


def _campos():
    """(arquivo, nome do campo, tag) de todo <input> dos templates."""
    for arquivo in sorted(TEMPLATES.rglob("*.html")):
        texto = arquivo.read_text(encoding="utf-8", errors="replace")
        for tag in ENTRADA.findall(texto):
            achado = NOME.search(tag)
            if achado:
                yield (arquivo.relative_to(TEMPLATES).as_posix(),
                       achado.group(1), tag)


def _terminologia_esperada(nome):
    """Terminologia devida a um campo, pelo nome. None se não for campo de código."""
    for prefixo, tabela in ESPERADO.items():
        if nome == prefixo or nome.startswith(prefixo + "_"):
            return tabela
    return None


def test_campo_de_codigo_oficial_consulta_a_terminologia():
    """Nenhum campo de CID ou de procedimento SIGTAP fica sem autocomplete."""
    soltos = []
    for arquivo, nome, tag in _campos():
        tabela = _terminologia_esperada(nome)
        if tabela is None:
            continue
        if (arquivo, nome) in LIVRE_POR_DECISAO:
            continue
        if 'data-terminologia' not in tag:
            soltos.append(f"  {arquivo}: name={nome!r} (esperado {tabela})")

    assert not soltos, (
        "campo de código oficial aceitando texto livre — o usuário digita, o "
        "sistema grava e a agregação não fecha:\n" + "\n".join(soltos) +
        "\n\nLigue com data-terminologia=\"...\" ou justifique em "
        "LIVRE_POR_DECISAO."
    )


def test_a_terminologia_declarada_e_a_devida_ao_campo():
    """Campo de CID não pode apontar para SIGTAP, e vice-versa.

    Errar a tabela é pior do que não ter autocomplete: a lista sugere códigos
    do catálogo errado, e o usuário confia nela.
    """
    trocados = []
    for arquivo, nome, tag in _campos():
        achado = re.search(r'data-terminologia="([^"]+)"', tag)
        if not achado:
            continue
        esperada = _terminologia_esperada(nome)
        if esperada and achado.group(1) != esperada:
            trocados.append(
                f"  {arquivo}: name={nome!r} usa {achado.group(1)!r}, "
                f"esperado {esperada!r}")

    assert not trocados, "terminologia trocada:\n" + "\n".join(trocados)


def test_justificativa_de_texto_livre_ainda_se_aplica():
    """O outro sentido: entrada que sobrou depois que o campo foi ligado."""
    vivos = {(a, n) for a, n, _ in _campos()}
    obsoletas = []
    for chave in LIVRE_POR_DECISAO:
        if chave not in vivos:
            obsoletas.append(f"  {chave[0]}: name={chave[1]!r} não existe mais")
            continue
        for arquivo, nome, tag in _campos():
            if (arquivo, nome) == chave and 'data-terminologia' in tag:
                obsoletas.append(
                    f"  {chave[0]}: name={chave[1]!r} já consulta terminologia")

    assert not obsoletas, (
        "justificativa em LIVRE_POR_DECISAO que não vale mais — remova:\n"
        + "\n".join(obsoletas)
    )


@pytest.mark.parametrize("tabela", sorted(set(ESPERADO.values())))
def test_a_terminologia_usada_pelos_formularios_responde(cliente, tabela):
    """O wiring precisa apontar para catálogo que existe e devolve item.

    Sem isto, ligar o campo à tabela errada passaria despercebido: o
    autocomplete simplesmente nunca sugeriria nada, que é como ele se comporta
    quando está offline.
    """
    resposta = cliente.get(f"/tabelas/api/{tabela}")
    assert resposta.status_code == 200, resposta.get_data(as_text=True)[:200]

    itens = resposta.get_json()
    assert isinstance(itens, list) and itens, f"catálogo {tabela} veio vazio"
    assert "codigo" in itens[0], (
        f"o autocomplete lê 'codigo' de cada item; {tabela} devolveu "
        f"{sorted(itens[0])}")
