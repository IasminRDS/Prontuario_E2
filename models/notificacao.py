# -*- coding: utf-8 -*-
"""Notificação compulsória (SINAN) — porte do model `NotificacaoCompulsoria`.

Um agravo de notificação obrigatória é detectado pelo CID informado no
atendimento e entra numa fila para o serviço de vigilância epidemiológica
despachar ao SINAN.
"""
from datetime import datetime

from extensions import db

# Agravos de notificação compulsória (Portaria GM/MS 217/2023), por prefixo CID-10.
# Mapa reduzido ao que o sistema cobre; a chave é o prefixo, o valor é o agravo.
AGRAVOS_POR_CID = {
    "A00": "Cólera",
    "A01": "Febre tifoide e paratifoide",
    "A05": "Intoxicação alimentar bacteriana",
    "A15": "Tuberculose respiratória",
    "A16": "Tuberculose respiratória (sem confirmação)",
    "A17": "Tuberculose do sistema nervoso",
    "A18": "Tuberculose de outros órgãos",
    "A19": "Tuberculose miliar",
    "A20": "Peste",
    "A22": "Carbúnculo (antraz)",
    "A23": "Brucelose",
    "A27": "Leptospirose",
    "A30": "Hanseníase",
    "A33": "Tétano neonatal",
    "A35": "Tétano acidental",
    "A36": "Difteria",
    "A37": "Coqueluche",
    "A39": "Doença meningocócica",
    "A50": "Sífilis congênita",
    "A51": "Sífilis adquirida recente",
    "A53": "Sífilis não especificada",
    "A80": "Poliomielite",
    "A82": "Raiva humana",
    "A90": "Dengue",
    "A91": "Dengue com sinais de alarme",
    "A92": "Febre de Chikungunya / Zika",
    "A95": "Febre amarela",
    "B05": "Sarampo",
    "B06": "Rubéola",
    "B15": "Hepatite A",
    "B16": "Hepatite B",
    "B17": "Hepatite viral aguda (outras)",
    "B18": "Hepatite viral crônica",
    "B19": "Hepatite viral não especificada",
    "B20": "HIV/AIDS",
    "B21": "HIV/AIDS",
    "B22": "HIV/AIDS",
    "B23": "HIV/AIDS",
    "B24": "HIV/AIDS",
    "B50": "Malária",
    "B51": "Malária",
    "B52": "Malária",
    "B53": "Malária",
    "B54": "Malária",
    "B55": "Leishmaniose",
    "B57": "Doença de Chagas",
    "J09": "Influenza por vírus identificado",
    "J10": "Influenza por vírus identificado",
    "J11": "Influenza por vírus não identificado",
    "U07": "Covid-19",
    "T78": "Anafilaxia / evento adverso",
    "X20": "Acidente por animal peçonhento",
    "X29": "Acidente por animal peçonhento",
    "Y58": "Evento adverso pós-vacinação",
}

STATUS = ("pendente", "enviada", "descartada")


def agravo_para_cid(cid):
    """Devolve o nome do agravo se o CID for de notificação compulsória."""
    if not cid:
        return None
    chave = str(cid).strip().upper().replace(".", "")[:3]
    return AGRAVOS_POR_CID.get(chave)


class NotificacaoCompulsoria(db.Model):
    __tablename__ = "notificacoes_compulsorias"

    id = db.Column(db.Integer, primary_key=True)

    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)
    prontuario_id = db.Column(db.Integer, db.ForeignKey("prontuarios.id"), nullable=True)
    unidade_id = db.Column(db.Integer, db.ForeignKey("unidades_saude.id"), nullable=True, index=True)

    cid = db.Column(db.String(10), nullable=False, index=True)
    agravo = db.Column(db.String(120), nullable=False)

    status = db.Column(db.String(20), nullable=False, default="pendente", index=True)
    # pendente | enviada | descartada

    observacoes = db.Column(db.Text, nullable=True)
    motivo_descarte = db.Column(db.String(255), nullable=True)

    # Nº de retorno do SINAN, quando a ficha é aceita.
    numero_sinan = db.Column(db.String(30), nullable=True)

    detectado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    resolvido_em = db.Column(db.DateTime, nullable=True)
    resolvido_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    paciente = db.relationship("Paciente", backref="notificacoes")
    unidade = db.relationship("UnidadeSaude", backref="notificacoes")

    def __repr__(self):
        return f"<NotificacaoCompulsoria {self.cid} {self.status}>"
