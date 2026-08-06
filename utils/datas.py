# -*- coding: utf-8 -*-
"""Datas por extenso em português, para os documentos impressos.

Os PDFs clínicos usavam `strftime("%d de %B de %Y")`, e `%B` sai no idioma da
LOCALE do processo — que em servidor é quase sempre a C. O atestado médico, o
receituário e a guia de encaminhamento saíam datados de "06 de August de 2026".
São documentos oficiais do SUS, entregues ao paciente.

`locale.setlocale` resolveria e não serve: é estado GLOBAL do processo, não é
seguro entre threads (e o servidor atende em várias), e depende de a locale
pt_BR existir no sistema operacional — no Windows ela nem tem esse nome. Uma
tabela de doze nomes não tem nenhum desses problemas.
"""

MESES = (
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
)


def por_extenso(data):
    """`date`/`datetime` -> "6 de agosto de 2026".

    Sem zero à esquerda no dia: é como se escreve data por extenso em português.
    """
    return f"{data.day} de {MESES[data.month - 1]} de {data.year}"
