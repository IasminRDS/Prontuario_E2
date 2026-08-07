# -*- coding: utf-8 -*-
"""Converte docs/TCC.md em monografia .docx com formatação ABNT.

    python scripts/gerar_tcc_docx.py

Por que um conversor próprio, e não `pandoc`: a ABNT exige coisas que um
conversor genérico não faz — capa e elementos pré-textuais sem numeração de
seção e fora do sumário, numeração de página que CONTA a partir da folha de
rosto mas só APARECE a partir da introdução, legenda de quadro e tabela acima
com fonte abaixo, seções primárias em página nova, e margens assimétricas
(3 cm à esquerda e no topo, 2 cm à direita e embaixo).

**A formatação aplicada aqui é a da NBR 14724.** O Art. 14 do regulamento do
curso delega essa definição às "Normas Gerais para Redação da Monografia" do
COLEGIADO. Se esse documento divergir, ele prevalece — ajuste as constantes
abaixo em vez de reformatar o arquivo à mão, para a conversão continuar
reproduzível.

## Convenções que o markdown de origem usa

`{{sumario}}`, `{{lista-de-quadros}}`, `{{lista-de-tabelas}}`,
`{{lista-de-figuras}}`
    Viram campos do Word, que se preenchem sozinhos ao abrir o arquivo. Manter
    o sumário à mão é garantia de página errada na versão entregue.

`Quadro — título` / `Tabela — título` / `Figura — título`
    Legenda do bloco seguinte. **A numeração é automática**, por tipo: o travessão
    é substituído por "Quadro 3 —". Numerar à mão significa renumerar tudo a cada
    bloco inserido, e é assim que sai monografia com dois "Quadro 5".

`Fonte: ...`
    Fonte do bloco anterior, em corpo menor. A ABNT exige fonte em toda
    ilustração e tabela, inclusive quando é a própria autora.

`{{espaco}}`
    Uma linha em branco. Usado para distribuir a capa e a folha de rosto ao
    longo da página. O Word sabe justificar verticalmente uma seção inteira,
    mas nem todo editor implementa isso, e a capa é a primeira página que a
    banca abre.

A distinção entre **quadro** e **tabela** não é cosmética: tabela apresenta dado
numérico e tem laterais abertas; quadro apresenta informação textual e é
fechado. Quase todos os blocos desta monografia são quadros.
"""
import datetime
import pathlib
import re
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# --- Parâmetros de formatação (NBR 14724) ---------------------------------
FONTE = "Times New Roman"
FONTE_MONO = "Consolas"
CORPO_PT = 12
CITACAO_PT = 10          # citação longa, legenda, fonte e conteúdo de tabela
CODIGO_PT = 9
ENTRELINHAS = 1.5
RECUO_PARAGRAFO = Cm(1.25)
RECUO_CITACAO = Cm(4)    # NBR 10520: citação com mais de três linhas
RECUO_NATUREZA = Cm(8)   # NBR 14724: a nota de natureza da folha de rosto
MARGEM_ESQ, MARGEM_SUP = Cm(3), Cm(3)
MARGEM_DIR, MARGEM_INF = Cm(2), Cm(2)

CINZA_CODIGO = "F2F2F2"
CINZA_CABECALHO = "D9D9D9"

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ORIGEM = RAIZ / "docs" / "TCC.md"
DESTINO = RAIZ / "docs" / "TCC.docx"

AUTORA = "Iasmin Ribeiro de Souza"
TITULO = ("Construção de um prontuário eletrônico multi-tenant: avaliação "
          "empírica de controles de segurança, isolamento de dados e auditoria")

# A primeira seção textual. Tudo antes dela é pré-textual: sem numeração de
# página visível, sem estilo de título (para não entrar no sumário).
INICIO_DO_TEXTO = re.compile(r"^##\s+1\.\s", re.IGNORECASE)

# Elementos pré e pós-textuais têm o título centralizado e sem indicativo
# numérico (NBR 14724, 5.1).
CENTRALIZADOS = ("FOLHA DE ROSTO", "FOLHA DE APROVAÇÃO", "DEDICATÓRIA",
                 "AGRADECIMENTOS", "EPÍGRAFE", "RESUMO", "ABSTRACT",
                 "LISTA DE", "SUMÁRIO", "REFERÊNCIAS", "APÊNDICE", "ANEXO")


