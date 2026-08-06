import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}

def _to_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _normalizar_db_url(url: str) -> str:
    """Resolve caminho relativo de SQLite e o dialeto legado do Postgres.

    - `sqlite:///instance/app.db` depende do diretório de trabalho: rodar de
      outra pasta abre (ou cria) um banco diferente. Convertemos para absoluto,
      ancorado na raiz do projeto.
    - Alguns provedores exportam `postgres://`, que o SQLAlchemy 2 não conhece.
    """
    url = (url or "").strip()

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    prefixo = "sqlite:///"
    if url.startswith(prefixo):
        caminho = url[len(prefixo):]
        if caminho and caminho != ":memory:" and not os.path.isabs(caminho):
            destino = (BASE_DIR / caminho).resolve()
            destino.parent.mkdir(parents=True, exist_ok=True)
            url = prefixo + destino.as_posix()

    return url

class Config:
    # Flask / Segurança
    SECRET_KEY = os.environ["SECRET_KEY"]
    WTF_CSRF_ENABLED = _to_bool(os.getenv("WTF_CSRF_ENABLED"), True)
    
    # Tamanho máximo de corpo de requisição. Sem isto, /pdf/processar e
    # /importacao/csv aceitam arquivo de qualquer tamanho e viram vetor de
    # negação de serviço por consumo de disco e memória.
    MAX_CONTENT_LENGTH = _to_int(os.getenv("MAX_UPLOAD_MB"), 16) * 1024 * 1024

    # Sessão de sistema clínico não deve durar um mês. 12 horas cobre o turno.
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=_to_int(os.getenv("SESSION_HOURS"), 12)
    )
    SESSION_REFRESH_EACH_REQUEST = True

    # Segurança de Cookies.
    #
    # `SECURE` nasce LIGADO: o padrão precisa ser o seguro, porque o custo de
    # errar para cada lado é assimétrico. Desligado por engano em produção, o
    # cookie de sessão de um prontuário trafega em claro no primeiro request que
    # cair em HTTP; ligado por engano em dev, o login apenas não funciona — e
    # isso se descobre em dez segundos. Só `DevelopmentConfig` desliga.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _to_bool(os.getenv("SESSION_COOKIE_SECURE"), True)
    SESSION_COOKIE_SAMESITE = "Lax"

    # Banco de Dados
    DEFAULT_DB_URL = "postgresql://postgres:admin@localhost:5432/prontuario_db"
    SQLALCHEMY_DATABASE_URI = _normalizar_db_url(
        os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # As opções de pool valem só para bancos em rede. O pool do SQLite não
    # aceita pool_size/max_overflow — passá-las levanta TypeError na engine.
    #
    # O teto de conexões é POR WORKER, não por aplicação: o Procfile sobe 2
    # workers de gunicorn e cada um abre seu próprio pool. Com os 20+40 que
    # estavam aqui, dois workers pediam 120 conexões contra as 97 úteis de um
    # Postgres padrão (`max_connections` 100 menos 3 reservadas ao superusuário)
    # — sob carga isso vira `FATAL: sorry, too many clients already`. 5+15 deixa
    # 30 para dois workers, com folga. Suba pelas env vars, conferindo antes que
    # (pool_size + max_overflow) × workers caiba no `max_connections` do servidor.
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"pool_pre_ping": True}
        if SQLALCHEMY_DATABASE_URI.startswith("sqlite")
        else {
            "pool_pre_ping": True,
            "pool_recycle": _to_int(os.getenv("DB_POOL_RECYCLE"), 1800),
            "pool_size": _to_int(os.getenv("DB_POOL_SIZE"), 5),
            "max_overflow": _to_int(os.getenv("DB_MAX_OVERFLOW"), 15),
        }
    )

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    # Dev roda em http://localhost: com o cookie marcado como `Secure` o
    # navegador não o devolve, e o login fica em laço infinito.
    SESSION_COOKIE_SECURE = _to_bool(os.getenv("SESSION_COOKIE_SECURE"), False)

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    LOG_LEVEL = "INFO"

config_map = {
    "dev": DevelopmentConfig,
    "prod": ProductionConfig,
}

def get_config_class():
    """Classe de configuração a partir de `APP_ENV`, sem recuo silencioso.

    Antes: `os.getenv("APP_ENV", "dev")` com `config_map.get(env, Development)`.
    Duas portas para a configuração de DESENVOLVIMENTO entrar em produção sem
    ninguém perceber — e ela carrega `DEBUG = True` e cookie sem `Secure`:

    - a variável não definida no servidor caía em "dev";
    - `APP_ENV=production` (em vez de "prod"), `APP_ENV=PROD `, ou qualquer
      erro de digitação caíam em "dev" também, calados.

    Configuração errada tem de FALHAR, não degradar. O `.env.example` e o CI já
    definem `APP_ENV`, então exigir a variável não muda nenhum fluxo existente.
    """
    bruto = os.getenv("APP_ENV")
    if bruto is None or not bruto.strip():
        raise RuntimeError(
            "APP_ENV não definida. Use APP_ENV=dev ou APP_ENV=prod — não há "
            "padrão, porque o padrão errado seria a configuração insegura."
        )

    env = bruto.strip().lower()
    if env not in config_map:
        raise RuntimeError(
            f"APP_ENV={bruto!r} não é válida. Valores aceitos: "
            f"{', '.join(sorted(config_map))}."
        )
    return config_map[env]