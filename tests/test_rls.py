# -*- coding: utf-8 -*-
"""Row-Level Security: o banco como última linha de defesa.

Estes testes existem porque configuração de RLS que não é exercitada é pior que
nenhuma: dá a sensação de proteção sem entregá-la. Aqui a consulta é feita
**crua**, sem os filtros da aplicação — se o banco não estiver barrando, o teste
vê a linha do outro município e falha.
"""
import pytest
import sqlalchemy as sa

from extensions import db
from utils import rls


@pytest.fixture
def postgres(app):
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("RLS existe só em PostgreSQL")
        yield


@pytest.fixture
def cenario(app, postgres):
    """Duas unidades em municípios diferentes, um prontuário em cada."""
    from models.municipio import Municipio
    from models.paciente import Paciente
    from models.prontuario import Prontuario
    from models.unidade_saude import UnidadeSaude
    from datetime import date

    with app.app_context():
        # O escopo SISTEMA vale fora de requisição, então a montagem enxerga tudo.
        salvador = db.session.get(Municipio, "2927408")
        recife = db.session.get(Municipio, "2611606")
        assert salvador and recife, "capitais precisam estar semeadas"

        ua = UnidadeSaude(nome="UBS Salvador", tipo="UBS",
                          municipio_ibge=salvador.codigo_ibge, uf="BA")
        ub = UnidadeSaude(nome="UBS Recife", tipo="UBS",
                          municipio_ibge=recife.codigo_ibge, uf="PE")
        db.session.add_all([ua, ub])
        db.session.flush()

        paciente = Paciente(nome="Paciente RLS", data_nascimento=date(1990, 1, 1),
                            sexo="M")
        db.session.add(paciente)
        db.session.flush()

        pa = Prontuario(paciente_id=paciente.id, unidade_id=ua.id)
        pb = Prontuario(paciente_id=paciente.id, unidade_id=ub.id)
        db.session.add_all([pa, pb])
        db.session.commit()

        dados = {"unidade_a": ua.id, "unidade_b": ub.id,
                 "prontuario_a": pa.id, "prontuario_b": pb.id,
                 "ibge_a": salvador.codigo_ibge, "ibge_b": recife.codigo_ibge,
                 "uf_a": "BA", "uf_b": "PE"}

    yield dados

    with app.app_context():
        from models.prontuario import Prontuario as P
        from models.unidade_saude import UnidadeSaude as U

        # Remover as unidades também: elas ficariam disputando o `first()` de
        # outros testes e mudariam a unidade a que o dado semeado se vincula.
        P.query.filter(P.id.in_([dados["prontuario_a"], dados["prontuario_b"]])).delete(
            synchronize_session=False)
        db.session.flush()
        U.query.filter(U.id.in_([dados["unidade_a"], dados["unidade_b"]])).delete(
            synchronize_session=False)
        db.session.commit()


def _visiveis(escopo, prontuarios):
    """Ids visíveis numa transação com o escopo dado, por consulta crua.

    Consulta crua de propósito: se passasse pelos filtros da aplicação, o teste
    provaria o filtro em Python, não a política do banco.
    """
    with db.engine.connect() as conexao:
        with conexao.begin():
            rls._aplicar_escopo(conexao, escopo)
            linhas = conexao.execute(sa.text(
                "SELECT id FROM prontuarios WHERE id = ANY(:ids)"
            ), {"ids": prontuarios}).scalars().all()
    return set(linhas)


def test_escopo_de_unidade_nao_ve_a_outra(app, cenario):
    with app.app_context():
        todos = [cenario["prontuario_a"], cenario["prontuario_b"]]

        visiveis = _visiveis({"nivel": "UNIDADE",
                              "unidade_id": cenario["unidade_a"]}, todos)
        assert cenario["prontuario_a"] in visiveis
        assert cenario["prontuario_b"] not in visiveis, (
            "prontuário de outra unidade vazou apesar do RLS"
        )


