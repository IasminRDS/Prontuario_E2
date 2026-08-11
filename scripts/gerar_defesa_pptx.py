# -*- coding: utf-8 -*-
"""Gera `docs/defesa_slides.pptx` a partir de `docs/defesa_roteiro.md`.

Uma fonte só para os dois artefatos da defesa. O roteiro em markdown já separa,
por slide, **o que aparece** (rubrica "Visual") do **que se fala** (o bloco de
citação). Este gerador aproveita exatamente essa separação:

- o que está sob "Visual" vira o corpo do slide;
- a fala vira **nota do apresentador**, que é onde ela serve — no modo
  apresentador do PowerPoint, e não projetada na parede.

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
from pptx.util import Emu, Inches, Pt

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
 2: [("Uma pessoa, muitos municípios: unidades administrativamente independentes", 0),
     ("Adesão ao prontuário eletrônico na atenção primária: 8.930 unidades (2017) para 26.091 (2022)", 0),
     ("Ampliar o acesso melhora o cuidado. Restringi-lo protege o titular.", 0),
     ("d", "Onde essa fronteira é traçada é decisão de governança — a arquitetura apenas a executa")],
 3: [("Exposição entre unidades não gera erro, alerta nem sinal ao usuário", 0),
     ("Segregar sem impedir o cuidado longitudinal: cadastro é nacional", 0),
     ("Rastreabilidade é obrigação legal — LGPD, art. 37", 0),
     ("Backup nunca restaurado é a suposição de uma garantia", 0)],
 4: [("d", "Geral: construir o sistema e verificar empiricamente seus controles"),
     ("Isolamento aplicado na camada de banco, e não só na aplicação", 0),
     ("Controle de acesso orientado pelo menor privilégio", 0),
     ("Auditoria com detecção de adulteração", 0),
     ("Backup com validação automatizada de restauração", 0),
     ("Usabilidade por inspeção heurística", 0),
     ("Analisar criticamente os limites dos próprios controles", 0)],
 5: [("Multi-tenancy — Kabbedijk et al. (2015): 761 artigos, 43 definições", 0),
     ("Estratégias de isolamento — Chong, Carraro e Wolter (2006)", 0),
     ("Propriedades de segurança — ISO/IEC 27000:2018", 0),
     ("Falha fechada (fail-safe defaults) — Saltzer e Schroeder (1975)", 0),
     ("d", "Autenticidade e não repúdio no primeiro plano: em prontuário, autoria não é atributo acessório")],
 6: [("Flask · Jinja2 · SQLAlchemy · PostgreSQL", 0),
     ("Usuário → Aplicação: RBAC por permissão nomeada", 0),
     ("→ ORM: escopo territorial reposto a cada transação", 0),
     ("→ PostgreSQL: políticas de RLS, integridade e trilha encadeada", 0),
     ("45 módulos · 213 rotas · 42 tabelas · 118 telas · 14 migrações", 0),
     ("d", "Contagem automatizada sobre o código, não estimativa")],
 7: [("Bancos separados — isolamento máximo; consulta entre unidades inviável", 0),
     ("Esquemas separados — mesma limitação, com complexidade adicional", 0),
     ("Coluna discriminadora (unidade_id) — ADOTADA: consulta natural", 0),
     ("Segunda camada: Row-Level Security — hoje, 23 tabelas sob política", 0),
     ("d", "Quatro condições: FORCE · falha fechada · escopo por transação · COBERTURA EFETIVA")],
 8: [("RBAC — 27 permissões, 7 perfis, no formato recurso:ação", 0),
     ("Ortogonal ao escopo: a permissão diz o quê; o escopo, sobre quais registros", 0),
     ("Auditoria — leituras e escritas encadeadas por hash, em tabela de papel próprio", 0),
     ("LGPD — art. 5º II · art. 9º · art. 11 II f · art. 37", 0),
     ("d", "Tutela da saúde tem base legal própria: não é consentimento")],
 9: [("d", "A inspeção de código é insuficiente para verificar controles de segurança."),
     ("Instrumentar o motor de telas e renderizar tudo com dado real", 0),
     ("Confrontar formulário × rota e tela × rota, nos dois sentidos", 0),
     ("Gerar os PDFs e os CSVs e conferir o que saiu", 0),
     ("Cobertura de execução como MAPA, não como meta", 0),
     ("417 casos · 264 funções · 35 arquivos · dois bancos", 0)],
 10: [("d", "Dezenove achados. Nenhum produz mensagem de erro."),
      ("I — a declaração que deixou de ser verdadeira", 0),
      ("II — a regra escrita mais de uma vez", 0),
      ("III — o caminho que não existe", 0),
      ("IV — o efeito que não ocorre", 0),
      ("V — o próprio controle como origem do defeito", 0)],
 11: [("I → confrontar a declaração com o estado real, não com outra declaração", 0),
      ("II → comparar as cópias no nível do efeito: perfis, e não nomes", 0),
      ("III → alcançabilidade nos dois sentidos", 0),
      ("IV → medir o efeito, nunca a chamada", 0),
      ("V → verificar o verificador: introduzir o defeito e exigir reprovação", 0),
      ("d", "Cinco instrumentos permanentes: a próxima ocorrência reprova a suíte")],
 12: [("Isolamento — 10, depois 15, hoje 23 tabelas sob política", 0),
      ("Desempenho — 185,9 ms para 0,96 ms (ordem de grandeza, não benchmark)", 0),
      ("Continuidade — restauração conferida em 13 tabelas, correspondência exata", 0),
      ("Configuração — hardening-check: 8 verificadas, 1 não verificável", 0),
      ("d", "Declarar uma lacuna é melhor que ocultá-la — e não é o mesmo que corrigi-la")],
 13: [("RLS correto, e cinco tabelas clínicas fora de qualquer política", 0),
      ("A auditoria de leitura que era criada e nunca persistida", 0),
      ("O detector cego para o próprio defeito: de 19 para 46 achados", 0),
      ("d", "O defeito escondia a si mesmo: quanto mais a tela dependia da variável ausente, menos o verificador a via")],
 14: [("Não repúdio — detectável, não irrefutável", 0),
      ("Âncora de auditoria — a custódia é externa ao software", 0),
      ("Desempenho — ordem de grandeza, sem tratamento estatístico", 0),
      ("Usabilidade — inspeção pela própria equipe, sem usuários finais", 0),
      ("RBAC — matriz não configurável por organização", 0)],
 15: [("d", "Um controle de detecção produz duas informações:"),
      ("d", "os achados, e a confiança de que não há mais nada."),
      ("d", "A primeira é verificável por inspeção. A segunda, não.")],
 16: [("d", "A contribuição decorre da cobertura verificada do mecanismo, não da sua existência."),
      ("Isolamento implementado, ampliado e quantificado — ainda que não integral", 0),
      ("Acesso com permissão e escopo distinguidos", 0),
      ("Auditoria encadeada e registrando leituras; imutabilidade depende de infraestrutura", 0),
      ("Continuidade com validação automatizada de restauração", 0),
      ("Usabilidade avaliada sem participação de usuários finais", 0)],
 17: [("Matriz de permissões configurável por organização, com auditoria das alterações", 0),
      ("Avaliação de usabilidade com usuários dos perfis reais", 0),
      ("Medição sob distribuição real de dados", 0),
      ("Camada de serviço com autorização em ponto único", 0),
      ("Ampliação da conformidade com FHIR", 0),
      ("Custódia externa da âncora, com emissão e verificação separadas", 0)],
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


def conteudo(prs, titulo, itens, notas, numero):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _faixa_titulo(slide, titulo)

    caixa = _caixa(slide, Inches(0.9), Inches(1.85), Inches(11.5), Inches(4.7))
    quadro = caixa.text_frame
    quadro.word_wrap = True

    for item in itens:
        destaque = item.get("destaque", False)
        _escrever(quadro,
                  ("" if destaque else "•  ") + item["texto"],
                  item.get("tamanho", 19 if not destaque else 23),
                  AZUL_ESCURO if destaque else GRAFITE,
                  negrito=destaque,
                  espaco_depois=14 if destaque else 11,
                  nivel=item.get("nivel", 0))

    _rodape(slide, numero)
    _notas(slide, notas)
    return slide


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
            if entrada[0] == "d":
                itens.append({"texto": entrada[1], "destaque": True})
            else:
                itens.append({"texto": entrada[0], "nivel": entrada[1]})
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
    com_notas = sum(1 for s in slides if s["fala"])
    print(f"gerado:  {SAIDA}")
    print(f"tamanho: {SAIDA.stat().st_size:,} bytes")
    print(f"slides:  {len(prs.slides.__iter__.__self__._sldIdLst)} ao todo "
          f"(capa, 3 divisores, conteúdo, referências e encerramento)")
    print(f"notas:   {com_notas} slides com a fala nas notas do apresentador")
    print("A fala NÃO vai projetada: está nas notas, para o modo apresentador.")


if __name__ == "__main__":
    gerar()
