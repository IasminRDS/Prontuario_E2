# -*- coding: utf-8 -*-
"""Converte docs/TCC.md em monografia .docx com formatação ABNT.

    python scripts/gerar_tcc_docx.py

Por que um conversor próprio, e não `pandoc`: a ABNT exige coisas que um
conversor genérico não faz — elementos pré-textuais sem numeração de seção,
seções primárias em página nova, tabelas com título acima e fonte abaixo, e
margens assimétricas (3 cm à esquerda e no topo, 2 cm à direita e embaixo).

**A formatação aplicada aqui é a da NBR 14724.** O Art. 14 do regulamento do
curso delega essa definição às "Normas Gerais para Redação da Monografia" do
COLEGIADO. Se esse documento divergir, ele prevalece — ajuste as constantes
abaixo em vez de reformatar o arquivo à mão, para a conversão continuar
reproduzível.
"""
import pathlib
import re
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# --- Parâmetros de formatação (NBR 14724) ---------------------------------
FONTE = "Times New Roman"
CORPO_PT = 12
CITACAO_PT = 10          # citação longa e legenda de tabela
ENTRELINHAS = 1.5
RECUO_PARAGRAFO = Cm(1.25)
MARGEM_ESQ, MARGEM_SUP = Cm(3), Cm(3)
MARGEM_DIR, MARGEM_INF = Cm(2), Cm(2)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "docs" / "TCC.md"
DESTINO = RAIZ / "docs" / "TCC.docx"

# Seções que abrem página nova e NÃO recebem numeração progressiva.
PRE_TEXTUAIS = ("FOLHA DE ROSTO", "FOLHA DE APROVAÇÃO", "RESUMO", "ABSTRACT",
                "LISTA DE ABREVIATURAS", "SUMÁRIO")
POS_TEXTUAIS = ("REFERÊNCIAS", "APÊNDICE")


def _configurar_estilos(doc):
    normal = doc.styles["Normal"]
    normal.font.name = FONTE
    normal.font.size = Pt(CORPO_PT)
    # `w:eastAsia` é necessário ou o Word ignora a fonte em parte do texto.
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
    pf = normal.paragraph_format
    pf.line_spacing = ENTRELINHAS
    pf.space_after = Pt(0)
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    for nivel in range(1, 5):
        estilo = doc.styles[f"Heading {nivel}"]
        estilo.font.name = FONTE
        estilo.font.size = Pt(CORPO_PT)
        estilo.font.bold = True
        estilo.font.color.rgb = RGBColor(0, 0, 0)
        estilo.paragraph_format.line_spacing = ENTRELINHAS
        estilo.paragraph_format.space_before = Pt(12)
        estilo.paragraph_format.space_after = Pt(12)
        estilo.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _margens(doc):
    for secao in doc.sections:
        secao.left_margin, secao.top_margin = MARGEM_ESQ, MARGEM_SUP
        secao.right_margin, secao.bottom_margin = MARGEM_DIR, MARGEM_INF


_NEGRITO = re.compile(r"\*\*(.+?)\*\*")
_ITALICO = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_CODIGO = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _escrever_inline(paragrafo, texto):
    """Aplica negrito, itálico e monoespaçado dentro do parágrafo."""
    texto = _LINK.sub(r"\1", texto)          # link vira só o rótulo
    texto = texto.replace("&nbsp;", " ")

    # Tokeniza mantendo os marcadores, para não perder ordem.
    partes = re.split(r"(\*\*.+?\*\*|`[^`]+`|(?<!\*)\*(?!\*).+?(?<!\*)\*(?!\*))",
                      texto)
    for parte in partes:
        if not parte:
            continue
        if parte.startswith("**") and parte.endswith("**"):
            paragrafo.add_run(parte[2:-2]).bold = True
        elif parte.startswith("`") and parte.endswith("`"):
            run = paragrafo.add_run(parte[1:-1])
            run.font.name = "Courier New"
            run.font.size = Pt(CORPO_PT - 1)
        elif parte.startswith("*") and parte.endswith("*"):
            paragrafo.add_run(parte[1:-1]).italic = True
        else:
            paragrafo.add_run(parte)


def _e_pre_ou_pos(titulo):
    alvo = titulo.upper()
    return (any(alvo.startswith(p) for p in PRE_TEXTUAIS)
            or any(alvo.startswith(p) for p in POS_TEXTUAIS))


