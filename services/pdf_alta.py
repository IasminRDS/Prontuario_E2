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
    KeepTogether,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from io import BytesIO
from datetime import datetime

AZUL = colors.HexColor("#003F88")
AZUL2 = colors.HexColor("#0060C0")
AZULC = colors.HexColor("#E8F0FB")
VERDE = colors.HexColor("#007C3E")
VERDEC = colors.HexColor("#E6F4ED")
CINZA = colors.HexColor("#2C3140")
CBORDA = colors.HexColor("#D8DDE6")
CFUNDO = colors.HexColor("#F7F8FA")


def _estilos():
    return {
        "titulo": ParagraphStyle(
            "ti", fontName="Helvetica-Bold", fontSize=14, textColor=AZUL, spaceAfter=2
        ),
        "sub": ParagraphStyle(
            "su", fontName="Helvetica", fontSize=9, textColor=CINZA, spaceAfter=2
        ),
        "secao": ParagraphStyle(
            "se",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=AZUL2,
            spaceBefore=10,
            spaceAfter=4,
            textTransform="uppercase",
        ),
        "corpo": ParagraphStyle(
            "co",
            fontName="Helvetica",
            fontSize=9,
            leading=14,
            textColor=CINZA,
            spaceAfter=4,
        ),
        "corpo_j": ParagraphStyle(
            "cj",
            fontName="Helvetica",
            fontSize=9,
            leading=14,
            textColor=CINZA,
            alignment=TA_JUSTIFY,
        ),
        "label": ParagraphStyle(
            "la",
            fontName="Helvetica-Bold",
            fontSize=7.5,
            textColor=colors.HexColor("#5A6478"),
        ),
        "valor": ParagraphStyle(
            "va", fontName="Helvetica", fontSize=9, leading=12, textColor=CINZA
        ),
        "rodape": ParagraphStyle(
            "ro",
            fontName="Helvetica",
            fontSize=7,
            textColor=colors.HexColor("#8A95A8"),
            alignment=TA_CENTER,
        ),
        "centro": ParagraphStyle(
            "ce", fontName="Helvetica", fontSize=9, alignment=TA_CENTER, textColor=CINZA
        ),
        "bold": ParagraphStyle(
            "bo", fontName="Helvetica-Bold", fontSize=9, textColor=CINZA
        ),
    }


