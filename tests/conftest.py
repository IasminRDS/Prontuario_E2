# -*- coding: utf-8 -*-
"""Infraestrutura da suíte.

**Isolamento**: os testes nunca tocam o banco de desenvolvimento. Em PostgreSQL
tudo acontece num schema próprio, criado e destruído pela sessão de teste — o
`search_path` da conexão aponta só para ele, então uma consulta que escape do
schema não encontra tabela nenhuma em vez de ler dado real. Em SQLite, o banco
vai para um arquivo temporário.

A escolha do schema (em vez de um banco dedicado) é deliberada: o papel da
aplicação não tem CREATEDB, mas tem CREATE no próprio banco. Assim a suíte roda
com as mesmas credenciais da aplicação, sem exigir superusuário.
"""
import os
import pathlib
import re
import sys
import tempfile

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

# --- tudo isto precisa acontecer ANTES de importar `app` -------------------
os.environ.setdefault("SECRET_KEY", "chave-de-teste-nao-usar-em-producao")
os.environ.setdefault("APP_ENV", "dev")

_URL_TESTE = os.environ.get("TEST_DATABASE_URL")
if _URL_TESTE:
    os.environ["DATABASE_URL"] = _URL_TESTE

# SQLite não tem schema; sem um arquivo próprio a suíte escreveria no banco de
# desenvolvimento. Redireciona antes que a app leia a configuração.
if os.environ.get("DATABASE_URL", "").startswith("sqlite"):
    _tmp = pathlib.Path(tempfile.gettempdir()) / "prontuario_suite_testes.db"
    _tmp.unlink(missing_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.as_posix()}"

import pytest  # noqa: E402
import sqlalchemy as sa  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app import app as aplicacao  # noqa: E402
from extensions import db  # noqa: E402

ESQUEMA = "teste_automatizado"

SENHA = "senha12345"
PERFIS = {
    "admin": ("Ana Admin", "admin@sus.gov.br", "admin"),
    "medico": ("Dr. Teste", "medico2@sus.gov.br", "medico"),
    "recepcao": ("Recep Teste", "recepcao@sus.gov.br", "recepcionista"),
    "gestor": ("Gestor Teste", "gestor2@sus.gov.br", "gestor"),
}


def _isolar_postgres(engine):
    """Cria o schema da suíte e prende toda conexão a ele."""
    with engine.connect() as con:
        con.execute(sa.text(f"DROP SCHEMA IF EXISTS {ESQUEMA} CASCADE"))
        con.execute(sa.text(f"CREATE SCHEMA {ESQUEMA}"))
        con.commit()

    @event.listens_for(engine, "connect")
    def _fixar_search_path(conexao_dbapi, _registro):
        cursor = conexao_dbapi.cursor()
        # Só o schema de teste: sem `public` no caminho, uma tabela que escape
        # do isolamento dá erro em vez de ler dado de desenvolvimento.
        cursor.execute(f"SET search_path TO {ESQUEMA}")
        cursor.close()

    # As conexões já no pool não passaram pelo listener.
    engine.dispose()


@pytest.fixture(scope="session")
def app():
    aplicacao.config.update(TESTING=True, WTF_CSRF_ENABLED=True)

    with aplicacao.app_context():
        postgres = db.engine.dialect.name == "postgresql"
        if postgres:
            _isolar_postgres(db.engine)

        db.create_all()

        if postgres:
            # As políticas vêm da migration, que a suíte não roda (o schema é
            # montado com create_all). Sem aplicá-las aqui, os testes de RLS
            # rodariam contra um banco sem RLS e passariam sem provar nada.
            from utils.rls import aplicar_politicas, tabelas_protegidas

            with db.engine.begin() as conexao:
                aplicar_politicas(conexao, tabelas_protegidas(db.metadata))

        _semear()

    yield aplicacao

    with aplicacao.app_context():
        if db.engine.dialect.name == "postgresql":
            with db.engine.connect() as con:
                con.execute(sa.text(f"DROP SCHEMA IF EXISTS {ESQUEMA} CASCADE"))
                con.commit()