# --------------------------------------------------------------------------
# Auxiliares de XML — o que a API do python-docx não expõe
# --------------------------------------------------------------------------
def _campo(paragrafo, instrucao, marcador="atualize com F9"):
    """Insere um campo do Word (SUMÁRIO, PAGE, ...).

    Um campo é um trecho que o Word recalcula sozinho. É o que faz o sumário
    trazer a página certa depois da diagramação final — um sumário digitado à
    mão desatualiza na primeira quebra de página que mudar.
    """
    run = paragrafo.add_run()
    inicio = OxmlElement("w:fldChar")
    inicio.set(qn("w:fldCharType"), "begin")
    texto = OxmlElement("w:instrText")
    texto.set(qn("xml:space"), "preserve")
    texto.text = instrucao
    separador = OxmlElement("w:fldChar")
    separador.set(qn("w:fldCharType"), "separate")
    fim = OxmlElement("w:fldChar")
    fim.set(qn("w:fldCharType"), "end")

    for elemento in (inicio, texto, separador):
        run._r.append(elemento)
    if marcador:
        run._r.append(_texto_xml(marcador))
    run._r.append(fim)
    return run


def _texto_xml(valor):
    elemento = OxmlElement("w:t")
    elemento.text = valor
    return elemento


def _atualizar_campos_ao_abrir(doc):
    """Faz o Word recalcular os campos na abertura.

    Sem isto o sumário nasce com o texto do marcador e depende de alguém
    lembrar de apertar F9 antes de imprimir.
    """
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is None:
        elemento = OxmlElement("w:updateFields")
        elemento.set(qn("w:val"), "true")
        settings.append(elemento)


def _sombra(cor):
    elemento = OxmlElement("w:shd")
    elemento.set(qn("w:val"), "clear")
    elemento.set(qn("w:fill"), cor)
    return elemento


def _sombrear_paragrafo(paragrafo, cor):
    paragrafo._p.get_or_add_pPr().append(_sombra(cor))


def _sombrear_celula(celula, cor):
    celula._tc.get_or_add_tcPr().append(_sombra(cor))


def _repetir_cabecalho(linha):
    """Marca a linha como cabeçalho, para repetir em tabela que vira a página."""
    propriedades = linha._tr.get_or_add_trPr()
    marca = OxmlElement("w:tblHeader")
    marca.set(qn("w:val"), "true")
    propriedades.append(marca)


# --------------------------------------------------------------------------
# Estilos e seções
# --------------------------------------------------------------------------
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
    pf.widow_control = True

    for nivel in range(1, 5):
        estilo = doc.styles[f"Heading {nivel}"]
        estilo.font.name = FONTE
        estilo.font.size = Pt(CORPO_PT)
        estilo.font.bold = True
        estilo.font.color.rgb = RGBColor(0, 0, 0)
        estilo.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)
        pf = estilo.paragraph_format
        pf.line_spacing = ENTRELINHAS
        pf.space_before = Pt(12)
        pf.space_after = Pt(12)
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        # Título sozinho no rodapé da página é erro de diagramação clássico.
        pf.keep_with_next = True
        pf.page_break_before = False

    for nome in ("List Bullet", "List Number"):
        estilo = doc.styles[nome]
        estilo.font.name = FONTE
        estilo.font.size = Pt(CORPO_PT)

    # O estilo `Caption` do Word vem em azul e itálico; a ABNT quer preto e
    # corpo menor. É o estilo que as listas de quadros e tabelas procuram, então
    # não dá para trocá-lo por formatação direta.
    legenda = doc.styles["Caption"]
    legenda.font.name = FONTE
    legenda.font.size = Pt(CITACAO_PT)
    legenda.font.italic = False
    legenda.font.bold = False
    legenda.font.color.rgb = RGBColor(0, 0, 0)
    legenda.element.rPr.rFonts.set(qn("w:eastAsia"), FONTE)