def _tabela_info(dados, e, col_widths=None):
    """Cria tabela de dados label/valor."""
    if col_widths is None:
        col_widths = [3 * cm, 5.5 * cm, 3 * cm, 5.5 * cm]
    rows = []
    for i in range(0, len(dados), 2):
        row = []
        for j in range(2):
            if i + j < len(dados):
                lbl, val = dados[i + j]
                row.extend(
                    [
                        Paragraph(lbl, e["label"]),
                        Paragraph(str(val) if val else "—", e["valor"]),
                    ]
                )
            else:
                row.extend([Paragraph("", e["label"]), Paragraph("", e["valor"])])
        rows.append(row)
    t = Table(rows, colWidths=col_widths)
    t.setStyle(
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
    return t



def _resultado_do_exame(ex):
    """Resultado legível de um exame, vindo das colunas que existem.

    O model separa `resultado_texto` (laudo descritivo) de `resultado_valor` +
    `resultado_unidade` (numérico). Exame laboratorial preenche o par numérico;
    exame de imagem preenche o texto. O sumário de alta precisa dos dois casos.
    """
    if getattr(ex, "resultado_texto", None):
        return ex.resultado_texto.strip()
    valor = getattr(ex, "resultado_valor", None)
    if valor:
        unidade = getattr(ex, "resultado_unidade", None)
        return f"{valor} {unidade}".strip() if unidade else str(valor).strip()
    return ""


def gerar_alta(internacao, paciente, medico, unidade):
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
                    e["sub"],
                ),
                Paragraph(
                    datetime.now().strftime("%d/%m/%Y"),
                    ParagraphStyle(
                        "d",
                        fontName="Helvetica",
                        fontSize=8,
                        alignment=TA_RIGHT,
                        textColor=CINZA,
                    ),
                ),
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
    s.append(Paragraph("Sumário de Alta Hospitalar", e["titulo"]))
    s.append(HRFlowable(width="100%", thickness=0.5, color=CBORDA, spaceAfter=8))

    # ── Dados do paciente ──
    s.append(Paragraph("Dados do Paciente", e["secao"]))
    s.append(
        _tabela_info(
            [
                ("Nome", paciente.nome_exibicao),
                ("Data de Nasc.", paciente.data_nascimento.strftime("%d/%m/%Y")),
                ("CNS", paciente.cns or "—"),
                ("CPF", paciente.cpf or "—"),
                ("Idade", f"{paciente.idade} anos"),
                (
                    "Sexo",
                    (
                        "Masculino"
                        if paciente.sexo == "M"
                        else "Feminino" if paciente.sexo == "F" else "—"
                    ),
                ),
                ("Telefone", paciente.telefone or "—"),
                ("Município", f'{paciente.municipio or "—"}/{paciente.uf or ""}'),
            ],
            e,
        )
    )
    if paciente.alergias:
        s.append(Spacer(1, 0.2 * cm))
        al = Table(
            [
                [
                    # Sem o "⚠" (U+26A0), que não existe no WinAnsi das fontes
                    # padrão do reportlab e virava um quadrado preto.
                    Paragraph("ALERGIAS CONHECIDAS:", e["label"]),
                    Paragraph(paciente.alergias, e["valor"]),
                ]
            ],
            colWidths=[4 * cm, 13.5 * cm],
        )
        al.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C0392B")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FDECEA")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        s.append(al)
    s.append(Spacer(1, 0.2 * cm))

    # ── Dados da internação ──
    s.append(Paragraph("Dados da Internação", e["secao"]))
    tipo_alta_map = {
        "curado": "Alta — Curado",
        "melhorado": "Alta — Melhorado",
        "transferencia": "Transferência",
        "obito": "Óbito",
        "a_pedido": "Alta a pedido",
        "evasao": "Evasão",
    }
    tipo_alta_lbl = tipo_alta_map.get(
        internacao.tipo_alta or "", internacao.tipo_alta or "—"
    )

    s.append(
        _tabela_info(
            [
                ("Data de entrada", internacao.data_entrada.strftime("%d/%m/%Y")),
                (
                    "Data de alta",
                    (
                        internacao.data_alta.strftime("%d/%m/%Y")
                        if internacao.data_alta
                        else "—"
                    ),
                ),
                ("Dias internado", f"{internacao.dias_internado} dias"),
                ("Tipo de alta", tipo_alta_lbl),
                ("Leito", internacao.leito.numero if internacao.leito else "—"),
                ("Setor", internacao.leito.setor.nome if internacao.leito else "—"),
                ("Médico responsável", medico.nome if medico else "—"),
                ("CID de alta", internacao.cid_alta or internacao.cid_principal or "—"),
                ("Nº AIH", internacao.aih_numero or "—"),
                ("Hipótese diagnóstica", internacao.hipotese_diag or "—"),
            ],
            e,
        )
    )
    s.append(Spacer(1, 0.2 * cm))

    # ── Sumário clínico ──
    if internacao.sumario_alta:
        s.append(
            KeepTogether(
                [
                    Paragraph("Sumário Clínico / Evolução", e["secao"]),
                    Paragraph(
                        internacao.sumario_alta.replace("\n", "<br/>"), e["corpo_j"]
                    ),
                ]
            )
        )
        s.append(Spacer(1, 0.2 * cm))

    # ── Prescrições ativas na alta ──
    # `Internacao` não tem backref para PrescricaoHospitalar — a relação existe
    # só pela FK. Consultamos direto em vez de acessar um atributo inexistente.
    from models.prescricao_hospitalar import PrescricaoHospitalar

    prescricoes_ativas = (
        PrescricaoHospitalar.query
        .filter_by(internacao_id=internacao.id, status="ativa")
        .all()
    )
    if prescricoes_ativas:
        pres = prescricoes_ativas[0]
        bloco = [Paragraph("Medicamentos em Uso na Alta", e["secao"])]
        # `dieta` é lido aqui e em três templates, e routes/prescricao_hosp.py
        # tenta gravá-lo — mas a coluna nunca existiu no model, e o acesso direto
        # derrubava a alta inteira com AttributeError. O getattr é provisório:
        # ou a coluna entra (com migration), ou estas leituras saem.
        dieta = getattr(pres, "dieta", None)
        if dieta:
            bloco.append(Paragraph(f"<b>Dieta:</b> {dieta}", e["corpo"]))
        for i, item in enumerate(pres.itens, 1):
            partes = [f"<b>{i}. {item.nome_exibicao}</b>"]
            if item.dose:
                partes.append(item.dose)
            if item.via:
                partes.append(item.via)
            if item.frequencia:
                partes.append(item.frequencia)
            # Mesmo caso do `dieta` acima: ItemPrescricaoHosp não tem `duracao`
            # (quem tem é ItemPrescricao, o item ambulatorial).
            duracao = getattr(item, "duracao", None)
            if duracao:
                partes.append(f"por {duracao}")
            bloco.append(Paragraph(" · ".join(partes), e["corpo"]))
        s.append(KeepTogether(bloco))
        s.append(Spacer(1, 0.2 * cm))

    # ── Cirurgias realizadas ──
    cirurgias = list(internacao.cirurgias)
    if cirurgias:
        bloco = [Paragraph("Procedimentos Cirúrgicos Realizados", e["secao"])]
        for c in cirurgias:
            # O model chama o procedimento de `descricao` e a duração calculada
            # de `duracao_minutos`; `procedimento`/`duracao_real` não existem e
            # saíam em branco (ou estouravam) no sumário de alta.
            linha = f"<b>{c.descricao}</b>"
            if c.data_inicio:
                linha += f' — {c.data_inicio.strftime("%d/%m/%Y")}'
            if c.duracao_minutos:
                linha += f" ({c.duracao_minutos} min)"
            bloco.append(Paragraph(linha, e["corpo"]))
        s.append(KeepTogether(bloco))
        s.append(Spacer(1, 0.2 * cm))

    # ── Exames realizados ──
    from models.exame import ExameSolicitado

    # `ExameSolicitado` não tem FK para internação: o vínculo é o paciente mais a
    # janela da internação. Antes havia um filter_by(internacao_id=...) sobre
    # coluna inexistente, que estourava InvalidRequestError e derrubava o PDF.
    filtros = [ExameSolicitado.paciente_id == internacao.paciente_id]
    if internacao.data_entrada:
        filtros.append(ExameSolicitado.data_solicitacao >= internacao.data_entrada)
    # Fecha a janela na alta, para não trazer exame de internação posterior.
    if internacao.data_alta:
        filtros.append(ExameSolicitado.data_solicitacao <= internacao.data_alta)

    exames = (
        ExameSolicitado.query
        .filter(*filtros)
        .order_by(ExameSolicitado.data_solicitacao)
        .all()
    )
    if exames:
        bloco = [Paragraph("Exames Realizados", e["secao"])]
        for ex in exames[:10]:
            status_map = {
                "resultado": "Com resultado",
                "pendente": "Pendente",
                "cancelado": "Cancelado",
            }
            st = status_map.get(ex.status, ex.status)
            bloco.append(
                Paragraph(
                    # `ex.resultado` não existe: o model guarda o resultado em
                    # três colunas — `resultado_texto`, `resultado_valor` e
                    # `resultado_unidade`. O acesso levantava AttributeError e
                    # derrubava a geração do sumário de alta inteiro, mas só
                    # quando havia exame no período: com o exame fora da janela,
                    # o laço não executava e o defeito ficava invisível.
                    f'• {ex.tipo_exame.nome if ex.tipo_exame else "Exame"} — {st}'
                    + (f": {_resultado_do_exame(ex)[:80]}"
                       if _resultado_do_exame(ex) else ""),
                    e["corpo"],
                )
            )
        s.append(KeepTogether(bloco))
        s.append(Spacer(1, 0.2 * cm))

    # ── Orientações de alta ──
    s.append(
        KeepTogether(
            [
                Paragraph("Orientações e Recomendações de Alta", e["secao"]),
                Table(
                    [
                        [
                            Paragraph(
                                "Retornar ao serviço de saúde em caso de: febre, piora dos sintomas, "
                                "sangramento, dificuldade respiratória ou qualquer outra situação de alerta. "
                                "Seguir corretamente as orientações médicas e os medicamentos prescritos. "
                                "Comparecer às consultas de retorno agendadas.",
                                e["corpo_j"],
                            )
                        ]
                    ],
                    colWidths=[17.5 * cm],
                    style=[
                        ("BOX", (0, 0), (-1, -1), 0.5, VERDE),
                        ("BACKGROUND", (0, 0), (-1, -1), VERDEC),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ],
                ),
            ]
        )
    )
    s.append(Spacer(1, 0.4 * cm))

    # ── Retorno ──
    ret = Table(
        [
            [
                Paragraph("Retorno agendado em:", e["label"]),
                Paragraph("____ / ____ / ________", e["valor"]),
                Paragraph("Local:", e["label"]),
                Paragraph("_________________________________", e["valor"]),
            ]
        ],
        colWidths=[3.5 * cm, 4.5 * cm, 2 * cm, 7.5 * cm],
    )
    ret.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, CBORDA),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    s.append(ret)
    s.append(Spacer(1, 1.2 * cm))

    # ── Assinatura ──
    med_nome = medico.nome if medico else "—"
    med_crm = f"CRM {medico.crm}" if medico and medico.crm else ""
    assin = Table(
        [
            [
                Table(
                    [
                        [
                            Paragraph("_" * 40, e["centro"]),
                            Paragraph(med_nome, e["centro"]),
                            Paragraph(med_crm, e["centro"]),
                        ]
                    ],
                    colWidths=[8.75 * cm],
                ),
                Table(
                    [
                        [
                            Paragraph("_" * 40, e["centro"]),
                            Paragraph(
                                "Assinatura / Digital do paciente ou responsável",
                                e["centro"],
                            ),
                        ]
                    ],
                    colWidths=[8.75 * cm],
                ),
            ]
        ],
        colWidths=[8.75 * cm, 8.75 * cm],
    )
    s.append(assin)
    s.append(Spacer(1, 0.4 * cm))

    # ── Rodapé ──
    s.append(HRFlowable(width="100%", thickness=0.5, color=CBORDA))
    s.append(
        Paragraph(
            f'Documento gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}  ·  '
            f"Internação #{internacao.id}  ·  Sistema de Prontuário Único SUS",
            e["rodape"],
        )
    )

    doc.build(s)
    buf.seek(0)
    return buf
