# -*- coding: utf-8 -*-
from extensions import db
from datetime import datetime


class TipoExame(db.Model):
    """Catálogo de tipos de exame (tabela de referência)."""

    __tablename__ = "tipos_exame"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(20), unique=True, nullable=False)  # ex: HMG, URO
    nome = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(50), nullable=True)
    # laboratorial | imagem | funcional | anatomopatologico | outro
    instrucoes = db.Column(db.Text, nullable=True)  # preparo do paciente
    ativo = db.Column(db.Boolean, default=True)

    solicitacoes = db.relationship(
        "ExameSolicitado", backref="tipo_exame", lazy="dynamic"
    )

    def __repr__(self):
        return f"<TipoExame {self.codigo}>"


class ExameSolicitado(db.Model):
    """Solicitação de exame vinculada a um atendimento/prontuário."""

    __tablename__ = "exames_solicitados"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)
    prontuario_id = db.Column(
        db.Integer, db.ForeignKey("prontuarios.id"), nullable=True,
        index=True,
    )
    medico_id = db.Column(db.Integer, db.ForeignKey("medicos.id"), nullable=True, index=True)
    unidade_id = db.Column(
        db.Integer, db.ForeignKey("unidades_saude.id"), nullable=False,
        index=True,
    )
    tipo_exame_id = db.Column(
        db.Integer, db.ForeignKey("tipos_exame.id"), nullable=False,
        index=True,
    )

    status = db.Column(db.String(20), default="solicitado")
    # solicitado | coletado | em_analise | resultado_disponivel | cancelado

    urgencia = db.Column(db.String(10), default="rotina")
    # rotina | urgente | urgentissimo

    indicacao_clinica = db.Column(db.Text, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    # Resultado
    resultado_texto = db.Column(db.Text, nullable=True)
    resultado_valor = db.Column(db.String(100), nullable=True)
    resultado_unidade = db.Column(db.String(30), nullable=True)
    valor_referencia = db.Column(db.String(100), nullable=True)
    interpretacao = db.Column(db.String(20), nullable=True)
    # normal | alterado | critico | indeterminado

    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_coleta = db.Column(db.DateTime, nullable=True)
    data_resultado = db.Column(db.DateTime, nullable=True)

    criado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True,
        index=True,
    )

    # Relacionamentos
    paciente = db.relationship("Paciente", backref="exames_solicitados")
    prontuario = db.relationship("Prontuario", backref="exames_solicitados")
    medico = db.relationship("Medico", backref="exames_solicitados")
    unidade = db.relationship("UnidadeSaude", backref="exames_solicitados")

    STATUS_LABELS = {
        "solicitado": ("Solicitado", "cinza"),
        "coletado": ("Coletado", "azul"),
        "em_analise": ("Em análise", "amarelo"),
        "resultado_disponivel": ("Resultado disponível", "verde"),
        "cancelado": ("Cancelado", "vermelho"),
    }

    URGENCIA_LABELS = {
        "rotina": ("Rotina", "cinza"),
        "urgente": ("Urgente", "amarelo"),
        "urgentissimo": ("Urgentíssimo", "vermelho"),
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status, "cinza"))

    @property
    def urgencia_label(self):
        return self.URGENCIA_LABELS.get(self.urgencia, (self.urgencia, "cinza"))

    def __repr__(self):
        return f"<ExameSolicitado {self.id} {self.status}>"
