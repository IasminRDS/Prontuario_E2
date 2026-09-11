# -*- coding: utf-8 -*-
"""O comparativo entre municípios, e o recorte que o banco impõe a ele.

Dois assuntos distintos moram aqui, e é de propósito:

**A agregação.** O eixo do relatório é o município, e a chave é o código IBGE.
Agrupar por `cidade` em texto é o defeito que `models/municipio.py` descreve:
"Feira de Santana" escrito de três jeitos vira três linhas, cada uma com um
terço do movimento — e o comparativo, que existe para ordenar municípios, passa
a mentir na ordem.

**O recorte territorial.** Este é o único relatório do sistema que tenta olhar
além da própria unidade, e por isso o único em que o RLS aparece na tela. Um
usuário de nível UNIDADE que peça "Brasil" não recebe erro: recebe uma linha.
Isso é a política funcionando — e é indistinguível de tela quebrada se a
interface não disser o que está acontecendo.

Escrever estes testes revelou duas coisas que nenhum deles mede diretamente,
mas que valem registro porque custaram tempo:

1. O primeiro esboço afirmava contra o HTML inteiro, e passava lendo as opções
   do `<select>` de municípios em vez da tabela. Por isso as asserções aqui
   recortam o `<tbody>`: um comparativo que "encontra" o município na lista de
   filtros não provou nada.
2. O `admin` da suíte **não** tem escopo SISTEMA no RLS. `nivel_acesso` sozinho
   não concede: `escopo_do_usuario` rebaixa qualquer valor que não venha
   acompanhado do perfil SuperAdmin. Sem entender isso, o comparativo parecia
   ignorar metade dos dados — e a primeira hipótese levantada foi de erro na
   junção, que a medição desmentiu. O relatório estava certo desde o início;
   errada era a suposição sobre o alcance do usuário de teste.
"""
import re
from datetime import datetime, timedelta

import pytest

from tests.conftest import PERFIS, SENHA, autenticar

# Capitais reais, vindas de `database/municipios.py` — nenhum código inventado.
SALVADOR = ("2927408", "Salvador", "BA")
RECIFE = ("2611606", "Recife", "PE")

# Movimento diferente de propósito: o relatório ordena por total, e com empate
# a ordenação não provaria nada.
MOVIMENTO = {SALVADOR[0]: 3, RECIFE[0]: 1}


def _corpo_da_tabela(html):
    """Só as linhas de dado. Fora daqui moram as opções dos filtros."""
    achado = re.search(r"<tbody>(.*?)</tbody>", html, re.S)
    return achado.group(1) if achado else ""


@pytest.fixture(scope="module")
def dois_municipios(app):
    """Uma unidade em cada capital, com movimento em cada uma."""
    from extensions import db
    from models.atendimento import Atendimento
    from models.paciente import Paciente
    from models.unidade_saude import UnidadeSaude

    with app.app_context():
        unidades = {}
        for codigo, nome, uf in (SALVADOR, RECIFE):
            unidade = UnidadeSaude.query.filter_by(
                nome=f"Unidade Teste {nome}").first()
            if unidade is None:
                unidade = UnidadeSaude(nome=f"Unidade Teste {nome}", tipo="UBS",
                                       cidade=nome, uf=uf,
                                       municipio_ibge=codigo, ativo=True)
                db.session.add(unidade)
            unidades[codigo] = unidade
        db.session.commit()

        paciente = Paciente.query.order_by(Paciente.id.asc()).first()
        assert paciente is not None, "nenhum paciente semeado"

        agora = datetime.utcnow()
        for codigo, quantos in MOVIMENTO.items():
            unidade = unidades[codigo]
            existentes = Atendimento.query.filter_by(unidade_id=unidade.id).count()
            for _ in range(max(0, quantos - existentes)):
                db.session.add(Atendimento(
                    paciente_id=paciente.id, unidade_id=unidade.id,
                    data_hora=agora - timedelta(hours=1), tipo="consulta"))
        db.session.commit()
        return {c: u.id for c, u in unidades.items()}


@pytest.fixture(scope="module")
def operador_nacional(app, dados_clinicos, dois_municipios):
    """Usuário de escopo SISTEMA — o único que enxerga municípios de UFs diferentes.

    Precisa do **perfil** SuperAdmin, e não só de `nivel_acesso`: o RLS recusa
    escopo SISTEMA vindo do cadastro, porque nível de acesso é campo editável e
    atravessar o isolamento territorial não pode depender de um campo editável.
    """
    from extensions import db
    from models.user import User

    email = "operador.territorio@sus.gov.br"
    with app.app_context():
        if not User.query.filter_by(email=email).first():
            usuario = User(nome="Operador Territorial", email=email,
                           perfil="SuperAdmin", ativo=True,
                           nivel_acesso="SISTEMA")
            usuario.set_password(SENHA)
            db.session.add(usuario)
            db.session.commit()
    return autenticar(app, email)


