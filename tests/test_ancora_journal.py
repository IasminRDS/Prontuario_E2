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
import hashlib
import json
from datetime import datetime

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


# --- Manipulações, uma a uma: o que detecta e o que não ---------------------
#
# "Limitação teórica" é o estado em que uma afirmação de segurança sobrevive sem
# ser medida. Cada caso abaixo aplica UMA manipulação e fixa o resultado —
# inclusive quando o resultado é "não detecta", que é a informação mais cara de
# obter e a mais fácil de perder.

def test_reordenar_linhas_e_detectado():
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"), (30, 30, "h30"))
    linhas[1], linhas[2] = linhas[2], linhas[1]

    problemas = an.verificar(linhas)
    assert any("elo rompido" in p for p in problemas), (
        "trocar duas âncoras de lugar passou — a ordem faz parte da prova")


def test_duplicar_linha_e_detectado():
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"))
    linhas.insert(1, dict(linhas[1]))

    problemas = an.verificar(linhas)
    assert any("elo rompido" in p for p in problemas), (
        "duplicar uma âncora passou — repetir um retrato inflaria a contagem "
        "de checkpoints sem que nenhum novo tenha sido emitido")


def test_inserir_linha_forjada_no_meio_e_detectado():
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"), (30, 30, "h30"))
    intrusa = an.montar(15, 15, "h15", anterior=linhas[0]["hash_ancora"])
    linhas.insert(1, intrusa)

    problemas = an.verificar(linhas)
    assert problemas, (
        "inserir âncora forjada no meio passou, ainda que ela se encadeie "
        "corretamente na anterior: a SEGUINTE deixa de fechar")
    assert any("elo rompido" in p for p in problemas)


def test_truncar_o_meio_e_detectado():
    linhas = _cadeia((10, 10, "h10"), (20, 20, "h20"), (30, 30, "h30"),
                     (40, 40, "h40"))
    del linhas[1:3]

    assert any("elo rompido" in p for p in an.verificar(linhas))


def test_recomputar_a_cadeia_inteira_NAO_e_detectado():
    """A limitação de fundo, exercitada — e a razão de a custódia ser o ponto.

    Quem controla o arquivo pode reescrever TODAS as âncoras a partir do zero,
    coerentes entre si e coerentes com uma trilha já truncada. Nenhuma
    propriedade interna distingue esse journal de um legítimo, porque não há
    nada dentro do arquivo que testemunhe sobre o que existia fora dele.

    É o que separa este mecanismo de uma prova: ele detecta adulteração
    PARCIAL. Contra reescrita total, só vale um valor retido fora — e é por
    isso que `--retida` existe e que a emissão insiste em imprimir o hash.
    """
    honesto = _cadeia((10, 10, "h10"), (20, 20, "h20"), (30, 30, "h30"))
    retido = honesto[1]["hash_ancora"]

    forjado = _cadeia((10, 10, "h10"), (12, 12, "h12"))

    assert an.verificar(forjado) == [], (
        "a reescrita completa passou a ser detectável internamente — se foi "
        "de propósito, atualize a seção 12 da monografia")

    # O que a desmascara é exclusivamente o valor guardado fora.
    assert an.localizar(forjado, retido) is None, (
        "a âncora retida não deveria existir no journal forjado")


def test_formato_da_linha_e_contrato_congelado():
    """Golden vector: mudar a serialização invalida TODO hash já retido.

    É a falha mais silenciosa possível deste mecanismo. Uma refatoração que
    reordene campos, troque separadores ou passe a escapar não-ASCII não quebra
    teste algum, não gera erro — e faz com que toda âncora guardada fora deixe
    de conferir, precisamente quando alguém for usá-la. Este caso trava o
    formato com um valor calculado à mão.
    """
    linha = an.montar(42, 99, "abc", anterior=None,
                      emitida_em=datetime(2026, 1, 15, 10, 30, 0))

    esperado = ('{"emitida_em":"2026-01-15T10:30:00","hash_final":"abc",'
                '"total":42,"ultimo_id":99,"versao":1}')
    conteudo = {c: linha[c] for c in
                ("versao", "emitida_em", "total", "ultimo_id", "hash_final")}
    assert an._canonico(conteudo) == esperado, (
        "a forma canônica mudou — toda âncora já guardada fora deste servidor "
        "deixou de conferir, e ninguém será avisado até tentar usá-la")

    assert linha["hash_ancora"] == hashlib.sha256(
        (esperado + "|").encode("utf-8")).hexdigest()
