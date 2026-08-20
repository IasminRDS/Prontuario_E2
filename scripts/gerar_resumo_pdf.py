# -*- coding: utf-8 -*-
"""Gera `docs/RESUMO_SISTEMA.pdf` — o resumo executivo do sistema.

Existe porque a monografia responde a uma pergunta ("o que a verificação
empírica destes controles mostrou?") e este documento responde a outra: **o que
é o sistema, o que ele faz e com que garantias.** São públicos diferentes — a
banca lê a primeira; quem for avaliar, herdar ou implantar o sistema lê este.

Nada aqui é estimado. Todo número vem da contagem sobre o repositório, e é o
mesmo que consta no README e na monografia; divergência entre os três é defeito,
não versão.

Uso:
    python scripts/gerar_resumo_pdf.py
"""
import pathlib

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle, KeepTogether)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "docs" / "RESUMO_SISTEMA.pdf"

# Os tokens do design system do próprio sistema (static/css/dsgov.css).
AZUL = colors.HexColor("#1351B4")
AZUL_ESCURO = colors.HexColor("#0B2E69")
AMARELO = colors.HexColor("#FFCD07")
AZUL_CLARO = colors.HexColor("#EDF3FC")
GRAFITE = colors.HexColor("#1C1C1C")
CINZA = colors.HexColor("#5A5A5A")
CINZA_LINHA = colors.HexColor("#D8DDE6")
CINZA_ZEBRA = colors.HexColor("#F6F8FA")

MARGEM = 1.7 * cm
LARGURA_UTIL = A4[0] - 2 * MARGEM

# --------------------------------------------------------------------------
# Estilos
# --------------------------------------------------------------------------
corpo = ParagraphStyle("corpo", fontName="Helvetica", fontSize=9.2, leading=12.6,
                       alignment=TA_JUSTIFY, textColor=GRAFITE, spaceAfter=5)
corpo_pequeno = ParagraphStyle("corpo_pequeno", parent=corpo, fontSize=8.3,
                               leading=11)
item = ParagraphStyle("item", parent=corpo, leftIndent=0.42 * cm,
                      bulletIndent=0.05 * cm, spaceAfter=3.5)
secao = ParagraphStyle("secao", fontName="Helvetica-Bold", fontSize=11,
                       leading=14, textColor=colors.white,
                       backColor=AZUL, borderPadding=(4, 6, 4, 6),
                       spaceBefore=13, spaceAfter=7)
sub = ParagraphStyle("sub", fontName="Helvetica-Bold", fontSize=9.4, leading=12,
                     textColor=AZUL_ESCURO, spaceBefore=7, spaceAfter=3)
legenda = ParagraphStyle("legenda", fontName="Helvetica-Oblique", fontSize=7.6,
                         leading=9.6, textColor=CINZA, spaceBefore=3,
                         spaceAfter=9)
celula = ParagraphStyle("celula", fontName="Helvetica", fontSize=8.2, leading=10.6,
                        textColor=GRAFITE)
celula_neg = ParagraphStyle("celula_neg", parent=celula,
                            fontName="Helvetica-Bold")
celula_cab = ParagraphStyle("celula_cab", parent=celula,
                            fontName="Helvetica-Bold", textColor=colors.white)
mono = ParagraphStyle("mono", fontName="Courier", fontSize=7.9, leading=11,
                      textColor=AZUL_ESCURO)


def p(texto, estilo=corpo):
    return Paragraph(texto, estilo)


def li(texto):
    return Paragraph(texto, item, bulletText="\u25aa")