@pytest.fixture
def usuario_de_unidade(app, dados_clinicos, dois_municipios):
    """Perfil com `reports:read` e escopo de UNIDADE."""
    return autenticar(app, PERFIS["gestor"][1])


def _pagina(cliente, **argumentos):
    resposta = cliente.get("/relatorios/territorio", query_string=argumentos)
    assert resposta.status_code == 200, resposta.status_code
    return resposta.get_data(as_text=True)


def test_compara_municipios_diferentes_na_mesma_tela(operador_nacional):
    corpo = _corpo_da_tabela(_pagina(operador_nacional))
    assert "Salvador" in corpo
    assert "Recife" in corpo


def test_a_linha_e_identificada_pelo_codigo_ibge(operador_nacional):
    """A chave da agregação aparece na tela — é o que permite conferir que dois
    municípios de nome parecido não foram somados num só."""
    corpo = _corpo_da_tabela(_pagina(operador_nacional))
    assert SALVADOR[0] in corpo, "o código IBGE não aparece na tabela"
    assert RECIFE[0] in corpo


def test_o_municipio_com_mais_movimento_vem_primeiro(operador_nacional):
    """Comparativo sem ordem obriga a ler a tabela inteira para achar o maior."""
    corpo = _corpo_da_tabela(_pagina(operador_nacional))
    assert corpo.index("Salvador") < corpo.index("Recife"), (
        "a ordenação por total não está sendo aplicada")


def test_filtro_por_uf_separa_os_estados(operador_nacional):
    corpo = _corpo_da_tabela(_pagina(operador_nacional, abrangencia="uf", uf="PE"))
    assert "Recife" in corpo
    assert "Salvador" not in corpo, "o filtro por UF não recortou"


def test_filtro_por_municipio_isola_um_so(operador_nacional):
    corpo = _corpo_da_tabela(
        _pagina(operador_nacional, abrangencia="municipio", municipio=SALVADOR[0]))
    assert "Salvador" in corpo
    assert "Recife" not in corpo


def test_a_contagem_por_municipio_e_a_que_foi_criada(operador_nacional):
    """O número, e não só a presença da linha.

    Presença de linha passa mesmo com junção errada — basta o município
    aparecer uma vez. Um relatório comparativo errado no número é pior do que
    um que não abre, porque o erro se lê como resultado.
    """
    corpo = _corpo_da_tabela(_pagina(operador_nacional))
    linha = next(l for l in corpo.split("<tr>") if SALVADOR[0] in l)
    numeros = re.findall(r">(\d+)<", linha)
    assert str(MOVIMENTO[SALVADOR[0]]) in numeros, (
        f"esperava {MOVIMENTO[SALVADOR[0]]} atendimentos em Salvador; "
        f"a linha traz {numeros}")


def test_exportacao_csv_traz_as_mesmas_linhas(operador_nacional):
    resposta = operador_nacional.get("/relatorios/territorio",
                                     query_string={"exportar": "csv"})
    assert resposta.status_code == 200
    assert "text/csv" in resposta.headers.get("Content-Type", "")

    csv = resposta.get_data().decode("utf-8-sig")
    assert "Código IBGE" in csv
    assert SALVADOR[0] in csv and RECIFE[0] in csv
    assert "TOTAL" in csv, "a linha de totais não foi exportada"


def test_o_recorte_territorial_e_explicado_a_quem_e_limitado(usuario_de_unidade):
    """O usuário de unidade precisa saber POR QUE vê pouco.

    Sem esta frase, o comparativo parece quebrado exatamente para quem está
    corretamente protegido — e a reação natural é pedir mais permissão.
    """
    html = _pagina(usuario_de_unidade)
    assert "Você enxerga" in html, (
        "a tela não informa o recorte territorial em vigor")


def test_quem_nao_tem_reports_read_nao_entra(app, dados_clinicos):
    """Recepção não tem `reports:read` na matriz. O backend é a autoridade."""
    cliente = autenticar(app, PERFIS["recepcao"][1])
    resposta = cliente.get("/relatorios/territorio")
    assert resposta.status_code in (302, 403), (
        f"recepção alcançou o relatório: {resposta.status_code}")
