# -*- coding: utf-8 -*-
"""Gera `docs/RESUMO_SISTEMA.pdf` — o resumo executivo do sistema.

Existe porque a monografia responde a uma pergunta ("o que a verificação
empírica destes controles mostrou?") e este documento responde a outra: **o que
é o sistema, o que ele faz e com que garantias.** São públicos diferentes — a
banca lê a primeira; quem for avaliar, herdar ou implantar o sistema lê este.

O escopo é o sistema, e só ele. **Nenhum número aqui vem de dado fabricado.**
Fica de fora, por decisão e não por esquecimento, tudo o que foi medido sobre
carga sintética — os tempos de consulta obtidos com cinquenta mil pacientes
gerados existem, estão na monografia e são honestos lá, onde vêm acompanhados
do protocolo e da ressalva de ambiente. Citados aqui, soltos, descreveriam um
desempenho em produção que ninguém observou. Fica de fora, pela mesma razão, o
relato dos defeitos encontrados na verificação: é resultado de pesquisa sobre o
sistema, não característica dele.

O que sobra é contagem sobre o repositório — a suíte de testes, o mapa de rotas
da aplicação, o metadata do ORM —, e é o mesmo que consta no README e na
monografia; divergência entre os três é defeito, não versão.

Uma seção foge à regra de propósito, e o desvio é declarado: a de **posição
diante dos dados nacionais** fala de algo que o sistema **não** faz. Existe
porque a pergunta aparece — um prontuário do SUS deveria consumir dados do
DATASUS? — e deixá-la sem resposta é pior do que respondê-la. A forma de
mantê-la honesta é dupla: o texto diz "levantado e não implementado" com todas
as letras, e a limitação correspondente aparece na última seção, junto com as
outras. Seção que descrevesse a integração como se existisse seria exatamente o
tipo de afirmação que este documento recusa.

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
    h.append(p("O que é", secao))
    h.append(p(
        "Sistema de <b>prontuário eletrônico hospitalar</b> para a rede pública de "
        "saúde, escrito em Python/Flask sobre PostgreSQL. Cobre o ciclo assistencial "
        "completo — do cadastro do cidadão à alta hospitalar e ao faturamento SUS — "
        "com <b>116 telas</b> distribuídas em 45 módulos, interface no Padrão Digital "
        "de Governo (gov.br) e acessibilidade eMAG/WCAG 2.1 AA."))
    h.append(p(
        "A característica que o define é ser <b>multi-tenant</b>: uma única instância "
        "atende várias unidades de saúde administrativamente independentes, e cada "
        "uma enxerga apenas os próprios registros. O isolamento não é apenas um filtro "
        "na aplicação: está declarado <b>dentro do banco de dados</b>, de modo que uma "
        "consulta nova que esqueça o filtro continua sem enxergar registro de outra "
        "unidade."))

    # ── 2 ──────────────────────────────────────────────────────────────────
    h.append(p("O problema que ele endereça", secao))
    h.append(p(
        "No SUS, a mesma pessoa é atendida em municípios diferentes, por unidades "
        "que não respondem umas às outras. Isso produz quatro exigências que puxam em "
        "direções opostas, e são elas que explicam a forma do sistema:"))
    h.append(li(
        "<b>Exposição entre unidades não gera erro.</b> Quando o isolamento depende de "
        "um filtro escrito à mão em cada consulta, a consulta que o esquece devolve "
        "dados a mais sem alerta, sem exceção e sem sinal para o usuário — o "
        "incidente se apresenta como funcionamento normal."))
    h.append(li(
        "<b>Mas a segregação não pode ser total.</b> Cadastro de paciente é nacional: "
        "descobrir que o cidadão atendido hoje já foi atendido em outro município é "
        "a razão de existir do prontuário em rede."))
    h.append(li(
        "<b>Rastreabilidade é obrigação legal.</b> O art. 37 da LGPD exige registro das "
        "operações de tratamento, e em saúde isso tem contrapartida concreta: o "
        "titular tem direito de saber quem acessou o prontuário dele."))
    h.append(li(
        "<b>Continuidade suposta não é continuidade.</b> Rotina de backup que nunca foi "
        "restaurada não é garantia — é a suposição de uma garantia."))

    # ── 3 ──────────────────────────────────────────────────────────────────
    h.append(p("O sistema em números", secao))
    h.append(tabela(
        None,
        [["Módulos (blueprints)", "<b>45</b>", "Testes",
          "<b>463</b> casos, em 303 funções e 37 arquivos"],
         ["Rotas", "<b>213</b> (152 GET, 105 mutação)", "Tabelas sob RLS", "<b>23</b>"],
         ["Telas (templates)", "<b>116</b>", "Permissões RBAC", "<b>27</b>, em 7 perfis"],
         ["Modelos de dados", "<b>42</b> tabelas, 532 colunas, 114 FKs", "Migrações", "<b>14</b>"],
         ["Terminologias oficiais", "CID-10, RENAME, CBO, SIGTAP, CNES", "Bancos exercitados",
          "PostgreSQL e SQLite, no CI"]],
        [3.9 * cm, 4.9 * cm, 3.3 * cm, 5.3 * cm]))
    h.append(p(
        "Todos os valores acima são obtidos por contagem sobre o repositório — a suíte "
        "de testes, o mapa de rotas da aplicação e o <i>metadata</i> do ORM —, e não "
        "por estimativa.", legenda))

    # ── 4 ──────────────────────────────────────────────────────────────────
    h.append(p("O caminho do paciente dentro do sistema", secao))
    h.append(p(
        "Os módulos não são um catálogo de telas independentes: acompanham um "
        "percurso, e o estado de cada etapa condiciona a seguinte."))
    h.append(li(
        "<b>Cadastro</b> — o cidadão é identificado por CPF e CNS, e o município de "
        "residência entra por <b>código IBGE</b>, não por texto livre: cidade digitada "
        "de três jeitos vira três municípios em qualquer relatório."))
    h.append(li(
        "<b>Acolhimento e triagem</b> — classificação de risco <b>Manchester</b> em "
        "cinco níveis, com as cores oficiais e tempo-alvo de atendimento. A fila do "
        "pronto-socorro ordena por gravidade e, dentro dela, por tempo de espera."))
    h.append(li(
        "<b>Atendimento</b> — evolução no prontuário em formato <b>SOAP</b>, com "
        "diagnóstico em CID-10 e prescrição apoiada na RENAME."))
    h.append(li(
        "<b>Apoio diagnóstico</b> — solicitação e resultado de exames, aplicação de "
        "vacinas, dispensação pela farmácia com baixa no estoque."))
    h.append(li(
        "<b>Internação</b> — a internação <b>ocupa o leito na mesma transação</b> em "
        "que é criada, e a alta manda o leito para higienização, nunca direto para "
        "livre. Cobre evolução de enfermagem, prescrição hospitalar com registro de "
        "administração, centro cirúrgico e encaminhamentos."))
    h.append(li(
        "<b>Alta e faturamento</b> — sumário de alta em PDF e produção lançada em "
        "AIH/APAC, com apoio da tabela SIGTAP."))
    h.append(p(
        "Atravessando o percurso, três comportamentos que o sistema executa sem "
        "depender de o profissional lembrar:", sub))
    h.append(li(
        "<b>Notificação compulsória automática</b> — ao lançar no prontuário um CID-10 "
        "de notificação obrigatória, o sistema gera a ficha SINAN sozinho e a "
        "enfileira na vigilância. Ninguém precisa saber de cor quais agravos são "
        "notificáveis."))
    h.append(li(
        "<b>Índice mestre de pacientes</b> — a mesma pessoa cadastrada em municípios "
        "diferentes é reconciliada por chave de bloqueio e pontuação de similaridade. "
        "<b>Nada é unificado automaticamente</b>, nem com pontuação máxima: unir dois "
        "pacientes errados mistura o histórico clínico de duas pessoas, e isso não tem "
        "desfazer bom. A tela mostra os dois cadastros lado a lado e a decisão é "
        "humana."))
    h.append(li(
        "<b>Portal do cidadão</b> — o paciente consulta o próprio histórico e a trilha "
        "de quem acessou o prontuário dele."))

    # ── 5 ──────────────────────────────────────────────────────────────────
    h.append(p("Módulos", secao))
    h.append(tabela(
        ["Área", "Módulos"],
        [["Atendimento",
          "Pacientes · Prontuário (SOAP) · Triagem (Manchester) · Atendimentos · "
          "Pronto-Socorro · Portal do Cidadão · Prescrição"],
         ["Assistência hospitalar",
          "Internação · Leitos e setores · Centro cirúrgico · Encaminhamentos · "
          "Agenda · Agendamentos"],
         ["Apoio diagnóstico",
          "Exames · Catálogo de exames · Vacinas · Catálogo de vacinas · Farmácia · Estoque"],
         ["Vigilância e regulação",
          "Vigilância (SINAN) · Regulação de vagas · Epidemiologia · Integração RNDS (FHIR R4)"],
         ["Gestão",
          "Relatórios · Relatórios hospitalares · Faturamento AIH/APAC · Importação e "
          "exportação · Tabelas oficiais"],
         ["Plataforma",
          "Autenticação com MFA · Login gov.br (OIDC) · Auditoria encadeada · Unidades · "
          "Usuários · Configurações · Backup · Documentos assinados"]],
        [3.6 * cm, 13.8 * cm]))

    # ── 6 ──────────────────────────────────────────────────────────────────
    h.append(p("Arquitetura", secao))
    h.append(p(
        "<b>Backend</b> Python 3.11 · Flask 3 · SQLAlchemy · Alembic · Flask-Login · "
        "CSRF em todo formulário · pyotp (TOTP) · ReportLab (PDF). &nbsp;&nbsp;"
        "<b>Banco</b> PostgreSQL em produção, SQLite no desenvolvimento e no CI. "
        "&nbsp;&nbsp;<b>Frontend</b> Jinja2 e CSS puro, <b>sem etapa de build e sem CDN</b> — "
        "a aplicação precisa funcionar em rede restrita de unidade de saúde. "
        "&nbsp;&nbsp;<b>Deploy</b> Gunicorn."))
    h.append(p(
        "Cada controle tem uma camada onde é aplicado, e a escolha dessa camada é a "
        "decisão de projeto. O percurso de uma requisição torna isso concreto:", sub))
    passos = [
        "A sessão é validada e o usuário identificado.",
        "O <b>escopo territorial</b> do usuário é resolvido <b>uma única vez por "
        "requisição</b>, antes de qualquer acesso a dados.",
        "O decorador de autorização confere se o perfil possui a permissão nomeada "
        "que a rota exige; sem ela, a requisição é rejeitada ali.",
        "Ao iniciar <b>cada transação</b>, o escopo é publicado na sessão do "
        "PostgreSQL com validade local à transação.",
        "As consultas executam. Além do filtro da aplicação, a política de RLS "
        "restringe as linhas que o banco devolve.",
        "Mutações gravam o evento de auditoria <b>na mesma transação</b> da escrita: "
        "ou as duas persistem, ou nenhuma persiste.",
    ]
    for n, passo in enumerate(passos, start=1):
        h.append(Paragraph(passo, item, bulletText="%d." % n))
    h.append(p(
        "Os passos 2 e 4 são separados por necessidade, e não por estilo: ler a "
        "identidade do usuário dispara consulta ao banco, que abre transação, que "
        "acionaria de novo o mesmo gatilho — recursão. Resolver o escopo uma vez e "
        "publicá-lo a cada transação é consequência direta disso.", corpo_pequeno))

    # ── 7 ──────────────────────────────────────────────────────────────────
    h.append(KeepTogether([
        p("Os controles, e o que cada um garante", secao),
        p("Isolamento entre unidades (Row-Level Security)", sub),
        p(
        "23 tabelas carregam política do próprio PostgreSQL, com <b>FORCE</b> — sem ele "
        "o dono da tabela ignoraria a política, e a aplicação <i>é</i> a dona. A lista "
        "não é mantida à mão: deriva do <i>metadata</i> do ORM, alcançando toda tabela "
        "que tenha a coluna de unidade. <b>Falha fechada</b>: sem escopo definido, nada "
        "é liberado — aplicação vazia é defeito óbvio; aplicação mostrando o país "
        "inteiro é incidente que ninguém percebe. As tabelas que ficam de fora "
        "<b>precisam de razão escrita</b>, e um teste confere isso nos dois sentidos.")]))

    h.append(p("Controle de acesso (RBAC)", sub))
    h.append(p(
        "27 permissões nomeadas no formato <font face=\"Courier\">recurso:ação</font>, "
        "distribuídas em 7 perfis, <b>ortogonais ao escopo territorial</b>: a permissão "
        "diz <i>o que</i> se pode fazer; o escopo diz <i>sobre quais registros</i>. O "
        "backend é a autoridade — o template apenas espelha a mesma decisão para "
        "esconder o controle. Esconder botão não protege nada."))

    h.append(p("Auditoria encadeada por hash", sub))
    h.append(p(
        "Cada evento carrega o hash do anterior: alterar ou remover uma linha do meio "
        "rompe a cadeia, e a verificação aponta onde. A tabela pertence a um papel "
        "próprio, e a aplicação não tem UPDATE nem DELETE nela."))
    h.append(p(
        "O limite é declarado em vez de omitido: <b>truncar o FIM da trilha não rompe "
        "elo nenhum</b> — os elos que sobram seguem consistentes, e nada na tabela diz "
        "que ela já foi maior. Por isso existe um <b>journal de âncoras</b>, também "
        "encadeado, com retratos periódicos da trilha. Guardada <b>uma linha qualquer</b> "
        "fora do servidor, todo o prefixo até ela pode ser validado — a custódia deixa "
        "de exigir disciplina contínua e passa a exigir um gesto único."))

    h.append(p("Continuidade", sub))
    h.append(p(
        "O comando de validação <b>restaura</b> a cópia num schema temporário e compara "
        "as contagens com a origem, saindo com erro se divergirem. Cópias antigas são "
        "expurgadas por data de modificação — e não por nome, que ordena bem por "
        "acaso até alguém renomear um arquivo à mão."))

    h.append(p("LGPD e proteção do titular", sub))
    h.append(p(
        "A base legal é registrada <b>por finalidade</b>, e a tela distingue o que se "
        "apoia em <b>consentimento</b> (pesquisa, contato, compartilhamento) do que se "
        "apoia na <b>tutela da saúde</b> do art. 11, II, “f”: assistência não depende de "
        "consentimento, e só o que depende dele é revogável. Há trilha de “quem acessou "
        "meu prontuário” e exportação auditada. O acesso tem verificação em duas etapas "
        "(TOTP) — o segredo só é gravado depois que o usuário prova um código válido, "
        "de modo que ninguém se tranca fora da própria conta — e login federado gov.br."))

    h.append(p("Documentos verificáveis", sub))
    h.append(p(
        "Todo PDF emitido (receituário, atestado, encaminhamento, sumário de alta) "
        "recebe um código impresso no rodapé e a impressão digital SHA-256 do arquivo "
        "produzido, conferíveis publicamente <b>sem precisar de conta</b>."))

    # ── 8 ──────────────────────────────────────────────────────────────────
    h.append(p("Terminologias oficiais e interoperabilidade", secao))
    h.append(p(
        "As terminologias não são listas soltas: alimentam os campos de preenchimento "
        "assistido dos formulários, com busca por código (prefixo) ou por descrição "
        "(sem acento). São <b>CID-10</b> para diagnóstico, <b>RENAME</b> para "
        "medicamentos, <b>CBO</b> para ocupação, <b>SIGTAP</b> para procedimento e "
        "faturamento, e <b>CNES</b> para estabelecimento — as mesmas que o SUS usa, de "
        "modo que o dado sai do sistema no vocabulário em que é esperado."))
    h.append(p(
        "O envio à <b>Rede Nacional de Dados em Saúde</b> segue FHIR R4 "
        "(<font face=\"Courier\">Patient</font>, "
        "<font face=\"Courier\">Encounter</font>, "
        "<font face=\"Courier\">Observation</font>). A tela <b>enfileira</b>; quem "
        "envia é um drenador separado — sem isso, uma indisponibilidade momentânea da "
        "RNDS viraria registro clínico perdido. A fila tem recuo exponencial, e "
        "distingue erro <b>transitório</b>, que reagenda, de erro de <b>validação</b>, "
        "que encerra o envio: retentar o mesmo conteúdo daria o mesmo resultado. Cada "
        "envio carrega uma chave de idempotência derivada do conteúdo, que impede "
        "duplicata quando a resposta anterior se perde."))

    # ── 9 ──────────────────────────────────────────────────────────────────
    h.append(p("Posição diante dos dados nacionais do SUS", secao))
    h.append(p(
        "Quanto aos sistemas nacionais de informação, este sistema está do lado de "
        "<b>quem produz o dado</b>, e não de quem o consulta depois de consolidado. "
        "A AIH e a APAC que ele emite são a matéria-prima do SIH e do SIA — a ponto de "
        "o arquivo central do SIHSUS no portal do DATASUS se chamar literalmente "
        "<b>RD, AIH Reduzida</b>, e o do SIASUS, <b>PA, Produção Ambulatorial</b>."))
    h.append(tabela(
        ["O que o sistema registra", "Para onde isso desagua nacionalmente"],
        [["AIH — Autorização de Internação Hospitalar",
          "SIHSUS, arquivo <font face=\"Courier\">RD</font>"],
         ["APAC e produção ambulatorial",
          "SIASUS, arquivo <font face=\"Courier\">PA</font>"],
         ["Notificação compulsória", "SINAN"],
         ["Registro clínico em FHIR R4", "RNDS — envio pela fila descrita acima"],
         ["Município por código IBGE",
          "Chave de agregação comum a CNES, SIA/SIH e SINAN"]],
        [8.0 * cm, 9.4 * cm]))
    h.append(p(
        "O caminho inverso — <b>consumir</b> os dados públicos já consolidados para "
        "comparar o desempenho da unidade com o do município — foi <b>levantado e não "
        "implementado</b>, e é registrado aqui como posição, não como recurso. O "
        "levantamento está em "
        "<font face=\"Courier\">docs/datasus_levantamento.md</font> e apurou, nas "
        "fontes oficiais, que o portal de transferência publica <b>18 fontes em 167 "
        "tipos de arquivo</b>, com séries desde 1979, no formato <b>.DBC</b> — um DBF "
        "comprimido com o algoritmo <i>implode</i> da PKWare, que nenhuma biblioteca "
        "padrão lê. Apurou também que a função já existe em ferramenta oficial: o "
        "<b>TabWin</b>, do próprio DATASUS, tabula, calcula indicadores e desenha "
        "mapas — o que uma implementação nova precisaria superar não é a função, e sim "
        "a forma de entrega, já que o TabWin é executável Windows de instalação "
        "manual."))
    h.append(p(
        "Um detalhe do levantamento decide o desenho de qualquer trabalho futuro nessa "
        "direção: a base populacional do IBGE é servida pelo mesmo portal, e sem ela "
        "não há indicador. Contagem de óbitos é contagem; óbito por cem mil habitantes "
        "é indicador, e a diferença entre os dois é o denominador."))

    # ── 10 ─────────────────────────────────────────────────────────────────
    h.append(p("Interface", secao))
    h.append(p(
        "Padrão Digital de Governo (<b>DSGov / gov.br</b>): barra institucional, azul "
        "<font face=\"Courier\">#1351B4</font>, amarelo "
        "<font face=\"Courier\">#FFCD07</font>, barra lateral com grupos colapsáveis "
        "filtrada pelas permissões do usuário. Os tokens de cor vivem num arquivo só e "
        "são o <b>ponto único de re-skin</b> — nenhum componente fixa cor, e isso "
        "inclui as cores de estado clínico e as da classificação Manchester."))
    h.append(p(
        "<b>Tema claro e escuro</b>, aplicado antes da primeira pintura para não piscar "
        "na navegação. Os tons médios e fortes não mudam entre os temas: as cores "
        "oficiais Manchester e os botões de ação destrutiva continuam idênticos, porque "
        "ali a cor carrega significado clínico e não estética. <b>Acessibilidade</b> "
        "(eMAG / WCAG 2.1 AA): atalho para o conteúdo, foco visível em todo controle, "
        "contraste verificado nos dois temas e VLibras."))

    # ── 11 ─────────────────────────────────────────────────────────────────
    h.append(KeepTogether([
        p("Operação", secao),
        tabela(
        ["Comando", "O que faz"],
        [["<font face=\"Courier\">flask hardening-check</font>",
          "Confronta o banco com o metadata e verifica o que a aplicação <b>não</b> "
          "garante sozinha. Sai com erro se falhar."],
         ["<font face=\"Courier\">flask backup-validar</font>",
          "Restaura a cópia num schema temporário e compara as contagens com a origem."],
         ["<font face=\"Courier\">flask auditoria-ancora</font>",
          "Grava e confere os retratos da trilha de auditoria; valida o prefixo a partir "
          "de uma âncora guardada fora do servidor."],
         ["<font face=\"Courier\">flask pacientes-deduplicar</font>",
          "Varre e enfileira candidatos a duplicata. <b>Não unifica nada</b> — a decisão "
          "é humana."],
         ["<font face=\"Courier\">flask rnds-processar</font>",
          "Drena a fila de envios à RNDS, com recuo exponencial e idempotência por "
          "hash do conteúdo."],
         ["<font face=\"Courier\">flask municipios-importar</font>",
          "Carrega a tabela territorial do IBGE, recusando linha cujo código não "
          "corresponda à UF declarada."]],
        [5.3 * cm, 12.1 * cm])]))

    # ── 12 ─────────────────────────────────────────────────────────────────
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
        "<b>O envio à RNDS é simulado</b> enquanto não houver certificado ICP-Brasil e "
        "credenciais do DATASUS. Está isolado numa única função, os protocolos saem "
        "marcados como simulados e a tela avisa — nada sai da máquina."))
    h.append(li(
        "<b>O sistema não consome os dados públicos do DATASUS.</b> A seção anterior "
        "descreve o levantamento dessas fontes e a posição do sistema diante delas; "
        "não há importação, indicador comparativo nem relatório a partir de base "
        "pública, e a incorporação consta de trabalhos futuros na monografia."))
    h.append(li(
        "<b>As cópias de segurança residem no mesmo servidor que o banco</b>: a rotação "
        "existe, a custódia externa não."))
    h.append(li(
        "<b>O sistema não foi usado em atendimento real.</b> Roda com dados de "
        "demonstração; não há base clínica de produção, e nenhum número deste "
        "documento descreve uso assistencial."))

    h.append(Spacer(1, 0.4 * cm))
    h.append(p(
        "Documentação completa em <font face=\"Courier\">docs/TCC.md</font>. Código sob "
        "licença MIT.", legenda))
    return h


if __name__ == "__main__":
    montar(historia())
    print("gerado:  %s" % SAIDA)
    print("tamanho: %s bytes" % format(SAIDA.stat().st_size, ","))
