# -*- coding: utf-8 -*-
"""Plausibilidade fisiológica dos sinais vitais.

`utils/numeros.py` resolve se o que foi digitado **é um número**. Este módulo
resolve se o número **pode ser aquela medida**. São perguntas diferentes, e só
a primeira tinha resposta: uma altura de 172 — metros, porque é o que o rótulo
do campo pede — era convertida sem erro, gravada, exibida, entrava no cálculo
de IMC e saía num recurso FHIR `8302-2` bem formado. Documento válido e
impossível, que o transporte aceita e o registro nacional guarda.

**Recusa apenas o impossível, nunca o improvável.** A distinção é clínica, não
técnica: uma temperatura de 41,8 °C é rara e verdadeira, e um sistema que a
recusasse obrigaria quem tria a contornar o próprio prontuário no momento em
que ele mais importa. Restrição que barra quem deveria passar é
indisponibilidade clínica, não segurança — é a mesma lição de 9.4.19. Por isso
os limites abaixo são deliberadamente generosos, ancorados em extremos
registrados na literatura e não em faixas de normalidade.

**O que ele NÃO pega, e não tem como pegar:** o erro plausível. Peso 7,0 no
lugar de 70,0 passa, porque 7 kg é o peso de um lactente. Nenhuma faixa
distingue isso sem saber a idade do paciente, e prometer o contrário seria
vender uma conferência que não existe. O que este módulo elimina é a classe do
absurdo — troca de unidade, dígito a mais, campo trocado.

A tabela é a **fonte única**: o formulário desenha `min`/`max` a partir dela e o
servidor decide por ela. Escrita duas vezes, viraria a replicação de regra que a
seção 9.4.14 da monografia documenta — e a metade que envelhecesse seria
justamente a do HTML, que ninguém testa.
"""
import re

# campo -> (mínimo, máximo, unidade, rótulo, justificativa do extremo)
#
# A justificativa fica na tabela de propósito. Limite sem origem é limite que
# alguém aperta "por segurança" no ano seguinte, e o aperto só aparece quando
# recusa a medida de um paciente real.
LIMITES = {
    "temperatura": (25.0, 45.0, "°C", "Temperatura",
                    "hipotermia acidental com sobrevida abaixo de 14 °C e "
                    "hipertermia acima de 46 °C estão relatadas; 98,6 aqui é "
                    "Fahrenheit digitado no campo de Celsius"),
    "frequencia_cardiaca": (0, 300, "bpm", "Frequência cardíaca",
                            "zero é parada, que se registra; taquiarritmia "
                            "neonatal alcança 300"),
    "frequencia_respiratoria": (0, 120, "irpm", "Frequência respiratória",
                                "zero é apneia, que se registra; taquipneia do "
                                "recém-nascido passa de 100"),
    "saturacao_o2": (0.0, 100.0, "%", "Saturação de O₂",
                     "é uma fração do total: acima de 100 não existe medida, "
                     "existe erro"),
    "glicemia": (5.0, 2000.0, "mg/dL", "Glicemia",
                 "há relato de sobrevida acima de 2.000 mg/dL em estado "
                 "hiperosmolar"),
    "peso": (0.2, 500.0, "kg", "Peso",
             "prematuro extremo pesa cerca de 250 g; o maior peso humano "
             "registrado é de 635 kg"),
    "altura": (0.2, 2.8, "m", "Altura",
               "o campo é em METROS: 1,72 e não 172. O maior estatura humana "
               "registrada é de 2,72 m"),
    "dor_escala": (0, 10, "", "Escala de dor",
                   "a escala é definida de 0 a 10; fora disso não é a escala"),
    "diurese_ml": (0, 30000, "mL", "Diurese",
                   "poliúria extrema chega a 20 L em 24 h"),
}

# `balanco_hidrico` fica de fora com razão declarada, e não por esquecimento:
# é uma DIFERENÇA entre o que entrou e o que saiu, legitimamente negativa, e
# sem um intervalo de tempo associado não há extremo fisiológico a comparar.
# Inventar um limite aqui seria recusar medida verdadeira para dar a impressão
# de rigor.
SEM_LIMITE = {
    "balanco_hidrico": "é diferença com sinal, e o campo não guarda o período "
                       "a que se refere",
}

