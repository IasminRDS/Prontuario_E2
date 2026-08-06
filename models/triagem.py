# -*- coding: utf-8 -*-
from extensions import db
from datetime import datetime


class Triagem(db.Model):
    __tablename__ = "triagens"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)
    unidade_id = db.Column(
        db.Integer, db.ForeignKey("unidades_saude.id"), nullable=False,
        index=True,
    )
    realizado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    agendamento_id = db.Column(
        db.Integer, db.ForeignKey("agendamentos.id"), nullable=True,
        index=True,
    )

    # Classificação de risco - Protocolo Manchester
    classificacao = db.Column(db.String(20), nullable=False, default="verde")
    # vermelho | laranja | amarelo | verde | azul

    queixa_principal = db.Column(db.String(200), nullable=True)

    # Sinais vitais na triagem
    pressao_arterial = db.Column(db.String(10), nullable=True)
    temperatura = db.Column(db.Float, nullable=True)
    frequencia_cardiaca = db.Column(db.Integer, nullable=True)
    frequencia_respiratoria = db.Column(db.Integer, nullable=True)
    saturacao_o2 = db.Column(db.Float, nullable=True)
    glicemia = db.Column(db.Float, nullable=True)
    peso = db.Column(db.Float, nullable=True)
    altura = db.Column(db.Float, nullable=True)
    dor_escala = db.Column(db.Integer, nullable=True)  # 0-10

    # Discriminadores Manchester
    discriminadores = db.Column(db.Text, nullable=True)  # JSON list
    observacoes = db.Column(db.Text, nullable=True)

    status = db.Column(db.String(20), default="aguardando")
    # aguardando | em_atendimento | finalizado

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamentos
    paciente = db.relationship("Paciente", backref="triagens")
    unidade = db.relationship("UnidadeSaude", backref="triagens")
    responsavel = db.relationship("User", backref="triagens")

    CORES = {
        "vermelho": ("Emergência", "#C0392B", "Imediato"),
        "laranja": ("Muito urgente", "#E67E22", "10 min"),
        "amarelo": ("Urgente", "#F1C40F", "60 min"),
        "verde": ("Pouco urgente", "#27AE60", "120 min"),
        "azul": ("Não urgente", "#2980B9", "240 min"),
    }

    @property
    def cor_info(self):
        return self.CORES.get(self.classificacao, ("Indefinido", "#888", "—"))

    @property
    def imc(self):
        if self.peso and self.altura and self.altura > 0:
            return round(self.peso / (self.altura**2), 1)
        return None

    def __repr__(self):
        return f"<Triagem {self.id} {self.classificacao}>"
