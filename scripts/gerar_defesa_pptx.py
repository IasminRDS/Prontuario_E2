# -*- coding: utf-8 -*-
"""Gera `docs/defesa_slides.pptx` a partir de `docs/defesa_roteiro.md`.

Uma fonte só para os dois artefatos da defesa. O roteiro em markdown já separa,
por slide, **o que aparece** (rubrica "Visual") do **que se fala** (o bloco de
citação). Este gerador aproveita exatamente essa separação:

- a fala vira **nota do apresentador**, que é onde ela serve — no modo
  apresentador, e não projetada na parede;
- o corpo do slide é escrito em `CONTEUDO`, aqui neste arquivo, no formato do
  modelo indicado: um parágrafo denso por slide, e tabela onde o dado é
  tabular.

A densidade só é sustentável porque a fala está nas notas: o parágrafo
projetado é o resumo que a plateia lê, não o texto que a apresentadora recita.

A conferência de que nada estoura o rodapé é feita renderizando o `.pptx` em
PDF e medindo a posição do texto mais baixo de cada página — arranjo de caixa
de texto não se confere por leitura.

Formato seguindo o modelo indicado: 16:9, título no alto, divisores de seção
entre os atos, numeração no rodapé e referências ao final.

Uso:
    python scripts/gerar_defesa_pptx.py
"""
import pathlib
import re
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ENTRADA = RAIZ / "docs" / "defesa_roteiro.md"
SAIDA = RAIZ / "docs" / "defesa_slides.pptx"

# 16:9 widescreen, como o modelo (960 x 540 pt).
LARGURA = Inches(13.333)
ALTURA = Inches(7.5)

FONTE = "Calibri"
AZUL = RGBColor(0x13, 0x51, 0xB4)      # azul institucional gov.br, o do sistema
AZUL_ESCURO = RGBColor(0x0B, 0x2E, 0x69)
AMARELO = RGBColor(0xFF, 0xCD, 0x07)   # o outro token do design system
GRAFITE = RGBColor(0x1C, 0x1C, 0x1C)
CINZA = RGBColor(0x5A, 0x5A, 0x5A)
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)

# --- dados da capa. Os marcadores seguem a convenção da monografia. ---------
TITULO = ("Construção de um prontuário eletrônico multi-tenant")
SUBTITULO = ("avaliação empírica de controles de segurança, "
             "isolamento de dados e auditoria")
INSTITUICAO = "Instituto Federal Baiano — Campus Bom Jesus da Lapa"
CURSO = "Curso Superior de Tecnologia em Gestão da Tecnologia da Informação"
AUTORA = "Iasmin Ribeiro de Souza"
ORIENTACAO = "Orientação: ...."
LOCAL_ANO = "Bom Jesus da Lapa, ...."

REFERENCIAS = [
    "CELUPPI, I. C. et al. Dez anos do Prontuário Eletrônico do Cidadão e-SUS "
    "APS. Revista de Saúde Pública, v. 58, 2024.",
    "CHONG, F.; CARRARO, G.; WOLTER, R. Multi-tenant data architecture. "
    "Microsoft Corporation, 2006.",
    "ISO/IEC 27000:2018 — Information security management systems: overview "
    "and vocabulary.",
    "KABBEDIJK, J. et al. Defining multi-tenancy: a systematic mapping study. "
    "Journal of Systems and Software, v. 100, 2015.",
    "KENT, K.; SOUPPAYA, M. Guide to computer security log management. NIST "
    "SP 800-92, 2006.",
    "SALTZER, J. H.; SCHROEDER, M. D. The protection of information in "
    "computer systems. Proceedings of the IEEE, v. 63, n. 9, 1975.",
    "VAN GREMBERGEN, W.; DE HAES, S.; GULDENTOPS, E. Structures, processes and "
    "relational mechanisms for IT governance. Idea Group, 2004.",
    "ISACA. COBIT 2019 framework. 2018.  ·  BRASIL. Lei nº 13.709/2018 (LGPD).",
]


