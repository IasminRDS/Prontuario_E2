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
import pathlib
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



# --- A matriz de garantias -------------------------------------------------
#
# Esta tabela É a fonte dos casos abaixo, e não um documento ao lado deles.
# Documento paralelo deriva: alguém corrige o código, o teste acompanha, e a
# tabela continua afirmando o que era verdade no ano passado. Aqui a única
# forma de mudar o que a tabela promete é mudar o que o teste mede.
#
# A coluna que importa é a das linhas com `detectado=False`. Elas são o que
# distingue este mecanismo de uma prova, e existem para ser confrontadas: quem
# quiser convertê-las precisa antes explicar como detectar coerência interna
# de fora dela.

def _reordenar(linhas):
    linhas[1], linhas[2] = linhas[2], linhas[1]
    return linhas


def _duplicar(linhas):
    linhas.insert(1, dict(linhas[1]))
    return linhas


def _inserir_forjada(linhas):
    linhas.insert(1, an.montar(15, 15, "h15",
                               anterior=linhas[0]["hash_ancora"]))
    return linhas


def _remover_do_meio(linhas):
    del linhas[1]
    return linhas


def _reescrever_do_meio(linhas):
    linhas[1]["total"] = 5
    return linhas


def _campo_extra(linhas):
    linhas[1]["observacao"] = "conferido e aprovado pela auditoria externa"
    return linhas


def _truncar_o_fim(linhas):
    return linhas[:1]


def _recomputar_tudo(_linhas):
    # Coerente consigo mesmo, e coerente com uma trilha já truncada.
    return _cadeia((10, 10, "h10"), (12, 12, "h12"))


MATRIZ = (
    ("reordenar duas linhas", _reordenar, True,
     "a ordem faz parte da prova: o elo da linha deslocada deixa de bater"),
    ("duplicar uma linha", _duplicar, True,
     "a cópia ocupa o lugar da precedente e a seguinte deixa de apontar certo"),
    ("inserir linha forjada no meio", _inserir_forjada, True,
     "encadeia-se corretamente na anterior, mas a SEGUINTE não fecha"),
    ("remover linha do meio", _remover_do_meio, True,
     "o elo da seguinte aponta para uma linha que não está mais ali"),
    ("reescrever uma linha passada", _reescrever_do_meio, True,
     "é a manobra que a âncora ÚNICA não vê, e a razão de haver journal"),
    ("acrescentar campo não previsto", _campo_extra, True,
     "o hash cobre só os campos declarados; sem validação de forma, conteúdo "
     "forjado viajaria dentro de uma linha que fecha"),
    ("truncar o FIM do journal", _truncar_o_fim, False,
     "as linhas que sobram seguem encadeadas e nada no arquivo diz que ele "
     "já foi maior — mesma recursão do problema original"),
    ("recomputar o journal inteiro", _recomputar_tudo, False,
     "quem controla o arquivo produz um journal internamente coerente; só o "
     "valor retido FORA o desmascara"),
)


@pytest.mark.parametrize("nome,manipular,detectado,porque",
                         MATRIZ, ids=[m[0] for m in MATRIZ])
def test_matriz_de_garantias(nome, manipular, detectado, porque):
    """Cada linha da matriz, medida. Inclusive as que dizem 'não detecta'."""
    linhas = manipular(_cadeia((10, 10, "h10"), (20, 20, "h20"),
                               (30, 30, "h30")))
    problemas = an.verificar(linhas)

    if detectado:
        assert problemas, (
            f"a matriz promete detectar '{nome}' e não detectou — {porque}")
    else:
        assert problemas == [], (
            f"'{nome}' passou a ser detectado. Se foi de propósito, atualize a "
            f"MATRIZ, a constante NAO_DETECTAVEL e a seção 12 da monografia, "
            f"que hoje afirmam o contrário. Motivo registrado: {porque}")


def test_matriz_cobre_tudo_que_o_modulo_declara_indetectavel():
    """`NAO_DETECTAVEL` e a matriz não podem divergir.

    A constante é o que alguém lê no código; a matriz é o que foi medido. Se
    uma listar o que a outra não lista, uma das duas está mentindo, e não há
    como saber qual sem refazer a medição.
    """
    na_matriz = {nome for nome, _f, detectado, _p in MATRIZ if not detectado}
    assert len(na_matriz) == len(an.NAO_DETECTAVEL), (
        f"a matriz mede {len(na_matriz)} manipulações indetectáveis e o módulo "
        f"declara {len(an.NAO_DETECTAVEL)} — as duas listas divergiram")
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