# "120/80", "120 x 80". Duas grandezas num campo de texto, que é como o
# prontuário de papel registra e como a tela captura.
PRESSAO = re.compile(r"^\s*(\d{1,3})\s*[/xX]\s*(\d{1,3})\s*$")

SISTOLICA = (30, 300)
DIASTOLICA = (10, 200)


def _numero(valor):
    """Formata sem o `.0` pendurado: '2.8' e não '2.8', '300' e não '300.0'."""
    if isinstance(valor, float) and valor == int(valor):
        return str(int(valor))
    return str(valor)


def conferir(campo, valor):
    """Devolve a mensagem de recusa, ou `None` quando o valor é aceitável.

    Campo desconhecido e valor `None` passam: ausência de medida é legítima, e
    campo fora da tabela é campo que este módulo não se propõe a julgar.
    """
    if valor is None or campo not in LIMITES:
        return None

    # Coage antes de comparar. A porta JSON entrega o que o cliente mandou, e
    # `"172" <= 2.8` levanta TypeError em Python 3 — a conferência morreria com
    # erro 500 justamente no caminho que ela existe para vigiar. Texto que nem
    # número é passa adiante: essa é a pergunta de `utils/numeros.py`, e dar
    # duas respostas diferentes para ela seria o começo da divergência.
    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return None

    minimo, maximo, unidade, rotulo, _razao = LIMITES[campo]
    if minimo <= valor <= maximo:
        return None

    sufixo = f" {unidade}" if unidade else ""
    return (f"{rotulo}: {_numero(valor)}{sufixo} está fora do possível "
            f"(de {_numero(minimo)} a {_numero(maximo)}{sufixo}). "
            f"Confira a unidade e a vírgula.")


def conferir_pressao(texto):
    """Pressão arterial, que é duas medidas num campo só.

    Vazio e formato irreconhecível passam: o campo é texto livre de propósito,
    e recusar "PA inaudível" tiraria da enfermagem o registro de um achado que
    é ele próprio clínico. O que se confere é o que dá para ler como par de
    números — inclusive a **inversão**, que é o erro de digitação mais comum
    aqui e o único que nenhum intervalo isolado pega: 80/120 tem as duas metades
    dentro da faixa e mesmo assim não existe.
    """
    casado = PRESSAO.match(texto or "")
    if not casado:
        return None

    sistolica, diastolica = int(casado.group(1)), int(casado.group(2))
    if not SISTOLICA[0] <= sistolica <= SISTOLICA[1]:
        return (f"Pressão arterial: sistólica {sistolica} fora do possível "
                f"(de {SISTOLICA[0]} a {SISTOLICA[1]} mmHg).")
    if not DIASTOLICA[0] <= diastolica <= DIASTOLICA[1]:
        return (f"Pressão arterial: diastólica {diastolica} fora do possível "
                f"(de {DIASTOLICA[0]} a {DIASTOLICA[1]} mmHg).")
    if sistolica <= diastolica:
        return (f"Pressão arterial: {sistolica}/{diastolica} tem a sistólica "
                "menor que a diastólica. Os dois números estão trocados?")
    return None


def conferir_muitos(valores):
    """As mensagens de todos os campos implausíveis de um formulário.

    Devolve TODAS, e não a primeira: quem preencheu oito campos e errou dois
    merece corrigir os dois de uma vez, em vez de descobrir o segundo depois de
    submeter de novo.
    """
    mensagens = []
    for campo, valor in valores.items():
        if campo == "pressao_arterial":
            recusa = conferir_pressao(valor)
        else:
            recusa = conferir(campo, valor)
        if recusa:
            mensagens.append(recusa)
    return mensagens


def plausivel(campo, valor):
    """A mesma pergunta em forma de booleano, para quem só precisa decidir."""
    return conferir(campo, valor) is None


def atributos(campo):
    """`min` e `max` para o formulário desenhar, vindos da mesma tabela.

    O navegador avisa cedo e o servidor decide — a validação do HTML é
    conveniência, nunca controle: ela não existe para quem posta sem passar
    pela tela.
    """
    if campo not in LIMITES:
        return {}
    minimo, maximo, _unidade, _rotulo, _razao = LIMITES[campo]
    return {"min": _numero(minimo), "max": _numero(maximo)}
