from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO
from datetime import datetime

from utils.datas import por_extenso

# ── Paleta SUS ──
AZUL_SUS = colors.HexColor("#003F88")
AZUL_MEDIO = colors.HexColor("#0060C0")
AZUL_CLARO = colors.HexColor("#E8F0FB")
VERDE_SUS = colors.HexColor("#007C3E")
CINZA_TEXTO = colors.HexColor("#2C3140")
CINZA_CLARO = colors.HexColor("#F7F8FA")
CINZA_BORDA = colors.HexColor("#D8DDE6")


def _estilos():
    s = getSampleStyleSheet()
    base = dict(fontName="Helvetica", textColor=CINZA_TEXTO)

    def _ps(nome, **kw):
        """ParagraphStyle com os defaults de `base`; o estilo sempre vence.

        Antes era `ParagraphStyle(nome, **base, fontName=...)`, que duplicava o
        keyword e quebrava toda emissão de PDF com TypeError.
        """
        return ParagraphStyle(nome, **{**base, **kw})

    return {
        "titulo": _ps(
            "titulo",
            fontSize=13,
            fontName="Helvetica-Bold",
            textColor=AZUL_SUS,
            spaceAfter=2,
        ),
        "subtitulo": _ps(
            "subtitulo",
            fontSize=9,
            textColor=colors.HexColor("#5A6478"),
            spaceAfter=8,
        ),
        "secao": _ps(
            "secao",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=AZUL_MEDIO,
            spaceBefore=10,
            spaceAfter=4,
            borderPad=2,
        ),
        "corpo": _ps("corpo", fontSize=9, leading=14, spaceAfter=4),
        "label": _ps(
            "label",
            fontSize=7.5,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#5A6478"),
        ),
        "valor": _ps("valor", fontSize=9, leading=12),
        "rodape": _ps(
            "rodape",
            fontSize=7,
            textColor=colors.HexColor("#8A95A8"),
            alignment=TA_CENTER,
        ),
        "assinatura": _ps("assin", fontSize=9, alignment=TA_CENTER),
        "direita": _ps("dir", fontSize=8, alignment=TA_RIGHT),
    }


def _cabecalho(story, unidade, titulo_doc, e):
    # Linha superior: SUS + nome unidade + data
    data_str = datetime.now().strftime("%d/%m/%Y  %H:%M")
    cab = Table(
        [
            [
                Paragraph(
                    '<b><font color="#FFFFFF">SUS</font></b>',
                    ParagraphStyle(
                        "sus",
                        fontSize=9,
                        fontName="Helvetica-Bold",
                        backColor=AZUL_SUS,
                        textColor=colors.white,
                        borderPad=4,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph(
                    f'<b>{unidade.nome if unidade else "Unidade de Saúde"}</b><br/>'
                    f'<font size="7" color="#5A6478">'
                    f'{"CNES " + unidade.cnes if unidade and unidade.cnes else ""}'
                    f'{"  ·  " + unidade.municipio + "/" + unidade.uf if unidade and unidade.municipio else ""}'
                    f"</font>",
                    e["corpo"],
                ),
                Paragraph(data_str, e["direita"]),
            ],
        ],
        colWidths=[1.5 * cm, 12 * cm, 4 * cm],
    )
    cab.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (0, 0), AZUL_SUS),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    story.append(cab)
    story.append(Spacer(1, 0.3 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=AZUL_SUS, spaceAfter=6))
    story.append(Paragraph(titulo_doc, e["titulo"]))
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=CINZA_BORDA, spaceAfter=8)
    )


def _campo(label, valor, e):
    return [
        Paragraph(label, e["label"]),
        Paragraph(str(valor) if valor else "—", e["valor"]),
    ]


def _rodape(story, e, texto_extra=""):
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=CINZA_BORDA))
    rodape = (
        f'Documento gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}  ·  '
        f"Sistema de Prontuário Único SUS"
    )
    if texto_extra:
        rodape += f"  ·  {texto_extra}"
    story.append(Paragraph(rodape, e["rodape"]))