def tabela(cabecalho, linhas, larguras, alinhar_direita=()):
    """Tabela com cabeçalho azul e zebra.

    `cabecalho=None` produz a variante sem faixa: a tabela de números não tem
    o que rotular, e a faixa vazia seria uma barra azul sem função.
    """
    dados = []
    if cabecalho:
        dados.append([Paragraph(c, celula_cab) for c in cabecalho])
    for linha in linhas:
        dados.append([Paragraph(c, celula) for c in linha])

    t = Table(dados, colWidths=larguras, repeatRows=1 if cabecalho else 0,
              hAlign="LEFT")
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), AZUL if cabecalho else AZUL_CLARO),
        ("LINEBELOW", (0, 0), (-1, 0), 1.6,
         AMARELO if cabecalho else CINZA_LINHA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, CINZA_LINHA),
        ("BOX", (0, 0), (-1, -1), 0.6, CINZA_LINHA),
    ]
    inicio = 2 if cabecalho else 1
    for n in range(inicio, len(dados), 2):
        estilo.append(("BACKGROUND", (0, n), (-1, n), CINZA_ZEBRA))
    for col in alinhar_direita:
        estilo.append(("ALIGN", (col, 0), (col, -1), "RIGHT"))
    t.setStyle(TableStyle(estilo))
    return t


# --------------------------------------------------------------------------
# Moldura: capa no alto da primeira página, rodapé em todas
# --------------------------------------------------------------------------
def _rodape(canvas, doc):
    canvas.saveState()
    y = 1.05 * cm
    canvas.setStrokeColor(CINZA_LINHA)
    canvas.setLineWidth(0.5)
    canvas.line(MARGEM, y + 0.32 * cm, A4[0] - MARGEM, y + 0.32 * cm)
    canvas.setFont("Helvetica", 7.2)
    canvas.setFillColor(CINZA)
    canvas.drawString(MARGEM, y,
                      "Prontuario Eletronico Hospitalar  \u00b7  resumo do sistema")
    canvas.drawRightString(A4[0] - MARGEM, y, str(canvas.getPageNumber()))
    canvas.restoreState()


def _capa(canvas, doc):
    """Faixa institucional no topo da primeira página."""
    canvas.saveState()
    altura = 3.5 * cm
    topo = A4[1]
    canvas.setFillColor(AZUL)
    canvas.rect(0, topo - altura, A4[0], altura, stroke=0, fill=1)
    canvas.setFillColor(AMARELO)
    canvas.rect(0, topo - altura - 0.14 * cm, A4[0], 0.14 * cm, stroke=0, fill=1)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 19)
    canvas.drawString(MARGEM, topo - 1.55 * cm, "Prontu\u00e1rio Eletr\u00f4nico Hospitalar")
    canvas.setFont("Helvetica", 10.6)
    canvas.drawString(MARGEM, topo - 2.15 * cm,
                      "Sistema multi-tenant para a rede p\u00fablica de sa\u00fade  \u00b7  resumo do sistema")
    canvas.setFont("Helvetica", 8.4)
    canvas.setFillColor(colors.HexColor("#C7D8F2"))
    canvas.drawString(MARGEM, topo - 2.92 * cm,
                      "Iasmin Ribeiro de Souza  \u00b7  IF Baiano, Campus Bom Jesus da Lapa  "
                      "\u00b7  Tecnologia em Gest\u00e3o da TI  \u00b7  2026")
    canvas.restoreState()
    _rodape(canvas, doc)


def montar(historia):
    doc = BaseDocTemplate(str(SAIDA), pagesize=A4,
                          leftMargin=MARGEM, rightMargin=MARGEM,
                          topMargin=1.5 * cm, bottomMargin=1.7 * cm,
                          title="Prontu\u00e1rio Eletr\u00f4nico Hospitalar \u2014 resumo do sistema",
                          author="Iasmin Ribeiro de Souza")
    quadro_capa = Frame(MARGEM, 1.7 * cm, LARGURA_UTIL,
                        A4[1] - 4.4 * cm - 1.7 * cm, id="capa")
    quadro = Frame(MARGEM, 1.7 * cm, LARGURA_UTIL,
                   A4[1] - 1.5 * cm - 1.7 * cm, id="normal")
    doc.addPageTemplates([
        PageTemplate(id="capa", frames=[quadro_capa], onPage=_capa),
        PageTemplate(id="normal", frames=[quadro], onPage=_rodape),
    ])
    doc.build(historia)


