from extensions import db
from datetime import datetime

class AIH(db.Model):
    """Autorização de Internação Hospitalar"""
    __tablename__ = 'faturamento_aih'

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False, index=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey('internacoes.id'), nullable=True, index=True)
    medico_solicitante_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=True, index=True)

    numero_aih = db.Column(db.String(20), unique=True, nullable=True)
    procedimento_principal = db.Column(db.String(255), nullable=False)
    cid_principal = db.Column(db.String(10), nullable=True)

    # --- campos da AIH que as telas pediam e o schema não tinha (e2f7b48c9d13)
    competencia = db.Column(db.String(7), nullable=True, index=True)  # AAAA/MM
    tipo_aih = db.Column(db.String(2), nullable=True)
    carater_internacao = db.Column(db.String(2), nullable=True)
    cid_secundario = db.Column(db.String(10), nullable=True)
    procedimento_secundario = db.Column(db.String(255), nullable=True)
    data_internacao = db.Column(db.Date, nullable=True)
    data_saida = db.Column(db.Date, nullable=True)
    motivo_saida = db.Column(db.String(40), nullable=True)
    valor_sh = db.Column(db.Numeric(10, 2), nullable=True)
    valor_sp = db.Column(db.Numeric(10, 2), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    data_emissao = db.Column(db.Date, default=datetime.utcnow)
    data_apresentacao = db.Column(db.Date, nullable=True)

    valor_total = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(20), default='aberta') # aberta, faturada, rejeitada, cancelada
    
    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True,
        index=True,
    )
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

    @property
    def dias_permanencia(self):
        """Dias entre internação e saída.

        Propriedade e NÃO coluna: guardar o derivado ao lado das duas datas cria
        a chance de divergirem, e quando divergem não há como saber qual está
        certo. O formulário exibe este valor calculado em vez de pedir que
        alguém o digite.
        """
        if not self.data_internacao or not self.data_saida:
            return None
        return max((self.data_saida - self.data_internacao).days, 0)

    def __repr__(self):
        return f'<AIH {self.numero_aih} - Status: {self.status}>'


class APAC(db.Model):
    """Autorização de Procedimentos Ambulatoriais de Alta Complexidade"""
    __tablename__ = 'faturamento_apac'

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False, index=True)
    medico_solicitante_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=True, index=True)

    numero_apac = db.Column(db.String(20), unique=True, nullable=True)
    procedimento_principal = db.Column(db.String(255), nullable=False)
    cid_principal = db.Column(db.String(10), nullable=True)

    # --- campos da APAC que a tela pedia e o schema não tinha (e2f7b48c9d13).
    # `cid` e `procedimento`, que o template usava, NÃO viraram coluna: eram
    # apelidos de `cid_principal` e `procedimento_principal`, que já existiam.
    competencia = db.Column(db.String(7), nullable=True, index=True)  # AAAA/MM
    tipo = db.Column(db.String(20), nullable=True)
    justificativa = db.Column(db.Text, nullable=True)

    data_inicio_validade = db.Column(db.Date, nullable=False)
    data_fim_validade = db.Column(db.Date, nullable=False)
    
    quantidade_aprovada = db.Column(db.Integer, default=1)
    quantidade_realizada = db.Column(db.Integer, default=0)

    valor_total = db.Column(db.Numeric(10, 2), nullable=True)
    status = db.Column(db.String(20), default='ativa') # ativa, encerrada, cancelada

    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True,
        index=True,
    )
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