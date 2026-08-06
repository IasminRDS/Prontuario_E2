# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime

from utils.datas import por_extenso

AZUL = colors.HexColor("#003F88")
AZUL2 = colors.HexColor("#0060C0")
AZULC = colors.HexColor("#E8F0FB")
VERDE = colors.HexColor("#007C3E")
CINZA = colors.HexColor("#2C3140")
CBORDA = colors.HexColor("#D8DDE6")
CFUNDO = colors.HexColor("#F7F8FA")

PRIORIDADE_CORES = {
    "eletivo": colors.HexColor("#5A6478"),
    "prioritario": colors.HexColor("#F5A623"),
    "urgente": colors.HexColor("#C0392B"),
}
PRIORIDADE_LABELS = {
    "eletivo": "ELETIVO",
    "prioritario": "PRIORITÁRIO",
    "urgente": "URGENTE",
}


def _estilos():
    base = dict(fontName="Helvetica", textColor=CINZA)

    def _ps(nome, **kw):
        """ParagraphStyle com os defaults de `base`; o estilo sempre vence.

        Antes era `ParagraphStyle(nome, **base, fontName=...)`, que duplicava o
        keyword e quebrava toda emissão de PDF com TypeError.
        """
        return ParagraphStyle(nome, **{**base, **kw})

    return {
        "titulo": _ps(
            "t",
            fontSize=13,
            fontName="Helvetica-Bold",
            textColor=AZUL,
            spaceAfter=2,
        ),
        "secao": _ps(
            "s",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=AZUL2,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "corpo": _ps("c", fontSize=9, leading=14, spaceAfter=4),
        "label": _ps(
            "l",
            fontSize=7.5,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#5A6478"),
        ),
        "valor": _ps("v", fontSize=9, leading=12),
        "rodape": _ps(
            "r",
            fontSize=7,
            textColor=colors.HexColor("#8A95A8"),
            alignment=TA_CENTER,
        ),
        "centro": _ps("ce", fontSize=9, alignment=TA_CENTER),
        "direita": _ps("d", fontSize=8, alignment=TA_RIGHT),
        "prio": _ps(
            "p",
            fontName="Helvetica-Bold",
            fontSize=11,
            alignment=TA_CENTER,
            textColor=colors.white,
        ),
    }


def gerar_encaminhamento(enc, paciente, medico, unidade):
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
    s = []

    # ── Cabeçalho ──
    cor_prio = PRIORIDADE_CORES.get(enc.prioridade, CINZA)
    prio_lbl = PRIORIDADE_LABELS.get(enc.prioridade, enc.prioridade.upper())

    cab = Table(
        [
            [
                Paragraph(
                    '<b><font color="#FFFFFF">SUS</font></b>',
                    ParagraphStyle(
                        "sus",
                        fontSize=9,
                        fontName="Helvetica-Bold",
                        backColor=AZUL,
                        textColor=colors.white,
                        borderPad=4,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph(
                    f'<b>{unidade.nome if unidade else "Unidade de Saúde"}</b><br/>'
                    f'<font size="7" color="#5A6478">'
                    f'{"CNES " + unidade.cnes if unidade and unidade.cnes else ""}'
                    f'{"  ·  " + (unidade.municipio or "") + "/" + (unidade.uf or "") if unidade and unidade.municipio else ""}'
                    f"</font>",
                    e["corpo"],
                ),
                Paragraph(datetime.now().strftime("%d/%m/%Y"), e["direita"]),
            ]
        ],
        colWidths=[1.5 * cm, 12 * cm, 4 * cm],
    )
    cab.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (0, 0), AZUL),
            ]
        )
    )
    s.append(cab)
    s.append(Spacer(1, 0.3 * cm))
    s.append(HRFlowable(width="100%", thickness=2, color=AZUL, spaceAfter=6))
    s.append(Paragraph("Guia de Encaminhamento", e["titulo"]))
    s.append(HRFlowable(width="100%", thickness=0.5, color=CBORDA, spaceAfter=8))

    # ── Prioridade (destaque) ──
    tbl_prio = Table(
        [[Paragraph(f"Prioridade: {prio_lbl}", e["prio"])]],
        colWidths=[17.5 * cm],
        rowHeights=[0.8 * cm],
    )
    tbl_prio.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), cor_prio),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROUNDEDCORNERS", [4, 4, 4, 4]),
            ]
        )
    )
    s.append(tbl_prio)
    s.append(Spacer(1, 0.4 * cm))

    # ── Dados do paciente ──
    s.append(Paragraph("DADOS DO PACIENTE", e["secao"]))
    dados_pac = [
        [
            Paragraph("Nome", e["label"]),
            Paragraph(paciente.nome_exibicao, e["valor"]),
            Paragraph("Data de Nasc.", e["label"]),
            Paragraph(paciente.data_nascimento.strftime("%d/%m/%Y"), e["valor"]),
        ],
        [
            Paragraph("CNS", e["label"]),
            Paragraph(paciente.cns or "—", e["valor"]),
            Paragraph("CPF", e["label"]),
            Paragraph(paciente.cpf or "—", e["valor"]),
        ],
        [
            Paragraph("Idade", e["label"]),
            Paragraph(f"{paciente.idade} anos", e["valor"]),
            Paragraph("Sexo", e["label"]),
            Paragraph(
                (
                    "Masculino"
                    if paciente.sexo == "M"
                    else "Feminino" if paciente.sexo == "F" else "—"
                ),
                e["valor"],
            ),
        ],
        [
            Paragraph("Telefone", e["label"]),
            Paragraph(paciente.telefone or "—", e["valor"]),
            Paragraph("Município", e["label"]),
            Paragraph(f'{paciente.municipio or "—"}/{paciente.uf or ""}', e["valor"]),
        ],
    ]
    if paciente.alergias:
        dados_pac.append(
            [
                # Sem o "⚠" (U+26A0), fora do WinAnsi das fontes padrão do
                # reportlab: saía como quadrado preto.
                Paragraph("ALERGIAS", e["label"]),
                Paragraph(paciente.alergias, e["valor"]),
                Paragraph("", e["label"]),
                Paragraph("", e["valor"]),
            ]
        )

    tbl = Table(dados_pac, colWidths=[3 * cm, 5.75 * cm, 3 * cm, 5.75 * cm])
    tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, CBORDA),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, CBORDA),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, CFUNDO]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    s.append(tbl)
    s.append(Spacer(1, 0.3 * cm))

    # ── Especialidade / destino ──
    s.append(Paragraph("ENCAMINHAMENTO", e["secao"]))
    enc_dados = [
        [
            Paragraph("Especialidade", e["label"]),
            Paragraph(f"<b>{enc.especialidade}</b>", e["valor"]),
            Paragraph("CID-10", e["label"]),
            Paragraph(enc.cid or "—", e["valor"]),
        ],
        [
            Paragraph("Serviço destino", e["label"]),
            Paragraph(enc.servico_destino or "—", e["valor"]),
            Paragraph("Data agendada", e["label"]),
            Paragraph(
                (
                    enc.data_agendada.strftime("%d/%m/%Y %H:%M")
                    if enc.data_agendada
                    else "—"
                ),
                e["valor"],
            ),
        ],
    ]
    if enc.hipotese_diagnostica:
        enc_dados.append(
            [
                Paragraph("Hipótese diag.", e["label"]),
                Paragraph(enc.hipotese_diagnostica, e["valor"]),
                Paragraph("", e["label"]),
                Paragraph("", e["valor"]),
            ]
        )

    tbl2 = Table(enc_dados, colWidths=[3 * cm, 5.75 * cm, 3 * cm, 5.75 * cm])
    tbl2.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, CBORDA),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, CBORDA),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, CFUNDO]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    s.append(tbl2)
    s.append(Spacer(1, 0.3 * cm))

    # ── Motivo ──
    s.append(Paragraph("MOTIVO DO ENCAMINHAMENTO", e["secao"]))
    s.append(Paragraph(enc.motivo.replace("\n", "<br/>"), e["corpo"]))

    if enc.observacoes:
        s.append(Paragraph("OBSERVAÇÕES", e["secao"]))
        s.append(Paragraph(enc.observacoes.replace("\n", "<br/>"), e["corpo"]))

    # ── Assinatura ──
    s.append(Spacer(1, 1.5 * cm))
    med_nome = medico.nome if medico else "—"
    med_crm = f"CRM {medico.crm}" if medico and medico.crm else ""
    assin = Table(
        [
            [
                Paragraph("_" * 45, e["centro"]),
            ]
        ],
        colWidths=[17.5 * cm],
    )
    s.append(assin)
    s.append(Paragraph(med_nome, e["centro"]))
    if med_crm:
        s.append(Paragraph(med_crm, e["centro"]))
    if medico and medico.especialidade:
        s.append(Paragraph(medico.especialidade, e["centro"]))
    s.append(Spacer(1, 0.3 * cm))
    s.append(
        Paragraph(
            f'{unidade.municipio if unidade and unidade.municipio else "Local"}, '
            f'{por_extenso(datetime.now())}',
            e["centro"],
        )
    )

    # ── Rodapé ──
    s.append(Spacer(1, 0.5 * cm))
    s.append(HRFlowable(width="100%", thickness=0.5, color=CBORDA))
    s.append(
        Paragraph(
            f'Documento gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}  ·  '
            f"Encaminhamento #{enc.id}  ·  Sistema de Prontuário Único SUS",
            e["rodape"],
        )
    )

    doc.build(s)
    buf.seek(0)
    return buf