# ══════════════════════════════════════════
# 1. PRONTUÁRIO COMPLETO
# ══════════════════════════════════════════
def gerar_prontuario(prontuario, paciente, medico, unidade):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    e = _estilos()
    story = []

    _cabecalho(story, unidade, "Prontuário Clínico", e)

    # Dados do paciente
    story.append(Paragraph("IDENTIFICAÇÃO DO PACIENTE", e["secao"]))
    dados = [
        [
            "Nome",
            paciente.nome_exibicao,
            "Data de Nasc.",
            paciente.data_nascimento.strftime("%d/%m/%Y"),
        ],
        ["CNS", paciente.cns or "—", "CPF", paciente.cpf or "—"],
        [
            "Idade",
            f"{paciente.idade} anos",
            "Sexo",
            (
                "Masculino"
                if paciente.sexo == "M"
                else "Feminino" if paciente.sexo == "F" else "—"
            ),
        ],
        [
            "Mãe",
            paciente.nome_mae or "—",
            "Tipo Sanguíneo",
            paciente.tipo_sanguineo or "—",
        ],
        [
            "Município",
            f'{paciente.municipio or "—"}/{paciente.uf or ""}',
            "Telefone",
            paciente.telefone or "—",
        ],
    ]
    if paciente.alergias:
        # Sem glifo: o "⚠" (U+26A0) não existe no WinAnsi das fontes padrão do
        # reportlab e saía como um quadrado preto — justamente na linha de
        # alergia, que é a que não pode ficar ilegível.
        dados.append(["ALERGIAS", paciente.alergias, "", ""])

    tbl = Table(
        [
            [
                Paragraph(
                    c if i % 2 == 0 else str(c),
                    e["label"] if i % 2 == 0 else e["valor"],
                )
                for i, c in enumerate(row)
            ]
            for row in dados
        ],
        colWidths=[3 * cm, 6 * cm, 3 * cm, 5.5 * cm],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CINZA_CLARO),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, CINZA_CLARO]),
                ("BOX", (0, 0), (-1, -1), 0.5, CINZA_BORDA),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, CINZA_BORDA),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 0.4 * cm))

    # Sinais vitais
    vitais = []
    if prontuario.pressao_arterial:
        vitais.append(("PA", prontuario.pressao_arterial, "mmHg"))
    if prontuario.temperatura:
        vitais.append(("Temp.", f"{prontuario.temperatura:.1f}", "°C"))
    if prontuario.frequencia_cardiaca:
        vitais.append(("FC", str(prontuario.frequencia_cardiaca), "bpm"))
    if prontuario.saturacao_o2:
        # "SpO2" e não "SpO₂": o subscrito (U+2082) também está fora do WinAnsi
        # e saía como quadrado preto no lugar do 2.
        vitais.append(("SpO2", f"{prontuario.saturacao_o2:.0f}", "%"))
    if prontuario.peso:
        vitais.append(("Peso", f"{prontuario.peso:.1f}", "kg"))
    if prontuario.altura:
        vitais.append(("Altura", f"{prontuario.altura:.2f}", "m"))
    if prontuario.imc:
        vitais.append(("IMC", f"{prontuario.imc:.1f}", "kg/m²"))
    if prontuario.glicemia:
        vitais.append(("Glicemia", str(int(prontuario.glicemia)), "mg/dL"))

    if vitais:
        story.append(Paragraph("SINAIS VITAIS", e["secao"]))
        vrow = [
            [
                Paragraph(
                    f'<b>{v[0]}</b><br/><font size="10">{v[1]}</font><br/>'
                    f'<font size="7" color="#8A95A8">{v[2]}</font>',
                    e["assinatura"],
                )
                for v in vitais
            ]
        ]
        vtbl = Table(vrow, colWidths=[17.5 * cm / len(vitais)] * len(vitais))
        vtbl.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, CINZA_BORDA),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, CINZA_BORDA),
                    ("BACKGROUND", (0, 0), (-1, -1), AZUL_CLARO),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(vtbl)
        story.append(Spacer(1, 0.4 * cm))

    # SOAP
    soap = [
        ("S — SUBJETIVO (Anamnese)", prontuario.subjetivo),
        ("O — OBJETIVO (Exame Físico)", prontuario.objetivo),
        ("A — AVALIAÇÃO (Diagnóstico)", prontuario.avaliacao),
        ("P — PLANO (Conduta)", prontuario.plano),
    ]
    for titulo, texto in soap:
        if texto:
            story.append(Paragraph(titulo, e["secao"]))
            story.append(Paragraph(texto.replace("\n", "<br/>"), e["corpo"]))

    # CID
    if prontuario.cid_principal:
        story.append(Paragraph("CID-10", e["secao"]))
        cid_txt = f"Principal: <b>{prontuario.cid_principal}</b>"
        if prontuario.cid_secundario:
            cid_txt += f"   Secundário: <b>{prontuario.cid_secundario}</b>"
        story.append(Paragraph(cid_txt, e["corpo"]))

    # Prescrição
    if prontuario.prescricao:
        story.append(Paragraph("PRESCRIÇÃO MÉDICA", e["secao"]))
        story.append(
            Paragraph(prontuario.prescricao.replace("\n", "<br/>"), e["corpo"])
        )

    # Encaminhamento
    if prontuario.encaminhamento:
        story.append(Paragraph("ENCAMINHAMENTOS", e["secao"]))
        story.append(
            Paragraph(prontuario.encaminhamento.replace("\n", "<br/>"), e["corpo"])
        )

    # Assinatura
    story.append(Spacer(1, 1 * cm))
    med_nome = medico.nome if medico else "—"
    med_crm = medico.crm if medico else ""
    assin = Table(
        [
            [
                Paragraph("_" * 40, e["assinatura"]),
            ]
        ],
        colWidths=[17.5 * cm],
    )
    story.append(assin)
    story.append(Paragraph(f"{med_nome}", e["assinatura"]))
    if med_crm:
        story.append(Paragraph(f"CRM {med_crm}", e["assinatura"]))
    if prontuario.assinado_em:
        story.append(
            Paragraph(
                f'Assinado em {prontuario.assinado_em.strftime("%d/%m/%Y às %H:%M")}',
                e["assinatura"],
            )
        )

    _rodape(story, e, f"Prontuário #{prontuario.id}")
    doc.build(story)
    buf.seek(0)
    return buf


