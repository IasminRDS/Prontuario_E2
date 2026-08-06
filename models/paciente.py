from extensions import db
from datetime import datetime, date


class Paciente(db.Model):
    __tablename__ = "pacientes"

    # Declarados aqui, e não só na migration, porque `flask db check` compara o
    # banco com o METADATA: índice que existe no banco e não no model é
    # reportado como deriva, e o autogenerate seguinte proporia removê-lo.
    #
    # Ambos foram escolhidos por medição com 50 mil linhas (ver a migration
    # c3d9e15b7a42): a lista paginada caiu de 40,1 ms para 0,19 ms e o
    # autocomplete de 185,9 ms para 0,96 ms.
    __table_args__ = (
        # Na ordem certa, o mesmo índice filtra (município, UF) E ordena (nome),
        # o que elimina o Sort. Parcial em `ativo` porque paciente inativo não
        # aparece nessas telas.
        db.Index("ix_pacientes_territorio", "municipio", "uf", "nome",
                 postgresql_where=db.text("ativo"),
                 sqlite_where=db.text("ativo")),
        # `ILIKE '%texto%'` não usa B-tree: o curinga à esquerda impede busca por
        # prefixo. Em SQLite as opções `postgresql_*` são ignoradas e sobra um
        # índice comum, que é inofensivo — o banco de teste não tem volume.
        #
        # `public.` na classe de operadores não é enfeite: a extensão instala em
        # `public`, e a suíte prende o `search_path` ao schema de teste. Sem
        # qualificar, `create_all` falha com "gin_trgm_ops não existe".
        db.Index("ix_pacientes_nome_trgm", "nome",
                 postgresql_using="gin",
                 postgresql_ops={"nome": "public.gin_trgm_ops"}),
    )

    id = db.Column(db.Integer, primary_key=True)

    # Identificação
    nome = db.Column(db.String(150), nullable=False)
    nome_social = db.Column(db.String(150), nullable=True)
    cns = db.Column(
        db.String(20), unique=True, nullable=True
    )  # Cartão Nacional de Saúde
    cpf = db.Column(db.String(14), unique=True, nullable=True)
    rg = db.Column(db.String(20), nullable=True)
    data_nascimento = db.Column(db.Date, nullable=False)
    sexo = db.Column(db.String(1), nullable=False)  # M / F / I
    raca_cor = db.Column(db.String(20), nullable=True)
    nome_mae = db.Column(db.String(150), nullable=True)
    nome_pai = db.Column(db.String(150), nullable=True)

    # Contato
    telefone = db.Column(db.String(20), nullable=True)
    telefone2 = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)

    # Endereço
    cep = db.Column(db.String(9), nullable=True)
    logradouro = db.Column(db.String(200), nullable=True)
    numero = db.Column(db.String(10), nullable=True)
    complemento = db.Column(db.String(100), nullable=True)
    bairro = db.Column(db.String(100), nullable=True)
    municipio = db.Column(db.String(100), nullable=True)
    municipio_ibge = db.Column(db.String(7), nullable=True, index=True)
    uf = db.Column(db.String(2), nullable=True)

    # Informações clínicas básicas
    tipo_sanguineo = db.Column(db.String(5), nullable=True)
    alergias = db.Column(db.Text, nullable=True)
    observacoes = db.Column(db.Text, nullable=True)

    # Unificação de cadastros duplicados.
    #
    # O registro absorvido NÃO é apagado: em prontuário, apagar é perder
    # rastro. Ele fica inativo — some das listas, que já filtram por `ativo` —
    # apontando para o sobrevivente, de modo que quem chegar por um link antigo
    # ou por um documento impresso seja levado ao cadastro correto.
    unificado_para_id = db.Column(db.Integer, db.ForeignKey("pacientes.id"),
                                  nullable=True, index=True)
    unificado_em = db.Column(db.DateTime, nullable=True)
    unificado_para = db.relationship("Paciente", remote_side=[id],
                                     backref="absorvidos")

    @property
    def foi_unificado(self):
        return self.unificado_para_id is not None

    # Controle
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    criado_por = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)

    # Relacionamentos
    atendimentos = db.relationship("Atendimento", backref="paciente", lazy="dynamic")
    prontuarios = db.relationship("Prontuario", backref="paciente", lazy="dynamic")

    @property
    def idade(self):
        hoje = date.today()
        nascimento = self.data_nascimento
        anos = (
            hoje.year
            - nascimento.year
            - ((hoje.month, hoje.day) < (nascimento.month, nascimento.day))
        )
        return anos

    @property
    def nome_exibicao(self):
        return self.nome_social if self.nome_social else self.nome

    def __repr__(self):
        return f"<Paciente {self.nome}>"