# --- Compatibilidade retroativa --------------------------------------------

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "journal_v1_congelado.jsonl"

# Hash da SEGUNDA âncora do arquivo congelado, transcrito aqui à mão. Faz o
# papel do valor que um operador teria guardado fora do servidor em março de
# 2026 — e é contra ele que a compatibilidade se mede.
RETIDO_EM_MARCO = "3f5cf6460b89e4c0a11cea626c1dacae57101b952bd1acc36555a5a102416df4"


def test_journal_v1_antigo_continua_valido():
    """O risco nº 1 deste mecanismo, e o mais silencioso.

    O golden vector trava a serialização de UMA linha. Este caso trava o
    pipeline inteiro contra BYTES escritos por uma versão anterior: leitura,
    validação de forma, recálculo de hash e conferência da cadeia.

    O arquivo em `tests/fixtures/` é dado literal e **não deve ser
    regenerado**. Regenerá-lo para fazer o teste passar é destruir a própria
    medição: se ele deixou de conferir, é porque toda âncora já retida fora de
    um servidor em produção também deixou — e ninguém saberá disso até tentar
    usá-la, que é sempre o pior momento.
    """
    linhas, defeitos = an.ler(FIXTURE)

    assert defeitos == [], f"o journal congelado ficou ilegível: {defeitos}"
    assert len(linhas) == 3
    assert an.verificar(linhas) == [], (
        "um journal emitido por versão anterior deixou de conferir — a "
        "compatibilidade retroativa quebrou, e com ela toda âncora retida")


def test_hash_retido_ha_meses_ainda_localiza_e_valida_o_prefixo():
    """A promessa operacional: 'guarde uma, uma vez' precisa valer no futuro."""
    linhas, _ = an.ler(FIXTURE)

    indice = an.localizar(linhas, RETIDO_EM_MARCO)
    assert indice == 1, (
        "o hash retido não foi mais encontrado no journal — o cálculo mudou, e "
        "quem guardou o valor não tem como saber")
    assert an.verificar(linhas[: indice + 1]) == []


def test_verificador_e_idempotente():
    """Duas execuções, o mesmo resultado — e o mesmo texto.

    Parece trivial e não é: pega leitura parcial de arquivo, dependência de
    estado entre chamadas e diferença de decodificação entre a primeira e a
    segunda leitura. Verificador cujo veredito oscila é pior que nenhum,
    porque a dúvida passa a recair sobre o instrumento.
    """
    primeira_leitura, _ = an.ler(FIXTURE)
    segunda_leitura, _ = an.ler(FIXTURE)
    assert primeira_leitura == segunda_leitura

    assert an.verificar(primeira_leitura) == an.verificar(primeira_leitura)

    quebrado = _reescrever_do_meio(_cadeia((10, 10, "h10"), (20, 20, "h20"),
                                           (30, 30, "h30")))
    assert an.verificar(quebrado) == an.verificar(quebrado), (
        "o relatório de problemas mudou entre duas execuções sobre a mesma "
        "entrada")


def test_nenhuma_mensagem_afirma_causa_que_o_dado_nao_sustenta():
    """Varredura das mensagens: sintoma é sintoma, causa é inferência.

    A mensagem de elo rompido enumerava duas causas ("removida do meio ou
    reescrita") quando a MATRIZ prova que cinco manipulações distintas
    produzem o mesmo sintoma. Diagnóstico que nomeia causa não provada manda
    quem investiga procurar na direção errada — e num incidente de auditoria
    isso custa o tempo que mais importa.
    """
    linhas = _remover_do_meio(_cadeia((10, 10, "h10"), (20, 20, "h20"),
                                      (30, 30, "h30")))
    texto = " ".join(an.verificar(linhas))

    for suposicao in ("removida do meio ou reescrita", "provavelmente",
                      "possivelmente", "alguém"):
        assert suposicao not in texto, (
            f"a mensagem afirma {suposicao!r}, que o dado não distingue")
