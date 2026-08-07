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
    # Espelha `unidade_origem_id`. Redundante de propósito: `tabelas_protegidas`
    # descobre o escopo pela coluna `unidade_id`, e uma política especial só
    # para esta tabela seria a exceção que ninguém lembra de manter.
    unidade_id = db.Column(db.Integer, db.ForeignKey('unidades_saude.id'),
                           nullable=False, index=True)

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
    # `foreign_keys` é obrigatório desde que a tabela passou a ter DUAS chaves
    # para `unidades_saude` (origem e escopo do RLS): sem isto o mapeamento
    # falha inteiro com AmbiguousForeignKeysError.
    unidade_origem = db.relationship('UnidadeSaude', backref='encaminhamentos',
                                     foreign_keys=[unidade_origem_id])

    # Dicionários Auxiliares de Labels
    STATUS_LABELS = {
        'solicitado': ('Solicitado', 'cinza'),
        'agendado': ('Agendado', 'azul'),
        'realizado': ('Realizado', 'verde'),
        'cancelado': ('Cancelado', 'vermelho')
    }

    # Vocabulário de prioridade, DA MAIS GRAVE PARA A MENOS. A ordem é
    # significativa: as filas de encaminhamento e de regulação ordenam por ela.
    #
    # Este dicionário é a autoridade sobre quais prioridades existem. Fica no
    # model, e não na rota que as valida, porque é o único lugar que services e
    # templates alcançam sem import circular — e o vocabulário já esteve escrito
    # em cinco lugares, com três conteúdos diferentes: a rota gravava
    # `prioritario`, o painel não sabia rotulá-lo e o mostrava cru e cinza, e o
    # PDF conhecia um `urgente` que a rota nunca grava, imprimindo "EMERGENCIA"
    # sem acento pelo fallback.
    PRIORIDADE_LABELS = {
        'emergencia': ('Emergência', 'vermelho'),
        'urgencia': ('Urgência', 'amarelo'),
        'prioritario': ('Prioritário', 'azul'),
        'eletivo': ('Eletivo', 'verde'),
    }

    #: Chaves aceitas, na ordem de gravidade acima.
    PRIORIDADES = tuple(PRIORIDADE_LABELS)

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status, 'cinza'))

    @property
    def prioridade_label(self):
        return self.PRIORIDADE_LABELS.get(self.prioridade, (self.prioridade, 'cinza'))

    def __repr__(self):
        return f'<Encaminhamento {self.id} {self.especialidade}>'