# -*- coding: utf-8 -*-
"""A tela que concede alcance territorial — e a escalação que ela poderia abrir.

O escopo territorial é o controle central deste sistema: é o que o Row-Level
Security lê para decidir o que cada usuário enxerga. Até aqui ele só existia no
banco, e conceder alcance estadual exigia `UPDATE` manual. A monografia
apresentava como central um controle que nenhuma tela editava.

**Abrir o campo numa tela abre uma porta.** Se qualquer administrador puder
escolher `ESTADO` num seletor, o administrador de uma única unidade cria um
usuário com alcance estadual, entra com ele e lê o estado inteiro — saiu do
próprio isolamento pela porta de gestão de contas, sem violar regra nenhuma das
que existiam. Os casos abaixo medem a fechadura pelos dois lados: que a
concessão legítima funciona E que a ilegítima é recusada.

Dois deles não falavam de escopo e entraram porque a mesma porta os expunha:
o perfil que chegava no POST nunca era conferido contra `perfis_atribuiveis`
(um `perfil=SuperAdmin` montado à mão passava direto, e SuperAdmin atravessa
todo o isolamento pelo próprio perfil), e um administrador podia abrir o
cadastro de um SuperAdmin e trocar-lhe a senha.
"""
import pytest

from tests.conftest import PERFIS, autenticar

UBS_CENTRAL = "UBS Central"          # João Pessoa/PB — a unidade do admin da suíte
JOAO_PESSOA = "2507507"
SALVADOR = "2927408"


@pytest.fixture
def unidade_do_admin(app):
    from models.unidade_saude import UnidadeSaude

    with app.app_context():
        return UnidadeSaude.query.filter_by(nome=UBS_CENTRAL).first().id


@pytest.fixture
def operador_plataforma(app):
    """O admin da suíte promovido a SuperAdmin, e devolvido ao que era.

    Promover o usuário existente em vez de criar um novo é deliberado: conta
    criada aqui sobreviveria ao teste (usuário com trilha de auditoria não se
    apaga, por decisão de projeto) e mudaria as contagens de quem rodasse
    depois.
    """
    from extensions import db
    from models.user import User

    email = PERFIS["admin"][1]
    with app.app_context():
        u = User.query.filter_by(email=email).first()
        anterior = u.perfil
        u.perfil = "SuperAdmin"
        db.session.commit()
    yield autenticar(app, email)
    with app.app_context():
        u = User.query.filter_by(email=email).first()
        u.perfil = anterior
        db.session.commit()


def _criar(cliente, email, **campos):
    dados = {"nome": "Fulano de Teste", "email": email, "senha": "senha-longa-1",
             "perfil": "Recepcao", "nivel_acesso": "UNIDADE"}
    dados.update(campos)
    return cliente.post("/admin/usuarios/novo", data=dados, follow_redirects=True)


def _buscar(app, email):
    from models.user import User

    with app.app_context():
        return User.query.filter_by(email=email).first()


# ------------------------------------------------------------------ a tela
def test_a_tela_oferece_o_escopo_territorial(cliente):
    """O campo existe na tela. Antes disto, só existia no banco."""
    html = cliente.get("/admin/usuarios/novo").get_data(as_text=True)
    assert 'name="nivel_acesso"' in html
    assert 'name="municipio_ibge"' in html
    assert 'name="regional_id"' in html
    assert 'name="uf"' in html


def test_a_tela_nao_oferece_o_nivel_sistema(operador_plataforma):
    """`SISTEMA` é escopo de processo, não de gente — nem para o SuperAdmin.

    `utils.rls.escopo_do_usuario` rebaixa `SISTEMA` vindo do cadastro para
    `UNIDADE`. Oferecê-lo no seletor criaria um valor que a tela promete e o
    banco ignora, e ninguém descobriria pela tela — o usuário simplesmente não
    veria nada, o que se lê como sistema quebrado.
    """
    html = operador_plataforma.get("/admin/usuarios/novo").get_data(as_text=True)
    assert 'value="SISTEMA"' not in html


def test_a_tela_declara_o_proprio_recorte(cliente):
    """Limite que não se declara vira pedido de privilégio.

    Quem vê uma lista curta sem explicação conclui que a tela está quebrada, e
    a reação natural é pedir mais acesso. O recorte dito em voz alta é parte do
    controle, não decoração — é o argumento da seção 11.3 da monografia
    aplicado à tela que concede o escopo.
    """
    html = cliente.get("/admin/usuarios/novo").get_data(as_text=True)
    assert "só concede alcance dentro dele" in html


