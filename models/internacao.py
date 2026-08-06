# -*- coding: utf-8 -*-
from extensions import db
from datetime import datetime


class Setor(db.Model):
    """Setor / ala do hospital (Clínica Médica, UTI, Pediatria, etc.)."""

    __tablename__ = "setores"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    sigla = db.Column(db.String(10), nullable=True)
    tipo = db.Column(db.String(30), nullable=False, default="enfermaria")
    # enfermaria | uti | semi_intensivo | ps | cirurgia | recuperacao | isolamento
    andar = db.Column(db.String(10), nullable=True)
    responsavel = db.Column(db.String(100), nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    leitos = db.relationship("Leito", backref="setor", lazy="dynamic")

    @property
    def total_leitos(self):
        return self.leitos.filter_by(ativo=True).count()

    @property
    def leitos_ocupados(self):
        return self.leitos.filter_by(status="ocupado", ativo=True).count()

    @property
    def leitos_livres(self):
        return self.leitos.filter_by(status="livre", ativo=True).count()

    @property
    def taxa_ocupacao(self):
        t = self.total_leitos
        if t == 0:
            return 0
        return round(self.leitos_ocupados / t * 100)

    def __repr__(self):
        return f"<Setor {self.nome}>"


class Leito(db.Model):
    """Leito individual dentro de um setor."""

    __tablename__ = "leitos"

    id = db.Column(db.Integer, primary_key=True)
    unidade_id = db.Column(
        db.Integer, db.ForeignKey("unidades_saude.id"), nullable=False, index=True
    )
    unidade = db.relationship("UnidadeSaude", backref="leitos")
    setor_id = db.Column(db.Integer, db.ForeignKey("setores.id"), nullable=False, index=True)
    numero = db.Column(db.String(20), nullable=False)  # ex: 201A, UTI-03
    tipo = db.Column(db.String(30), nullable=True)  # comum | isolamento | uti
    status = db.Column(db.String(20), default="livre")
    # livre | ocupado | reservado | em_higienizacao | interditado
    observacoes = db.Column(db.String(200), nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    internacoes = db.relationship("Internacao", backref="leito", lazy="dynamic")

    @property
    def internacao_ativa(self):
        return self.internacoes.filter_by(status="ativa").first()

    STATUS_LABELS = {
        "livre": ("Livre", "verde"),
        "ocupado": ("Ocupado", "vermelho"),
        "reservado": ("Reservado", "amarelo"),
        "em_higienizacao": ("Em higienização", "cinza"),
        "interditado": ("Interditado", "vermelho"),
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status, "cinza"))

    def __repr__(self):
        return f"<Leito {self.numero}>"


class Internacao(db.Model):
    """Registro de internação de um paciente."""

    __tablename__ = "internacoes"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)
    leito_id = db.Column(db.Integer, db.ForeignKey("leitos.id"), nullable=False, index=True)
    medico_id = db.Column(db.Integer, db.ForeignKey("medicos.id"), nullable=True, index=True)
    unidade_id = db.Column(
        db.Integer, db.ForeignKey("unidades_saude.id"), nullable=False,
        index=True,
    )
    criado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    # Tipo e motivo
    tipo = db.Column(db.String(30), default="clinica")
    # clinica | cirurgica | obstetricia | pediatrica | psiquiatria | uti
    motivo = db.Column(db.Text, nullable=False)
    hipotese_diag = db.Column(db.String(200), nullable=True)
    cid_principal = db.Column(db.String(10), nullable=True)

    # Datas
    data_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    data_prevista_alta = db.Column(db.DateTime, nullable=True)
    data_alta = db.Column(db.DateTime, nullable=True)

    status = db.Column(db.String(20), default="ativa")
    # ativa | alta | transferida | obito

    # Alta
    tipo_alta = db.Column(db.String(30), nullable=True)
    # curado | melhorado | transferencia | obito | a_pedido | evasao
    sumario_alta = db.Column(db.Text, nullable=True)
    cid_alta = db.Column(db.String(10), nullable=True)

    # AIH
    aih_numero = db.Column(db.String(20), nullable=True)

    observacoes = db.Column(db.Text, nullable=True)

    # Relacionamentos
    paciente = db.relationship("Paciente", backref="internacoes")
    medico = db.relationship("Medico", backref="internacoes")
    unidade = db.relationship("UnidadeSaude", backref="setores")
    evolucoes = db.relationship(
        "EvolucaoInternacao",
        backref="internacao",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    STATUS_LABELS = {
        "ativa": ("Ativa", "verde"),
        "alta": ("Alta", "azul"),
        "transferida": ("Transferida", "amarelo"),
        "obito": ("Óbito", "vermelho"),
    }

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, (self.status, "cinza"))

    @property
    def dias_internado(self):
        fim = self.data_alta or datetime.utcnow()
        # Nunca negativo. `timedelta.days` trunca para baixo, então uma alta
        # registrada com hora anterior à entrada — mesmo por segundos, o que
        # acontece quando as duas são preenchidas na mesma tela — devolvia -1, e
        # o sumário de alta imprimia "Dias internado: -1 dias". Pior: o
        # `permanencia_media` de routes/relatorios_hosp.py soma isto, então um
        # registro torto puxava a média do hospital inteiro para baixo.
        return max(0, (fim - self.data_entrada).days)

    def __repr__(self):
        return f"<Internacao {self.id} paciente={self.paciente_id}>"


class EvolucaoInternacao(db.Model):
    """Evolução diária do paciente internado (nota de evolução)."""

    __tablename__ = "evolucoes_internacao"

    id = db.Column(db.Integer, primary_key=True)
    internacao_id = db.Column(
        db.Integer, db.ForeignKey("internacoes.id"), nullable=False,
        index=True,
    )
    profissional_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    tipo = db.Column(db.String(20), default="medica")
    # medica | enfermagem | fisioterapia | nutricao | psicologia | servico_social

    # Sinais vitais
    pressao_arterial = db.Column(db.String(10), nullable=True)
    temperatura = db.Column(db.Float, nullable=True)
    frequencia_cardiaca = db.Column(db.Integer, nullable=True)
    frequencia_respiratoria = db.Column(db.Integer, nullable=True)
    saturacao_o2 = db.Column(db.Float, nullable=True)
    diurese_ml = db.Column(db.Integer, nullable=True)
    balanco_hidrico = db.Column(db.Integer, nullable=True)  # ml

    # SOAP
    subjetivo = db.Column(db.Text, nullable=True)
    objetivo = db.Column(db.Text, nullable=True)
    avaliacao = db.Column(db.Text, nullable=True)
    plano = db.Column(db.Text, nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    profissional = db.relationship("User", backref="evolucoes_internacao")

    def __repr__(self):
        return f"<EvolucaoInternacao {self.id}>"
