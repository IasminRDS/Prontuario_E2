# -*- coding: utf-8 -*-
"""Município do IBGE — a chave territorial do sistema.

`cidade` e `uf` como texto livre funcionam numa unidade e falham numa federação:
"Feira de Santana", "feira de santana" e "F. de Santana" viram três municípios
diferentes em qualquer relatório agregado. O código IBGE resolve isso sendo a
chave — e é também o que o SUS usa para tudo (CNES, SIA/SIH, e-SUS, SINAN).
"""
from extensions import db

# Os dois primeiros dígitos do código IBGE são a UF. Isso não é convenção
# interna: é a estrutura do próprio código, e serve para validar de graça.
PREFIXO_UF = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

REGIOES = {
    "N": {"RO", "AC", "AM", "RR", "PA", "AP", "TO"},
    "NE": {"MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE", "BA"},
    "SE": {"MG", "ES", "RJ", "SP"},
    "S": {"PR", "SC", "RS"},
    "CO": {"MS", "MT", "GO", "DF"},
}


def uf_do_codigo(codigo):
    """UF embutida no código IBGE, ou None se o código for inválido."""
    codigo = (codigo or "").strip()
    if len(codigo) != 7 or not codigo.isdigit():
        return None
    return PREFIXO_UF.get(codigo[:2])


def codigo_valido(codigo):
    return uf_do_codigo(codigo) is not None


class Municipio(db.Model):
    __tablename__ = "municipios"

    # O código IBGE é a chave natural: estável, nacional e já usado por todos os
    # sistemas do SUS. Um id sequencial nosso só acrescentaria indireção.
    codigo_ibge = db.Column(db.String(7), primary_key=True)
    nome = db.Column(db.String(120), nullable=False, index=True)
    uf = db.Column(db.String(2), nullable=False, index=True)

    # Região de saúde (agrupamento do SUS), quando conhecida.
    regional_id = db.Column(db.Integer, db.ForeignKey("regionais.id"),
                            nullable=True, index=True)
    regional = db.relationship("Regional", backref="municipios")

    @property
    def regiao(self):
        """Região geográfica (N, NE, SE, S, CO)."""
        for sigla, ufs in REGIOES.items():
            if self.uf in ufs:
                return sigla
        return None

    @property
    def nome_completo(self):
        return f"{self.nome}/{self.uf}"

    def __repr__(self):
        return f"<Municipio {self.codigo_ibge} {self.nome}/{self.uf}>"
