from extensions import db
from datetime import datetime


class Medico(db.Model):
    __tablename__ = "medicos"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    crm = db.Column(db.String(20), unique=True, nullable=False)
    especialidade = db.Column(db.String(100), nullable=True)
    unidade_id = db.Column(
        db.Integer, db.ForeignKey("unidades_saude.id"), nullable=True,
        index=True,
    )

    user = db.relationship("User", backref="medico_perfil")
    unidade = db.relationship("UnidadeSaude", backref="medicos")
    atendimentos = db.relationship("Atendimento", backref="medico", lazy="dynamic")

    @property
    def nome(self):
        return self.user.nome

    def __repr__(self):
        return f"<Medico {self.crm}>"
