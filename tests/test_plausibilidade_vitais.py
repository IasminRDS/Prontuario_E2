# -*- coding: utf-8 -*-
"""O número que era número e não podia ser aquela medida.

`utils/numeros.py` respondia se o texto digitado **é um número**. Faltava a
outra pergunta: se o número **pode ser aquela medida**. Uma altura de 172 —
metros, porque é o que o rótulo do campo pede — atravessava tudo: convertia sem
erro, gravava, aparecia na tela, entrava no cálculo de IMC e saía num recurso
FHIR `8302-2` bem formado. Documento válido e impossível, aceito pelo transporte
e guardado pelo registro nacional.

O achado é da mesma família de 9.4.13 e 9.4.17: **defeito que não gera erro**.
Nada falha, nada acusa, e o dado errado se parece com dado.

Os casos abaixo verificam **os dois sentidos**, como 9.4.19 estabeleceu:

- que o impossível é recusado — porque essa é a função;
- que o **raro e verdadeiro passa** — porque um sistema que recusasse 41,8 °C
  obrigaria quem tria a contornar o prontuário no momento em que ele mais
  importa. Restrição que barra quem deveria passar é indisponibilidade clínica,
  não segurança.

E um caso registra o que este controle **não** pega: peso 7,0 no lugar de 70,0
passa, porque 7 kg é o peso de um lactente. Fixar a limitação por medição evita
que a documentação passe a prometer uma conferência que não existe.
"""
import pytest

from tests.conftest import PERFIS, autenticar
from utils import sinais_vitais


# --------------------------------------------------------------- a regra
@pytest.mark.parametrize("campo, valor, motivo", [
    ("altura", 172.0, "o campo é em metros; 172 é a estatura em centímetros"),
    ("altura", 0.05, "menor que qualquer recém-nascido"),
    ("temperatura", 98.6, "Fahrenheit digitado no campo de Celsius"),
    ("temperatura", 3.6, "vírgula perdida em 36"),
    ("saturacao_o2", 980.0, "dígito a mais numa fração do total"),
    ("saturacao_o2", 101.0, "acima de 100% não existe medida, existe erro"),
    ("frequencia_cardiaca", 800, "dígito a mais"),
    ("peso", 700.0, "acima do maior peso humano registrado"),
    ("glicemia", 90000.0, "três dígitos a mais"),
    ("dor_escala", 11, "a escala é definida de 0 a 10"),
])
def test_o_impossivel_e_recusado(campo, valor, motivo):
    recusa = sinais_vitais.conferir(campo, valor)
    assert recusa, f"{campo}={valor} passou, e {motivo}"
    assert str(int(valor)) in recusa or str(valor) in recusa, (
        "a mensagem não repete o valor recusado, e quem errou precisa ver "
        "qual número o sistema leu")


@pytest.mark.parametrize("campo, valor, motivo", [
    ("temperatura", 41.8, "hipertermia grave é rara e verdadeira"),
    ("temperatura", 28.0, "hipotermia acidental com sobrevida documentada"),
    ("frequencia_cardiaca", 0, "parada cardíaca se registra, e o valor é zero"),
    ("frequencia_cardiaca", 240, "taquiarritmia"),
    ("frequencia_respiratoria", 0, "apneia se registra"),
    ("saturacao_o2", 100.0, "o extremo do intervalo pertence ao intervalo"),
    ("saturacao_o2", 45.0, "cardiopatia cianótica"),
    ("peso", 0.4, "prematuro extremo"),
    ("altura", 0.48, "recém-nascido"),
    ("altura", 2.4, "estatura excepcional, e documentada"),
    ("glicemia", 1200.0, "estado hiperosmolar"),
])
def test_o_raro_e_verdadeiro_passa(campo, valor, motivo):
    """Recusar apenas o impossível, nunca o improvável."""
    assert sinais_vitais.conferir(campo, valor) is None, (
        f"{campo}={valor} foi recusado, e {motivo} — restrição que barra quem "
        "deveria passar é indisponibilidade clínica, não segurança")


def test_ausencia_de_medida_nao_e_erro():
    """Campo em branco é ausência legítima, e não valor fora da faixa."""
    for campo in sinais_vitais.LIMITES:
        assert sinais_vitais.conferir(campo, None) is None