def _margens(secao):
    secao.left_margin, secao.top_margin = MARGEM_ESQ, MARGEM_SUP
    secao.right_margin, secao.bottom_margin = MARGEM_DIR, MARGEM_INF
    secao.header_distance = Cm(2)
    secao.footer_distance = Cm(1.5)


def _numerar_paginas(secao):
    """Número no canto superior direito, a 2 cm da borda (NBR 14724, 5.3).

    A contagem inclui as folhas pré-textuais, mas o número só aparece a partir
    da primeira folha textual. Por isso o campo PAGE vai numa seção nova com
    cabeçalho desvinculado, e não numa numeração reiniciada: reiniciar exigiria
    adivinhar quantas páginas o pré-textual ocupa depois de diagramado.
    """
    secao.header.is_linked_to_previous = False
    paragrafo = secao.header.paragraphs[0]
    paragrafo.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragrafo.paragraph_format.line_spacing = 1.0
    run = _campo(paragrafo, "PAGE", marcador="1")
    run.font.name = FONTE
    run.font.size = Pt(CITACAO_PT)


# --------------------------------------------------------------------------
# Texto em linha
# --------------------------------------------------------------------------
_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_TOKENS = re.compile(r"(\*\*.+?\*\*|`[^`]+`|(?<!\*)\*(?!\*).+?(?<!\*)\*(?!\*))")


def _escrever_inline(paragrafo, texto, tamanho=None):
    """Aplica negrito, itálico e monoespaçado dentro do parágrafo."""
    texto = _LINK.sub(r"\1", texto)          # link vira só o rótulo
    texto = texto.replace("&nbsp;", " ")

    for parte in _TOKENS.split(texto):
        if not parte:
            continue
        if parte.startswith("**") and parte.endswith("**"):
            run = paragrafo.add_run(parte[2:-2])
            run.bold = True
        elif parte.startswith("`") and parte.endswith("`"):
            run = paragrafo.add_run(parte[1:-1])
            run.font.name = FONTE_MONO
            run.font.size = Pt((tamanho or CORPO_PT) - 1)
            continue
        elif parte.startswith("*") and parte.endswith("*"):
            run = paragrafo.add_run(parte[1:-1])
            run.italic = True
        else:
            run = paragrafo.add_run(parte)
        run.font.name = FONTE
        if tamanho:
            run.font.size = Pt(tamanho)


