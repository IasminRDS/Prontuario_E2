# -*- coding: utf-8 -*-
"""Configuração do sistema — armazenamento chave/valor persistido.

Antes disso as configurações viviam num dict de módulo, que se perdia a cada
restart e não era compartilhado entre workers do Gunicorn.
"""
from datetime import datetime

from extensions import db

# Chaves conhecidas e seus padrões. Serve de documentação e de fallback quando a
# chave ainda não foi gravada.
PADROES = {
    "nome_unidade": "UBS Central",
    "uf": "BA",
    "municipio": "",
    "cnes": "",
    "tema_padrao": "light",
    "retencao_auditoria_dias": "1825",
    "rnds_ativo": "0",
    "mfa_obrigatorio_perfis": "Administrador,SuperAdmin",
}


class Configuracao(db.Model):
    __tablename__ = "configuracoes"

    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(80), unique=True, nullable=False, index=True)
    valor = db.Column(db.Text, nullable=True)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    atualizado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    def __repr__(self):
        return f"<Configuracao {self.chave}={self.valor!r}>"

    # --- API de acesso -----------------------------------------------------

    @classmethod
    def obter(cls, chave, default=None):
        row = cls.query.filter_by(chave=chave).first()
        if row is not None and row.valor is not None:
            return row.valor
        if default is not None:
            return default
        return PADROES.get(chave)

    @classmethod
    def definir(cls, chave, valor, usuario_id=None):
        row = cls.query.filter_by(chave=chave).first()
        if row is None:
            row = cls(chave=chave)
            db.session.add(row)
        row.valor = valor
        row.atualizado_por = usuario_id
        return row

    @classmethod
    def todas(cls):
        """Dict com todas as chaves conhecidas, já com os padrões aplicados."""
        gravadas = {r.chave: r.valor for r in cls.query.all()}
        return {chave: gravadas.get(chave) or padrao for chave, padrao in PADROES.items()}
