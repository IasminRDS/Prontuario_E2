# -*- coding: utf-8 -*-
from extensions import db
from datetime import datetime

TIPO_LABELS = {
    "entrada": ("Entrada", "verde"),
    "saida": ("Saída", "vermelho"),
    "ajuste": ("Ajuste", "azul"),
    "perda": ("Perda/Quebra", "amarelo"),
    "vencimento": ("Vencimento", "amarelo"),
    "transferencia": ("Transferência", "cinza"),
}


class ItemEstoque(db.Model):
    __tablename__ = "itens_estoque"

    id = db.Column(db.Integer, primary_key=True)
    unidade_id = db.Column(
        db.Integer, db.ForeignKey("unidades_saude.id"), nullable=False,
        index=True,
    )
    medicamento_id = db.Column(db.Integer, nullable=True)

    nome = db.Column(db.String(150), nullable=False)
    categoria = db.Column(db.String(50), default="medicamento")
    apresentacao = db.Column(db.String(100), nullable=True)
    unidade_medida = db.Column(db.String(20), default="un")
    codigo_interno = db.Column(db.String(30), nullable=True)
    lote_atual = db.Column(db.String(30), nullable=True)
    validade = db.Column(db.Date, nullable=True)

    quantidade = db.Column(db.Float, default=0)
    estoque_minimo = db.Column(db.Float, default=10)
    estoque_maximo = db.Column(db.Float, nullable=True)
    preco_unitario = db.Column(db.Float, nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    unidade = db.relationship("UnidadeSaude", backref="itens_estoque")
    medicamento = None
    movimentacoes = db.relationship(
        "MovEstoque", backref="item", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def status(self):
        if self.quantidade <= 0:
            return ("Zerado", "vermelho")
        if self.quantidade <= self.estoque_minimo:
            return ("Crítico", "vermelho")
        if self.quantidade <= self.estoque_minimo * 1.5:
            return ("Baixo", "amarelo")
        return ("Normal", "verde")

    @property
    def abaixo_minimo(self):
        return self.quantidade <= self.estoque_minimo

    def __repr__(self):
        return f"<ItemEstoque {self.nome}>"


class MovEstoque(db.Model):
    __tablename__ = "mov_estoque"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey("itens_estoque.id"), nullable=False, index=True)
    unidade_id = db.Column(
        db.Integer, db.ForeignKey("unidades_saude.id"), nullable=False,
        index=True,
    )
    usuario_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    tipo = db.Column(db.String(20), nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    quantidade_anterior = db.Column(db.Float, nullable=True)
    quantidade_posterior = db.Column(db.Float, nullable=True)
    motivo = db.Column(db.String(200), nullable=True)
    lote = db.Column(db.String(30), nullable=True)
    fornecedor = db.Column(db.String(100), nullable=True)
    nota_fiscal = db.Column(db.String(50), nullable=True)
    internacao_id = db.Column(
        db.Integer, db.ForeignKey("internacoes.id"), nullable=True,
        index=True,
    )

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship("User", backref="movimentacoes_estoque")
    unidade = db.relationship("UnidadeSaude", backref="movimentacoes_estoque")

    @property
    def tipo_label(self):
        return TIPO_LABELS.get(self.tipo, (self.tipo, "cinza"))

    def __repr__(self):
        return f"<MovEstoque {self.tipo} {self.quantidade}>"
