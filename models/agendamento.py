from extensions import db
from datetime import datetime


class Agendamento(db.Model):
    __tablename__ = "agendamentos"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey("medicos.id"), nullable=True)
    unidade_id = db.Column(
        db.Integer, db.ForeignKey("unidades_saude.id"), nullable=False
    )  # <- aqui
    criado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    data_hora = db.Column(db.DateTime, nullable=False)
    tipo = db.Column(db.String(30), default="consulta")

    status = db.Column(db.String(20), default="agendado")

    observacoes = db.Column(db.Text, nullable=True)
    motivo_cancel = db.Column(db.String(200), nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    paciente = db.relationship("Paciente", backref="agendamentos")
    medico = db.relationship("Medico", backref="agendamentos")
    unidade = db.relationship("UnidadeSaude", backref="agendamentos")

    # routes/agendamento.py já usava `Agendamento.STATUS_LABELS` para validar o
    # status recebido e `ag.status_label[0]` na mensagem de sucesso — nenhum dos
    # dois existia, e a troca de status quebrava com AttributeError.
    STATUS_LABELS = {
        "agendado": ("Agendado", "azul"),
        "confirmado": ("Confirmado", "verde"),
        "atendido": ("Atendido", "verde"),
        "faltou": ("Faltou", "amarelo"),
        "cancelado": ("Cancelado", "cinza"),
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status or "—", "cinza"))

    # A API de horários (routes/agendamento.py) devolve `a.tipo_label` no JSON.
    # A propriedade não existia: a rota estourava assim que houvesse um
    # agendamento no dia consultado — com a agenda vazia, ninguém percebia.
    TIPO_LABELS = {
        "consulta": "Consulta",
        "retorno": "Retorno",
        "exame": "Exame",
        "procedimento": "Procedimento",
        "vacina": "Vacina",
    }

    @property
    def tipo_label(self):
        return self.TIPO_LABELS.get(self.tipo, (self.tipo or "—").capitalize())