# --------------------------------------------------------------------------
# O QUE APARECE NO SLIDE
#
# A rubrica "Visual" do roteiro descreve o que DESENHAR ("um mapa mental
# simples", "a figura de camadas") — é especificação para quem monta, e não
# texto projetável. Gerar o slide a partir dela produzia slides que diziam
# "Um mapa mental simples: ...".
#
# Então o corpo é escrito aqui, implementando aquela especificação. A FALA
# continua vindo do roteiro, porque ali ela já é texto final. Uma fonte para
# cada coisa, e nenhuma das duas inventada.
#
# ("d", texto) marca destaque: a frase-âncora do slide, maior e em azul.
# --------------------------------------------------------------------------
CONTEUDO = {
 2: [("p", "O prontuário saiu do papel para sistemas que concentram, num único "
      "repositório, identificação civil, histórico clínico, prescrições, exames "
      "e internações. No SUS essa concentração ocorre em escala federativa: a "
      "mesma pessoa é atendida em municípios distintos, por unidades "
      "administrativamente independentes. E a escala está medida — Celuppi et "
      "al. (2024) registram que a adesão ao Prontuário Eletrônico do Cidadão na "
      "atenção primária passou de 8.930 unidades em 2017 para 26.091 em 2022."),
     ("d", "Ampliar o acesso melhora o cuidado; restringi-lo protege o titular. "
      "Onde essa fronteira é traçada é decisão de governança — e a arquitetura "
      "do sistema é o instrumento que a executa.")],

 3: [("p", "Em arquitetura multi-tenant, o isolamento costuma ser implementado "
      "por filtros adicionados às consultas, e passa a depender da disciplina de "
      "quem escreve cada uma. Uma consulta nova que esqueça o filtro expõe dados "
      "de outra unidade sem gerar erro, sem alerta e sem sinal perceptível ao "
      "usuário: o incidente não se manifesta como falha, e sim como "
      "funcionamento normal com dados a mais."),
     ("p", "A segregação, porém, não pode ser total — cadastro de paciente é "
      "nacional. Soma-se a isso o art. 37 da LGPD, que exige registro das "
      "operações de tratamento, e a constatação de que rotina de backup nunca "
      "restaurada não é garantia de continuidade: é a suposição de uma "
      "garantia.")],

 4: [("p", "O objetivo geral foi construir um sistema de prontuário eletrônico "
      "multi-tenant e verificar empiricamente seus controles, analisando como "
      "isolamento, controle de acesso, auditoria e continuidade contribuem para "
      "a governança de TI numa organização de saúde."),
     ("b", "Isolamento aplicado na camada de banco, e não só na aplicação"),
     ("b", "Controle de acesso orientado pelo menor privilégio"),
     ("b", "Auditoria com propriedades de detecção de adulteração"),
     ("b", "Backup com validação automatizada de restauração"),
     ("b", "Usabilidade avaliada por inspeção heurística"),
     ("b", "Análise crítica dos limites dos próprios controles implementados"),
     ("d", "A avaliação crítica é resultado do trabalho, e não apenas seu "
      "método.")],

 5: [("p", "Multi-tenancy não tem definição uniforme: Kabbedijk et al. (2015) "
      "analisaram 761 artigos e encontraram 43 definições distintas. Adotou-se a "
      "que os autores consolidam, na qual múltiplos clientes compartilham de "
      "forma transparente os recursos do sistema — e é a palavra transparente "
      "que converte o isolamento de dado em requisito, e não em característica "
      "desejável."),
     ("p", "A ISO/IEC 27000:2018 define segurança da informação como preservação "
      "de confidencialidade, integridade e disponibilidade, mencionando em nota "
      "outras propriedades. Autenticidade e não repúdio foram trazidos ao "
      "primeiro plano por decisão declarada: em prontuário, a autoria do "
      "registro clínico é objeto de regulação, não atributo acessório.")],

 6: [("p", "A aplicação é Flask com Jinja2 e SQLAlchemy, sobre PostgreSQL, "
      "organizada em módulos por domínio funcional. Cada controle tem uma camada "
      "onde é aplicado, e a escolha dessa camada é a decisão de projeto: o RBAC "
      "atua na aplicação, o escopo territorial é reposto pelo ORM a cada "
      "transação, e as políticas de isolamento vivem dentro do banco. Os valores "
      "abaixo saem de contagem automatizada sobre o código, e não de "
      "estimativa."),
     ("t", ["Elemento", "Quantidade"],
      [["Módulos funcionais", "45"],
       ["Rotas expostas", "214 — 153 aceitam GET; 105, mutação"],
       ["Tabelas no modelo de dados", "42, com 538 colunas"],
       ["Telas e migrações", "117 telas · 16 migrações versionadas"],
       ["Casos de teste", "663, em 424 funções e 49 arquivos"]])],

 7: [("p", "Chong, Carraro e Wolter (2006) descrevem três estratégias de "
      "isolamento, dispostas num contínuo entre isolamento e compartilhamento. "
      "A escolha foi avaliada por grau de isolamento, custo operacional, "
      "viabilidade de consulta entre inquilinos e adequação ao cuidado "
      "longitudinal em rede pública de saúde."),
     ("t", ["Estratégia", "Isolamento", "Consulta entre unidades"],
      [["Banco por inquilino", "Máximo", "Muito custosa"],
       ["Esquema por inquilino", "Alto", "Custosa"],
       ["Coluna discriminadora — ADOTADA", "Médio", "Natural"]]),
     ("p", "A fragilidade é depender da aplicação para aplicar o filtro; por "
      "isso existe a segunda camada — o Row-Level Security, hoje sobre 23 "
      "tabelas. Quatro condições decidem se é proteção ou teatro: FORCE, falha "
      "fechada, escopo por transação e cobertura efetiva.")],

 8: [("p", "O controle de acesso é por permissão nomeada, no formato recurso e "
      "ação — 27 permissões distribuídas em 7 perfis —, e é ortogonal ao escopo "
      "territorial: a permissão diz o que se pode fazer, o escopo diz sobre "
      "quais registros. A auditoria registra leituras e escritas, encadeadas por "
      "hash, em tabela que pertence a papel de banco distinto do usado pela "
      "aplicação."),
     ("p", "Quanto à LGPD, o sistema registra base legal por finalidade, e não "
      "trata tudo como consentimento. O tratamento para tutela da saúde tem base "
      "própria no art. 11, II, “f”: condicioná-lo a consentimento implicaria que "
      "a recusa do titular impede o atendimento. Consentimento é a base de "
      "finalidades acessórias, e só o que nele se apoia é revogável.")],

 9: [("d", "A inspeção de código é insuficiente para verificar controles de "
      "segurança."),
     ("p", "Em lugar dela, instrumentação e exercício efetivo do sistema. Foram "
      "construídos verificadores que instrumentam o motor de telas para "
      "registrar acesso a variável inexistente e renderizam todas as páginas com "
      "dados reais; que confrontam os campos que cada formulário envia com os "
      "que a rota lê; que conciliam telas e rotas nos dois sentidos; que geram "
      "os documentos e conferem o que saiu; e que consultam o catálogo do "
      "PostgreSQL para ver se as políticas estão ativas."),
     ("p", "São 663 casos de teste, em 424 funções e 49 arquivos, executados "
      "integralmente sobre os dois bancos do projeto. A medição de cobertura de "
      "execução entrou como mapa, e não como meta: a lista dos trechos que "
      "nenhum teste percorre diz onde nenhuma evidência foi produzida.")],

 10: [("d", "Dezenove achados. Nenhum produz mensagem de erro."),
      ("p", "O sistema não interrompe nem registra exceção: uma consulta "
       "retorna menos linhas do que deveria, um campo é descartado, uma trilha "
       "deixa de crescer. É a categoria que o teste convencional não alcança — "
       "ele verifica que o esperado aconteceu, e aqui falta a expectativa. Em "
       "conjunto, os achados agrupam-se em cinco mecanismos."),
      ("t", ["", "Mecanismo"],
       [["I", "A declaração que deixou de ser verdadeira"],
        ["II", "A regra escrita mais de uma vez"],
        ["III", "O caminho que não existe"],
        ["IV", "O efeito que não ocorre"],
        ["V", "O próprio controle como origem do defeito"]])],

 11: [("p", "Cada mecanismo admite uma verificação específica que o torna "
       "detectável por medição, e não por atenção. As cinco existem como casos "
       "permanentes da suíte."),
      ("t", ["Classe", "Verificação que a torna detectável"],
       [["I", "Confrontar a declaração com o estado real, não com outra declaração"],
        ["II", "Comparar as cópias no nível do efeito: perfis, e não nomes"],
        ["III", "Alcançabilidade nos dois sentidos: tela sem rota, rota sem tela"],
        ["IV", "Medir o efeito, nunca a chamada"],
        ["V", "Verificar o verificador: introduzir o defeito e exigir reprovação"]]),
      ("d", "É a diferença entre haver corrigido dezenove defeitos e haver "
       "instalado cinco instrumentos que encontram a próxima ocorrência de cada "
       "um.")],

 12: [("p", "O isolamento percorreu três estados, e a sequência é o resultado "
       "mais instrutivo. No primeiro, dez tabelas estavam sob política e a "
       "documentação afirmava cobertura total. No segundo, passou a declarar "
       "honestamente que dez permaneciam fora, nomeando-as. No terceiro, oito "
       "dessas dez foram cobertas e as duas restantes passaram a exigir "
       "justificativa escrita e verificada — hoje são 23 tabelas."),
      ("t", ["Resultado", "Medida"],
       [["Isolamento", "10 → 15 → 23 tabelas sob política"],
        ["Desempenho", "185,9 ms → 0,96 ms (ordem de grandeza)"],
        ["Continuidade", "restauração conferida em 13 tabelas"],
        ["Configuração", "10 verificações: 9 aprovadas, 1 reprovada"]]),
      ("d", "Declarar honestamente uma lacuna é melhor que ocultá-la — e não é o "
       "mesmo que corrigi-la.")],

 13: [("p", "A documentação escrita durante a construção afirmava que as "
       "políticas cobriam toda tabela com escopo territorial. A verificação "
       "mostrou cinco tabelas clínicas centrais integralmente fora de qualquer "
       "política. O mecanismo estava correto; o alcance é que não era o "
       "anunciado — e a afirmação era literalmente verdadeira, porque cobria as "
       "tabelas que tinham a coluna."),
      ("p", "As rotas de leitura chamavam o registro de auditoria sem confirmar "
       "a transação, correto para escritas e inútil em leitura: o sistema "
       "aparentava auditar consultas e não as auditava."),
      ("d", "E o detector de variáveis ausentes era cego para o próprio defeito: "
       "corrigido, os achados passaram de dezenove para quarenta e seis. O "
       "defeito escondia a si mesmo.")],

 14: [("p", "As limitações são limites de método, e estão declaradas. A mais "
       "importante é conceitual: a ISO define não repúdio como a capacidade de "
       "provar a ocorrência de um evento, e o que o sistema oferece é detecção — "
       "adulteração se torna detectável, o que não é prova oponível ao próprio "
       "operador."),
      ("t", ["Limitação", "Natureza"],
       [["Não repúdio", "detectável, não irrefutável"],
        ["Âncora de auditoria", "a custódia é externa ao software"],
        ["Desempenho", "protocolo implementado; ambiente ainda sintético"],
        ["Usabilidade", "inspeção pela equipe, sem usuários finais"],
        ["Matriz de permissões", "não configurável por organização"]])],

 15: [("d", "Um controle de detecção produz duas informações: os achados, e a "
       "confiança de que não há mais nada. A primeira é verificável por "
       "inspeção. A segunda, não."),
      ("p", "Construir o sistema foi a condição, e não o resultado: foi o que "
       "permitiu abrir cada controle, instrumentá-lo e exercitá-lo por dentro. "
       "Há diferença substantiva entre implementar um controle e haver "
       "verificado que ele opera sobre a superfície que se pretende cobrir. E "
       "como o risco residual é aceito com base na segunda informação, ela "
       "precisa de evidência própria — obtida confrontando cada verificador com "
       "defeito conhecido por outra via.")],

 16: [("d", "A contribuição decorre da cobertura verificada do mecanismo, e não "
       "da sua existência."),
      ("p", "Quanto ao problema de pesquisa, a associação entre arquitetura "
       "multi-tenant e controles na camada de dados contribui para a "
       "confiabilidade e a proteção da informação, sob essa condição. Os "
       "objetivos específicos foram atendidos com as ressalvas registradas: o "
       "isolamento foi ampliado e quantificado, ainda que não integral; permissão "
       "e escopo foram distinguidos; a auditoria passou a registrar leituras, "
       "permanecendo a imutabilidade efetiva dependente de infraestrutura; a "
       "continuidade tem validação automatizada; e a usabilidade foi avaliada "
       "sem participação de usuários finais.")],

 17: [("b", "Matriz de permissões configurável por organização, com auditoria "
       "das próprias alterações de permissão"),
      ("b", "Avaliação de usabilidade com usuários dos perfis reais"),
      ("b", "Medição sob distribuição real de dados, e não sintética"),
      ("b", "Camada de serviço explícita, com autorização em ponto único"),
      ("b", "Ampliação da conformidade com o padrão FHIR"),
      ("b", "Custódia externa da âncora de auditoria, com emissão e verificação "
       "em papéis distintos"),
      ("d", "A custódia é decisão de governança, e nenhum código a resolve.")],
}