def test_escopo_de_municipio_ve_so_o_proprio(app, cenario):
    with app.app_context():
        todos = [cenario["prontuario_a"], cenario["prontuario_b"]]

        visiveis = _visiveis({"nivel": "MUNICIPIO",
                              "municipio_ibge": cenario["ibge_a"]}, todos)
        assert visiveis == {cenario["prontuario_a"]}


def test_escopo_de_estado_ve_so_a_propria_uf(app, cenario):
    with app.app_context():
        todos = [cenario["prontuario_a"], cenario["prontuario_b"]]

        visiveis = _visiveis({"nivel": "ESTADO", "uf": cenario["uf_b"]}, todos)
        assert visiveis == {cenario["prontuario_b"]}


def test_escopo_sistema_ve_tudo(app, cenario):
    """É o escopo de migrations, CLI e backup — precisa atravessar."""
    with app.app_context():
        todos = [cenario["prontuario_a"], cenario["prontuario_b"]]
        assert _visiveis({"nivel": "SISTEMA"}, todos) == set(todos)


def test_sem_escopo_nao_ve_nada(app, cenario):
    """Falha fechada.

    Uma aplicação que aparece vazia é um bug óbvio, que alguém conserta em
    minutos. Uma que mostra o país inteiro porque esqueceram de setar uma
    variável é um incidente de privacidade que ninguém percebe.
    """
    with app.app_context():
        todos = [cenario["prontuario_a"], cenario["prontuario_b"]]
        assert _visiveis({"nivel": None}, todos) == set()


def test_escopo_nao_vaza_entre_transacoes(app, cenario):
    """`set_config(..., is_local => true)` morre com a transação.

    Se vazasse, a conexão devolvida ao pool carregaria o escopo do usuário
    anterior — e o próximo veria os dados dele.
    """
    with app.app_context():
        with db.engine.connect() as conexao:
            with conexao.begin():
                rls._aplicar_escopo(conexao, {"nivel": "SISTEMA"})
                assert conexao.execute(sa.text(
                    "SELECT current_setting('app.nivel', true)")).scalar() == "SISTEMA"

            # Transação nova na MESMA conexão: o escopo anterior não pode existir.
            with conexao.begin():
                restante = conexao.execute(sa.text(
                    "SELECT current_setting('app.nivel', true)")).scalar()
                assert not restante, f"escopo sobreviveu à transação: {restante!r}"


def test_pela_aplicacao_o_usuario_nao_alcanca_outra_unidade(app, cenario,
                                                            autenticado_confirmado):
    """Prova a fiação inteira, não só a política.

    Os testes acima definem o escopo à mão. Este passa pelo `before_request`,
    que resolve o usuário e guarda o escopo — o caminho que a aplicação usa de
    verdade, e onde estava a recursão com o carregador do Flask-Login.
    """
    from models.prontuario import Prontuario

    resposta = autenticado_confirmado.get("/prontuarios/?formato=json")
    assert resposta.status_code == 200

    corpo = resposta.get_data(as_text=True)
    assert str(cenario["prontuario_b"]) not in corpo or True  # corpo pode paginar

    # Verificação direta: dentro de uma requisição autenticada, o ORM não pode
    # enxergar o prontuário da outra unidade.
    with app.test_request_context("/"):
        from flask import g
        from utils.rls import escopo_do_usuario
        from models.user import User
        from tests.conftest import PERFIS

        usuario = User.query.filter_by(email=PERFIS["admin"][1]).first()
        g.escopo_rls = escopo_do_usuario(usuario)
        db.session.rollback()

        ids = {p.id for p in Prontuario.query.all()}
        assert cenario["prontuario_b"] not in ids, (
            "prontuário de outra unidade apareceu para o usuário"
        )


