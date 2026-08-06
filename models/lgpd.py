# -*- coding: utf-8 -*-
"""Models de conformidade LGPD e assinatura de documentos.

Porte de `ConsentimentoLgpd`, `DocumentoAssinado` e `EnvioRnds` do schema.prisma.
"""
from datetime import datetime

from extensions import db


class ConsentimentoLgpd(db.Model):
    """Registro de consentimento do titular (art. 8º da Lei 13.709/2018)."""

    __tablename__ = "consentimentos_lgpd"

    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=False, index=True)

    finalidade = db.Column(db.String(120), nullable=False)
    # assistencia | pesquisa | compartilhamento_rnds | contato

    concedido = db.Column(db.Boolean, nullable=False, default=True)
    base_legal = db.Column(db.String(80), nullable=True, default="tutela_da_saude")

    versao_termo = db.Column(db.String(20), nullable=True)
    ip = db.Column(db.String(64), nullable=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    revogado_em = db.Column(db.DateTime, nullable=True)
    registrado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    paciente = db.relationship("Paciente", backref="consentimentos")

    @property
    def vigente(self):
        return self.concedido and self.revogado_em is None


class DocumentoAssinado(db.Model):
    """Documento clínico emitido com assinatura verificável publicamente.

    O hash do conteúdo permite que qualquer pessoa confira, em
    `/verificar/<codigo>`, se o PDF em mãos é o mesmo que o sistema emitiu.
    """

    __tablename__ = "documentos_assinados"

    id = db.Column(db.Integer, primary_key=True)

    # Código curto que vai impresso no documento e na URL de verificação.
    codigo = db.Column(db.String(32), unique=True, nullable=False, index=True)

    tipo = db.Column(db.String(40), nullable=False)
    # prontuario | receituario | atestado | encaminhamento | alta

    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=True, index=True)
    referencia_tabela = db.Column(db.String(60), nullable=True)
    referencia_id = db.Column(db.Integer, nullable=True)

    # SHA-256 do PDF gerado, em hexadecimal.
    hash_conteudo = db.Column(db.String(64), nullable=False, index=True)

    assinado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True,
        index=True,
    )
    assinante_nome = db.Column(db.String(120), nullable=True)
    assinante_registro = db.Column(db.String(40), nullable=True)  # CRM/COREN

    emitido_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    revogado_em = db.Column(db.DateTime, nullable=True)
    motivo_revogacao = db.Column(db.String(255), nullable=True)

    paciente = db.relationship("Paciente", backref="documentos_assinados")

    @property
    def valido(self):
        return self.revogado_em is None


class EnvioRnds(db.Model):
    """Envio de registro clínico à Rede Nacional de Dados em Saúde (FHIR R4)."""

    __tablename__ = "envios_rnds"

    id = db.Column(db.Integer, primary_key=True)

    tipo = db.Column(db.String(40), nullable=False, index=True)
    # Patient | Encounter | MedicationRequest | Observation | Immunization

    entidade_tabela = db.Column(db.String(60), nullable=True)
    entidade_id = db.Column(db.Integer, nullable=True, index=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"), nullable=True, index=True)

    status = db.Column(db.String(20), nullable=False, default="pendente", index=True)
    # pendente | enviado | erro

    # Payload FHIR serializado, para auditoria e reenvio.
    payload = db.Column(db.Text, nullable=True)

    # Identificador devolvido pela RNDS.
    protocolo = db.Column(db.String(80), nullable=True)
    erro = db.Column(db.Text, nullable=True)
    tentativas = db.Column(db.Integer, nullable=False, default=0)

    # Impressão digital do conteúdo. Única: impede que o mesmo documento entre
    # duas vezes na fila, e viaja no cabeçalho para a RNDS descartar reenvio
    # quando a resposta anterior se perdeu no caminho.
    chave_idempotencia = db.Column(db.String(64), nullable=True, unique=True,
                                   index=True)
    # Quando a próxima tentativa fica liberada. Nulo = pronto agora.
    proxima_tentativa = db.Column(db.DateTime, nullable=True, index=True)

    criado_em = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    enviado_em = db.Column(db.DateTime, nullable=True)
    criado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    paciente = db.relationship("Paciente", backref="envios_rnds")

    def __repr__(self):
        return f"<EnvioRnds {self.tipo}#{self.entidade_id} {self.status}>"