# --------------------------------------------------------------------------
# Blocos
# --------------------------------------------------------------------------
class Conversor:
    def __init__(self, doc):
        self.doc = doc
        self.capa = True          # antes da folha de rosto
        self.pre_textual = True   # antes da introdução
        self.primeiro_bloco = True
        self.contador = {"Quadro": 0, "Tabela": 0, "Figura": 0}
        self.legenda_pendente = None

    # -- parágrafos utilitários -------------------------------------------
    def _p(self, alinhamento=WD_ALIGN_PARAGRAPH.JUSTIFY, entrelinhas=ENTRELINHAS,
           antes=0, depois=0):
        p = self.doc.add_paragraph()
        pf = p.paragraph_format
        pf.alignment = alinhamento
        pf.line_spacing = entrelinhas
        pf.space_before = Pt(antes)
        pf.space_after = Pt(depois)
        return p

    def quebra_de_pagina(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    # -- capa e pré-textual -----------------------------------------------
    def titulo_de_capa(self, texto, nivel):
        """Título antes da introdução: centralizado e SEM estilo de título.

        Usar `Heading` aqui faria RESUMO e ABSTRACT entrarem no sumário, o que a
        NBR 14724 não admite: elemento pré-textual não é seção.
        """
        p = self._p(WD_ALIGN_PARAGRAPH.CENTER, antes=6, depois=6)
        _escrever_inline(p, texto)
        for run in p.runs:
            run.bold = True
            run.font.size = Pt(CORPO_PT if nivel > 1 else CORPO_PT + 2)

    def e_elemento_pre_textual(self, texto):
        """A capa termina no primeiro elemento pré-textual nomeado.

        Sem esta distinção cada linha da capa abriria uma página: instituição,
        campus e curso são títulos de markdown, mas não são elementos — são
        partes da mesma folha.
        """
        alvo = texto.upper()
        return any(alvo.startswith(c) for c in CENTRALIZADOS)

    def titulo(self, nivel, texto):
        alvo = texto.upper()
        centralizar = any(alvo.startswith(c) for c in CENTRALIZADOS)

        if nivel <= 2 and not self.primeiro_bloco:
            self.quebra_de_pagina()
        self.primeiro_bloco = False

        # No markdown a seção primária é `##`, porque `#` é o título da capa.
        # No Word ela precisa ser Heading 1: o sumário automático monta a
        # hierarquia pelos níveis de estilo, e começar em 2 empurraria a
        # subseção mais profunda (9.4.1) para fora do intervalo indexado.
        p = self.doc.add_heading(level=max(1, min(nivel - 1, 4)))
        p.alignment = (WD_ALIGN_PARAGRAPH.CENTER if centralizar
                       else WD_ALIGN_PARAGRAPH.LEFT)
        _escrever_inline(p, texto)
        for run in p.runs:
            run.font.name = FONTE
            run.font.size = Pt(CORPO_PT)
            run.bold = True
            run.font.color.rgb = RGBColor(0, 0, 0)

    # -- legenda e fonte ---------------------------------------------------
    def legenda(self, tipo, titulo):
        """Legenda numerada automaticamente, acima do bloco (NBR 14724, 5.8).

        A numeração é um campo `SEQ` no estilo *Caption*, e não texto digitado,
        porque é isso que as listas de quadros e tabelas procuram: `TOC \\c` só
        enxerga legenda que combine as duas coisas. Legenda escrita à mão
        produz lista vazia — e a lista vazia passa despercebida.
        """
        self.contador[tipo] += 1
        p = self.doc.add_paragraph(style="Caption")
        pf = p.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf.line_spacing = 1.0
        pf.space_before = Pt(12)
        pf.space_after = Pt(2)
        # Legenda separada do bloco por quebra de página é defeito visível.
        pf.keep_with_next = True

        rotulo = p.add_run(f"{tipo} ")
        _campo(p, f"SEQ {tipo} \\* ARABIC", marcador=str(self.contador[tipo]))
        travessao = p.add_run(" — ")
        for run in (rotulo, travessao):
            run.bold = True
        _escrever_inline(p, titulo)
        for run in p.runs:
            run.font.name = FONTE
            run.font.size = Pt(CITACAO_PT)
            run.font.color.rgb = RGBColor(0, 0, 0)
            run.italic = False

    def fonte(self, texto):
        p = self._p(WD_ALIGN_PARAGRAPH.LEFT, entrelinhas=1.0, depois=12)
        _escrever_inline(p, texto, tamanho=CITACAO_PT)

    # -- tabela ------------------------------------------------------------
    def tabela(self, linhas):
        celulas = [[c.strip() for c in l.strip().strip("|").split("|")]
                   for l in linhas]
        # a segunda linha do markdown é o separador (---)
        corpo = [celulas[0]] + celulas[2:]
        colunas = max(len(l) for l in corpo)

        tab = self.doc.add_table(rows=0, cols=colunas)
        tab.style = "Table Grid"
        tab.alignment = WD_TABLE_ALIGNMENT.CENTER
        tab.autofit = True

        for i, linha in enumerate(corpo):
            cells = tab.add_row().cells
            for j in range(colunas):
                texto = linha[j] if j < len(linha) else ""
                p = cells[j].paragraphs[0]
                pf = p.paragraph_format
                pf.line_spacing = 1.0
                pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
                pf.space_before = Pt(2)
                pf.space_after = Pt(2)
                _escrever_inline(p, texto, tamanho=CITACAO_PT)
                if i == 0:
                    for run in p.runs:
                        run.bold = True
                    _sombrear_celula(cells[j], CINZA_CABECALHO)
            if i == 0:
                _repetir_cabecalho(tab.rows[0])

    # -- bloco de código / diagrama ---------------------------------------
    def codigo(self, linhas):
        for indice, linha in enumerate(linhas):
            p = self._p(WD_ALIGN_PARAGRAPH.LEFT, entrelinhas=1.0)
            p.paragraph_format.left_indent = Cm(1)
            # Diagrama partido ao meio por quebra de página fica ilegível.
            p.paragraph_format.keep_with_next = indice < len(linhas) - 1
            run = p.add_run(linha)
            run.font.name = FONTE_MONO
            run.font.size = Pt(CODIGO_PT)
            _sombrear_paragrafo(p, CINZA_CODIGO)


# --------------------------------------------------------------------------
_CABECALHO = re.compile(r"^(#{1,4})\s+(.*)$")
_ITEM = re.compile(r"^\s*[-*]\s+(.*)$")
_NUMERADO = re.compile(r"^\s*\d+\.\s+(.*)$")
_LEGENDA = re.compile(r"^(Quadro|Tabela|Figura)\s+—\s+(.+)$")
_FONTE_LEGENDA = re.compile(r"^Fonte:\s*(.+)$")
_MARCADOR = re.compile(r"^\{\{([a-z-]+)\}\}$")
_SEPARADOR = ("---", "***", "___")

_CAMPOS = {
    "sumario": r'TOC \o "1-4" \h \z \u',
    "lista-de-quadros": r'TOC \h \z \c "Quadro"',
    "lista-de-tabelas": r'TOC \h \z \c "Tabela"',
    "lista-de-figuras": r'TOC \h \z \c "Figura"',
}


def converter():
    if not ORIGEM.is_file():
        sys.exit(f"não encontrei {ORIGEM}")

    doc = Document()
    _configurar_estilos(doc)
    _margens(doc.sections[0])

    doc.core_properties.title = TITULO
    doc.core_properties.author = AUTORA
    doc.core_properties.subject = ("Trabalho de Conclusão de Curso — Tecnologia "
                                   "em Gestão da Tecnologia da Informação")
    doc.core_properties.comments = (
        "Gerado por scripts/gerar_tcc_docx.py a partir de docs/TCC.md em "
        f"{datetime.date.today():%d/%m/%Y}. Edite o markdown, não este arquivo.")

    conv = Conversor(doc)
    linhas = ORIGEM.read_text(encoding="utf-8").splitlines()
    i = 0
    dentro_de_codigo = False
    bloco_codigo = []

    while i < len(linhas):
        linha = linhas[i]

        # A primeira seção textual abre seção nova do Word, que é o que permite
        # o número de página aparecer só a partir daqui.
        if conv.pre_textual and INICIO_DO_TEXTO.match(linha):
            secao = doc.add_section(WD_SECTION.NEW_PAGE)
            _margens(secao)
            _numerar_paginas(secao)
            conv.pre_textual = False
            conv.primeiro_bloco = True

        # Comentários HTML do markdown são instruções para a autora: não entram.
        if linha.strip().startswith("<!--"):
            while i < len(linhas) and "-->" not in linhas[i]:
                i += 1
            i += 1
            continue

        if linha.strip().startswith("```"):
            dentro_de_codigo = not dentro_de_codigo
            if not dentro_de_codigo and bloco_codigo:
                conv.codigo(bloco_codigo)
                bloco_codigo = []
            i += 1
            continue

        if dentro_de_codigo:
            bloco_codigo.append(linha)
            i += 1
            continue

        marcador = _MARCADOR.match(linha.strip())
        if marcador and marcador.group(1) == "espaco":
            # Espaçador explícito da capa e da folha de rosto. O alinhamento
            # vertical de seção do Word faria o mesmo, mas nem todo editor o
            # implementa — e capa é a primeira coisa que a banca vê.
            conv._p(entrelinhas=1.0, depois=0)
            i += 1
            continue

        if marcador and marcador.group(1) in _CAMPOS:
            p = conv._p(WD_ALIGN_PARAGRAPH.LEFT, entrelinhas=ENTRELINHAS)
            _campo(p, _CAMPOS[marcador.group(1)],
                   marcador="[atualize os campos: Ctrl+A, F9]")
            i += 1
            continue

        legenda = _LEGENDA.match(linha.strip())
        if legenda:
            conv.legenda(legenda.group(1), legenda.group(2))
            i += 1
            continue

        fonte = _FONTE_LEGENDA.match(linha.strip())
        if fonte:
            conv.fonte(f"Fonte: {fonte.group(1)}")
            i += 1
            continue

        if linha.strip().startswith("|"):
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            if len(bloco) >= 2:
                conv.tabela(bloco)
            continue

        cabecalho = _CABECALHO.match(linha)
        if cabecalho:
            nivel = len(cabecalho.group(1))
            titulo = _LINK.sub(r"\1", cabecalho.group(2).strip()).replace("**", "")
            if conv.pre_textual:
                elemento = conv.e_elemento_pre_textual(titulo)
                if conv.capa and elemento:
                    conv.capa = False
                    conv.quebra_de_pagina()
                elif elemento and not conv.primeiro_bloco:
                    conv.quebra_de_pagina()
                conv.primeiro_bloco = False
                conv.titulo_de_capa(titulo, nivel)
            else:
                conv.titulo(nivel, titulo)
            i += 1
            continue

        # Separador horizontal: no markdown marcava troca de seção; aqui a
        # quebra de página já cumpre o papel.
        if linha.strip() in _SEPARADOR:
            i += 1
            continue

        # Citação longa (NBR 10520): recuo, corpo menor, espaço simples, sem
        # aspas. Na folha de rosto o mesmo bloco é a nota de natureza do
        # trabalho, que a NBR 14724 recua a partir do meio da mancha.
        if linha.strip().startswith(">"):
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith(">"):
                bloco.append(linhas[i].strip().lstrip(">").strip())
                i += 1
            p = conv._p(WD_ALIGN_PARAGRAPH.JUSTIFY, entrelinhas=1.0, depois=12)
            p.paragraph_format.left_indent = (RECUO_NATUREZA if conv.pre_textual
                                              else RECUO_CITACAO)
            _escrever_inline(p, " ".join(x for x in bloco if x),
                             tamanho=CITACAO_PT)
            continue

        item = _ITEM.match(linha)
        if item:
            p = doc.add_paragraph(style="List Bullet")
            p.paragraph_format.line_spacing = ENTRELINHAS
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _escrever_inline(p, item.group(1))
            i += 1
            continue

        numerado = _NUMERADO.match(linha)
        if numerado:
            p = doc.add_paragraph(style="List Number")
            p.paragraph_format.line_spacing = ENTRELINHAS
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            _escrever_inline(p, numerado.group(1))
            i += 1
            continue

        # Parágrafo: junta as linhas até a próxima linha em branco, porque no
        # markdown a quebra é cosmética e no Word viraria parágrafo novo.
        if linha.strip():
            bloco = []
            while (i < len(linhas) and linhas[i].strip()
                   and not _CABECALHO.match(linhas[i])
                   and not _ITEM.match(linhas[i])
                   and not _NUMERADO.match(linhas[i])
                   and not _LEGENDA.match(linhas[i].strip())
                   and not _FONTE_LEGENDA.match(linhas[i].strip())
                   and not linhas[i].lstrip().startswith(("|", ">", "```"))
                   and linhas[i].strip() not in _SEPARADOR):
                bloco.append(linhas[i].strip())
                i += 1
            if not bloco:            # a linha era um bloco de outro tipo
                continue
            texto = " ".join(bloco)
            if conv.pre_textual:
                p = conv._p(WD_ALIGN_PARAGRAPH.CENTER)
                _escrever_inline(p, texto)
            else:
                p = conv._p()
                p.paragraph_format.first_line_indent = RECUO_PARAGRAFO
                _escrever_inline(p, texto)
            continue

        i += 1

    _atualizar_campos_ao_abrir(doc)
    doc.save(DESTINO)
    print(f"gerado:  {DESTINO}")
    print(f"tamanho: {DESTINO.stat().st_size:,} bytes")
    print(f"blocos:  {conv.contador['Quadro']} quadros, "
          f"{conv.contador['Tabela']} tabelas, {conv.contador['Figura']} figuras")
    print("O sumário e as listas se preenchem ao abrir no Word. Se o editor não "
          "atualizar sozinho, use Ctrl+A e F9.")


if __name__ == "__main__":
    converter()
