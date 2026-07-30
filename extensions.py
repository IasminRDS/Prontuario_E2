# extensions.py — instâncias únicas das extensões Flask.
#
# Este é o ÚNICO lugar onde as extensões são construídas. Nunca instancie
# SQLAlchemy()/Migrate()/LoginManager() em outro módulo: duas instâncias de
# SQLAlchemy no mesmo processo produzem models registrados num metadata e
# sessões abertas no outro, e toda escrita falha.
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()
migrate = Migrate()
login_manager = LoginManager()

login_manager.login_view = "auth.login"
login_manager.login_message = "Faça login para acessar esta página."
login_manager.login_message_category = "warning"
login_manager.session_protection = "strong"


@login_manager.user_loader
def load_user(user_id):
    # Import tardio: models importa `db` daqui, então importar no topo criaria ciclo.
    from models.user import User

    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
