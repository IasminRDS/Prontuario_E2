from datetime import datetime
from extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    tabela = db.Column(
        db.String(80), nullable=False, index=True
    )  # ex: users, pacientes
    registro_id = db.Column(
        db.Integer, nullable=True, index=True
    )  # id do registro alvo
    acao = db.Column(
        db.String(40), nullable=False, index=True
    )  # create/update/delete/list_html
    descricao = db.Column(db.Text, nullable=True)  # evitar "detalhe" por enquanto
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )
    ip = db.Column(db.String(64), nullable=True)
    criado_em = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # --- Encadeamento por hash (integridade da trilha) -------------------
    # Cada registro carrega o hash do anterior. Alterar ou remover uma linha
    # no meio quebra a cadeia e a verificação aponta exatamente onde. É o que
    # torna a trilha WORM na prática, sem depender de permissão do banco.
    hash_anterior = db.Column(db.String(64), nullable=True)
    hash_atual = db.Column(db.String(64), nullable=True, index=True)

    usuario = db.relationship("User", backref="logs_auditoria")

    def calcular_hash(self):
        """SHA-256 do conteúdo canônico + hash do registro anterior."""
        import hashlib

        campos = "|".join(
            str(v) if v is not None else ""
            for v in (
                self.tabela,
                self.registro_id,
                self.acao,
                self.descricao,
                self.usuario_id,
                self.ip,
                self.criado_em.isoformat() if self.criado_em else "",
                self.hash_anterior or "",
            )
        )
        return hashlib.sha256(campos.encode("utf-8")).hexdigest()

    @property
    def detalhe(self):
        # compatibilidade para templates/código antigo que usam log.detalhe
        return self.descricao