_NEGRITO = re.compile(r"\*\*([^*]+)\*\*")
_ITALICO = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")
_CODIGO = re.compile(r"`([^`]+)`")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def _limpar(texto):
    """Tira a marcação do markdown — o slide não a renderiza."""
    texto = _LINK.sub(r"\1", texto)
    texto = _NEGRITO.sub(r"\1", texto)
    texto = _CODIGO.sub(r"\1", texto)
    texto = _ITALICO.sub(r"\1", texto)
    return texto.replace("—", "—").strip()


# --------------------------------------------------------------------------
# Desenho
# --------------------------------------------------------------------------
def _fundo(slide, cor):
    fundo = slide.background.fill
    fundo.solid()
    fundo.fore_color.rgb = cor


def _caixa(slide, x, y, larg, alt):
    return slide.shapes.add_textbox(x, y, larg, alt)


def _escrever(quadro, texto, tamanho, cor=GRAFITE, negrito=False,
              alinhamento=PP_ALIGN.LEFT, espaco_depois=6, nivel=0):
    p = quadro.paragraphs[0] if not quadro.paragraphs[0].runs \
        and not quadro.paragraphs[0].text else quadro.add_paragraph()
    p.alignment = alinhamento
    p.level = nivel
    p.space_after = Pt(espaco_depois)
    run = p.add_run()
    run.text = texto
    run.font.size = Pt(tamanho)
    run.font.bold = negrito
    run.font.name = FONTE
    run.font.color.rgb = cor
    return p


