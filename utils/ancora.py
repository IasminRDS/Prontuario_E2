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

# Campos que ENTRAM no hash, na ordem em que a forma canônica os põe. Mexer
# nesta tupla invalida toda âncora já retida fora do servidor — ver o caso
# `test_formato_da_linha_e_contrato_congelado`.
CAMPOS_CONTEUDO = ("versao", "emitida_em", "total", "ultimo_id", "hash_final")

# Campos de encadeamento, que ficam FORA do hash do próprio conteúdo pela razão
# óbvia: `hash_ancora` não pode conter a si mesmo.
CAMPOS_ELO = ("ancora_anterior", "hash_ancora")

CAMPOS_VALIDOS = frozenset(CAMPOS_CONTEUDO + CAMPOS_ELO)

# Manipulações que este mecanismo NÃO detecta, por construção e não por
# omissão. A lista existe para ser confrontada: quem tentar "corrigir" uma
# delas precisa antes explicar como, já que ambas consistem em produzir um
# arquivo internamente coerente — e coerência interna é tudo o que um
# verificador que só lê o arquivo pode medir.
NAO_DETECTAVEL = (
    "truncar o FIM do journal (as linhas que sobram seguem encadeadas)",
    "recomputar o journal inteiro, coerente com uma trilha já truncada",
)


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


def validar_forma(linha):
    """Confere que a linha tem exatamente os campos previstos, e nada mais.

    Rejeitar campo DESCONHECIDO não é preciosismo de formato: o hash cobre
    apenas os campos declarados, de modo que qualquer chave a mais viaja dentro
    de uma linha que fecha, sem estar coberta por nada. Sem esta validação é
    possível anexar a uma âncora legítima um texto como "conferido e aprovado
    pela auditoria externa" e a verificação continua aprovando — o conteúdo
    forjado passa a ter, aos olhos de quem lê o arquivo, a mesma autoridade da
    parte assinada.

    Regra: o que não é exatamente válido é inválido. Parser permissivo em
    artefato de auditoria é superfície, não conveniência.
    """
    problemas = []

    if not isinstance(linha, dict):
        return ["não é um objeto JSON"]

    presentes = set(linha)
    extras = presentes - CAMPOS_VALIDOS
    if extras:
        problemas.append(
            f"campos não previstos, fora do alcance do hash: "
            f"{', '.join(sorted(extras))}")

    faltantes = CAMPOS_VALIDOS - presentes
    if faltantes:
        problemas.append(f"campos ausentes: {', '.join(sorted(faltantes))}")

    tipos = {
        "versao": (int,), "emitida_em": (str,), "total": (int,),
        "ultimo_id": (int, type(None)), "hash_final": (str, type(None)),
        "ancora_anterior": (str, type(None)), "hash_ancora": (str,),
    }
    for campo, aceitos in tipos.items():
        if campo in linha and not isinstance(linha[campo], aceitos):
            # `bool` é subclasse de `int` em Python: `True` passaria por
            # `total` sem esta exclusão, e `total: true` não é uma contagem.
            problemas.append(
                f"{campo} tem tipo inesperado ({type(linha[campo]).__name__})")
        elif campo in linha and isinstance(linha[campo], bool):
            problemas.append(f"{campo} é booleano, e nenhum campo daqui é")

    if linha.get("versao") not in (None, VERSAO):
        problemas.append(
            f"versão {linha['versao']} desconhecida — este verificador só "
            f"sabe ler a {VERSAO}")

    return problemas


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

        forma = validar_forma(linha)
        if forma:
            problemas += [f"{rotulo}: {p}" for p in forma]
            # Sem forma válida não há o que verificar adiante: um hash sobre
            # campos incompletos produziria divergência acessória, e o relatório
            # apontaria para o sintoma em vez da causa.
            anterior_hash = linha.get("hash_ancora") if isinstance(linha, dict) else None
            anterior = linha if isinstance(linha, dict) else None
            continue

        conteudo = {c: linha[c] for c in CAMPOS_CONTEUDO}
        esperado = _hash_da_linha(conteudo, linha["ancora_anterior"])
        if linha["hash_ancora"] != esperado:
            problemas.append(f"{rotulo}: conteúdo alterado após a emissão")

        if linha["ancora_anterior"] != anterior_hash:
            # A mensagem NÃO nomeia a causa. Ela dizia "alguma foi removida do
            # meio ou reescrita", e os casos de `test_ancora_journal` provam que
            # remoção, reescrita, reordenação, duplicação e inserção produzem
            # todos este mesmo sintoma. Enumerar duas das cinco fazia o
            # diagnóstico afirmar mais do que o dado sustenta, e mandava quem
            # investiga procurar na direção errada.
            problemas.append(
                f"{rotulo}: elo rompido — o campo `ancora_anterior` não "
                "corresponde ao hash da linha precedente. A sequência de "
                "linhas deste arquivo não é a que foi emitida")

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
