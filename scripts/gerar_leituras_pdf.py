# -*- coding: utf-8 -*-
"""Gera `docs/LEITURAS.pdf` — artigos e softwares de referência do projeto.

Documento de trabalho, não parte da monografia. Reúne apenas duas coisas:
**artigos e pesquisas** com relação direta com o sistema, e **softwares
comparáveis** — aqueles que a banca pode perguntar por que não foram usados.

**Todo item foi aberto na fonte do editor ou do projeto.** A citação completa —
autores, periódico, volume, DOI — foi lida no próprio artigo, e não copiada de
agregador ou de índice. Referência tirada de agregador entra na monografia com
data errada ou autor faltando, e a banca encontra: aconteceu de um agregador
anunciar o Decreto 12.560/2025 com a data de outra norma. O Google Acadêmico
ficou de fora porque bloqueia acesso automatizado com CAPTCHA — e, de todo modo,
ele é índice, não editor: a procedência forte é a página do periódico.

O que foi descartado, e por quê:

- itens que não puderam ser abertos na fonte (um artigo de controle de acesso em
  periódico que devolveu 403 e não está indexado no Europe PMC);
- as normas e a especificação da RNDS, que não são artigo nem software e cabem
  em `docs/sbis_gap_analysis.md` e no próprio código;
- listas curadas de projetos, que são diretório e não software comparável.

O conteúdo mora aqui, e não num markdown separado, pela mesma razão que o do
`gerar_resumo_pdf.py`: duas cópias divergem, e a que ninguém regenera mente.

Uso:
    python scripts/gerar_leituras_pdf.py
"""
import pathlib

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Frame, HRFlowable, KeepTogether,
                                PageTemplate, Paragraph, Spacer)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "docs" / "LEITURAS.pdf"

DATA = "28 de agosto de 2026"

# Tokens do design system do próprio sistema (static/css/dsgov.css).
AZUL = colors.HexColor("#1351B4")
AZUL_ESCURO = colors.HexColor("#0B2E69")
AMARELO = colors.HexColor("#FFCD07")
GRAFITE = colors.HexColor("#1C1C1C")
CINZA = colors.HexColor("#5A5A5A")
CINZA_LINHA = colors.HexColor("#D8DDE6")

MARGEM = 2.1 * cm

# ---------------------------------------------------------------- estilos
# A hierarquia é de TAMANHO, e não só de peso: 20 / 13.5 / 9.6 / 8.2. Título de
# seção e título de item precisam ser distinguíveis de relance, sem ler.
h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, leading=24,
                    textColor=AZUL, spaceBefore=6, spaceAfter=1)
h1_nota = ParagraphStyle("h1_nota", fontName="Helvetica", fontSize=9.6,
                         leading=13.4, textColor=CINZA, spaceAfter=13)
h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13.5, leading=17,
                    textColor=AZUL_ESCURO, spaceBefore=2, spaceAfter=4)
citacao = ParagraphStyle("citacao", fontName="Helvetica-Oblique", fontSize=8.4,
                         leading=11.6, textColor=CINZA, spaceAfter=3)
link = ParagraphStyle("link", fontName="Courier", fontSize=7.6, leading=10,
                      textColor=AZUL, spaceAfter=7)
corpo = ParagraphStyle("corpo", fontName="Helvetica", fontSize=9.6, leading=14,
                       alignment=TA_JUSTIFY, textColor=GRAFITE, spaceAfter=7)
projeto = ParagraphStyle("projeto", parent=corpo, fontSize=9.4, leading=13.6,
                         leftIndent=0.55 * cm, borderPadding=0, spaceAfter=2,
                         textColor=colors.HexColor("#12324F"))
intro = ParagraphStyle("intro", parent=corpo, fontSize=10, leading=14.6,
                       spaceAfter=9)
rodape_nota = ParagraphStyle("rodape_nota", fontName="Helvetica-Oblique",
                             fontSize=8.2, leading=11.4, textColor=CINZA,
                             spaceBefore=6)


