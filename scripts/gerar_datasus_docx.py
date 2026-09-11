# -*- coding: utf-8 -*-
"""Converte `docs/datasus_levantamento.md` em `docs/datasus_levantamento.docx`.

Terceiro conversor do projeto, e pela mesma razão que existe o segundo: o
destino é outro. `gerar_tcc_docx.py` produz ABNT; `gerar_defesa_docx.py` produz
documento de ensaio, para ler em pé. Este produz um **documento de consulta**,
que se lê sentado e se percorre pelas tabelas — porque é isso que um
levantamento é.

As decisões de formatação seguem desse uso:

- **a tabela é o corpo do texto**, e não ilustração dele. Fonte menor, cabeçalho
  sombreado e largura cheia, para caber comparação de seis colunas sem quebrar;
- **a coluna "Verificação" é colorida** — verde para o que foi lido na fonte,
  âmbar para o que é indicação de busca. É a regra do projeto (nada afirmado sem
  a fonte que prova) transformada em coisa que se vê de relance, em vez de
  parágrafo que se pula;
- **as seções são numeradas em faixa azul**, para localizar item no meio de uma
  conversa com o orientador sem folhear;
- **URL fica em monoespaçado e corpo menor**, porque endereço longo dentro de
  parágrafo justificado abre buraco de espaçamento.

Nunca edite o `.docx`: a próxima geração descarta a edição, e enquanto isso os
dois arquivos afirmam coisas diferentes.

Uso:
    python scripts/gerar_datasus_docx.py
"""
import pathlib
import re
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "docs" / "datasus_levantamento.md"
SAIDA = RAIZ / "docs" / "datasus_levantamento.docx"

FONTE = "Calibri"
FONTE_MONO = "Consolas"
CORPO_PT = 11
TABELA_PT = 9

AZUL = RGBColor(0x13, 0x51, 0xB4)          # institucional, o mesmo do sistema
AZUL_ESCURO = RGBColor(0x0D, 0x33, 0x71)
CINZA_TEXTO = RGBColor(0x3A, 0x3A, 0x3A)
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)

FUNDO_CABECALHO = "1351B4"
FUNDO_TABELA = "E8EEF9"
FUNDO_ZEBRA = "F5F7FB"
FUNDO_NOTA = "FFF8E1"

# As duas marcas de procedência. Verde é fato conferido na origem; âmbar é
# pista que ainda não vale citação.
VERIFICACAO = {
    "fonte primária": ("D8F0DC", RGBColor(0x14, 0x53, 0x21)),
    "indicação de busca": ("FDECC8", RGBColor(0x7A, 0x4E, 0x00)),
}

_TOKENS = re.compile(r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_URL = re.compile(r"https?://\S+")
_SEPARADOR = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")


# --------------------------------------------------------------------------
# python-docx não expõe sombreamento, borda nem largura de coluna
# --------------------------------------------------------------------------
def _sombrear(elemento_pr, cor):
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), cor)
    elemento_pr.append(shd)


def _sombrear_paragrafo(paragrafo, cor):
    _sombrear(paragrafo._p.get_or_add_pPr(), cor)


def _sombrear_celula(celula, cor):
    _sombrear(celula._tc.get_or_add_tcPr(), cor)


def _barra_lateral(paragrafo, cor="1351B4", largura=18):
    pPr = paragrafo._p.get_or_add_pPr()
    bordas = OxmlElement("w:pBdr")
    esquerda = OxmlElement("w:left")
    esquerda.set(qn("w:val"), "single")
    esquerda.set(qn("w:sz"), str(largura))
    esquerda.set(qn("w:space"), "10")
    esquerda.set(qn("w:color"), cor)
    bordas.append(esquerda)
    pPr.append(bordas)


def _regua(doc):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(10)
    pPr = p._p.get_or_add_pPr()
    bordas = OxmlElement("w:pBdr")
    baixo = OxmlElement("w:bottom")
    baixo.set(qn("w:val"), "single")
    baixo.set(qn("w:sz"), "6")
    baixo.set(qn("w:space"), "1")
    baixo.set(qn("w:color"), "C9D3E4")
    bordas.append(baixo)
    pPr.append(bordas)