def test_campo_fora_da_tabela_nao_e_julgado():
    """`retorno_dias` passa pelo mesmo laço do prontuário e não é sinal vital."""
    assert sinais_vitais.conferir("retorno_dias", 999) is None


def test_o_que_este_controle_nao_pega():
    """A limitação, fixada por medição e não por memória.

    7 kg é o peso de um lactente, e nenhuma faixa distingue isso de um adulto
    de 70 kg com a vírgula perdida sem saber a idade do paciente. Se um dia
    alguém acrescentar faixa por faixa etária, este caso falha — e é o momento
    certo de rever o que a documentação promete.
    """
    assert sinais_vitais.conferir("peso", 7.0) is None
    assert sinais_vitais.conferir("temperatura", 36.0) is None


# ------------------------------------------------------------- pressão
@pytest.mark.parametrize("texto", ["80/120", "120/120", "400/90", "120/5"])
def test_pressao_impossivel_e_recusada(texto):
    assert sinais_vitais.conferir_pressao(texto), f"{texto} passou"


def test_a_inversao_e_o_erro_que_nenhuma_faixa_isolada_pega():
    """80/120 tem as duas metades dentro da faixa e mesmo assim não existe.

    É o erro de digitação mais comum no campo, e o único que só se encontra
    comparando os dois números entre si.
    """
    recusa = sinais_vitais.conferir_pressao("80/120")
    assert recusa and "trocados" in recusa


@pytest.mark.parametrize("texto", ["120/80", "90 x 60", "200/110", "", None,
                                   "inaudível", "PA não aferida"])
def test_pressao_legivel_ou_textual_passa(texto):
    """Texto que não é um par de números é achado clínico, não erro.

    Recusar "PA inaudível" tiraria da enfermagem o registro de uma informação
    que é ela própria relevante.
    """
    assert sinais_vitais.conferir_pressao(texto) is None


def test_o_formulario_e_o_servidor_leem_a_mesma_faixa():
    """`min`/`max` do HTML saem da tabela que a rota consulta.

    Escritos duas vezes, divergiriam na primeira revisão de limite — e a metade
    desatualizada seria a do formulário, que nenhum teste lê. É a replicação de
    regra da seção 9.4.14, aplicada a um atributo de HTML.
    """
    faixa = sinais_vitais.atributos("altura")
    assert faixa == {"min": "0.2", "max": "2.8"}
    assert sinais_vitais.conferir("altura", float(faixa["max"])) is None
    assert sinais_vitais.conferir("altura", float(faixa["max"]) + 0.1)


def test_todo_limite_tem_a_razao_escrita():
    """Limite sem origem é limite que alguém aperta 'por segurança' depois.

    E o aperto só aparece quando recusa a medida de um paciente real.
    """
    for campo, (minimo, maximo, _un, rotulo, razao) in sinais_vitais.LIMITES.items():
        assert minimo < maximo, f"{campo}: faixa vazia"
        assert rotulo, f"{campo}: sem rótulo de tela"
        assert len(razao) > 25, f"{campo}: justificativa vazia ou decorativa"


def test_campo_sem_limite_tem_a_razao_declarada():
    """Ausência por decisão, e não por esquecimento — como em FORA_POR_DECISAO."""
    assert sinais_vitais.SEM_LIMITE
    for campo, razao in sinais_vitais.SEM_LIMITE.items():
        assert campo not in sinais_vitais.LIMITES, (
            f"{campo} ganhou faixa e continua na lista de exceções")
        assert len(razao) > 25, f"{campo}: exceção sem justificativa"


# ----------------------------------------------------------- nas rotas
@pytest.fixture
def enfermeiro(app):
    return autenticar(app, PERFIS["enfermeiro"][1])