# ══════════════════════════════════════════
# 2. RECEITUÁRIO
# ══════════════════════════════════════════
def gerar_receituario(prontuario, paciente, medico, unidade):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    e = _estilos()
    story = []

    _cabecalho(story, unidade, "Receituário Médico", e)

    # Paciente
    story.append(Paragraph("PACIENTE", e["secao"]))
    tbl = Table(
        [
            [
                Paragraph("Nome", e["label"]),
                Paragraph(paciente.nome_exibicao, e["valor"]),
                Paragraph("Data", e["label"]),
                Paragraph(datetime.now().strftime("%d/%m/%Y"), e["valor"]),
            ],
            [
                Paragraph("CNS", e["label"]),
                Paragraph(paciente.cns or "—", e["valor"]),
                Paragraph("Idade", e["label"]),
                Paragraph(f"{paciente.idade} anos", e["valor"]),
            ],
        ],
        colWidths=[2.5 * cm, 8 * cm, 2 * cm, 5.5 * cm],
    )
    tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, CINZA_BORDA),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, CINZA_BORDA),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, CINZA_CLARO]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 0.5 * cm))

    # Prescrição
    story.append(Paragraph("PRESCRIÇÃO", e["secao"]))
    prescricao = prontuario.prescricao or "Sem prescrição registrada."
    for i, linha in enumerate(prescricao.split("\n"), 1):
        if linha.strip():
            story.append(Paragraph(f"{i}. {linha.strip()}", e["corpo"]))
    story.append(Spacer(1, 0.3 * cm))

    if prontuario.retorno_dias:
        story.append(
            Paragraph(f"<b>Retorno:</b> em {prontuario.retorno_dias} dias.", e["corpo"])
        )

    # Assinatura
    story.append(Spacer(1, 2 * cm))
    story.append(
        HRFlowable(
            width=8 * cm,
            thickness=0.5,
            color=CINZA_BORDA,
            hAlign="CENTER",
            spaceAfter=4,
        )
    )
    story.append(Paragraph(medico.nome if medico else "—", e["assinatura"]))
    if medico and medico.crm:
        story.append(Paragraph(f"CRM {medico.crm}", e["assinatura"]))
    if medico and medico.especialidade:
        story.append(Paragraph(medico.especialidade, e["assinatura"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f'{unidade.municipio if unidade and unidade.municipio else ""}, '
            f'{por_extenso(datetime.now())}',
            e["assinatura"],
        )
    )

    _rodape(story, e)
    doc.build(story)
    buf.seek(0)
    return buf


# ══════════════════════════════════════════
# 3. ATESTADO MÉDICO
# ══════════════════════════════════════════
def gerar_atestado(paciente, medico, unidade, dias, cid=None, observacao=None):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    e = _estilos()
    story = []

    _cabecalho(story, unidade, "Atestado Médico", e)
    story.append(Spacer(1, 1 * cm))

    # Corpo do atestado
    med_nome = medico.nome if medico else "o(a) profissional responsável"
    med_crm = f", CRM {medico.crm}" if medico and medico.crm else ""
    texto = (
        f"Atesto, para os devidos fins, que o(a) paciente <b>{paciente.nome_exibicao}</b>, "
        f'portador(a) do CNS <b>{paciente.cns or "—"}</b>, '
        f"esteve sob minha assistência médica e necessita de afastamento de suas atividades "
        f'pelo período de <b>{dias} ({_extenso(dias)}) dia{"s" if dias != 1 else ""}</b>, '
        f"a partir desta data."
    )
    story.append(
        Paragraph(
            texto,
            ParagraphStyle(
                "at",
                fontName="Helvetica",
                fontSize=10,
                leading=18,
                textColor=CINZA_TEXTO,
                spaceAfter=12,
            ),
        )
    )

    if cid:
        story.append(
            Paragraph(
                f"CID-10: <b>{cid}</b>",
                ParagraphStyle(
                    "cid",
                    fontName="Helvetica",
                    fontSize=9,
                    textColor=CINZA_TEXTO,
                    spaceAfter=8,
                ),
            )
        )
    if observacao:
        story.append(
            Paragraph(
                f"Observações: {observacao}",
                ParagraphStyle(
                    "obs",
                    fontName="Helvetica",
                    fontSize=9,
                    textColor=CINZA_TEXTO,
                    spaceAfter=8,
                ),
            )
        )

    story.append(Spacer(1, 2 * cm))
    story.append(
        Paragraph(
            f'{unidade.municipio if unidade and unidade.municipio else "Local"}, '
            f'{por_extenso(datetime.now())}',
            ParagraphStyle(
                "data",
                fontName="Helvetica",
                fontSize=9,
                textColor=CINZA_TEXTO,
                alignment=TA_RIGHT,
                spaceAfter=30,
            ),
        )
    )

    story.append(
        HRFlowable(
            width=8 * cm,
            thickness=0.5,
            color=CINZA_BORDA,
            hAlign="CENTER",
            spaceAfter=4,
        )
    )
    story.append(Paragraph(f"{med_nome}{med_crm}", e["assinatura"]))
    if medico and medico.especialidade:
        story.append(Paragraph(medico.especialidade, e["assinatura"]))

    _rodape(story, e)
    doc.build(story)
    buf.seek(0)
    return buf


def _extenso(n):
    nums = {
        1: "um",
        2: "dois",
        3: "três",
        4: "quatro",
        5: "cinco",
        6: "seis",
        7: "sete",
        8: "oito",
        9: "nove",
        10: "dez",
        15: "quinze",
        20: "vinte",
        30: "trinta",
    }
    return nums.get(n, str(n))