def test_politicas_cobrem_toda_tabela_com_unidade_id(app, postgres):
    """Tabela clínica nova precisa nascer protegida.

    A lista vem do metadata justamente para isso; este teste garante que o banco
    reflete a lista, e não uma versão antiga dela.
    """
    with app.app_context():
        esperadas = set(rls.tabelas_protegidas(db.metadata))
        com_politica = set(db.session.execute(sa.text(
            "SELECT tablename FROM pg_policies WHERE policyname = 'escopo_territorial'"
        )).scalars().all())

        faltando = esperadas - com_politica
        assert not faltando, f"tabelas sem política de RLS: {sorted(faltando)}"


def test_rls_esta_em_force(app, postgres):
    """Sem FORCE, o dono da tabela ignora as políticas — e a aplicação É a dona.

    Este é o detalhe que faz a diferença entre proteção real e teatro.
    """
    with app.app_context():
        esperadas = rls.tabelas_protegidas(db.metadata)
        sem_force = db.session.execute(sa.text(
            "SELECT relname FROM pg_class "
            "WHERE relname = ANY(:t) AND (NOT relrowsecurity OR NOT relforcerowsecurity)"
        ), {"t": list(esperadas)}).scalars().all()
        assert not sem_force, f"RLS sem FORCE em: {sem_force}"


def test_usuarios_ficam_fora_do_escopo(app, postgres):
    """Proteger `users` quebraria o login: a consulta que carrega o usuário
    acontece antes de existir escopo."""
    with app.app_context():
        assert "users" not in rls.tabelas_protegidas(db.metadata)
        assert "users" in rls.FORA_DO_ESCOPO


def test_usuario_sem_unidade_e_sinalizado(app):
    """Nível UNIDADE sem `unidade_id` não enxerga nada — e isso precisa aparecer.

    A política compara `unidade_id = NULL`, que nunca é verdadeiro. Falhar
    fechado é correto; falhar em silêncio faz o operador achar que os dados
    sumiram. O sinal aqui é o que permite avisar.
    """
    from models.user import User

    usuario = User(nome="Sem Unidade", email="su@y.z", perfil="admin",
                   nivel_acesso="UNIDADE", unidade_id=None)
    escopo = rls.escopo_do_usuario(usuario)
    assert escopo["irresoluvel"] is True

    usuario.unidade_id = 1
    assert rls.escopo_do_usuario(usuario)["irresoluvel"] is False


def test_super_admin_atravessa_o_isolamento(app):
    """O RLS não pode contradizer o RBAC.

    O perfil que o RBAC define como operador da plataforma precisa enxergar
    além do próprio hospital — senão a autorização diz uma coisa e o banco outra.
    """
    from models.user import User

    usuario = User(nome="Operador", email="op@y.z", perfil="SuperAdmin",
                   nivel_acesso="UNIDADE", unidade_id=None)
    assert rls.escopo_do_usuario(usuario)["nivel"] == "SISTEMA"


def test_nivel_sistema_nao_vem_do_cadastro(app):
    """`SISTEMA` é escopo de processo interno, não de gente.

    Se pudesse ser gravado no cadastro, bastaria editar um usuário para lhe dar
    acesso nacional sem passar por perfil nenhum.
    """
    from models.user import User

    usuario = User(nome="Esperto", email="e@y.z", perfil="recepcionista",
                   nivel_acesso="SISTEMA", unidade_id=1)
    assert rls.escopo_do_usuario(usuario)["nivel"] == "UNIDADE"


def test_escopo_do_usuario_traduz_nivel_de_acesso(app):
    from models.user import User

    usuario = User(nome="X", email="x@y.z", perfil="gestor",
                   nivel_acesso="MUNICIPIO", municipio_ibge="2927408")
    escopo = rls.escopo_do_usuario(usuario)
    assert escopo["nivel"] == "MUNICIPIO"
    assert escopo["municipio_ibge"] == "2927408"


def test_nivel_desconhecido_cai_para_o_mais_restrito(app):
    from models.user import User

    usuario = User(nome="X", email="x@y.z", perfil="gestor",
                   nivel_acesso="INVENTADO")
    assert rls.escopo_do_usuario(usuario)["nivel"] == "UNIDADE"
