from extensions import db
from datetime import datetime

class AtendimentoPS(db.Model):
    __tablename__ = 'atendimentos_ps'

    id = db.Column(db.Integer, primary_key=True)
    
    # Relacionamentos
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=True)
    triagem_id = db.Column(db.Integer, db.ForeignKey('triagens.id'), nullable=True)
    
    # Dados do Atendimento
    motivo_consulta = db.Column(db.Text, nullable=False)
    diagnostico_preliminar = db.Column(db.Text, nullable=True)
    conduta = db.Column(db.Text, nullable=True)
    
    # Status e Tempo
    status = db.Column(db.String(50), default='em_espera') # em_espera, em_atendimento, internado, alta, obito
    data_chegada = db.Column(db.DateTime, default=datetime.utcnow)
    data_atendimento = db.Column(db.DateTime, nullable=True)
    data_liberacao = db.Column(db.DateTime, nullable=True)
    
    # Controle
    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relacionamento reverso com o paciente
    paciente = db.relationship('Paciente', backref=db.backref('atendimentos_ps', lazy=True))
    # A classificação de risco mora na triagem; o atendimento só aponta para ela.
    triagem = db.relationship('Triagem', backref=db.backref('atendimentos_ps', lazy=True))
    medico = db.relationship('Medico', backref=db.backref('atendimentos_ps', lazy=True))

    # Rótulos de apresentação, no mesmo formato (texto, cor) de Internacao e
    # Cirurgia — o template não conhece o valor cru do banco.
    # Os nomes seguem a máquina de estados de routes/ps.py (TRANSICOES), que é
    # quem manda. O comentário antigo da coluna listava só cinco e omitia
    # 'em_observacao', 'transferido' e 'evadiu'.
    STATUS = {
        'em_espera': ('Em espera', 'amarelo'),
        'em_atendimento': ('Em atendimento', 'azul'),
        'em_observacao': ('Em observação', 'azul'),
        'internado': ('Internado', 'vermelho'),
        'transferido': ('Transferido', 'azul'),
        'alta': ('Alta', 'verde'),
        'obito': ('Óbito', 'cinza'),
        'evadiu': ('Evadiu', 'cinza'),
        'cancelado': ('Cancelado', 'cinza'),
    }

    # Status que encerram o atendimento — são estes que contam como desfecho.
    DESFECHOS = ('alta', 'internado', 'transferido', 'obito', 'evadiu')

    @property
    def status_label(self):
        return self.STATUS.get(self.status, (self.status or '—', 'cinza'))

    @property
    def classificacao(self):
        """Cor de risco Manchester, herdada da triagem.

        Templates e relatórios já liam `atendimento.classificacao` como se fosse
        coluna própria. Não é: o dado é da triagem, e um atendimento pode não ter
        sido triado ainda.
        """
        return self.triagem.classificacao if self.triagem else None

    @property
    def cor_info(self):
        """(rótulo, cor hex, tempo-alvo) da classificação — delega à triagem."""
        if self.triagem:
            return self.triagem.cor_info
        return ('Não triado', '#888', '—')

    @property
    def desfecho(self):
        """Como o atendimento terminou, ou None se ainda está em curso."""
        return self.status if self.status in self.DESFECHOS else None

    @property
    def tempo_espera_min(self):
        """Minutos até ser chamado — ou até agora, se ainda espera.

        O painel do PS compara este valor com faixas (>60, >120) para colorir a
        fila, então precisa ser sempre um número, nunca None.
        """
        if not self.data_chegada:
            return 0
        fim = self.data_atendimento or datetime.utcnow()
        return max(0, int((fim - self.data_chegada).total_seconds() // 60))

    @property
    def tempo_total_min(self):
        """Minutos entre a chegada e a liberação. None enquanto não liberado."""
        if not (self.data_chegada and self.data_liberacao):
            return None
        return int((self.data_liberacao - self.data_chegada).total_seconds() // 60)

    def __repr__(self):
        return f'<AtendimentoPS {self.id} - Status: {self.status}>'