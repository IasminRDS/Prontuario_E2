from extensions import db
from datetime import datetime

class AIH(db.Model):
    """Autorização de Internação Hospitalar"""
    __tablename__ = 'faturamento_aih'

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    internacao_id = db.Column(db.Integer, db.ForeignKey('internacoes.id'), nullable=True)
    medico_solicitante_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=True)

    numero_aih = db.Column(db.String(20), unique=True, nullable=True)
    procedimento_principal = db.Column(db.String(255), nullable=False)
    cid_principal = db.Column(db.String(10), nullable=True)

    data_emissao = db.Column(db.Date, default=datetime.utcnow)
    data_apresentacao = db.Column(db.Date, nullable=True)
    
    valor_total = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(20), default='aberta') # aberta, faturada, rejeitada, cancelada
    
    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # As FKs existiam sem relação declarada: a lista de AIH não conseguia
    # mostrar de quem era a autorização.
    paciente = db.relationship('Paciente', backref='aihs')
    medico_solicitante = db.relationship('Medico', backref='aihs')
    internacao = db.relationship('Internacao', backref='aihs')

    # Rótulos de apresentação (texto, cor). Cobre tanto os status de STATUS_AIH
    # em routes/faturamento.py quanto 'faturada', que aparece em dados antigos.
    STATUS = {
        'aberta': ('Aberta', 'azul'),
        'apresentada': ('Apresentada', 'amarelo'),
        'aprovada': ('Aprovada', 'verde'),
        'faturada': ('Faturada', 'verde'),
        'rejeitada': ('Rejeitada', 'vermelho'),
        'cancelada': ('Cancelada', 'cinza'),
    }

    @property
    def status_label(self):
        return self.STATUS.get(self.status, (self.status or '—', 'cinza'))

    def __repr__(self):
        return f'<AIH {self.numero_aih} - Status: {self.status}>'


class APAC(db.Model):
    """Autorização de Procedimentos Ambulatoriais de Alta Complexidade"""
    __tablename__ = 'faturamento_apac'

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    medico_solicitante_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=True)

    numero_apac = db.Column(db.String(20), unique=True, nullable=True)
    procedimento_principal = db.Column(db.String(255), nullable=False)
    cid_principal = db.Column(db.String(10), nullable=True)

    data_inicio_validade = db.Column(db.Date, nullable=False)
    data_fim_validade = db.Column(db.Date, nullable=False)
    
    quantidade_aprovada = db.Column(db.Integer, default=1)
    quantidade_realizada = db.Column(db.Integer, default=0)

    valor_total = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(20), default='ativa') # ativa, encerrada, cancelada

    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    paciente = db.relationship('Paciente', backref='apacs')
    medico_solicitante = db.relationship('Medico', backref='apacs')

    STATUS = {
        'ativa': ('Ativa', 'verde'),
        'encerrada': ('Encerrada', 'azul'),
        'cancelada': ('Cancelada', 'cinza'),
    }

    @property
    def status_label(self):
        return self.STATUS.get(self.status, (self.status or '—', 'cinza'))

    def __repr__(self):
        return f'<APAC {self.numero_apac} - Status: {self.status}>'