# --------------------------------------------------------------------------
# Conteúdo
# --------------------------------------------------------------------------
def historia():
    from reportlab.platypus import NextPageTemplate
    h = [NextPageTemplate("normal")]

    # ── 1 ──────────────────────────────────────────────────────────────────
    h.append(p("O que \u00e9", secao))
    h.append(p(
        "Sistema de <b>prontu\u00e1rio eletr\u00f4nico hospitalar</b> para a rede p\u00fablica de "
        "sa\u00fade, escrito em Python/Flask sobre PostgreSQL. Cobre o ciclo assistencial "
        "completo \u2014 do cadastro do cidad\u00e3o \u00e0 alta hospitalar e ao faturamento SUS \u2014 "
        "com <b>116 telas</b> distribu\u00eddas em 45 m\u00f3dulos, interface no Padr\u00e3o Digital de "
        "Governo (gov.br) e acessibilidade eMAG/WCAG 2.1 AA."))
    h.append(p(
        "A caracter\u00edstica que o define \u00e9 ser <b>multi-tenant</b>: uma \u00fanica inst\u00e2ncia "
        "atende v\u00e1rias unidades de sa\u00fade administrativamente independentes, e cada "
        "uma enxerga apenas os pr\u00f3prios registros. O isolamento n\u00e3o \u00e9 apenas um filtro "
        "na aplica\u00e7\u00e3o: est\u00e1 declarado <b>dentro do banco de dados</b>, de modo que uma "
        "consulta nova que esque\u00e7a o filtro continua sem enxergar registro de outra "
        "unidade."))
    h.append(p(
        "O sistema foi <b>constru\u00eddo integralmente nesta pesquisa</b>, e n\u00e3o adotado "
        "pronto. \u00c9 essa condi\u00e7\u00e3o que tornou poss\u00edvel abrir cada controle por dentro, "
        "quebr\u00e1-lo de prop\u00f3sito e medir se ele de fato resistia."))

    # ── 2 ──────────────────────────────────────────────────────────────────
    h.append(p("O problema que ele endere\u00e7a", secao))
    h.append(p(
        "No SUS, a mesma pessoa \u00e9 atendida em munic\u00edpios diferentes, por unidades "
        "que n\u00e3o respondem umas \u00e0s outras. Isso produz quatro exig\u00eancias que puxam em "
        "dire\u00e7\u00f5es opostas:"))
    h.append(li(
        "<b>Exposi\u00e7\u00e3o entre unidades n\u00e3o gera erro.</b> Quando o isolamento depende de "
        "um filtro escrito \u00e0 m\u00e3o em cada consulta, a consulta que o esquece devolve "
        "dados a mais sem alerta, sem exce\u00e7\u00e3o e sem sinal para o usu\u00e1rio \u2014 o "
        "incidente se apresenta como funcionamento normal."))
    h.append(li(
        "<b>Mas a segrega\u00e7\u00e3o n\u00e3o pode ser total.</b> Cadastro de paciente \u00e9 nacional: "
        "descobrir que o cidad\u00e3o atendido hoje j\u00e1 foi atendido em outro munic\u00edpio \u00e9 "
        "a raz\u00e3o de existir do prontu\u00e1rio em rede."))
    h.append(li(
        "<b>Rastreabilidade \u00e9 obriga\u00e7\u00e3o legal.</b> O art. 37 da LGPD exige registro das "
        "opera\u00e7\u00f5es de tratamento, e em sa\u00fade isso tem contrapartida concreta: o "
        "titular tem direito de saber quem acessou o prontu\u00e1rio dele."))
    h.append(li(
        "<b>Continuidade suposta n\u00e3o \u00e9 continuidade.</b> Rotina de backup que nunca foi "
        "restaurada n\u00e3o \u00e9 garantia \u2014 \u00e9 a suposi\u00e7\u00e3o de uma garantia."))

    # ── 3 ──────────────────────────────────────────────────────────────────
    h.append(p("O sistema em n\u00fameros", secao))
    h.append(tabela(
        ["", "", "", ""],
        [["M\u00f3dulos (blueprints)", "<b>45</b>", "Testes",
          "<b>432</b> casos, em 279 fun\u00e7\u00f5es e 37 arquivos"],
         ["Rotas", "<b>213</b> (152 GET, 105 muta\u00e7\u00e3o)", "Tabelas sob RLS", "<b>23</b>"],
         ["Telas (templates)", "<b>116</b>", "Permiss\u00f5es RBAC", "<b>27</b>, em 7 perfis"],
         ["Modelos de dados", "<b>42</b> tabelas, 532 colunas, 114 FKs", "Migra\u00e7\u00f5es", "<b>14</b>"],
         ["Terminologias oficiais", "CID-10, RENAME, CBO, SIGTAP, CNES", "Bancos exercitados",
          "PostgreSQL e SQLite, no CI"]],
        [3.9 * cm, 4.9 * cm, 3.3 * cm, 5.3 * cm]))
    h.append(p(
        "Todos os valores acima s\u00e3o obtidos por contagem sobre o reposit\u00f3rio \u2014 a suíte "
        "de testes, o mapa de rotas da aplica\u00e7\u00e3o e o <i>metadata</i> do ORM \u2014, e n\u00e3o "
        "por estimativa.", legenda))

    # ── 4 ──────────────────────────────────────────────────────────────────
    h.append(p("M\u00f3dulos", secao))
    h.append(tabela(
        ["\u00c1rea", "M\u00f3dulos"],
        [["Atendimento",
          "Pacientes \u00b7 Prontu\u00e1rio (SOAP) \u00b7 Triagem (Manchester) \u00b7 Atendimentos \u00b7 "
          "Pronto-Socorro \u00b7 Portal do Cidad\u00e3o \u00b7 Prescri\u00e7\u00e3o"],
         ["Assist\u00eancia hospitalar",
          "Interna\u00e7\u00e3o \u00b7 Leitos e setores \u00b7 Centro cir\u00fargico \u00b7 Encaminhamentos \u00b7 "
          "Agenda \u00b7 Agendamentos"],
         ["Apoio diagn\u00f3stico",
          "Exames \u00b7 Cat\u00e1logo de exames \u00b7 Vacinas \u00b7 Cat\u00e1logo de vacinas \u00b7 Farm\u00e1cia \u00b7 Estoque"],
         ["Vigil\u00e2ncia e regula\u00e7\u00e3o",
          "Vigil\u00e2ncia (SINAN) \u00b7 Regula\u00e7\u00e3o de vagas \u00b7 Epidemiologia \u00b7 Integra\u00e7\u00e3o RNDS (FHIR R4)"],
         ["Gest\u00e3o",
          "Relat\u00f3rios \u00b7 Relat\u00f3rios hospitalares \u00b7 Faturamento AIH/APAC \u00b7 Importa\u00e7\u00e3o e "
          "exporta\u00e7\u00e3o \u00b7 Tabelas oficiais"],
         ["Plataforma",
          "Autentica\u00e7\u00e3o com MFA \u00b7 Login gov.br (OIDC) \u00b7 Auditoria encadeada \u00b7 Unidades \u00b7 "
          "Usu\u00e1rios \u00b7 Configura\u00e7\u00f5es \u00b7 Backup \u00b7 Documentos assinados"]],
        [3.6 * cm, 13.8 * cm]))
    h.append(p("Tr\u00eas comportamentos que valem men\u00e7\u00e3o:", sub))
    h.append(li(
        "<b>Notifica\u00e7\u00e3o compuls\u00f3ria autom\u00e1tica</b> \u2014 ao lan\u00e7ar no prontu\u00e1rio um CID-10 "
        "de notifica\u00e7\u00e3o obrigat\u00f3ria, o sistema gera a ficha SINAN sozinho e a "
        "enfileira na vigil\u00e2ncia. O profissional n\u00e3o precisa saber de cor quais "
        "agravos s\u00e3o notific\u00e1veis."))
    h.append(li(
        "<b>Classifica\u00e7\u00e3o de risco Manchester</b> \u2014 cinco n\u00edveis com as cores oficiais e "
        "tempo-alvo. A fila do pronto-socorro ordena por gravidade e, dentro dela, "
        "por tempo de espera."))
    h.append(li(
        "<b>\u00cdndice mestre de pacientes</b> \u2014 a mesma pessoa cadastrada em munic\u00edpios "
        "diferentes \u00e9 reconciliada por chave de bloqueio e pontua\u00e7\u00e3o de similaridade. "
        "<b>Nada \u00e9 unificado automaticamente</b>, nem com pontua\u00e7\u00e3o m\u00e1xima: unir dois "
        "pacientes errados mistura o hist\u00f3rico cl\u00ednico de duas pessoas, e isso n\u00e3o tem "
        "desfazer bom."))

    # ── 5 ──────────────────────────────────────────────────────────────────
    h.append(p("Arquitetura", secao))
    h.append(p(
        "<b>Backend</b> Python 3.11 \u00b7 Flask 3 \u00b7 SQLAlchemy \u00b7 Alembic \u00b7 Flask-Login \u00b7 "
        "CSRF em todo formul\u00e1rio \u00b7 pyotp (TOTP) \u00b7 ReportLab (PDF). &nbsp;&nbsp;"
        "<b>Banco</b> PostgreSQL em produ\u00e7\u00e3o, SQLite no desenvolvimento e no CI. "
        "&nbsp;&nbsp;<b>Frontend</b> Jinja2 e CSS puro, <b>sem etapa de build e sem CDN</b> \u2014 "
        "a aplica\u00e7\u00e3o precisa funcionar em rede restrita de unidade de sa\u00fade. "
        "&nbsp;&nbsp;<b>Deploy</b> Gunicorn."))
    h.append(p(
        "Cada controle tem uma camada onde \u00e9 aplicado, e a escolha dessa camada \u00e9 a "
        "decis\u00e3o de projeto. O percurso de uma requisi\u00e7\u00e3o torna isso concreto:", sub))
    passos = [
        "A sess\u00e3o \u00e9 validada e o usu\u00e1rio identificado.",
        "O <b>escopo territorial</b> do usu\u00e1rio \u00e9 resolvido <b>uma \u00fanica vez por "
        "requisi\u00e7\u00e3o</b>, antes de qualquer acesso a dados.",
        "O decorador de autoriza\u00e7\u00e3o confere se o perfil possui a permiss\u00e3o nomeada "
        "que a rota exige; sem ela, a requisi\u00e7\u00e3o \u00e9 rejeitada ali.",
        "Ao iniciar <b>cada transa\u00e7\u00e3o</b>, o escopo \u00e9 publicado na sess\u00e3o do "
        "PostgreSQL com validade local \u00e0 transa\u00e7\u00e3o.",
        "As consultas executam. Al\u00e9m do filtro da aplica\u00e7\u00e3o, a pol\u00edtica de RLS "
        "restringe as linhas que o banco devolve.",
        "Muta\u00e7\u00f5es gravam o evento de auditoria <b>na mesma transa\u00e7\u00e3o</b> da escrita: "
        "ou as duas persistem, ou nenhuma persiste.",
    ]
    for n, passo in enumerate(passos, start=1):
        h.append(Paragraph(passo, item, bulletText="%d." % n))
    h.append(p(
        "Os passos 2 e 4 s\u00e3o separados por necessidade, e n\u00e3o por estilo: ler a "
        "identidade do usu\u00e1rio dispara consulta ao banco, que abre transa\u00e7\u00e3o, que "
        "acionaria de novo o mesmo gatilho \u2014 recurs\u00e3o. Resolver o escopo uma vez e "
        "public\u00e1-lo a cada transa\u00e7\u00e3o \u00e9 consequ\u00eancia direta disso.", corpo_pequeno))

    # ── 6 ──────────────────────────────────────────────────────────────────
    h.append(p("Os controles, e o que cada um garante", secao))

    h.append(p("Isolamento entre unidades (Row-Level Security)", sub))
    h.append(p(
        "23 tabelas carregam pol\u00edtica do pr\u00f3prio PostgreSQL, com <b>FORCE</b> \u2014 sem ele "
        "o dono da tabela ignoraria a pol\u00edtica, e a aplica\u00e7\u00e3o <i>\u00e9</i> a dona. A lista "
        "n\u00e3o \u00e9 mantida \u00e0 m\u00e3o: deriva do <i>metadata</i> do ORM, alcan\u00e7ando toda tabela "
        "que tenha a coluna de unidade. <b>Falha fechada</b>: sem escopo definido, nada "
        "\u00e9 liberado \u2014 aplica\u00e7\u00e3o vazia \u00e9 defeito \u00f3bvio; aplica\u00e7\u00e3o mostrando o pa\u00eds "
        "inteiro \u00e9 incidente que ningu\u00e9m percebe. As tabelas que ficam de fora "
        "<b>precisam de raz\u00e3o escrita</b>, e um teste confere isso nos dois sentidos."))

    h.append(p("Controle de acesso (RBAC)", sub))
    h.append(p(
        "27 permiss\u00f5es nomeadas no formato <font face=\"Courier\">recurso:a\u00e7\u00e3o</font>, "
        "distribu\u00eddas em 7 perfis, <b>ortogonais ao escopo territorial</b>: a permiss\u00e3o "
        "diz <i>o que</i> se pode fazer; o escopo diz <i>sobre quais registros</i>. O "
        "backend \u00e9 a autoridade \u2014 o template apenas espelha a mesma decis\u00e3o para "
        "esconder o controle. Esconder bot\u00e3o n\u00e3o protege nada."))

    h.append(p("Auditoria encadeada por hash", sub))
    h.append(p(
        "Cada evento carrega o hash do anterior: alterar ou remover uma linha do meio "
        "rompe a cadeia, e a verifica\u00e7\u00e3o aponta onde. A tabela pertence a um papel "
        "pr\u00f3prio, e a aplica\u00e7\u00e3o n\u00e3o tem UPDATE nem DELETE nela."))
    h.append(p(
        "O limite \u00e9 declarado em vez de omitido: <b>truncar o FIM da trilha n\u00e3o rompe "
        "elo nenhum</b> \u2014 os elos que sobram seguem consistentes, e nada na tabela diz "
        "que ela j\u00e1 foi maior. Por isso existe um <b>journal de \u00e2ncoras</b>, tamb\u00e9m "
        "encadeado, com retratos peri\u00f3dicos da trilha. Guardada <b>uma linha qualquer</b> "
        "fora do servidor, todo o prefixo at\u00e9 ela pode ser validado \u2014 a cust\u00f3dia deixa "
        "de exigir disciplina cont\u00ednua e passa a exigir um gesto \u00fanico. O que o "
        "mecanismo <i>n\u00e3o</i> fecha est\u00e1 exercitado em teste, e n\u00e3o apenas escrito."))

    h.append(p("Continuidade", sub))
    h.append(p(
        "O comando de valida\u00e7\u00e3o <b>restaura</b> a c\u00f3pia num schema tempor\u00e1rio e compara "
        "as contagens com a origem, saindo com erro se divergirem. C\u00f3pias antigas s\u00e3o "
        "expurgadas por data de modifica\u00e7\u00e3o \u2014 e n\u00e3o por nome, que ordena bem por "
        "acaso at\u00e9 algu\u00e9m renomear um arquivo \u00e0 m\u00e3o."))

    h.append(p("LGPD e prote\u00e7\u00e3o do titular", sub))
    h.append(p(
        "A base legal \u00e9 registrada <b>por finalidade</b>, e a tela distingue o que se "
        "apoia em <b>consentimento</b> (pesquisa, contato, compartilhamento) do que se "
        "apoia na <b>tutela da sa\u00fade</b> do art. 11, II, \u201cf\u201d: assist\u00eancia n\u00e3o depende de "
        "consentimento, e s\u00f3 o que depende dele \u00e9 revog\u00e1vel. H\u00e1 trilha de \u201cquem acessou "
        "meu prontu\u00e1rio\u201d e exporta\u00e7\u00e3o auditada. O acesso tem verifica\u00e7\u00e3o em duas etapas "
        "(TOTP) \u2014 o segredo s\u00f3 \u00e9 gravado depois que o usu\u00e1rio prova um c\u00f3digo v\u00e1lido, "
        "de modo que ningu\u00e9m se tranca fora da pr\u00f3pria conta \u2014 e login federado gov.br."))

    h.append(p("Documentos verific\u00e1veis", sub))
    h.append(p(
        "Todo PDF emitido (receitu\u00e1rio, atestado, encaminhamento, sum\u00e1rio de alta) "
        "recebe um c\u00f3digo impresso no rodap\u00e9 e a impress\u00e3o digital SHA-256 do arquivo "
        "produzido, conferíveis publicamente <b>sem precisar de conta</b>."))

    # ── 7 ──────────────────────────────────────────────────────────────────
    h.append(p("O que a verificação empírica encontrou", secao))
    h.append(p(
        "Os controles acima foram exercitados, e não apenas implementados. A "
        "verificação encontrou <b>dezenove defeitos</b> que compartilham uma "
        "propriedade: <b>nenhum produz mensagem de erro.</b> O sistema não "
        "interrompe, não registra exceção e não apresenta nada de anômalo ao "
        "operador — uma consulta devolve menos linhas do que deveria, um campo "
        "preenchido é descartado, uma trilha deixa de crescer. É a classe de defeito "
        "que o teste convencional não alcança, porque ele verifica que o esperado "
        "aconteceu, e aqui o que falta é justamente a expectativa."))
    h.append(p(
        "Examinados em conjunto, os dezenove se agrupam em <b>cinco mecanismos</b>, e "
        "cada mecanismo admite uma verificação que o torna detectável <b>por medição, "
        "e não por atenção</b>. As cinco verificações tornaram-se casos permanentes "
        "da suíte:"))
    h.append(tabela(
        ["Mecanismo recorrente", "Verificação que o torna detectável"],
        [["<b>I.</b> A declaração que deixou de ser verdadeira — o sistema evoluiu, a "
          "afirmação escrita sobre ele permaneceu",
          "Confrontar a declaração com o estado real, e não com outra declaração"],
         ["<b>II.</b> A regra escrita mais de uma vez — duas cópias divergem, cada uma "
          "internamente consistente",
          "Comparar as cópias entre si, no nível de abstração do efeito"],
         ["<b>III.</b> O caminho que não existe — código correto e inalcançável; não "
          "falha porque não executa",
          "Alcançabilidade nos dois sentidos: tela sem rota <i>e</i> rota sem tela"],
         ["<b>IV.</b> O efeito que não ocorre — a chamada acontece, o efeito não",
          "Medir o efeito, nunca a chamada"],
         ["<b>V.</b> O próprio controle como origem do defeito — o teste que verifica o "
          "objeto errado, o endurecimento que quebra o que protegia",
          "Verificação de segunda ordem: introduzir o defeito de propósito e confirmar "
          "que o verificador reprova"]],
        [9.0 * cm, 8.4 * cm]))
    h.append(p(
        "A lição operacional é a classe V, e ela vale além deste sistema: <b>o "
        "verificador também é um controle</b>, sujeito à mesma exigência. Um detector "
        "que nunca acusa nada é indistinguível de um que parou de funcionar."))

    # ── 8 ──────────────────────────────────────────────────────────────────
    h.append(p("Desempenho", secao))
    h.append(p(
        "Medido com volume sintético de 50 mil pacientes e cerca de 20 mil "
        "internações, <b>distribuídos de forma desbalanceada</b> entre unidades — a "
        "distribuição uniforme ocultaria o pior caso, que é o da unidade de maior "
        "movimento."))
    h.append(KeepTogether(tabela(
        ["Operação", "Antes", "Depois"],
        [["Sugestão de paciente (a cada tecla digitada)", "185,9 ms", "<b>0,96 ms</b>"],
         ["Listagem paginada de pacientes", "40,1 ms", "<b>0,19 ms</b>"],
         ["Relatório de pacientes", "4.616 ms", "<b>113 ms</b>"],
         ["Ocupação de leitos", "106 consultas · 190 ms", "<b>17 consultas · 78 ms</b>"]],
        [9.0 * cm, 4.2 * cm, 4.2 * cm])))
    h.append(p(
        "A sugestão de paciente é o caso determinante: dispara a cada caractere e "
        "varria a tabela inteira. <b>Com volume de demonstração o problema é "
        "indetectável</b> — o otimizador sequer considera índice em tabela pequena. Sem "
        "volume representativo, a decisão de indexação não é informada; é arbitrária. "
        "Pela mesma razão, <b>não foi criado índice onde a medição não o justificou</b>."))

    # ── 9 ──────────────────────────────────────────────────────────────────
    h.append(p("Operação", secao))
    h.append(tabela(
        ["Comando", "O que faz"],
        [["<font face=\"Courier\">flask hardening-check</font>",
          "Confronta o banco com o metadata e verifica o que a aplicação <b>não</b> "
          "garante sozinha. Sai com erro se falhar."],
         ["<font face=\"Courier\">flask backup-validar</font>",
          "Restaura a cópia num schema temporário e compara as contagens com a origem."],
         ["<font face=\"Courier\">flask auditoria-ancora</font>",
          "Grava e confere os retratos da trilha de auditoria; valida o prefixo a partir "
          "de uma âncora guardada fora do servidor."],
         ["<font face=\"Courier\">flask medir-desempenho</font>",
          "Mede as consultas críticas sob protocolo: descarta as primeiras execuções, "
          "repete, e reporta mediana com dispersão."],
         ["<font face=\"Courier\">flask pacientes-deduplicar</font>",
          "Varre e enfileira candidatos a duplicata. <b>Não unifica nada</b> — a decisão "
          "é humana."],
         ["<font face=\"Courier\">flask rnds-processar</font>",
          "Drena a fila de envios à RNDS, com recuo exponencial e idempotência por "
          "hash do conteúdo."]],
        [5.3 * cm, 12.1 * cm]))

    # ── 10 ─────────────────────────────────────────────────────────────────
    h.append(p("O que o sistema não garante", secao))
    h.append(p("Declarar os limites faz parte do controle. Os principais:"))
    h.append(li(
        "<b>Três garantias dependem de infraestrutura, e não de código</b> — se a "
        "aplicação pudesse aplicá-las, poderia desfazê-las, e então não seriam "
        "garantia: o acréscimo-somente de verdade no sistema de arquivos, a "
        "separação entre quem emite e quem verifica as âncoras, e a custódia de um "
        "hash fora do servidor."))
    h.append(li(
        "<b>Truncar o fim do journal de âncoras</b> continua indetectável — é a mesma "
        "recursão do problema original, e há um teste que exercita essa limitação de "
        "propósito, para que ela continue verdadeira por medição e não por memória."))
    h.append(li(
        "<b>O envio à RNDS é simulado</b> neste ambiente: o despacho real exige "
        "certificado ICP-Brasil e credenciais do DATASUS. Está isolado numa única "
        "função, e a tela avisa quando opera em simulação."))
    h.append(li(
        "<b>As cópias de segurança residem no mesmo servidor que o banco</b>: a rotação "
        "existe, a custódia externa não."))
    h.append(li(
        "<b>A medição de desempenho tem protocolo, mas o ambiente é sintético</b>: os "
        "valores servem para evidenciar ordem de grandeza, não como referência de "
        "capacidade."))
    h.append(li(
        "<b>A usabilidade foi avaliada por inspeção heurística</b>, e não com usuários "
        "reais em ambiente clínico."))

    h.append(Spacer(1, 0.4 * cm))
    h.append(p(
        "Documentação completa em <font face=\"Courier\">docs/TCC.md</font> — a "
        "monografia que descreve o sistema, a análise de segurança e o relato dos "
        "dezenove achados. Código sob licença MIT.", legenda))
    return h


if __name__ == "__main__":
    montar(historia())
    print("gerado:  %s" % SAIDA)
    print("tamanho: %s bytes" % format(SAIDA.stat().st_size, ","))