def test_a_listagem_distingue_lotacao_de_alcance(operador_plataforma):
    """Lotação é onde escreve; alcance é o que enxerga. Eram a mesma coluna."""
    html = operador_plataforma.get("/admin/").get_data(as_text=True)
    assert "Lotação" in html and "Alcance" in html


# ------------------------------------------------------- concessão legítima
def test_superadmin_concede_alcance_estadual(app, operador_plataforma,
                                             unidade_do_admin, sem_csrf):
    """E o escopo concedido é o que o RLS vai ler — não um campo decorativo."""
    from utils.rls import escopo_do_usuario

    email = "gestor-estadual@sus.gov.br"
    _criar(operador_plataforma, email, perfil="Gestor", nivel_acesso="ESTADO",
           uf="PB", unidade_id=unidade_do_admin)

    usuario = _buscar(app, email)
    assert usuario is not None, "o cadastro não foi criado"
    assert usuario.nivel_acesso == "ESTADO"
    assert usuario.uf == "PB"

    with app.app_context():
        escopo = escopo_do_usuario(usuario)
    assert escopo["nivel"] == "ESTADO" and escopo["uf"] == "PB"
    assert not escopo["irresoluvel"], (
        "o cadastro nasceu sem o campo que o próprio nível exige: o usuário "
        "entraria e não veria registro nenhum")


def test_trocar_de_nivel_apaga_o_escopo_antigo(app, operador_plataforma,
                                               unidade_do_admin, sem_csrf):
    """Escopo de nível abandonado não pode ficar guardado esperando voltar.

    Um usuário que foi municipal e virou de unidade guardaria o código IBGE
    antigo. No dia em que alguém o devolvesse a MUNICIPIO, o alcance de meses
    atrás voltaria a valer sem que ninguém o tivesse revisto.
    """
    email = "muda-de-nivel@sus.gov.br"
    _criar(operador_plataforma, email, perfil="Gestor", nivel_acesso="MUNICIPIO",
           municipio_ibge=JOAO_PESSOA, unidade_id=unidade_do_admin)
    usuario = _buscar(app, email)
    assert usuario.municipio_ibge == JOAO_PESSOA

    operador_plataforma.post(
        f"/admin/usuarios/{usuario.id}/editar",
        data={"nome": usuario.nome, "perfil": "Gestor", "ativo": "on",
              "nivel_acesso": "UNIDADE", "unidade_id": unidade_do_admin,
              "municipio_ibge": JOAO_PESSOA},
        follow_redirects=True)

    usuario = _buscar(app, email)
    assert usuario.nivel_acesso == "UNIDADE"
    assert usuario.municipio_ibge is None, (
        "o escopo municipal continuou guardado depois da troca de nível")


def test_nivel_sem_o_campo_que_ele_exige_e_recusado(app, operador_plataforma,
                                                    unidade_do_admin, sem_csrf):
    """Cadastro que nasceria cego é recusado, não salvo em silêncio.

    Com `nivel_acesso = MUNICIPIO` e `municipio_ibge` vazio, a política do banco
    compara com NULL e nega tudo. O usuário entra, não vê registro nenhum e
    conclui que o sistema perdeu os dados.
    """
    email = "municipal-sem-municipio@sus.gov.br"
    _criar(operador_plataforma, email, perfil="Gestor", nivel_acesso="MUNICIPIO",
           municipio_ibge="", unidade_id=unidade_do_admin)
    assert _buscar(app, email) is None


# ------------------------------------------------------ escalação recusada
def test_administrador_de_unidade_nao_concede_alcance_estadual(
        app, cliente, unidade_do_admin, sem_csrf):
    """A escalação que esta tela poderia abrir, medida de frente.

    O admin da suíte tem alcance de UNIDADE. Se ele pudesse conceder `ESTADO`,
    bastaria criar a conta e entrar com ela para ler o estado inteiro.
    """
    email = "escalada-por-uf@sus.gov.br"
    _criar(cliente, email, perfil="Gestor", nivel_acesso="ESTADO", uf="PB",
           unidade_id=unidade_do_admin)
    assert _buscar(app, email) is None, (
        "administrador de unidade concedeu alcance estadual e saiu do próprio "
        "isolamento pela porta de gestão de contas")


