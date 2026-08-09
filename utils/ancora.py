# -*- coding: utf-8 -*-
"""Journal de âncoras da trilha de auditoria — encadeado e só de acréscimo.

A trilha de auditoria já é encadeada por hash, o que detecta alteração de
registro e remoção intermediária. Não detecta truncamento do FIM, e para isso
existe a âncora: um retrato do estado (total, último id, hash final) guardado
antes, com o qual o estado atual é confrontado.

Uma âncora só, reescrita a cada emissão, tem duas fraquezas. A primeira é que
perder ou não guardar a última deixa o operador sem nada. A segunda é mais séria:
quem reescreve a trilha reescreve a âncora junto, e o par volta a ser
consistente.

Este módulo grava as âncoras num **journal encadeado**: cada linha referencia o
hash da anterior, de modo que a sequência de retratos é ela própria uma cadeia.

O que isso resolve, dito com precisão para não prometer o que não entrega:

- **Não** resolve truncar o fim do journal. É a mesma recursão do problema
  original, e nenhuma quantidade de encadeamento a fecha — só custódia externa.
- **Resolve** reescrever uma âncora passada para acomodar um truncamento antigo:
  o elo com a seguinte quebra.
- **Resolve**, e é o ganho principal, o custo da custódia externa. Guardada UMA
  linha qualquer fora do servidor — por e-mail, em ata, num cofre de senhas —,
  ela valida todo o prefixo do journal até ali. A obrigação operacional deixa de
  ser "guarde sempre a última" e passa a ser "guarde qualquer uma, uma vez", que
  é a diferença entre um procedimento que ninguém cumpre e um que sobrevive.
- **Resolve** um caso que a âncora isolada não vê: comparar âncoras
  **consecutivas** denuncia que a trilha encolheu ENTRE dois checkpoints, mesmo
  que ela esteja internamente consistente agora e mesmo sem nenhum valor externo.
"""
import hashlib
import json
from datetime import datetime

VERSAO = 1


def _canonico(registro):
    """Serialização estável do conteúdo que entra no hash.

    `sort_keys` e separadores fixos não são estética: um hash sobre JSON com
    ordem de chaves variável muda sem que o conteúdo mude, e a verificação
    passaria a acusar adulteração onde houve apenas reserialização.
    """
    return json.dumps(registro, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def _hash_da_linha(conteudo, anterior):
    base = _canonico(conteudo) + "|" + (anterior or "")
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def montar(total, ultimo_id, hash_final, anterior=None, emitida_em=None):
    """Monta uma linha de âncora encadeada à `anterior`."""
    conteudo = {
        "versao": VERSAO,
        "emitida_em": (emitida_em or datetime.utcnow()).isoformat(
            timespec="seconds"),
        "total": total,
        "ultimo_id": ultimo_id,
        "hash_final": hash_final,
    }
    linha = dict(conteudo)
    linha["ancora_anterior"] = anterior
    linha["hash_ancora"] = _hash_da_linha(conteudo, anterior)
    return linha


def ler(caminho):
    """Lê o journal. Devolve (linhas, defeitos_de_formato).

    Linha ilegível não interrompe a leitura: um journal parcialmente corrompido
    ainda tem prefixo verificável, e abortar esconderia o que sobrou.
    """
    linhas, defeitos = [], []
    if not caminho.is_file():
        return linhas, defeitos
    # `utf-8-sig` porque um BOM não é adulteração: aparece quando o journal
    # passa por ferramenta do Windows, e acusá-lo como "cadeia rompida" manda o
    # operador caçar fantasma no pior momento possível — o de uma verificação
    # que falhou.
    for numero, bruta in enumerate(
            caminho.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not bruta.strip():
            continue
        try:
            linhas.append(json.loads(bruta))
        except ValueError as exc:
            defeitos.append(f"linha {numero} ilegível: {exc}")
    return linhas, defeitos


def verificar(linhas):
    """Confere a cadeia de âncoras. Devolve a lista de problemas.

    Três perguntas distintas, e a terceira é a que a âncora isolada não faz:

    1. cada linha corresponde ao próprio hash — conteúdo não foi alterado;
    2. cada linha aponta para o hash da anterior — nenhuma foi removida do meio
       nem reescrita;
    3. total e último id **nunca diminuem** de uma âncora para a seguinte. Uma
       queda aqui é a trilha tendo encolhido ENTRE dois checkpoints, e é
       detectável sem nenhum valor guardado fora — o journal testemunha contra
       si mesmo.
    """
    problemas = []
    anterior_hash = None
    anterior = None

    for indice, linha in enumerate(linhas):
        rotulo = f"âncora #{indice + 1} ({linha.get('emitida_em', 'sem data')})"

        conteudo = {c: linha.get(c) for c in
                    ("versao", "emitida_em", "total", "ultimo_id", "hash_final")}
        esperado = _hash_da_linha(conteudo, linha.get("ancora_anterior"))
        if linha.get("hash_ancora") != esperado:
            problemas.append(f"{rotulo}: conteúdo alterado após a emissão")

        if linha.get("ancora_anterior") != anterior_hash:
            problemas.append(
                f"{rotulo}: elo rompido — não aponta para a âncora precedente "
                "(alguma foi removida do meio ou reescrita)")

        if anterior is not None:
            if (linha.get("total") or 0) < (anterior.get("total") or 0):
                problemas.append(
                    f"{rotulo}: a trilha ENCOLHEU entre checkpoints — "
                    f"{anterior.get('total')} registros antes, "
                    f"{linha.get('total')} depois")
            if (linha.get("ultimo_id") or 0) < (anterior.get("ultimo_id") or 0):
                problemas.append(
                    f"{rotulo}: o último id retrocedeu — "
                    f"{anterior.get('ultimo_id')} antes, "
                    f"{linha.get('ultimo_id')} depois")

        anterior_hash = linha.get("hash_ancora")
        anterior = linha

    return problemas


def localizar(linhas, hash_ancora):
    """Índice da âncora com este hash, ou None.

    É o que dá valor a guardar UMA linha fora: informado o hash retido, o
    verificador confirma que ele pertence a este journal e que todo o prefixo
    até ele fecha.
    """
    for indice, linha in enumerate(linhas):
        if linha.get("hash_ancora") == hash_ancora:
            return indice
    return None