def _semear():
    """Catálogos, unidade, médico e um usuário por perfil."""
    from database.seeds import seed_data
    from models.medico import Medico
    from models.unidade_saude import UnidadeSaude
    from models.user import User

    seed_data()

    # `first()` sem ordenação devolve linha arbitrária; com RLS ligado, o
    # usuário acabaria vinculado a uma unidade diferente da que os testes
    # semeiam, e nada seria visível.
    unidade = UnidadeSaude.query.order_by(UnidadeSaude.id.asc()).first()
    for _chave, (nome, email, perfil) in PERFIS.items():
        if User.query.filter_by(email=email).first():
            continue
        u = User(nome=nome, email=email, perfil=perfil, ativo=True,
                 unidade_id=unidade.id if unidade else None,
                 nivel_acesso="UNIDADE")
        u.set_password(SENHA)
        db.session.add(u)
    db.session.commit()

    # O usuário médico precisa de cadastro em `medicos` para prescrever e
    # assinar — sem isso metade dos fluxos clínicos não é exercitável.
    medico_user = User.query.filter_by(email=PERFIS["medico"][1]).first()
    if medico_user and not Medico.query.filter_by(user_id=medico_user.id).first():
        db.session.add(Medico(user_id=medico_user.id, crm="99999-BA",
                              especialidade="Clínica Geral",
                              unidade_id=medico_user.unidade_id))
        db.session.commit()


# --------------------------------------------------------------- clientes
def _token(html):
    achado = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return achado.group(1) if achado else None


def autenticar(app, email, senha=SENHA):
    """Login pela porta da frente, com o token colhido da própria tela.

    Fazer login sem o token deixa a sessão anônima em silêncio, e o teste
    seguinte mede a tela de login achando que mede a aplicação.
    """
    c = app.test_client()
    if app.config.get("WTF_CSRF_ENABLED"):
        pagina = c.get("/auth/login").get_data(as_text=True)
        dados = {"email": email, "senha": senha, "csrf_token": _token(pagina)}
    else:
        dados = {"email": email, "senha": senha}
    c.post("/auth/login", data=dados, follow_redirects=True)
    return c


@pytest.fixture(scope="session")
def dados_clinicos(app):
    """Uma linha em cada tabela, para os laços dos templates executarem.

    Sem isto a varredura de rotas responde 200 em tudo sem renderizar nenhuma
    linha, e telas quebradas passam despercebidas.
    """
    from tests.dados import semear_uma_linha_por_tabela

    with app.app_context():
        semeadas, _puladas = semear_uma_linha_por_tabela()
    return semeadas


@pytest.fixture(scope="session")
def ids_reais(app, dados_clinicos):
    """Menor id existente por tabela, para montar URLs que resolvem de fato."""
    import sqlalchemy as _sa

    with app.app_context():
        mapa = {}
        for nome in _sa.inspect(db.engine).get_table_names():
            try:
                mapa[nome] = db.session.execute(
                    _sa.text(f'select min(id) from "{nome}"')).scalar()
            except Exception:
                db.session.rollback()
        return mapa


@pytest.fixture(scope="session")
def unidade_padrao(app):
    """A unidade a que os usuários de teste pertencem.

    Com RLS ligado, dado clínico criado em outra unidade fica invisível para
    eles — então todo teste que cria registro precisa usar esta.
    """
    from models.unidade_saude import UnidadeSaude

    with app.app_context():
        return UnidadeSaude.query.order_by(UnidadeSaude.id.asc()).first().id


@pytest.fixture
def anonimo(app):
    return app.test_client()


@pytest.fixture
def cliente(app):
    """Sessão de admin — o perfil com mais permissão."""
    return autenticar(app, PERFIS["admin"][1])


@pytest.fixture
def clientes(app):
    """Um cliente autenticado por perfil, para as matrizes de RBAC."""
    return {chave: autenticar(app, email)
            for chave, (_n, email, _p) in PERFIS.items()}


@pytest.fixture
def sem_csrf(app):
    """Desliga o CSRF para que um 400 de token não mascare o que se mede.

    Usar só onde o alvo do teste é outro (RBAC, por exemplo). Nunca em teste
    cujo objeto seja o próprio CSRF.
    """
    anterior = app.config["WTF_CSRF_ENABLED"]
    app.config["WTF_CSRF_ENABLED"] = False
    yield
    app.config["WTF_CSRF_ENABLED"] = anterior


@pytest.fixture
def token_de():
    return _token


@pytest.fixture
def zera_limite():
    """Zera o contador de tentativas de login.

    O limitador guarda estado em memória por processo. Sem zerar, o teste de
    força bruta deixa a janela estourada e o teste seguinte mede um 429 achando
    que mede outra coisa — foi exatamente isso que fazia o teste de enumeração
    de usuário acusar vulnerabilidade que não existe.
    """
    from utils.seguranca_http import _tentativas

    _tentativas.clear()
    yield
    _tentativas.clear()


@pytest.fixture
def autenticado_confirmado(cliente):
    """Falha cedo se o login não pegou, em vez de deixar o teste medir o nada."""
    resposta = cliente.get("/pacientes/")
    assert resposta.status_code == 200, (
        f"login não autenticou: /pacientes/ devolveu {resposta.status_code}"
    )
    return cliente