def entrada(titulo, ref, url, resumo, para_o_projeto, ultima=False):
    """Um item completo, mantido inteiro na mesma página."""
    blocos = [
        Paragraph(titulo, h2),
        Paragraph(ref, citacao),
        Paragraph(f'<link href="{url}">{url}</link>', link),
        Paragraph(resumo, corpo),
        Paragraph(f'<b>Para o projeto.</b> {para_o_projeto}', projeto),
    ]
    if not ultima:
        blocos += [Spacer(1, 11),
                   HRFlowable(width="100%", thickness=0.5, color=CINZA_LINHA),
                   Spacer(1, 13)]
    return KeepTogether(blocos)


def secao(titulo, nota):
    return [Spacer(1, 6), Paragraph(titulo, h1),
            HRFlowable(width="100%", thickness=2, color=AMARELO,
                       spaceBefore=3, spaceAfter=7),
            Paragraph(nota, h1_nota)]


# ---------------------------------------------------------------- conteúdo
def historia():
    h = []

    h.append(Paragraph(
        "<b>Todo item deste documento foi aberto na fonte.</b> A citação "
        "completa — autores, periódico, volume, DOI — foi lida na página do "
        "editor, não copiada de agregador. O Google Acadêmico ficou de fora "
        "porque bloqueia acesso automatizado com CAPTCHA e porque é índice, e "
        "não editor: a procedência forte é o periódico.", intro))
    h.append(Spacer(1, 2))

    # ============================================================= artigos
    h += secao(
        "Artigos e pesquisas",
        "Oito trabalhos, todos com DOI conferido. Os três primeiros são "
        "brasileiros e sustentam a motivação e o método; os cinco seguintes "
        "dão fundamento às escolhas técnicas.")

    h.append(entrada(
        "Dez anos do Prontuário Eletrônico do Cidadão e-SUS APS",
        "Celuppi IC, Mohr ETB, Felisberto M, Rodrigues TS, Hammes JF, Cunha CL, "
        "Wazlawick RS, Dalmarco EM. <i>Revista de Saúde Pública</i>, 2024;58:23. "
        "DOI 10.11606/s1518-8787.2024058005770",
        "https://doi.org/10.11606/s1518-8787.2024058005770",
        "Estudo descritivo da adoção do PEC nos municípios brasileiros entre "
        "2017 e 2022, somado à síntese da evolução técnica da estratégia e-SUS "
        "APS em dez anos. A adesão cresceu de <b>8.930 unidades básicas em 2017 "
        "para 26.091 em 2022</b>, e o PEC passou de terceira opção a quase 60% "
        "de todos os prontuários eletrônicos em uso na atenção primária. O "
        "crescimento foi maior no Nordeste (367,72%), seguido do Norte (256,10%) "
        "e do Sudeste (157,04%). No período, o banco migrou de H2 para "
        "PostgreSQL e Oracle, e entraram módulos de pré-natal, puericultura, "
        "odontograma e videochamada. Os autores concluem apontando três frentes "
        "pendentes: capacitação de usuários, ampliação da interoperabilidade com "
        "a RNDS e usabilidade.",
        "é a referência brasileira, revisada por pares e recente, que sustenta a "
        "motivação do trabalho com número medido em vez de impressão. O Nordeste "
        "ser o recorte de maior crescimento não é detalhe decorativo: é o "
        "contexto do projeto. E as três frentes que o artigo deixa em aberto são "
        "exatamente onde este sistema atua."))

    h.append(entrada(
        "Interoperabilidade em sistemas universais de saúde: a experiência "
        "brasileira integrando atenção primária e hospitalar",
        "Fernandez M, Pinto HA, Fernandes LMM, Oliveira JAS, Lima AMFS, Santana "
        "JSS, Chioro A. <i>Frontiers in Digital Health</i>, 2025;7:1622302. "
        "DOI 10.3389/fdgth.2025.1622302",
        "https://doi.org/10.3389/fdgth.2025.1622302",
        "Análise descritiva da primeira federação de dados entre duas "
        "plataformas de interoperabilidade no Brasil, no Recife, unindo a rede "
        "municipal de saúde à Ebserh. A integração alcança <b>202 serviços de "
        "atenção primária e 45 hospitais universitários federais</b>, com "
        "arquitetura em nuvem baseada em APIs, um <i>Master Patient Index</i> e "
        "conformidade com HL7-FHIR e openEHR. Os autores relatam melhora na "
        "coordenação do cuidado e na decisão clínica, e concluem que "
        "interoperabilidade efetiva exige compromisso político alinhado a "
        "capacidade técnica e institucional — o modelo seria replicável onde "
        "houver prontuário eletrônico e acordo de governança.",
        "é o artigo mais próximo do que este sistema faz, e o mais útil para a "
        "defesa: eles resolvem por <i>Master Patient Index</i> o mesmo problema "
        "que o comando <font face=\"Courier\">flask pacientes-deduplicar</font> "
        "resolve aqui. Poder dizer “é o mecanismo que o Recife adotou” é "
        "diferente de dizer “eu implementei uma deduplicação”."))

    h.append(entrada(
        "Construindo a Base Nacional de Saúde centrada no indivíduo: pareamento "
        "de registros administrativos e epidemiológicos, Brasil 2000-2015",
        "Guerra Junior AA, Pereira RG, Gurgel EI, Cherchiglia M, Dias LV, Ávila "
        "JD, Santos N, Reis A, Acurcio FA, Meira Junior W. <i>International "
        "Journal of Population Data Science</i>, 2018;3(1):446. "
        "DOI 10.23889/ijpds.v3i1.446",
        "https://doi.org/10.23889/ijpds.v3i1.446",
        "Integração de quatro sistemas nacionais — SIH (188,5 milhões de "
        "registros), SIA (869,7 milhões), SIM (16,6 milhões) e SINAN (11 "
        "milhões) — num total de <b>1,3 bilhão de registros sem identificador "
        "universal</b>. O método combina pareamento determinístico e "
        "probabilístico sobre nome do paciente e da mãe, data de nascimento, "
        "sexo, CPF, CNS e endereço, usando <b>nove chaves de bloqueio</b>, "
        "Soundex adaptado a nomes brasileiros e distância de Jaro-Winkler com "
        "limiar de 90%. A deduplicação determinística resultou em 403,1 milhões "
        "de indivíduos possíveis; a probabilística chegou a <b>159,7 milhões de "
        "indivíduos únicos</b>, com 3,3% de falsos positivos e 12,3% de falsos "
        "negativos estimados e kappa de 0,952 na revisão independente.",
        "é a referência que faltava para o módulo de duplicatas, e valida "
        "decisão por decisão a arquitetura escolhida: chave de bloqueio para "
        "não comparar todos contra todos, código fonético, comparação por "
        "similaridade e revisão humana antes de unificar. Dá também o que "
        "nenhuma implementação isolada tem — <b>taxas de erro publicadas</b> "
        "com que comparar, em vez de só descrever o algoritmo."))

    h.append(entrada(
        "O padrão FHIR: revisão sistemática de implementações, aplicações, "
        "desafios e oportunidades",
        "Ayaz M, Pasha MF, Alzahrani MY, Budiarto R, Stiawan D. <i>JMIR Medical "
        "Informatics</i>, 2021;9(7):e21929. DOI 10.2196/21929",
        "https://doi.org/10.2196/21929",
        "Revisão sistemática da literatura sobre FHIR publicada entre 2012 e "
        "2019. Os autores rastrearam <b>8.181 artigos</b> em ACM, IEEE, "
        "Springer, PubMed e ScienceDirect e incluíram <b>80</b> após triagem. "
        "Identificaram cerca de 82 recursos FHIR em uso nas implementações, "
        "sendo aplicativos móveis, plataformas SMART on FHIR e aplicações de "
        "pesquisa os principais beneficiários. Entre as barreiras relatadas "
        "estão a complexidade de implementação, a dificuldade de adoção e a "
        "manutenção do próprio padrão.",
        "responde academicamente à pergunta que a banca faz — <i>por que "
        "FHIR?</i> — em vez de tratar a escolha como óbvia. E as barreiras que o "
        "artigo lista são as mesmas encontradas aqui: a RNDS não publica perfil "
        "para metade do que o sistema registra."))

    h.append(entrada(
        "Prontuário eletrônico e questões semânticas com FHIR: revisão "
        "sistemática de mapeamento",
        "Amar F, April A, Abran A. <i>Journal of Medical Internet Research</i>, "
        "2024;26:e45209. DOI 10.2196/45209",
        "https://doi.org/10.2196/45209",
        "Mapeamento sistemático de <b>70 estudos</b> sobre interoperabilidade "
        "semântica com FHIR, extraídos de dez bases entre 2012 e 2022. As "
        "abordagens se dividem em seis linhas: mapeamento para terminologias "
        "FHIR (24,6%), transformação RDF/OWL (19%), aprendizado de máquina e "
        "PLN (15,9%), anotação semântica (14,3%), serviços de terminologia "
        "(14,3%) e métodos baseados em ontologias (11,9%). Os recursos mais "
        "estudados são <b>Observation, Patient e Medication</b>, e as "
        "terminologias predominantes, SNOMED CT e LOINC.",
        "é o enquadramento teórico de um defeito real deste sistema: a pressão "
        "arterial era gravada como texto “120/80” sob um código LOINC que "
        "significa pressão sistólica. O documento saía válido no transporte e "
        "errado no significado — que é precisamente a distinção que este artigo "
        "organiza. Observation e Patient, os dois recursos mais estudados, são "
        "também os dois que o sistema envia."))

    h.append(entrada(
        "SMART on FHIR: uma plataforma de aplicativos interoperável e baseada "
        "em padrões para prontuários eletrônicos",
        "Mandel JC, Kreda DA, Mandl KD, Kohane IS, Ramoni RB. <i>Journal of the "
        "American Medical Informatics Association</i>, 2016;23(5):899-908. "
        "DOI 10.1093/jamia/ocv189",
        "https://doi.org/10.1093/jamia/ocv189",
        "Descreve a construção do SMART on FHIR, plataforma que permite a uma "
        "aplicação médica ser <i>“escrita uma vez e executada sem modificação em "
        "diferentes sistemas de TI em saúde”</i>. Combina FHIR com OAuth 2.0, "
        "OpenID Connect e APIs voltadas ao desenvolvedor, restringindo recursos "
        "FHIR por meio de perfis e terminologias comuns. A viabilidade foi "
        "demonstrada em protótipos apresentados no HIMSS de 2014, com "
        "participação de grandes fornecedores.",
        "é o caminho para o prontuário deixar de ser monólito e virar "
        "plataforma — laboratório, farmácia, telemedicina e BI consumindo a "
        "mesma API. Como “trabalhos futuros”, tem a vantagem de vir com nome, "
        "referência e prova de viabilidade, em vez de ser promessa vaga."))

    h.append(entrada(
        "A influência do desenho do prontuário eletrônico sobre usabilidade e "
        "segurança medicamentosa",
        "Cahill M, Cleary BJ, Cullinan S. <i>BMC Health Services Research</i>, "
        "2025;25(1):31. DOI 10.1186/s12913-024-12060-2",
        "https://doi.org/10.1186/s12913-024-12060-2",
        "Revisão sistemática de PubMed, EMBASE, CINAHL e ACM entre janeiro de "
        "2009 e outubro de 2024, com <b>32 estudos</b> incluídos, todos sobre o "
        "efeito de elementos de desenho do prontuário em ambientes de atenção "
        "secundária, terciária e quaternária. As características se agrupam em "
        "<b>sete temas</b>: buscabilidade, automação, personalização, entrada de "
        "dados, fluxo de trabalho, orientação ao usuário e interoperabilidade. "
        "Sistemas que priorizam esses aspectos aparecem associados a maior "
        "usabilidade e melhor segurança medicamentosa; os que os negligenciam, "
        "ao contrário.",
        "muda a pergunta de “o sistema funciona?” para “o sistema reduz erro "
        "clínico?”. Num sistema com prescrição, farmácia, estoque e "
        "administração de medicamentos, essa é a pergunta que importa — e é o "
        "artigo que ancora uma avaliação empírica com usuários, se houver tempo "
        "de fazê-la."))

    h.append(entrada(
        "Segurança e privacidade em prontuários eletrônicos: revisão "
        "sistemática da literatura",
        "Fernández-Alemán JL, Señor IC, Lozoya PÁ, Toval A. <i>Journal of "
        "Biomedical Informatics</i>, 2013;46(3):541-562. "
        "DOI 10.1016/j.jbi.2012.12.003",
        "https://doi.org/10.1016/j.jbi.2012.12.003",
        "Revisão que partiu de <b>775 artigos</b> e analisou <b>49</b>. HIPAA e "
        "a Diretiva Europeia 95/46/CE aparecem como as normas mais "
        "referenciadas. Entre os mecanismos, são recorrentes a criptografia, as "
        "técnicas de pseudoanonimização e o <b>controle de acesso baseado em "
        "papéis (RBAC)</b>; <b>trilhas de auditoria aparecem em 25 dos 49 "
        "estudos</b>. Apenas quatro trabalhos dão ênfase ao treinamento dos "
        "usuários em segurança.",
        "mostra que RBAC e trilha de auditoria não são preferência de projeto: "
        "são o que a literatura de prontuário registra como recorrente. É o que "
        "permite dizer que as decisões arquiteturais têm respaldo, em vez de "
        "terem sido adotadas porque pareciam boas. O artigo é de 2013 e vale "
        "citá-lo pelo que ele é — o levantamento fundador, não o estado da arte."))

    # =========================================================== softwares
    h += secao(
        "Softwares comparáveis",
        "Seis sistemas, todos abertos na fonte do projeto. Não estão aqui para "
        "servir de modelo de arquitetura, e sim para responder à pergunta que a "
        "banca faz: por que não usar o que já existe?")

    h.append(entrada(
        "e-SUS APS — Prontuário Eletrônico do Cidadão (PEC)",
        "Ministério da Saúde / Secretaria de Atenção Primária à Saúde. Gratuito, "
        "distribuído pelo SUS. Versões correntes: PEC 5.3.28 e CDS 3.2.29, "
        "Windows e Linux.",
        "https://sisaps.saude.gov.br/esus/",
        "O prontuário eletrônico do próprio Ministério da Saúde, descrito como "
        "<i>“feito pelo SUS e para o SUS”</i>, parte da estratégia de "
        "reestruturação das informações da Atenção Primária. Além do PEC há o "
        "módulo CDS de coleta simplificada, o Painel e-SUS APS e aplicativos "
        "móveis para território, atividade coletiva, atenção domiciliar e "
        "vacinação. Integra-se à RNDS, enviando dados de vacinação, consultas, "
        "prescrições e atestados.",
        "<b>é o comparável mais direto que existe</b>, e a pergunta “por que não "
        "usar o e-SUS?” vai ser feita. A resposta precisa ser específica e "
        "verdadeira: o PEC é de atenção primária, enquanto este sistema cobre "
        "pronto-socorro, triagem com classificação de risco, internação com "
        "gestão de leitos e faturamento AIH/APAC. Não é concorrência; é outra "
        "camada da rede."))

    h.append(entrada(
        "OpenEMR",
        "Comunidade OpenEMR. Licença GPL-3.0, PHP. 5,4 mil estrelas, 3 mil "
        "forks e cerca de 13.400 commits no ramo principal.",
        "https://github.com/openemr/openemr",
        "Prontuário e gestão de consultório com mais de duas décadas de "
        "existência, reunindo registro clínico, agenda, faturamento eletrônico "
        "e internacionalização. Tem documentação própria de FHIR e de SMART on "
        "FHIR, patrocinadores de certificação ONC e — detalhe relevante — um "
        "fluxo de integração contínua chamado <i>Inferno Certification Test</i>.",
        "vale observar como modelam paciente e encontro, como expõem a API FHIR "
        "e como documentam segurança. O fluxo de teste com Inferno é a "
        "confirmação prática de que validação de conformidade cabe no CI — que "
        "é exatamente o próximo passo previsto aqui."))

    h.append(entrada(
        "OpenMRS e o módulo FHIR2",
        "Comunidade OpenMRS. Licença MPL-2.0, Java com Spring, Hibernate e "
        "HAPI FHIR.",
        "https://github.com/openmrs/openmrs-module-fhir2",
        "Módulo que substitui o antigo módulo FHIR do OpenMRS, implementando "
        "<b>FHIR R4</b> (mantendo suporte a R3 na camada de provedores). A "
        "arquitetura é explicitamente em quatro camadas — <i>ResourceProviders</i> "
        "para a integração com o HAPI, <i>Services</i> para a lógica de negócio, "
        "<i>Translators</i> para o mapeamento entre modelos e <i>DAOs</i> para o "
        "banco —, com implementações substituíveis em tempo de execução.",
        "é a melhor referência de <b>como separar domínio clínico de "
        "representação FHIR</b>. Aqui essa tradução mora nos mappers de "
        "<font face=\"Courier\">routes/rnds.py</font>, misturada à rota; a "
        "camada de <i>Translators</i> deles mostra o que ganharia sendo "
        "extraído."))

    h.append(entrada(
        "Bahmni",
        "Bahmni Coalition. Código aberto; reconhecido como <i>Digital Public "
        "Good</i> e vencedor do Future of Government Awards 2023 na categoria de "
        "criação em código aberto.",
        "https://bahmni.org/",
        "Sistema hospitalar completo para ambientes de poucos recursos, que "
        "combina quatro projetos: OpenMRS para o registro clínico, OpenERP para "
        "estoque, faturamento e contabilidade, OpenELIS para laboratório e "
        "integração DICOM/PACS para imagem. O site relata mais de <b>500 "
        "instalações em mais de 50 países</b>, com cerca de 4 mil usuários e 20 "
        "milhões de registros de pacientes.",
        "a convergência conceitual é forte — nasceu para a unidade que ainda "
        "trabalha com papel, que é a motivação declarada deste projeto. A "
        "diferença de estratégia é o ponto interessante para a monografia: eles "
        "integram quatro sistemas independentes; aqui tudo é um só, e cada "
        "escolha tem custo."))

    h.append(entrada(
        "Medplum",
        "Medplum. Licença Apache-2.0, TypeScript de ponta a ponta, com Node.js, "
        "React, PostgreSQL e Redis.",
        "https://github.com/medplum/medplum",
        "Plataforma para desenvolvedores descrita como voltada ao "
        "desenvolvimento rápido de aplicações de saúde. Oferece autenticação, "
        "repositório de dados clínicos, APIs baseadas em FHIR, SDKs de cliente, "
        "aplicação web, execução de rotinas no servidor e componentes React. "
        "O dado nasce armazenado em FHIR, e a aplicação é construída por cima.",
        "é o contraponto arquitetural direto: <b>armazenar em FHIR versus "
        "traduzir para FHIR na borda</b>. Este sistema faz a segunda escolha — "
        "models SQLAlchemy próprios, convertidos nos mappers — e tem argumento "
        "para ela, já que a RNDS não publica perfil de Encounter nem de sinal "
        "vital. Discutir essa troca explicitamente vale uma seção."))

    h.append(entrada(
        "OpenEMPI",
        "Sysnet International. <b>Software comercial</b> — apesar do nome e de "
        "sua origem em projeto aberto, a página atual o descreve como produto "
        "comercial, sem licença livre declarada.",
        "https://www.openempi.org/",
        "Índice mestre de pacientes e resolução de entidades: liga registros "
        "duplicados a um registro mestre confiável. Combina três abordagens de "
        "pareamento — regras determinísticas, algoritmos probabilísticos e "
        "modelos de IA — organizadas em etapas de padronização, bloqueio, "
        "pontuação e resolução. Entre os algoritmos, Jaro-Winkler, Levenshtein, "
        "Soundex e Double Metaphone, com API REST, suporte a HL7/FHIR e revisão "
        "humana no fluxo.",
        "o desenho é quase o mesmo do módulo de duplicatas daqui: padronizar, "
        "bloquear, pontuar, decidir — com pessoa na decisão final. Serve para "
        "comparar quais atributos entram na pontuação e com que peso. "
        "<b>Atenção ao classificá-lo:</b> não é software livre, e citá-lo como "
        "tal seria erro.",
        ultima=True))

    h.append(Spacer(1, 14))
    h.append(HRFlowable(width="100%", thickness=0.5, color=CINZA_LINHA))
    h.append(Paragraph(
        f"Levantamento de {DATA}, com todos os itens abertos na fonte do editor "
        "ou do projeto. As citações foram lidas na página do periódico; as "
        "descrições de software, no repositório ou no site oficial. Refazer a "
        "conferência antes de citar, se passar muito tempo — versão de software "
        "muda, e licença também.", rodape_nota))

    return h


