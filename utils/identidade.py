# -*- coding: utf-8 -*-
"""Primitivas de identidade do paciente.

Num sistema de uma unidade, duplicata é acidente. Em escala nacional é certeza:
a mesma pessoa é cadastrada em municípios diferentes, às vezes só com CPF, às
vezes só com CNS, quase sempre com o nome digitado de um jeito diferente. Sem
reconciliar isso, o prontuário longitudinal — a razão de existir do sistema — não
acontece.

Aqui ficam as peças que não dependem de banco: normalizar, agrupar candidatos
sem comparar todo mundo com todo mundo, e pontuar um par.
"""
import re
import unicodedata
from difflib import SequenceMatcher

# Partículas que não ajudam a distinguir pessoas e atrapalham a comparação.
PARTICULAS = {"DE", "DA", "DO", "DAS", "DOS", "E", "DI", "DU", "DEL"}

# Dígrafos e equivalências que colapsam grafias diferentes do mesmo som. É uma
# fonética deliberadamente simples: o objetivo é AGRUPAR candidatos para depois
# comparar com calma, não decidir nada sozinha.
DIGRAFOS = [
    ("LH", "L"), ("NH", "N"), ("CH", "X"), ("PH", "F"), ("SH", "X"),
    ("SS", "S"), ("RR", "R"), ("SC", "S"), ("SÇ", "S"), ("XC", "S"),
    ("QU", "K"), ("GU", "G"), ("Ç", "S"),
]
# Só substituições de uma letra: os dígrafos (PH, CH, LH...) já foram
# resolvidos acima, antes desta tabela.
EQUIVALENTES = str.maketrans({"Y": "I", "W": "V", "Z": "S", "K": "C", "Q": "C",
                              "H": ""})

VOGAIS = set("AEIOU")


def so_digitos(valor):
    """Mantém apenas dígitos. CPF e CNS chegam formatados de mil maneiras."""
    return re.sub(r"\D", "", valor or "")


def sem_acento(texto):
    normalizado = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def normalizar_nome(nome):
    """Forma canônica para comparação: maiúsculas, sem acento, sem partícula.

    "José da Silva Filho" e "JOSE SILVA FILHO" viram a mesma coisa — que é o
    caso mais comum de duplicata digitada por pessoas diferentes.
    """
    limpo = sem_acento(nome or "").upper()
    limpo = re.sub(r"[^A-Z ]", " ", limpo)
    partes = [p for p in limpo.split() if p and p not in PARTICULAS]
    return " ".join(partes)


def codigo_fonetico(palavra):
    """Código aproximado de uma palavra, para agrupar grafias parecidas.

    Colapsa dígrafos, iguala letras que soam igual em português e descarta
    vogais depois da primeira letra — "SOUZA", "SOUSA" e "SOUZA" caem no mesmo
    código, "SILVA" e "SILVEIRA" também. É grosseiro de propósito: erra para o
    lado de agrupar demais, e a pontuação depois separa.
    """
    palavra = sem_acento(palavra or "").upper()
    palavra = re.sub(r"[^A-Z]", "", palavra)
    if not palavra:
        return ""

    for de, para in DIGRAFOS:
        palavra = palavra.replace(de, para)
    palavra = palavra.translate(EQUIVALENTES)
    if not palavra:
        return ""

    primeira, resto = palavra[0], palavra[1:]
    resto = "".join(c for c in resto if c not in VOGAIS)

    # Colapsa repetição consecutiva ("SS" que sobrou de outra regra).
    saida = [primeira]
    for c in resto:
        if c != saida[-1]:
            saida.append(c)
    return "".join(saida)[:6]


def chave_bloqueio(nome, data_nascimento):
    """Agrupa candidatos sem comparar todo mundo com todo mundo.

    Comparar N pacientes par a par é O(N²) — inviável em escala nacional. A
    chave de bloqueio reduz a comparação a quem nasceu no mesmo dia e tem o
    primeiro nome foneticamente parecido; só dentro desse grupo vale a pena
    calcular similaridade.
    """
    normalizado = normalizar_nome(nome)
    if not normalizado or not data_nascimento:
        return None
    primeiro = normalizado.split()[0]
    return f"{data_nascimento.isoformat()}|{codigo_fonetico(primeiro)}"


def similaridade(a, b):
    """0..1 entre dois nomes já normalizados."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


# Pesos da pontuação. Documentados aqui porque são decisão de produto, não
# detalhe de implementação: mexer nestes números muda o que o sistema considera
# "a mesma pessoa".
LIMIAR_CANDIDATO = 0.72   # abaixo disto nem entra na fila de revisão
LIMIAR_FORTE = 0.90       # acima disto a evidência é considerada forte


def pontuar(a, b):
    """Compara dois pacientes. Devolve (score 0..1, lista de evidências).

    Identificador oficial coincidente é prova: CPF e CNS são únicos por pessoa.
    O resto é indício, e a soma de indícios fracos nunca deve virar certeza
    sozinha — por isso o teto de quem não tem documento igual fica abaixo de 1.
    """
    evidencias = []
    score = 0.0

    cpf_a, cpf_b = so_digitos(a.cpf), so_digitos(b.cpf)
    cns_a, cns_b = so_digitos(a.cns), so_digitos(b.cns)

    if cpf_a and cpf_a == cpf_b:
        return 1.0, ["mesmo CPF"]
    if cns_a and cns_a == cns_b:
        return 1.0, ["mesmo CNS"]

    # Documento diferente é evidência CONTRA, e forte: duas pessoas com CPFs
    # distintos não são a mesma, por mais parecido que seja o nome.
    if cpf_a and cpf_b and cpf_a != cpf_b:
        return 0.0, ["CPFs diferentes"]
    if cns_a and cns_b and cns_a != cns_b:
        return 0.0, ["CNS diferentes"]

    mesma_data = bool(a.data_nascimento and a.data_nascimento == b.data_nascimento)
    if mesma_data:
        score += 0.40
        evidencias.append("mesma data de nascimento")
    else:
        # Sem data igual e sem documento igual, não é candidato.
        return 0.0, ["datas de nascimento diferentes"]

    nome = similaridade(normalizar_nome(a.nome), normalizar_nome(b.nome))
    score += 0.40 * nome
    evidencias.append(f"nome {int(nome * 100)}% semelhante")

    mae_a, mae_b = normalizar_nome(a.nome_mae), normalizar_nome(b.nome_mae)
    if mae_a and mae_b:
        mae = similaridade(mae_a, mae_b)
        score += 0.15 * mae
        evidencias.append(f"nome da mãe {int(mae * 100)}% semelhante")
        if mae < 0.5:
            # Mãe declarada e claramente diferente derruba o par: é o campo que
            # melhor distingue homônimos nascidos no mesmo dia.
            return 0.0, ["nomes de mãe diferentes"]

    if a.sexo and a.sexo == b.sexo:
        score += 0.05
        evidencias.append("mesmo sexo")

    return min(score, 0.99), evidencias
