from extensions import db
from datetime import datetime


class Prontuario(db.Model):
    __tablename__ = "prontuarios"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)
    atendimento_id = db.Column(
        db.Integer, db.ForeignKey("atendimentos.id"), nullable=True,
        index=True,
    )
    medico_id = db.Column(db.Integer, db.ForeignKey("medicos.id"), nullable=True, index=True)
    unidade_id = db.Column(
        db.Integer, db.ForeignKey("unidades_saude.id"), nullable=False,
        index=True,
    )

    # SOAP (padrão de prontuário clínico)
    subjetivo = db.Column(db.Text, nullable=True)  # S - Queixa / anamnese

    objetivo = db.Column(db.Text, nullable=True)  # O - Exame físico / dados objetivos
    avaliacao = db.Column(db.Text, nullable=True)  # A - Diagnóstico / hipóteses
    plano = db.Column(db.Text, nullable=True)  # P - Conduta / prescrição

    # Dados vitais
    pressao_arterial = db.Column(db.String(10), nullable=True)
    temperatura = db.Column(db.Float, nullable=True)
    frequencia_cardiaca = db.Column(db.Integer, nullable=True)
    frequencia_respiratoria = db.Column(db.Integer, nullable=True)
    saturacao_o2 = db.Column(db.Float, nullable=True)
    peso = db.Column(db.Float, nullable=True)
    altura = db.Column(db.Float, nullable=True)
    glicemia = db.Column(db.Float, nullable=True)

    # CID-10
    cid_principal = db.Column(db.String(10), nullable=True)
    cid_secundario = db.Column(db.String(10), nullable=True)

    # Prescrição / encaminhamentos
    prescricao = db.Column(db.Text, nullable=True)
    encaminhamento = db.Column(db.Text, nullable=True)
    retorno_dias = db.Column(db.Integer, nullable=True)

    # Controle
    assinado = db.Column(db.Boolean, default=False)
    assinado_em = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    medico = db.relationship("Medico", backref="prontuarios")
    unidade = db.relationship("UnidadeSaude", backref="prontuarios")

    @property
    def imc(self):
        if self.peso and self.altura and self.altura > 0:
            return round(self.peso / (self.altura**2), 1)
        return None

    def assinar(self):
        self.assinado = True
        self.assinado_em = datetime.utcnow()

    def __repr__(self):
        return f"<Prontuario {self.id} - Paciente {self.paciente_id}>"