def _tabela(doc, linhas):
    """Converte um bloco de tabela markdown."""
    celulas = [[c.strip() for c in l.strip().strip("|").split("|")] for l in linhas]
    # a segunda linha é o separador (---)
    corpo = [celulas[0]] + celulas[2:]
    colunas = max(len(l) for l in corpo)

    tab = doc.add_table(rows=0, cols=colunas)
    tab.style = "Table Grid"
    for i, linha in enumerate(corpo):
        cells = tab.add_row().cells
        for j in range(colunas):
            texto = linha[j] if j < len(linha) else ""
            p = cells[j].paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
            _escrever_inline(p, texto)
            for run in p.runs:
                run.font.size = Pt(CITACAO_PT)
                if i == 0:
                    run.bold = True
    doc.add_paragraph()


def converter():
    if not ORIGEM.is_file():
        sys.exit(f"não encontrei {ORIGEM}")

    doc = Document()
    _configurar_estilos(doc)
    _margens(doc)

    linhas = ORIGEM.read_text(encoding="utf-8").splitlines()
    i, primeira_secao = 0, True
    dentro_de_codigo = False

    while i < len(linhas):
        linha = linhas[i]

        # Comentários HTML do markdown são instruções para o autor: não entram.
        if linha.strip().startswith("<!--"):
            while i < len(linhas) and "-->" not in linhas[i]:
                i += 1
            i += 1
            continue

        if linha.strip().startswith("```"):
            dentro_de_codigo = not dentro_de_codigo
            i += 1
            continue

        if dentro_de_codigo:
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.left_indent = Cm(2)
            run = p.add_run(linha)
            run.font.name = "Courier New"
            run.font.size = Pt(9)
            i += 1
            continue

        # Tabela
        if linha.strip().startswith("|"):
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            if len(bloco) >= 2:
                _tabela(doc, bloco)
            continue

        # Títulos
        cabecalho = re.match(r"^(#{1,4})\s+(.*)$", linha)
        if cabecalho:
            nivel, titulo = len(cabecalho.group(1)), cabecalho.group(2).strip()
            titulo = _LINK.sub(r"\1", titulo).replace("**", "")

            # Seção primária começa em página nova (NBR 14724).
            if nivel <= 2 and not primeira_secao:
                doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            primeira_secao = False

            p = doc.add_heading(level=min(nivel, 4))
            p.alignment = (WD_ALIGN_PARAGRAPH.CENTER
                           if _e_pre_ou_pos(titulo) else WD_ALIGN_PARAGRAPH.LEFT)
            _escrever_inline(p, titulo)
            for run in p.runs:
                run.font.name = FONTE
                run.font.size = Pt(CORPO_PT)
                run.bold = True
                run.font.color.rgb = RGBColor(0, 0, 0)
            i += 1
            continue

        # Separador horizontal: no markdown marcava troca de seção; aqui a
        # quebra de página já cumpre o papel.
        if linha.strip() in ("---", "***", "___"):
            i += 1
            continue

        # Citação longa: recuo de 4 cm, fonte menor, sem aspas (NBR 10520).
        if linha.strip().startswith(">"):
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith(">"):
                bloco.append(linhas[i].strip().lstrip(">").strip())
                i += 1
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(4)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(12)
            _escrever_inline(p, " ".join(bloco))
            for run in p.runs:
                run.font.size = Pt(CITACAO_PT)
            continue

        # Lista
        item = re.match(r"^\s*[-*]\s+(.*)$", linha)
        if item:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.line_spacing = ENTRELINHAS
            _escrever_inline(p, item.group(1))
            i += 1
            continue

        numerado = re.match(r"^\s*\d+\.\s+(.*)$", linha)
        if numerado:
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.line_spacing = ENTRELINHAS
            _escrever_inline(p, numerado.group(1))
            i += 1
            continue

        # Parágrafo: junta as linhas até a próxima linha em branco, porque no
        # markdown a quebra é cosmética e no Word viraria parágrafo novo.
        if linha.strip():
            bloco = []
            while (i < len(linhas) and linhas[i].strip()
                   and not re.match(r"^(#{1,4}\s|\s*[-*]\s|\s*\d+\.\s|\||>|```)",
                                    linhas[i])
                   and linhas[i].strip() not in ("---", "***", "___")):
                bloco.append(linhas[i].strip())
                i += 1
            p = doc.add_paragraph()
            p.paragraph_format.first_line_indent = RECUO_PARAGRAFO
            _escrever_inline(p, " ".join(bloco))
            continue

        i += 1

    doc.save(DESTINO)
    print(f"gerado: {DESTINO}")
    print(f"tamanho: {DESTINO.stat().st_size:,} bytes")


if __name__ == "__main__":
    converter()
