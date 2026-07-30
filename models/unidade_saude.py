from extensions import db


class UnidadeSaude(db.Model):
    __tablename__ = "unidades_saude"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(140), nullable=False, index=True)
    tipo = db.Column(
        db.String(40), nullable=False, index=True
    )  # UBS | Clínica Pública | Hospital
    cnes = db.Column(db.String(20), nullable=True, unique=True, index=True)
    cidade = db.Column(db.String(80), nullable=True, index=True)
    uf = db.Column(db.String(2), nullable=True, index=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    @property
    def municipio(self):
        """Alias de `cidade`.

        Os geradores de PDF e alguns templates usam `unidade.municipio`, que é
        como o campo se chama em Paciente. Sem o alias, cada emissão de documento
        estourava AttributeError.
        """
        return self.cidade

    @municipio.setter
    def municipio(self, valor):
        self.cidade = valor

    def __repr__(self):
        return f"<UnidadeSaude {self.nome}>"
