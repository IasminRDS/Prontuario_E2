from extensions import db
from datetime import datetime

class Encaminhamento(db.Model):
    __tablename__ = 'encaminhamentos'

    id = db.Column(db.Integer, primary_key=True)
    
    # Relacionamentos FK
    paciente_id     = db.Column(db.Integer, db.ForeignKey('pacientes.id'),   nullable=False, index=True)
    prontuario_id   = db.Column(db.Integer, db.ForeignKey('prontuarios.id'), nullable=True, index=True)
    medico_id       = db.Column(db.Integer, db.ForeignKey('medicos.id'),     nullable=True, index=True)
    unidade_origem_id = db.Column(db.Integer, db.ForeignKey('unidades_saude.id'), nullable=False, index=True)

    # Dados do Encaminhamento
    especialidade   = db.Column(db.String(100), nullable=False)
    servico_destino = db.Column(db.String(200), nullable=True)
    prioridade      = db.Column(db.String(20), default='eletivo')

    # Diagnóstico e Motivo
    motivo          = db.Column(db.Text, nullable=False)
    hipotese_diagnostica = db.Column(db.String(200), nullable=True)
    cid             = db.Column(db.String(10),  nullable=True)

    status          = db.Column(db.String(20), default='solicitado')

    # Datas
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_agendada    = db.Column(db.DateTime, nullable=True)
    data_realizacao  = db.Column(db.DateTime, nullable=True)

    # Observações e Retorno
    observacoes      = db.Column(db.Text, nullable=True)
    retorno_info     = db.Column(db.Text, nullable=True)

    criado_por  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True,
        index=True,
    )

    # Relacionamentos (ORM)
    paciente       = db.relationship('Paciente',   backref='encaminhamentos')
    prontuario     = db.relationship('Prontuario', backref='encaminhamentos')
    medico         = db.relationship('Medico',     backref='encaminhamentos')
    unidade_origem = db.relationship('UnidadeSaude', backref='encaminhamentos')

    # Dicionários Auxiliares de Labels
    STATUS_LABELS = {
        'solicitado': ('Solicitado', 'cinza'),
        'agendado': ('Agendado', 'azul'),
        'realizado': ('Realizado', 'verde'),
        'cancelado': ('Cancelado', 'vermelho')
    }

    PRIORIDADE_LABELS = {
        'eletivo': ('Eletivo', 'verde'),
        'urgencia': ('Urgência', 'amarelo'),
        'emergencia': ('Emergência', 'vermelho')
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status, 'cinza'))

    @property
    def prioridade_label(self):
        return self.PRIORIDADE_LABELS.get(self.prioridade, (self.prioridade, 'cinza'))

    def __repr__(self):
        return f'<Encaminhamento {self.id} {self.especialidade}>'