@pytest.fixture
def paciente_do_medico(app, dados_clinicos):
    """Um paciente no município da unidade do médico, restaurado ao final.

    Mesma fixture de `test_auditoria_json_write`, e pela mesma razão: com o
    paciente fora do escopo, a rota devolve 403 ANTES de chegar à conferência —
    e o caso passaria a medir a autorização em vez da plausibilidade.
    """
    from extensions import db
    from models.paciente import Paciente
    from models.user import User

    with app.app_context():
        usuario = User.query.filter_by(email=PERFIS["medico"][1]).first()
        unidade = usuario.unidade
        paciente = Paciente.query.order_by(Paciente.id.asc()).first()
        anterior = (paciente.municipio, paciente.uf)
        paciente.municipio, paciente.uf = unidade.municipio, unidade.uf
        db.session.commit()
        alvo = paciente.id
    yield alvo
    with app.app_context():
        paciente = db.session.get(Paciente, alvo)
        paciente.municipio, paciente.uf = anterior
        db.session.commit()


@pytest.fixture
def paciente_id(app, dados_clinicos):
    from models.paciente import Paciente

    with app.app_context():
        return Paciente.query.filter_by(ativo=True).first().id


def _triagens(app):
    from models.triagem import Triagem

    with app.app_context():
        return Triagem.query.count()


def _postar_triagem(cliente, paciente_id, **vitais):
    dados = {"paciente_id": str(paciente_id), "classificacao": "verde",
             "queixa_principal": "dor torácica"}
    dados.update(vitais)
    return cliente.post("/triagem/nova", data=dados, follow_redirects=True)


def test_a_triagem_recusa_a_altura_em_centimetros(app, enfermeiro, paciente_id,
                                                  sem_csrf):
    """O caso concreto que originou este arquivo."""
    antes = _triagens(app)
    resposta = _postar_triagem(enfermeiro, paciente_id, altura="172", peso="70")

    assert _triagens(app) == antes, "a triagem impossível foi gravada"
    # "Altura" sozinha casaria com o rótulo do próprio campo no formulário
    # reapresentado — a asserção passaria sem que mensagem alguma existisse.
    assert "fora do possível" in resposta.get_data(as_text=True), (
        "a triagem foi recusada sem dizer por quê")


def test_a_triagem_aceita_a_medida_certa(app, enfermeiro, paciente_id, sem_csrf):
    """O outro sentido: a recusa não pode ter fechado o caminho normal."""
    antes = _triagens(app)
    _postar_triagem(enfermeiro, paciente_id, altura="1,72", peso="70,5",
                    temperatura="38,4", saturacao_o2="96",
                    frequencia_cardiaca="102", pressao_arterial="120/80")

    assert _triagens(app) == antes + 1, (
        "uma triagem inteiramente plausível foi recusada")


def test_a_triagem_recusa_a_pressao_invertida(app, enfermeiro, paciente_id,
                                              sem_csrf):
    antes = _triagens(app)
    resposta = _postar_triagem(enfermeiro, paciente_id,
                               pressao_arterial="80/120")

    assert _triagens(app) == antes
    assert "trocados" in resposta.get_data(as_text=True)


def test_o_valor_vindo_como_texto_e_conferido_igual(app):
    """A porta JSON entrega o que o cliente mandou, e texto compara diferente.

    '"172" <= 2.8' levanta TypeError em Python 3: sem coagir antes, a
    conferência morreria com erro 500 exatamente no caminho que ela vigia.
    """
    assert sinais_vitais.conferir("altura", "172")
    assert sinais_vitais.conferir("altura", "1.72") is None
    # Texto que nem número é passa adiante: essa pergunta é de .
    assert sinais_vitais.conferir("altura", "não aferida") is None


def test_a_interface_programatica_recusa_o_mesmo_que_a_tela(app, paciente_do_medico,
                                                            sem_csrf):
    """A mesma entidade tinha duas portas, e a conferência vivia só numa.

    É a estrutura de 9.4.18 com outro assunto: um integrador que postasse JSON
    contornava a conferência inteira — e é justamente o integrador que grava em
    volume, sem ninguém olhando a tela.
    """
    from models.prontuario import Prontuario

    medico = autenticar(app, PERFIS["medico"][1])
    with app.app_context():
        antes = Prontuario.query.count()

    resposta = medico.post("/prontuarios/", json={"paciente_id": paciente_do_medico,
                                                  "altura": 172})
    assert resposta.status_code == 400, (
        "a porta JSON aceitou uma altura de 172 metros")
    # Pelo JSON decodificado, e não pelo corpo cru: o Flask escapa o não-ASCII
    # na serialização, e "possível" chega como "possível".
    assert "fora do possível" in resposta.get_json()["erro"]

    with app.app_context():
        assert Prontuario.query.count() == antes, "gravou mesmo recusando"