def _faixa_titulo(slide, titulo):
    """Título no alto, com um filete amarelo abaixo — token do design system."""
    caixa = _caixa(slide, Inches(0.75), Inches(0.45), Inches(11.8), Inches(0.9))
    quadro = caixa.text_frame
    quadro.word_wrap = True
    _escrever(quadro, titulo, 28, AZUL_ESCURO, negrito=True)

    filete = slide.shapes.add_shape(1, Inches(0.75), Inches(1.42),
                                    Inches(1.6), Pt(4.5))
    filete.fill.solid()
    filete.fill.fore_color.rgb = AMARELO
    filete.line.fill.background()
    filete.shadow.inherit = False


def _rodape(slide, numero):
    caixa = _caixa(slide, Inches(12.3), Inches(6.85), Inches(0.8), Inches(0.4))
    _escrever(caixa.text_frame, str(numero), 12, CINZA,
              alinhamento=PP_ALIGN.RIGHT)


def _notas(slide, texto):
    if texto:
        slide.notes_slide.notes_text_frame.text = texto


# --------------------------------------------------------------------------
# Tipos de slide
# --------------------------------------------------------------------------
def capa(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fundo(slide, AZUL_ESCURO)

    barra = slide.shapes.add_shape(1, Inches(0.9), Inches(2.05),
                                   Inches(2.2), Pt(5))
    barra.fill.solid()
    barra.fill.fore_color.rgb = AMARELO
    barra.line.fill.background()
    barra.shadow.inherit = False

    caixa = _caixa(slide, Inches(0.9), Inches(2.35), Inches(11.5), Inches(2.2))
    quadro = caixa.text_frame
    quadro.word_wrap = True
    _escrever(quadro, TITULO, 34, BRANCO, negrito=True, espaco_depois=10)
    _escrever(quadro, SUBTITULO, 20, RGBColor(0xC8, 0xD8, 0xF5))

    caixa = _caixa(slide, Inches(0.9), Inches(5.15), Inches(11.5), Inches(1.9))
    quadro = caixa.text_frame
    quadro.word_wrap = True
    for texto, tamanho in ((INSTITUICAO, 14), (CURSO, 13), (AUTORA, 15),
                           (ORIENTACAO, 13), (LOCAL_ANO, 13)):
        _escrever(quadro, texto, tamanho,
                  BRANCO if texto == AUTORA else RGBColor(0xB9, 0xCA, 0xE8),
                  negrito=(texto == AUTORA), espaco_depois=3)
    return slide


def divisor(prs, titulo, subtitulo, numero):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _fundo(slide, AZUL)

    caixa = _caixa(slide, Inches(1.1), Inches(2.9), Inches(11.2), Inches(1.8))
    quadro = caixa.text_frame
    quadro.word_wrap = True
    _escrever(quadro, titulo, 40, BRANCO, negrito=True, espaco_depois=8)
    if subtitulo:
        _escrever(quadro, subtitulo, 18, RGBColor(0xD6, 0xE4, 0xFA))
    _rodape(slide, numero)
    return slide


def _tabela(slide, cabecalho, linhas, topo):
    """Tabela no formato do modelo: cabeçalho azul, corpo claro."""
    n_linhas, n_colunas = len(linhas) + 1, len(cabecalho)
    largura = Inches(11.5)
    altura = Inches(0.42) * n_linhas
    forma = slide.shapes.add_table(n_linhas, n_colunas, Inches(0.9), topo,
                                   largura, altura)
    tabela = forma.table

    # Primeira coluna estreita quando é só um rótulo curto (I, II, III…).
    if all(len(l[0]) <= 4 for l in linhas):
        tabela.columns[0].width = Inches(1.0)
        if n_colunas == 2:
            tabela.columns[1].width = largura - Inches(1.0)

    for j, texto in enumerate(cabecalho):
        celula = tabela.cell(0, j)
        celula.text = ""
        celula.fill.solid()
        celula.fill.fore_color.rgb = AZUL
        p = celula.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = texto
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.name = FONTE
        run.font.color.rgb = BRANCO
        celula.vertical_anchor = MSO_ANCHOR.MIDDLE

    for i, linha in enumerate(linhas, start=1):
        for j, texto in enumerate(linha):
            celula = tabela.cell(i, j)
            celula.text = ""
            celula.fill.solid()
            celula.fill.fore_color.rgb = (RGBColor(0xF4, 0xF7, 0xFC) if i % 2
                                          else RGBColor(0xFF, 0xFF, 0xFF))
            p = celula.text_frame.paragraphs[0]
            run = p.add_run()
            run.text = texto
            run.font.size = Pt(13.5)
            run.font.name = FONTE
            run.font.color.rgb = GRAFITE
            run.font.bold = j == 0 and len(texto) <= 4
            celula.vertical_anchor = MSO_ANCHOR.MIDDLE
    return altura


def conteudo(prs, titulo, itens, notas, numero):
    """Um slide no formato do modelo: prosa, tópicos e tabela.

    O corpo é denso de propósito — o modelo indicado apresenta um parágrafo
    por slide. A fala completa vai nas notas, o que impede que o parágrafo
    projetado vire leitura em voz alta.
    """
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _faixa_titulo(slide, titulo)

    topo = Inches(1.78)
    caixa = None
    quadro = None

    def _abrir_caixa(altura=Inches(1.0)):
        nonlocal caixa, quadro, topo
        caixa = _caixa(slide, Inches(0.9), topo, Inches(11.5), altura)
        quadro = caixa.text_frame
        quadro.word_wrap = True

    for item in itens:
        tipo = item["tipo"]

        if tipo == "t":
            if quadro is not None:
                topo += _altura_estimada(quadro) + Inches(0.12)
                quadro = None
            topo += _tabela(slide, item["cabecalho"], item["linhas"], topo)
            topo += Inches(0.22)
            continue

        if quadro is None:
            _abrir_caixa()

        if tipo == "d":
            _escrever(quadro, item["texto"], 19, AZUL_ESCURO, negrito=True,
                      espaco_depois=12, alinhamento=PP_ALIGN.LEFT)
        elif tipo == "b":
            _escrever(quadro, "•  " + item["texto"], 17, GRAFITE,
                      espaco_depois=6)
        else:
            _escrever(quadro, item["texto"], 18, GRAFITE, espaco_depois=12,
                      alinhamento=PP_ALIGN.JUSTIFY)

    _rodape(slide, numero)
    _notas(slide, notas)
    return slide


def _altura_estimada(quadro):
    """Aproxima a altura do texto já escrito, para posicionar a tabela.

    O PowerPoint só sabe a altura real ao renderizar; aqui basta uma
    estimativa por número de linhas, com ~95 caracteres por linha a 16pt.
    """
    linhas = 0
    for p in quadro.paragraphs:
        texto = "".join(r.text for r in p.runs)
        linhas += max(1, -(-len(texto) // 82)) + 0.35
    return Inches(0.34 * linhas)


def referencias(prs, numero):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _faixa_titulo(slide, "Referências")
    caixa = _caixa(slide, Inches(0.9), Inches(1.85), Inches(11.6), Inches(5.0))
    quadro = caixa.text_frame
    quadro.word_wrap = True
    for ref in REFERENCIAS:
        _escrever(quadro, ref, 13, GRAFITE, espaco_depois=9)
    _rodape(slide, numero)
    return slide


# --------------------------------------------------------------------------
# Leitura do roteiro
# --------------------------------------------------------------------------
def ler_roteiro():
    """Devolve a lista de slides: título, itens visuais e fala."""
    if not ENTRADA.is_file():
        sys.exit(f"não encontrei {ENTRADA}")

    linhas = ENTRADA.read_text(encoding="utf-8").splitlines()
    slides, atual, secao = [], None, None
    fala, dentro_da_fala = [], False

    for linha in linhas:
        texto = linha.strip()

        m = re.match(r"^## Slide (\d+) — (.+)$", texto)
        if m:
            if atual:
                atual["fala"] = " ".join(fala).strip()
                slides.append(atual)
            atual = {"numero": int(m.group(1)), "titulo": m.group(2),
                     "itens": [], "fala": ""}
            fala, dentro_da_fala, secao = [], False, None
            continue

        if atual is None:
            continue

        # a fala é o primeiro bloco de citação depois da rubrica "Fala"
        if texto.startswith(">"):
            if secao == "fala":
                dentro_da_fala = True
                fala.append(texto.lstrip(">").strip())
            elif secao == "visual":
                # citação dentro do Visual é conteúdo do slide (o slide 15)
                atual["itens"].append(
                    {"texto": _limpar(texto.lstrip(">").strip()),
                     "destaque": True})
            continue

        m = re.match(r"^\*\*([^*]+)\*\*\s*(?:[—-].*)?$", texto)
        if m:
            rotulo = m.group(1).lower()
            if rotulo.startswith("visual"):
                secao = "visual"
            elif rotulo.startswith("fala"):
                secao = "fala"
            elif rotulo.startswith(("objetivo", "perguntas")):
                secao = None
            else:
                # frase em negrito dentro do Visual: manchete do slide
                if secao == "visual":
                    atual["itens"].append(
                        {"texto": _limpar(m.group(1)), "destaque": True})
            continue

        if secao == "visual":
            m = re.match(r"^(\s*)- (.+)$", linha.rstrip())
            if m:
                atual["itens"].append(
                    {"texto": _limpar(m.group(2)),
                     "nivel": len(m.group(1)) // 2})

    if atual:
        atual["fala"] = " ".join(fala).strip()
        slides.append(atual)
    return slides


# --------------------------------------------------------------------------
def gerar():
    slides = ler_roteiro()
    if not slides:
        sys.exit("nenhum slide lido do roteiro")

    prs = Presentation()
    prs.slide_width, prs.slide_height = LARGURA, ALTURA

    # Os divisores entram antes do primeiro slide de cada ato.
    ATOS = {
        2: ("O artefato", "O que foi construído, e com que controles"),
        9: ("O método", "Como os controles foram verificados — e o que apareceu"),
        14: ("O significado", "Por que isto é contribuição de governança"),
    }

    numero = 0
    capa(prs)

    for s in slides:
        if s["numero"] == 1:
            continue                      # a capa já foi desenhada
        if s["numero"] in ATOS:
            numero += 1
            titulo, sub = ATOS[s["numero"]]
            divisor(prs, titulo, sub, numero)
        if s["numero"] == 18:
            continue                      # encerramento vira a folha final
        numero += 1
        itens = []
        for entrada in CONTEUDO.get(s["numero"], []):
            if entrada[0] == "t":
                itens.append({"tipo": "t", "cabecalho": entrada[1],
                              "linhas": entrada[2]})
            else:
                itens.append({"tipo": entrada[0], "texto": entrada[1]})
        conteudo(prs, s["titulo"], itens, s["fala"], numero)

    numero += 1
    referencias(prs, numero)

    # folha final
    fim = prs.slides.add_slide(prs.slide_layouts[6])
    _fundo(fim, AZUL_ESCURO)
    caixa = _caixa(fim, Inches(1.1), Inches(3.0), Inches(11.2), Inches(1.6))
    quadro = caixa.text_frame
    quadro.word_wrap = True
    _escrever(quadro, "Obrigada.", 40, BRANCO, negrito=True, espaco_depois=10)
    _escrever(quadro, AUTORA, 18, RGBColor(0xC8, 0xD8, 0xF5))

    prs.save(SAIDA)
    # Conta o que FOI ESCRITO no arquivo, e não o que o roteiro trazia: a capa
    # e o encerramento não viram slide de conteúdo, então relatar 18 aqui seria
    # a ferramenta afirmando duas notas que ela não gravou.
    com_notas = sum(1 for s in prs.slides
                    if s.has_notes_slide
                    and s.notes_slide.notes_text_frame.text.strip())
    print(f"gerado:  {SAIDA}")
    print(f"tamanho: {SAIDA.stat().st_size:,} bytes")
    print(f"slides:  {len(prs.slides.__iter__.__self__._sldIdLst)} ao todo "
          f"(capa, 3 divisores, conteúdo, referências e encerramento)")
    print(f"notas:   {com_notas} slides com a fala nas notas do apresentador")
    print("A fala NÃO vai projetada: está nas notas, para o modo apresentador.")


if __name__ == "__main__":
    gerar()