def _repetir_cabecalho(linha):
    """Faz o cabeçalho reaparecer quando a tabela quebra de página."""
    trPr = linha._tr.get_or_add_trPr()
    marca = OxmlElement("w:tblHeader")
    marca.set(qn("w:val"), "true")
    trPr.append(marca)


# --------------------------------------------------------------------------
def _inline(paragrafo, texto, tamanho=CORPO_PT, cor=None, negrito=False):
    """Aplica negrito, itálico, monoespaçado e realce de URL."""
    texto = _LINK.sub(r"\1", texto)
    for parte in _TOKENS.split(texto):
        if not parte:
            continue
        if parte.startswith("**") and parte.endswith("**"):
            run = paragrafo.add_run(parte[2:-2])
            run.bold = True
            run.font.name = FONTE
            run.font.size = Pt(tamanho)
        elif parte.startswith("`") and parte.endswith("`"):
            run = paragrafo.add_run(parte[1:-1])
            run.font.name = FONTE_MONO
            run.font.size = Pt(tamanho - 1.5)
            run.font.color.rgb = AZUL_ESCURO
            continue
        elif parte.startswith("*") and parte.endswith("*"):
            run = paragrafo.add_run(parte[1:-1])
            run.italic = True
            run.font.name = FONTE
            run.font.size = Pt(tamanho)
        else:
            # URL solta vai em monoespaçado menor: dentro de parágrafo
            # justificado, endereço longo abre buraco de espaçamento.
            resto = parte
            while True:
                achado = _URL.search(resto)
                if not achado:
                    break
                antes = resto[:achado.start()]
                if antes:
                    run = paragrafo.add_run(antes)
                    run.font.name = FONTE
                    run.font.size = Pt(tamanho)
                    if cor:
                        run.font.color.rgb = cor
                run = paragrafo.add_run(achado.group())
                run.font.name = FONTE_MONO
                run.font.size = Pt(tamanho - 2)
                run.font.color.rgb = AZUL
                resto = resto[achado.end():]
            if not resto:
                continue
            run = paragrafo.add_run(resto)
            run.font.name = FONTE
            run.font.size = Pt(tamanho)
        if negrito:
            run.bold = True
        if cor:
            run.font.color.rgb = cor


def _configurar(doc):
    normal = doc.styles["Normal"]
    normal.font.name = FONTE
    normal.font.size = Pt(CORPO_PT)
    normal.font.color.rgb = CINZA_TEXTO
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.2

    for secao in doc.sections:
        secao.top_margin = Cm(1.8)
        secao.bottom_margin = Cm(1.8)
        secao.left_margin = Cm(2.0)
        secao.right_margin = Cm(1.8)

    _rodape(doc.sections[0])


def _rodape(secao):
    """Número de página centralizado, como campo do Word."""
    p = secao.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run()
    run.font.name = FONTE
    run.font.size = Pt(8.5)
    run.font.color.rgb = RGBColor(0x88, 0x88, 0x88)
    for atributo, valor in (("w:fldCharType", "begin"), (None, "PAGE"),
                            ("w:fldCharType", "end")):
        if atributo is None:
            instrucao = OxmlElement("w:instrText")
            instrucao.set(qn("xml:space"), "preserve")
            instrucao.text = " PAGE "
            run._r.append(instrucao)
        else:
            marca = OxmlElement("w:fldChar")
            marca.set(qn(atributo), valor)
            run._r.append(marca)