def test_a_interface_programatica_continua_aceitando_o_valido(app,
                                                              paciente_do_medico,
                                                              sem_csrf):
    """O outro sentido: a guarda não pode ter fechado a porta."""
    medico = autenticar(app, PERFIS["medico"][1])
    resposta = medico.post("/prontuarios/", json={"paciente_id": paciente_do_medico,
                                                  "altura": 1.72, "peso": 70.5})
    assert resposta.status_code == 201, resposta.get_data(as_text=True)


def test_a_recusa_devolve_o_que_foi_digitado(app, enfermeiro, paciente_id,
                                             sem_csrf):
    """Formulário que pune quem erra é formulário que se aprende a contornar.

    A tela voltava em branco: um valor recusado custava os outros sete sinais
    vitais, a queixa e as observações. Numa triagem, esse atrito leva a deixar
    o campo vazio da próxima vez — e o resultado é menos dado registrado, que é
    o oposto do que a conferência existe para conseguir.
    """
    resposta = _postar_triagem(enfermeiro, paciente_id, altura="172",
                               peso="70,5", temperatura="38,4",
                               queixa_principal="dor toracica ha duas horas")
    html = resposta.get_data(as_text=True)

    # Com PONTO, e não com a vírgula digitada. Os campos são `type="number"`, e
    # `value="70,5"` é recusado pelo próprio navegador: o atributo aparece no
    # HTML e o campo renderiza VAZIO. Este caso nasceu afirmando a vírgula,
    # passou, e a tela continuava perdendo o valor — o defeito só apareceu ao
    # abrir a página. A asserção agora mede o que o navegador aceita.
    assert 'value="70.5"' in html, "o peso digitado se perdeu na recusa"
    assert 'value="38.4"' in html, "a temperatura digitada se perdeu"
    assert "dor toracica ha duas horas" in html, "a queixa se perdeu"
    assert 'value="172"' in html, (
        "o próprio valor recusado voltou em branco, e quem tria não vê o que "
        "o sistema leu")


# ------------------------------------------------------------ no FHIR
def test_valor_impossivel_gravado_antes_nao_vira_recurso_fhir(app,
                                                              dados_clinicos):
    """A guarda para o que já está no banco.

    A tela passou a recusar na entrada, mas registros anteriores continuam lá.
    Emitir uma altura de 172 metros produziria um `8302-2` que passa na
    validação do FHIR e é falso — o mesmo "aceito pelo transporte e errado no
    significado" que a pressão ilegível já evitava.
    """
    from extensions import db
    from models.prontuario import Prontuario
    from routes.rnds import _map_observations

    with app.app_context():
        pr = Prontuario.query.first()
        assert pr is not None, "faltou prontuário semeado"
        antes = (pr.altura, pr.pressao_arterial)
        pr.altura, pr.pressao_arterial = 172.0, "80/120"
        db.session.commit()

        codigos = [r["code"]["coding"][0]["code"] for r in _map_observations(pr)]

        pr.altura, pr.pressao_arterial = antes
        db.session.commit()

    assert "8302-2" not in codigos, "a altura impossível foi publicada"
    assert "85354-9" not in codigos, "a pressão invertida foi publicada"


def test_a_guarda_do_fhir_nao_engole_o_que_e_valido(app, dados_clinicos):
    """E o outro sentido, sem o qual a guarda acima poderia ser um `return []`."""
    from extensions import db
    from models.prontuario import Prontuario
    from routes.rnds import _map_observations

    with app.app_context():
        pr = Prontuario.query.first()
        antes = (pr.altura, pr.pressao_arterial)
        pr.altura, pr.pressao_arterial = 1.72, "120/80"
        db.session.commit()

        codigos = [r["code"]["coding"][0]["code"] for r in _map_observations(pr)]

        pr.altura, pr.pressao_arterial = antes
        db.session.commit()

    assert "8302-2" in codigos and "85354-9" in codigos
