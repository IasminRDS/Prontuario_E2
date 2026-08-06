from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)

    # perfil funcional (mantido)
    perfil = db.Column(db.String(20), nullable=False, default="recepcionista")
    # admin | medico | enfermeiro | recepcionista

    # vínculo operacional
    unidade_id = db.Column(
        db.Integer, db.ForeignKey("unidades_saude.id"), nullable=True,
        index=True,
    )

    # NOVO: nível territorial de acesso
    nivel_acesso = db.Column(db.String(20), nullable=False, default="UNIDADE")
    # ESTADO | REGIONAL | MUNICIPIO | UNIDADE

    # NOVO: escopos territoriais explícitos (opcional para admin global)
    regional_id = db.Column(db.Integer, db.ForeignKey("regionais.id"), nullable=True, index=True)
    municipio_ibge = db.Column(db.String(7), nullable=True, index=True)
    uf = db.Column(db.String(2), nullable=True, index=True)

    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso = db.Column(db.DateTime, nullable=True)

    # --- Verificação em duas etapas (TOTP) -------------------------------
    # O segredo base32 do autenticador. Fica nulo até o usuário concluir o
    # setup; `mfa_ativo` só vira True depois de ele provar um código válido —
    # assim ninguém se tranca fora da conta por ter escaneado o QR e parado.
    mfa_secret = db.Column(db.String(64), nullable=True)
    mfa_ativo = db.Column(db.Boolean, nullable=False, default=False)
    mfa_confirmado_em = db.Column(db.DateTime, nullable=True)

    # --- Identidade federada gov.br --------------------------------------
    govbr_sub = db.Column(db.String(120), unique=True, nullable=True, index=True)
    govbr_nivel = db.Column(db.String(20), nullable=True)  # bronze | prata | ouro
    cpf = db.Column(db.String(11), nullable=True, index=True)

    unidade = db.relationship("UnidadeSaude", backref="users")
    # regional = db.relationship("models.regional.Regional", backref="users")

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def is_medico(self):
        from utils.rbac import MEDICO, _normalizar

        return _normalizar(self.perfil) == MEDICO

    def is_admin(self):
        from utils.rbac import ADMINISTRADOR, SUPER_ADMIN, _normalizar

        return _normalizar(self.perfil) in (ADMINISTRADOR, SUPER_ADMIN)

    # --- RBAC -------------------------------------------------------------

    @property
    def permissoes(self):
        from utils.rbac import permissoes_de

        return permissoes_de(self.perfil)

    def tem_permissao(self, *permissoes):
        from utils.rbac import pode

        return pode(*permissoes, usuario=self)

    # --- MFA --------------------------------------------------------------

    def verificar_totp(self, codigo):
        """Valida um código TOTP de 6 dígitos, com 1 janela de tolerância."""
        if not self.mfa_secret or not codigo:
            return False
        try:
            import pyotp
        except ImportError:
            return False
        codigo = str(codigo).strip().replace(" ", "")
        return pyotp.TOTP(self.mfa_secret).verify(codigo, valid_window=1)

    # Helpers territoriais
    def is_estado(self):
        return self.nivel_acesso == "ESTADO"

    def is_regional(self):
        return self.nivel_acesso == "REGIONAL"

    def is_municipio(self):
        return self.nivel_acesso == "MUNICIPIO"

    def is_unidade(self):
        return self.nivel_acesso == "UNIDADE"

    def __repr__(self):
        return f"<User {self.email}>"