class Conversor:
    """Percorre o markdown uma vez, decidindo bloco a bloco."""

    def __init__(self, doc):
        self.doc = doc

    def titulo_documento(self, texto):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(texto)
        run.bold = True
        run.font.name = FONTE
        run.font.size = Pt(20)
        run.font.color.rgb = AZUL

    def secao(self, texto):
        """Faixa azul: é o que permite achar o item no meio de uma conversa."""
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(16)
        p.paragraph_format.space_after = Pt(8)
        p.paragraph_format.left_indent = Cm(0.2)
        run = p.add_run(" " + texto)
        run.bold = True
        run.font.name = FONTE
        run.font.size = Pt(13.5)
        run.font.color.rgb = BRANCO
        _sombrear_paragrafo(p, FUNDO_CABECALHO)

    def subsecao(self, texto):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(texto)
        run.bold = True
        run.font.name = FONTE
        run.font.size = Pt(11.5)
        run.font.color.rgb = AZUL_ESCURO

    def paragrafo(self, texto):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        _inline(p, texto)
        return p

    def item(self, texto, nivel=0):
        p = self.doc.add_paragraph(style="List Bullet")
        p.paragraph_format.left_indent = Cm(0.75 + 0.55 * nivel)
        p.paragraph_format.space_after = Pt(3)
        _inline(p, texto)

    def tabela(self, linhas):
        celulas = [[c.strip() for c in l.strip().strip("|").split("|")]
                   for l in linhas if not _SEPARADOR.match(l.strip())]
        if not celulas:
            return
        colunas = max(len(l) for l in celulas)
        cabecalho = [c.lower() for c in celulas[0]]
        coluna_verificacao = (cabecalho.index("verificação")
                              if "verificação" in cabecalho else None)

        t = self.doc.add_table(rows=len(celulas), cols=colunas)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, linha in enumerate(celulas):
            for j in range(colunas):
                celula = t.rows[i].cells[j]
                celula.paragraphs[0].text = ""
                p = celula.paragraphs[0]
                p.paragraph_format.space_after = Pt(2)
                valor = linha[j] if j < len(linha) else ""

                if i == 0:
                    _inline(p, valor, tamanho=TABELA_PT, cor=BRANCO,
                            negrito=True)
                    _sombrear_celula(celula, FUNDO_CABECALHO)
                    continue

                marca = VERIFICACAO.get(valor.strip().lower())
                if j == coluna_verificacao and marca:
                    fundo, tinta = marca
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    _inline(p, valor, tamanho=TABELA_PT, cor=tinta,
                            negrito=True)
                    _sombrear_celula(celula, fundo)
                    continue

                _inline(p, valor, tamanho=TABELA_PT)
                if i % 2 == 0:
                    _sombrear_celula(celula, FUNDO_ZEBRA)

        _repetir_cabecalho(t.rows[0])
        self.doc.add_paragraph()

    def nota(self, texto):
        """Bloco de advertência — o parágrafo da régua de verificação."""
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.right_indent = Cm(0.3)
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(10)
        _inline(p, texto, tamanho=10.5)
        _barra_lateral(p, cor="F0A400")
        _sombrear_paragrafo(p, FUNDO_NOTA)


def converter(markdown):
    doc = Document()
    _configurar(doc)
    c = Conversor(doc)

    linhas = markdown.splitlines()
    i = 0
    primeira_secao = True
    while i < len(linhas):
        linha = linhas[i]
        despido = linha.strip()

        if not despido:
            i += 1
            continue

        if despido.startswith("# "):
            c.titulo_documento(despido[2:].strip())
            i += 1
            continue

        if despido.startswith("### "):
            c.subsecao(despido[4:].strip())
            i += 1
            continue

        if despido.startswith("## "):
            c.secao(despido[3:].strip())
            primeira_secao = False
            i += 1
            continue

        if despido == "---":
            if not primeira_secao:
                i += 1
                continue
            _regua(doc)
            i += 1
            continue

        if despido.startswith("|"):
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            c.tabela(bloco)
            continue

        if despido.startswith("- "):
            nivel = (len(linha) - len(linha.lstrip())) // 2
            partes = [despido[2:].strip()]
            i += 1
            # continuação indentada do mesmo item
            while (i < len(linhas) and linhas[i].strip()
                   and not linhas[i].strip().startswith(("- ", "|", "#"))
                   and linhas[i].startswith(" ")):
                partes.append(linhas[i].strip())
                i += 1
            c.item(" ".join(partes), nivel)
            continue

        partes = []
        while (i < len(linhas) and linhas[i].strip()
               and not linhas[i].strip().startswith(("#", "|", "- ", "---"))):
            partes.append(linhas[i].strip())
            i += 1
        texto = " ".join(partes)
        if texto.startswith("Vale aqui a mesma régua"):
            c.nota(texto)
        else:
            c.paragrafo(texto)

    return doc


def main():
    if not ENTRADA.exists():
        print(f"nao encontrei {ENTRADA}", file=sys.stderr)
        return 1
    doc = converter(ENTRADA.read_text(encoding="utf-8"))
    doc.save(SAIDA)
    print(f"gerado: {SAIDA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
