# -*- coding: utf-8 -*-
"""O journal de âncoras, e o que ele prova e não prova.

Cada caso aqui corresponde a uma afirmação da docstring de `utils/ancora.py`.
Isso é deliberado: a docstring faz promessas de segurança, e promessa de
segurança sem caso que a exercite é a definição do defeito que a seção 9.4.2 da
monografia documenta.

Inclui os dois casos NEGATIVOS — o que o mecanismo não fecha —, porque uma
limitação que ninguém exercita vira, com o tempo, uma garantia que ninguém
verificou.
"""
import json

import pytest

from utils import ancora as an


@pytest.fixture
def journal(tmp_path):
    return tmp_path / "ancoras.jsonl"


def _cadeia(*retratos):
    """Monta um journal encadeado a partir de (total, ultimo_id, hash_final)."""
    linhas, anterior = [], None
    for total, ultimo_id, hash_final in retratos:
        linha = an.montar(total, ultimo_id, hash_final, anterior)
        anterior = linha["hash_ancora"]
        linhas.append(linha)
    return linhas


def _gravar(caminho, linhas):
    caminho.write_text(
        "\n".join(an._canonico(l) for l in linhas) + "\n", encoding="utf-8")


def test_cadeia_intacta_nao_acusa(journal):
    """Falso positivo aqui faz a verificação periódica virar ruído."""
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"), (30, 30, "h30"))
    assert an.verificar(linhas) == []


def test_ancora_reescrita_e_detectada(journal):
    """Reescrever uma âncora passada para acomodar truncamento antigo.

    É o caso que a âncora única não vê: com um só retrato, quem apaga o fim da
    trilha reescreve o retrato e o par volta a fechar.
    """
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"), (30, 30, "h30"))
    linhas[1]["total"] = 5          # finge que a trilha sempre foi menor

    problemas = an.verificar(linhas)
    assert problemas, "reescrever uma âncora do meio passou despercebido"
    assert any("conteúdo alterado" in p for p in problemas)


def test_ancora_removida_do_meio_e_detectada(journal):
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"), (30, 30, "h30"))
    del linhas[1]

    problemas = an.verificar(linhas)
    assert any("elo rompido" in p for p in problemas)


def test_trilha_que_encolheu_entre_checkpoints(journal):
    """O achado que não depende de NADA guardado fora.

    Duas âncoras legítimas, cadeia intacta, e a segunda registra menos
    registros que a primeira. A trilha encolheu entre os dois checkpoints —
    e hoje ela pode estar perfeitamente consistente consigo mesma.
    """
    linhas = _cadeia((100, 100, "h100"), (40, 40, "h40"))

    problemas = an.verificar(linhas)
    assert problemas, (
        "trilha que encolheu entre dois checkpoints passou — é o caso que "
        "justifica guardar mais de um retrato")
    assert any("ENCOLHEU" in p for p in problemas)
    assert any("retrocedeu" in p for p in problemas)


def test_uma_linha_retida_valida_todo_o_prefixo(journal):
    """O ganho principal: custódia de 'guarde qualquer uma, uma vez'.

    Retida a segunda âncora, o operador confirma que ela pertence a este
    journal e que tudo até ela fecha — sem ter guardado as demais.
    """
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"), (30, 30, "h30"))
    retida = linhas[1]["hash_ancora"]

    indice = an.localizar(linhas, retida)
    assert indice == 1
    assert an.verificar(linhas[:indice + 1]) == []

    # E se alguém reescreveu algo ANTES dela, o prefixo deixa de fechar.
    linhas[0]["total"] = 1
    assert an.verificar(linhas[:indice + 1])


def test_hash_retido_de_outro_journal_nao_e_encontrado(journal):
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"))
    assert an.localizar(linhas, "hash que nunca existiu") is None


def test_bom_no_arquivo_nao_e_tratado_como_adulteracao(journal):
    """BOM aparece quando o journal passa por ferramenta do Windows.

    Acusá-lo como cadeia rompida manda o operador caçar fantasma exatamente no
    momento em que ele precisa confiar no resultado.
    """
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"))
    journal.write_text(
        "﻿" + "\n".join(an._canonico(l) for l in linhas) + "\n",
        encoding="utf-8")

    lidas, defeitos = an.ler(journal)
    assert defeitos == []
    assert len(lidas) == 2
    assert an.verificar(lidas) == []


def test_linha_ilegivel_nao_impede_a_leitura_do_resto(journal):
    """Journal parcialmente corrompido ainda tem prefixo verificável."""
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"))
    journal.write_text(
        an._canonico(linhas[0]) + "\nnão é json\n" + an._canonico(linhas[1]) + "\n",
        encoding="utf-8")

    lidas, defeitos = an.ler(journal)
    assert len(defeitos) == 1
    assert len(lidas) == 2


def test_serializacao_e_estavel(journal):
    """Hash sobre JSON de ordem variável acusaria adulteração inexistente."""
    linha = an.montar(10, 10, "h10")
    assert an._canonico(linha) == an._canonico(json.loads(an._canonico(linha)))


# --- O que o mecanismo NÃO fecha ------------------------------------------

def test_truncar_o_fim_do_journal_permanece_indetectavel(journal):
    """A limitação, exercitada — e é por isso que a custódia externa é o ponto.

    Apagadas as últimas linhas, as que sobram continuam encadeadas entre si e
    nada no arquivo diz que ele já foi maior. É a mesma recursão do problema
    original: encadear desloca a pergunta, não a responde. Só um valor guardado
    fora, ou um destino que a aplicação não controle, a responde.

    Este caso existe para que a limitação continue verdadeira por medição. Se
    algum dia ele passar a falhar, é porque alguém acrescentou uma defesa — e
    então a documentação precisa mudar junto.
    """
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"), (30, 30, "h30"))
    truncado = linhas[:1]

    assert an.verificar(truncado) == [], (
        "truncar o fim passou a ser detectável pelo journal — se foi de "
        "propósito, atualize a docstring de utils/ancora.py e a seção 12 da "
        "monografia, que hoje afirmam o contrário")
