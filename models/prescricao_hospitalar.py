from extensions import db
from datetime import datetime

class PrescricaoHospitalar(db.Model):
    __tablename__ = 'prescricoes_hospitalares'

    id = db.Column(db.Integer, primary_key=True)
    internacao_id = db.Column(db.Integer, db.ForeignKey('internacoes.id'), nullable=True, index=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=True, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=True, index=True)
    unidade_id = db.Column(db.Integer, db.ForeignKey('unidades_saude.id'), nullable=True, index=True)

    data_prescricao = db.Column(db.DateTime, default=datetime.utcnow)
    # `validade_horas` é a janela declarada; `validade_ate` é o instante em que
    # ela expira, gravado no ato da prescrição. O segundo é o que a rota já
    # calculava — sem ele, reler a validade dependia de refazer a conta.
    validade_horas = db.Column(db.Integer, default=24)
    validade_ate = db.Column(db.DateTime, nullable=True)

    # Prescrição hospitalar não é só medicamento: dieta, decúbito e a rotina de
    # sinais vitais fazem parte do mesmo documento e já eram coletados na rota.
    dieta = db.Column(db.Text, nullable=True)
    decubito = db.Column(db.Text, nullable=True)
    sinais_vitais = db.Column(db.Text, nullable=True)

    observacoes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='ativa') # ativa, finalizada, suspensa

    # Assinatura, no mesmo formato de Prontuario.assinar().
    assinada_em = db.Column(db.DateTime, nullable=True)
    assinada_por = db.Column(db.Integer, db.ForeignKey('medicos.id'), nullable=True, index=True)

    criado_por = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True,
        index=True,
    )
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    # Relacionamento com os itens da prescrição
    itens = db.relationship('ItemPrescricaoHosp', backref='prescricao_hospitalar',
                            lazy=True, cascade="all, delete-orphan",
                            order_by='ItemPrescricaoHosp.ordem')

    # As chaves estrangeiras existiam sem relação declarada — a tela não sabia
    # de quem era a prescrição nem a qual internação pertencia.
    paciente = db.relationship('Paciente', backref='prescricoes_hospitalares')
    internacao = db.relationship('Internacao', backref='prescricoes_hospitalares')
    unidade = db.relationship('UnidadeSaude', backref='prescricoes_hospitalares')
    # São dois caminhos até `medicos` (quem prescreveu e quem assinou), então o
    # SQLAlchemy exige que cada relação diga por qual coluna vai.
    medico = db.relationship('Medico', foreign_keys=[medico_id],
                             backref='prescricoes_hospitalares')
    assinante = db.relationship('Medico', foreign_keys=[assinada_por],
                                backref='prescricoes_hospitalares_assinadas')

    @property
    def assinada(self):
        return self.assinada_em is not None

    def assinar(self, medico=None):
        """Carimba a assinatura. Sem médico informado, assume o prescritor.

        Recusa assinar sem responsável identificável: `assinada_em` preenchido
        com `assinada_por` nulo seria uma prescrição "assinada por ninguém" —
        pior que uma não assinada, porque a tela a exibiria como válida.
        """
        assinante_id = (medico.id if medico is not None else None) or self.medico_id
        if not assinante_id:
            raise ValueError(
                "Prescrição só pode ser assinada por um médico cadastrado."
            )
        self.assinada_em = datetime.utcnow()
        self.assinada_por = assinante_id

    STATUS_LABELS = {
        'ativa': ('Ativa', 'verde'),
        'finalizada': ('Finalizada', 'azul'),
        'suspensa': ('Suspensa', 'amarelo'),
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status or '—', 'cinza'))

    def __repr__(self):
        return f'<PrescricaoHospitalar {self.id}>'


class ItemPrescricaoHosp(db.Model):
    __tablename__ = 'itens_prescricao_hosp'

    id = db.Column(db.Integer, primary_key=True)
    # Era `prescricao_hosp_id`; a rota e os templates sempre usaram
    # `prescricao_id`, igual ao item ambulatorial. Renomeado para o nome que o
    # resto do código já assumia.
    prescricao_id = db.Column(db.Integer, db.ForeignKey('prescricoes_hospitalares.id'), nullable=False, index=True)
    medicamento_id = db.Column(db.Integer, db.ForeignKey('medicamentos.id'), nullable=True, index=True)

    nome_livre = db.Column(db.String(150), nullable=True)
    dose = db.Column(db.String(100), nullable=True)
    via = db.Column(db.String(50), nullable=True)
    frequencia = db.Column(db.String(100), nullable=True)
    instrucoes = db.Column(db.Text, nullable=True)

    # Detalhamento que a prescrição hospitalar exige e o item ambulatorial não:
    # como diluir, em que velocidade infundir e em que horários checar.
    concentracao = db.Column(db.String(100), nullable=True)
    diluicao = db.Column(db.String(150), nullable=True)
    velocidade = db.Column(db.String(100), nullable=True)
    horarios = db.Column(db.String(200), nullable=True)
    duracao = db.Column(db.String(100), nullable=True)
    # Ordem de exibição: a sequência dos itens na prescrição é clínica, não
    # alfabética nem por id.
    ordem = db.Column(db.Integer, default=0)

    # Relacionamento com as checagens (administração) da enfermagem
    administracoes = db.relationship('AdministracaoMed', backref='item_prescricao', lazy=True, cascade="all, delete-orphan")
    medicamento = db.relationship('Medicamento', backref='itens_prescricao_hosp')

    @property
    def nome_exibicao(self):
        """Nome do item para a tela — ver ItemPrescricao.nome_exibicao."""
        if self.medicamento:
            return self.medicamento.nome_generico
        return self.nome_livre or '—'

    def __repr__(self):
        return f'<ItemPrescricaoHosp {self.id}>'


class AdministracaoMed(db.Model):
    __tablename__ = 'administracoes_med'

    id = db.Column(db.Integer, primary_key=True)
    item_prescricao_id = db.Column(db.Integer, db.ForeignKey('itens_prescricao_hosp.id'), nullable=False, index=True)
    administrado_por = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    data_agendada = db.Column(db.DateTime, nullable=True)
    data_administracao = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='pendente') # pendente, realizado, recusado, atrasado
    observacoes = db.Column(db.Text, nullable=True)

    STATUS_LABELS = {
        'pendente': ('Pendente', 'cinza'),
        'realizado': ('Realizado', 'verde'),
        'recusado': ('Recusado', 'vermelho'),
        'atrasado': ('Atrasado', 'amarelo'),
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status or '—', 'cinza'))

    def __repr__(self):
        return f'<AdministracaoMed {self.id} Status: {self.status}>'