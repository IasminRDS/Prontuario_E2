# -*- coding: utf-8 -*-
"""Pares de pacientes suspeitos de serem a mesma pessoa.

A decisão sobre um par é permanente e precisa sobreviver a novas varreduras:
sem isto, todo par que alguém já analisou e considerou pessoas distintas voltaria
à fila na varredura seguinte, e a tela viraria ruído que ninguém olha.
"""
from datetime import datetime

from extensions import db


class CandidatoDuplicata(db.Model):
    __tablename__ = "candidatos_duplicata"
    __table_args__ = (
        # O par é o mesmo em qualquer ordem; guardamos sempre com o menor id
        # primeiro para que a restrição de unicidade funcione.
        db.UniqueConstraint("paciente_menor_id", "paciente_maior_id",
                            name="uq_candidato_par"),
    )

    id = db.Column(db.Integer, primary_key=True)

    paciente_menor_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"),
                                  nullable=False, index=True)
    paciente_maior_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"),
                                  nullable=False, index=True)

    score = db.Column(db.Float, nullable=False, default=0.0, index=True)
    evidencias = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="pendente",
                       index=True)
    # pendente | unificado | distintos

    # Para onde os registros foram, quando o par foi unificado.
    sobrevivente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"),
                                nullable=True, index=True)

    detectado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    decidido_em = db.Column(db.DateTime, nullable=True)
    decidido_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    menor = db.relationship("Paciente", foreign_keys=[paciente_menor_id])
    maior = db.relationship("Paciente", foreign_keys=[paciente_maior_id])
    sobrevivente = db.relationship("Paciente", foreign_keys=[sobrevivente_id])

    STATUS_LABELS = {
        "pendente": ("Aguardando revisão", "amarelo"),
        "unificado": ("Unificado", "verde"),
        "distintos": ("Pessoas distintas", "cinza"),
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status or "—", "cinza"))

    @property
    def confianca(self):
        """Rótulo da força da evidência, para a tela não mostrar número cru."""
        from utils.identidade import LIMIAR_FORTE

        if self.score >= 1.0:
            return ("Documento coincidente", "vermelho")
        if self.score >= LIMIAR_FORTE:
            return ("Forte", "laranja")
        return ("Moderada", "amarelo")

    def __repr__(self):
        return (f"<CandidatoDuplicata {self.paciente_menor_id}~"
                f"{self.paciente_maior_id} {self.score:.2f}>")