# ----------------------------------------------------------------- layout
def _rodape(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(CINZA_LINHA)
    canvas.setLineWidth(0.4)
    y = 1.15 * cm
    canvas.line(MARGEM, y + 0.34 * cm, A4[0] - MARGEM, y + 0.34 * cm)
    canvas.setFont("Helvetica", 7.4)
    canvas.setFillColor(CINZA)
    canvas.drawString(MARGEM, y, "Artigos e softwares de referência — Prontuário Único")
    canvas.drawRightString(A4[0] - MARGEM, y, str(canvas.getPageNumber()))
    canvas.restoreState()


def _capa(canvas, doc):
    canvas.saveState()
    altura = 3.9 * cm
    topo = A4[1]
    canvas.setFillColor(AZUL)
    canvas.rect(0, topo - altura, A4[0], altura, stroke=0, fill=1)
    canvas.setFillColor(AMARELO)
    canvas.rect(0, topo - altura - 0.16 * cm, A4[0], 0.16 * cm, stroke=0, fill=1)

    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 23)
    canvas.drawString(MARGEM, topo - 1.75 * cm, "Artigos e softwares")
    canvas.setFont("Helvetica", 12.5)
    canvas.drawString(MARGEM, topo - 2.5 * cm,
                      "Referências para o Prontuário Único")
    canvas.setFont("Helvetica-Oblique", 9)
    canvas.drawString(MARGEM, topo - 3.15 * cm,
                      f"Oito artigos e seis softwares · levantamento de {DATA}")
    canvas.restoreState()
    _rodape(canvas, doc)


def montar(historia_):
    doc = BaseDocTemplate(str(SAIDA), pagesize=A4,
                          leftMargin=MARGEM, rightMargin=MARGEM,
                          topMargin=MARGEM, bottomMargin=1.9 * cm,
                          title="Artigos e softwares de referência — Prontuário Único",
                          author="Iasmin Ribeiro de Souza")
    largura = A4[0] - 2 * MARGEM
    capa = Frame(MARGEM, 1.9 * cm, largura, A4[1] - 4.7 * cm - 1.9 * cm, id="capa")
    normal = Frame(MARGEM, 1.9 * cm, largura, A4[1] - MARGEM - 1.9 * cm, id="normal")
    doc.addPageTemplates([
        PageTemplate(id="capa", frames=[capa], onPage=_capa),
        PageTemplate(id="normal", frames=[normal], onPage=_rodape),
    ])
    doc.build(historia_)


if __name__ == "__main__":
    montar(historia())
    print(f"gerado:  {SAIDA}")
    print(f"tamanho: {SAIDA.stat().st_size:,} bytes")
