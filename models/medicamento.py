from extensions import db
from datetime import datetime

class Medicamento(db.Model):
    __tablename__ = 'medicamentos'

    id = db.Column(db.Integer, primary_key=True)
    nome_generico = db.Column(db.String(150), nullable=False)
    nome_comercial = db.Column(db.String(150), nullable=True)
    classe = db.Column(db.String(100), nullable=True)
    apresentacao = db.Column(db.String(100), nullable=True)
    via_admin = db.Column(db.String(50), nullable=True)
    controlado = db.Column(db.Boolean, default=False)
    lista_rename = db.Column(db.String(10), nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    # Relacionamento com os itens de prescrição
    itens_prescricao = db.relationship('ItemPrescricao', backref='medicamento_referencia', lazy=True)

    def __repr__(self):
        return f'<Medicamento {self.nome_generico}>'


class Prescricao(db.Model):
    __tablename__ = 'prescricoes'

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False, index=True)
    prontuario_id = db.Column(db.Integer, db.ForeignKey('prontuarios.id'), nullable=True, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=True, index=True)
    unidade_id = db.Column(db.Integer, db.ForeignKey('unidades_saude.id'), nullable=True, index=True)
    
    tipo = db.Column(db.String(50), default='ambulatorial')
    validade_dias = db.Column(db.Integer, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='ativa')
    
    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True,
        index=True,
    )
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento com os Itens da Prescrição
    itens = db.relationship('ItemPrescricao', backref='prescricao', lazy=True, cascade="all, delete-orphan")

    # As chaves estrangeiras existiam, mas sem relação declarada: a tela da
    # prescrição não tinha como dizer de quem ela é. Mesmo padrão dos demais
    # agregados (Cirurgia, Internacao, Encaminhamento).
    paciente = db.relationship('Paciente', backref='prescricoes')
    medico = db.relationship('Medico', backref='prescricoes')

    # (texto, cor), como nos demais agregados. As chaves não mudaram, então o
    # `novo in Prescricao.STATUS_LABELS` de routes/medicamentos.py segue valendo.
    STATUS_LABELS = {
        'ativa': ('Ativa', 'verde'),
        'suspensa': ('Suspensa', 'amarelo'),
        'concluida': ('Concluída', 'azul'),
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status or '—', 'cinza'))

    def __repr__(self):
        return f'<Prescricao {self.id} Paciente {self.paciente_id}>'


class ItemPrescricao(db.Model):
    __tablename__ = 'itens_prescricao'

    id = db.Column(db.Integer, primary_key=True)
    prescricao_id = db.Column(db.Integer, db.ForeignKey('prescricoes.id'), nullable=False, index=True)
    # Escopo territorial do RLS, desnormalizado da prescrição.
    unidade_id = db.Column(db.Integer, db.ForeignKey('unidades_saude.id'),
                           nullable=False, index=True)
    medicamento_id = db.Column(db.Integer, db.ForeignKey('medicamentos.id'), nullable=True, index=True)
    
    nome_livre = db.Column(db.String(150), nullable=True) # Caso o médico digite um remédio que não está no catálogo
    dose = db.Column(db.String(100), nullable=True)
    via = db.Column(db.String(50), nullable=True)
    frequencia = db.Column(db.String(100), nullable=True)
    duracao = db.Column(db.String(100), nullable=True)
    quantidade = db.Column(db.String(50), nullable=True)
    instrucoes = db.Column(db.Text, nullable=True)

    @property
    def nome_exibicao(self):
        """Nome do item para a tela: o do catálogo, ou o que o médico digitou.

        Os templates já chamavam `item.nome_exibicao`; a propriedade não existia
        e o Jinja renderizava vazio — a linha da prescrição aparecia sem o nome
        do medicamento, sem erro nenhum.
        """
        if self.medicamento_referencia:
            return self.medicamento_referencia.nome_generico
        return self.nome_livre or '—'

    def __repr__(self):
        nome = self.nome_livre if self.nome_livre else f'MedID {self.medicamento_id}'
        return f'<ItemPrescricao {nome}>'