# -*- coding: utf-8 -*-
"""Conversão de sinal vital vindo de formulário.

Existe porque a mesma conversão estava escrita em dois lugares com
comportamentos diferentes. `routes/prontuario.py` trocava a vírgula por ponto
antes de converter; `routes/triagem.py` chamava `float()` direto. Um "38,4" era
aceito pelo prontuário e derrubava a triagem inteira — com a exceção crua do
Python na tela e o registro perdido, porque a rota constrói o objeto e converte
tudo dentro do mesmo `try`.

O risco não é hipotético em português: a vírgula é o separador decimal daqui, e
`type="number"` protege apenas enquanto o valor vem do próprio campo — colar,
autopreencher ou um cliente que não seja o navegador contornam isso.

**Devolve `None` para vazio e levanta `ValueError` para inválido.** A distinção
importa: campo em branco é ausência legítima de medida, e texto ilegível é erro
que precisa chegar ao usuário nomeando o campo.
"""


def decimal_de(bruto):
    """'38,4' e '38.4' viram 38.4. Vazio vira None."""
    texto = (bruto or "").strip().replace(",", ".")
    if not texto:
        return None
    return float(texto)


def inteiro_de(bruto):
    """'102' vira 102. Vazio vira None.

    Aceita o decimal com parte fracionária nula ('102.0') porque campo de
    frequência preenchido por autocompletar às vezes chega assim, e recusar
    perderia a medida inteira por causa do formato.
    """
    texto = (bruto or "").strip().replace(",", ".")
    if not texto:
        return None
    valor = float(texto)
    if valor != int(valor):
        raise ValueError(f"{texto!r} não é inteiro")
    return int(valor)
