# -*- coding: utf-8 -*-
"""Medição de desempenho com protocolo declarado.

Existe para fechar uma limitação que a monografia declarava: os tempos
relatados vinham de observação, sem número de repetições nem medida de
dispersão, e a precisão decimal com que apareciam sugeria uma repetibilidade
que o dado não sustentava.

O que este módulo acrescenta não é velocidade — é **método**:

- **descarte de aquecimento**: a primeira execução paga o preço de plano de
  consulta ainda não em cache, buffers frios e conexão recém-aberta. Incluí-la
  na estatística mede a partida, não o regime;
- **repetição**: uma execução é uma anedota. O número fica registrado no
  resultado, e não na memória de quem mediu;
- **mediana em vez de média**: uma pausa do coletor de lixo ou do agendador do
  sistema operacional desloca a média e não desloca a mediana;
- **dispersão explícita**: a distância entre o primeiro e o terceiro quartil
  diz se as execuções concordam entre si. Sem ela, "0,96 ms" não informa se a
  próxima execução dará 0,9 ou 9.

O que ele **não** resolve, e continua declarado como limitação: a medição
segue feita em ambiente de desenvolvimento e sobre volume sintético. Protocolo
não transforma dado sintético em dado real.
"""
import statistics
import time
from dataclasses import dataclass, field


@dataclass
class Medida:
    """Resultado de uma consulta medida sob protocolo."""

    nome: str
    repeticoes: int
    aquecimentos: int
    amostras_ms: list = field(repr=False, default_factory=list)

    @property
    def mediana_ms(self):
        return statistics.median(self.amostras_ms)

    @property
    def minimo_ms(self):
        return min(self.amostras_ms)

    @property
    def maximo_ms(self):
        return max(self.amostras_ms)

    @property
    def q1_ms(self):
        return self._quartil(0.25)

    @property
    def q3_ms(self):
        return self._quartil(0.75)

    @property
    def iqr_ms(self):
        """Amplitude interquartil — a dispersão que a monografia não trazia."""
        return self.q3_ms - self.q1_ms

    def _quartil(self, fracao):
        dados = sorted(self.amostras_ms)
        if len(dados) == 1:
            return dados[0]
        posicao = fracao * (len(dados) - 1)
        baixo = int(posicao)
        alto = min(baixo + 1, len(dados) - 1)
        peso = posicao - baixo
        return dados[baixo] * (1 - peso) + dados[alto] * peso

    @property
    def dispersao_relativa(self):
        """IQR sobre mediana. Acima de ~0,25 o número não é estável."""
        return (self.iqr_ms / self.mediana_ms) if self.mediana_ms else 0.0

    @property
    def estavel(self):
        return self.dispersao_relativa <= 0.25

    def como_linha(self):
        marca = "" if self.estavel else "   <-- disperso"
        return (f"{self.nome:<38} {self.mediana_ms:9.2f} ms  "
                f"[{self.q1_ms:7.2f} – {self.q3_ms:7.2f}]  "
                f"n={self.repeticoes}{marca}")


def medir(nome, operacao, repeticoes=15, aquecimentos=3):
    """Executa `operacao` sob protocolo e devolve a `Medida`.

    `operacao` é chamada sem argumentos. O que ela devolve é ignorado — mas
    precisa ser **consumido** dentro dela: consulta preguiçosa de ORM que só
    monta a query e não a executa mediria a construção do objeto, e não o
    banco. É o erro clássico deste tipo de medição.
    """
    for _ in range(max(0, aquecimentos)):
        operacao()

    amostras = []
    for _ in range(max(1, repeticoes)):
        inicio = time.perf_counter()
        operacao()
        amostras.append((time.perf_counter() - inicio) * 1000.0)

    return Medida(nome=nome, repeticoes=len(amostras),
                  aquecimentos=max(0, aquecimentos), amostras_ms=amostras)


def relatorio(medidas):
    """Texto do resultado, com o protocolo declarado no cabeçalho."""
    if not medidas:
        return "nenhuma medida."

    linhas = [
        "PROTOCOLO: mediana de N execuções, após descarte de aquecimento.",
        "Entre colchetes, o intervalo interquartil (Q1 – Q3).",
        "Ambiente de desenvolvimento, volume sintético — ver limitações.",
        "",
        f"{'consulta':<38} {'mediana':>12}  {'dispersão (Q1 – Q3)':^21}  n",
        "-" * 92,
    ]
    linhas += [m.como_linha() for m in medidas]

    dispersos = [m.nome for m in medidas if not m.estavel]
    if dispersos:
        linhas += [
            "",
            "Dispersão acima de 25% da mediana em: " + ", ".join(dispersos),
            "Nesses casos o valor central NÃO deve ser citado como se fosse "
            "estável — repita com mais amostras ou investigue a variação.",
        ]
    return "\n".join(linhas)