def test_nao_se_lota_usuario_em_unidade_de_fora(app, cliente, sem_csrf):
    """O mesmo limite vale para a lotação, não só para o alcance."""
    from models.unidade_saude import UnidadeSaude

    with app.app_context():
        outra = UnidadeSaude.query.filter(
            UnidadeSaude.municipio_ibge == SALVADOR).first().id

    email = "lotado-em-salvador@sus.gov.br"
    _criar(cliente, email, unidade_id=outra)
    assert _buscar(app, email) is None


def test_perfil_fora_do_concedivel_e_recusado(app, cliente, unidade_do_admin,
                                              sem_csrf):
    """A restrição de perfil vivia só no `{% for %}` da tela.

    `perfis_atribuiveis` não oferece `SuperAdmin` a quem não é SuperAdmin, e sua
    docstring diz por quê. Mas a rota aceitava o que chegasse no POST: um
    formulário montado à mão com `perfil=SuperAdmin` criava o operador da
    plataforma — que atravessa todo o isolamento territorial pelo perfil,
    tornando decorativa qualquer regra de escopo.
    """
    email = "superadmin-por-post@sus.gov.br"
    _criar(cliente, email, perfil="SuperAdmin", unidade_id=unidade_do_admin)

    usuario = _buscar(app, email)
    assert usuario is None or usuario.perfil != "SuperAdmin", (
        "esconder a opção na tela não é a defesa: o POST concedeu SuperAdmin")


def test_administrador_nao_edita_superadmin(app, cliente, sem_csrf):
    """O caminho mais curto para a conta de outro é trocar-lhe a senha.

    Sem esta recusa, a defesa do perfil seria contornável sem conceder perfil
    nenhum: abre-se o SuperAdmin existente, define-se uma senha nova e entra-se
    como ele.
    """
    from extensions import db
    from models.user import User

    email = "alvo-superadmin@sus.gov.br"
    with app.app_context():
        alvo = User.query.filter_by(email=email).first()
        if alvo is None:
            alvo = User(nome="Operador", email=email, perfil="SuperAdmin",
                        ativo=True, nivel_acesso="UNIDADE")
            alvo.set_password("senha-longa-1")
            db.session.add(alvo)
            db.session.commit()
        alvo_id = alvo.id

    assert cliente.get(f"/admin/usuarios/{alvo_id}/editar").status_code == 403
    resposta = cliente.post(f"/admin/usuarios/{alvo_id}/editar",
                            data={"nome": "Invadido", "perfil": "Recepcao",
                                  "senha": "senha-do-invasor"},
                            follow_redirects=False)
    assert resposta.status_code == 403

    with app.app_context():
        depois = User.query.get(alvo_id)
        assert depois.perfil == "SuperAdmin"
        assert not depois.check_password("senha-do-invasor")


# ------------------------------------------------------- a regra, isolada
def test_contido_recusa_territorio_indeterminavel():
    """Dado faltando não é autorização.

    Unidade sem município nem UF não tem como ser comparada com um escopo
    estadual. Tratar isso como empate liberaria a concessão justamente no caso
    em que não se sabe nada — o oposto de falhar fechado.
    """
    from utils import territorio

    estadual = {"nivel": "ESTADO", "uf": "BA"}
    assert territorio.contido({"uf": "BA"}, estadual) is True
    assert territorio.contido({"uf": None}, estadual) is False
    assert territorio.contido(None, estadual) is False


def test_contido_dispensa_tabela_de_precedencia():
    """A ordem entre os níveis não está escrita em lugar nenhum — e não precisa.

    Um escopo estadual não cabe numa regional porque um estado não tem regional
    a comparar, e a comparação falha sozinha. Escrever a ordem à mão seria uma
    segunda fonte de verdade, que envelheceria em silêncio ao surgir um nível
    novo.
    """
    from utils import territorio

    regional = {"nivel": "REGIONAL", "regional_id": 3}
    assert territorio.contido(territorio.territorio_da_uf("BA"), regional) is False
    assert territorio.contido({"regional_id": 3}, regional) is True


def test_escopo_sem_nivel_nao_concede_nada():
    """Sessão sem escopo resolvido não é escopo amplo — é escopo nenhum."""
    from utils import territorio

    assert territorio.contido({"uf": "BA"}, {"nivel": None}) is False
    assert territorio.contido({"uf": "BA"}, {}) is False
