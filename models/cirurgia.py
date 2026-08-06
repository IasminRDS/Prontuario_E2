from extensions import db
from datetime import datetime

class SalaCirurgica(db.Model):
    __tablename__ = 'salas_cirurgicas'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    tipo = db.Column(db.String(50), nullable=False) # ex: geral, ortopedia, urgencia
    ativa = db.Column(db.Boolean, default=True)

    # Relacionamento com as cirurgias
    cirurgias = db.relationship('Cirurgia', backref='sala', lazy=True)

    def __repr__(self):
        return f'<SalaCirurgica {self.nome}>'


class Cirurgia(db.Model):
    __tablename__ = 'cirurgias'

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=True, index=True) # Cirurgião principal
    sala_id = db.Column(db.Integer, db.ForeignKey('salas_cirurgicas.id'), nullable=True, index=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey('internacoes.id'), nullable=True, index=True)

    descricao = db.Column(db.String(255), nullable=False) # Nome/tipo do procedimento
    status = db.Column(db.String(20), default='agendada') # agendada, em_andamento, concluida, cancelada
    
    data_agendada = db.Column(db.DateTime, nullable=True)
    data_inicio = db.Column(db.DateTime, nullable=True)
    data_fim = db.Column(db.DateTime, nullable=True)
    
    observacoes = db.Column(db.Text, nullable=True)
    
    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True,
        index=True,
    )
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relações explícitas: `sala` já vem do backref em SalaCirurgica.
    paciente = db.relationship('Paciente', backref='cirurgias')
    medico = db.relationship('Medico', backref='cirurgias')
    # O sumário de alta lista as cirurgias da internação por `internacao.cirurgias`.
    internacao = db.relationship('Internacao', backref='cirurgias')

    # Rótulos de apresentação. Devolvem (texto, cor) para os templates não
    # precisarem conhecer os valores crus do banco — mesmo padrão de
    # Internacao.status_label e Leito.status_label.
    STATUS = {
        'agendada': ('Agendada', 'azul'),
        'em_andamento': ('Em andamento', 'amarelo'),
        'concluida': ('Concluída', 'verde'),
        'realizada': ('Realizada', 'verde'),
        'cancelada': ('Cancelada', 'cinza'),
        'suspensa': ('Suspensa', 'vermelho'),
    }

    @property
    def status_label(self):
        return self.STATUS.get(self.status, (self.status or '—', 'cinza'))

    @property
    def carater_label(self):
        """Caráter do procedimento, derivado da sala.

        O modelo espelha o schema do monorepo, que não guarda caráter em coluna
        própria; sala de urgência implica procedimento de urgência.
        """
        tipo = (self.sala.tipo if self.sala else '') or ''
        if 'urgen' in tipo.lower() or 'emerg' in tipo.lower():
            return ('Urgência', 'vermelho')
        return ('Eletiva', 'cinza')

    @property
    def duracao_minutos(self):
        if not (self.data_inicio and self.data_fim):
            return None
        return int((self.data_fim - self.data_inicio).total_seconds() // 60)

    def __repr__(self):
        return f'<Cirurgia {self.id} Status: {self.status}>'