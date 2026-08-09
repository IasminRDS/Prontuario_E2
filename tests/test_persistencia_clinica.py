# -*- coding: utf-8 -*-
"""Os dados clínicos enviados chegam ao banco? Varredura de persistência.

Este projeto acumula um histórico específico: rota que responde 200, exibe
confirmação e não grava o que recebeu. Aconteceu no agendamento de cirurgia
(nunca criou linha), na conclusão da cirurgia (descartou o relatório inteiro),
na auditoria de escrita da API, na situação do agendamento e na edição de item
de estoque.

A medição de cobertura mostrou que os laços de sinais vitais — os que convertem
temperatura, saturação, peso, altura, glicemia e frequências — **nunca haviam
sido executados** em nenhuma rota. São o dado que sustenta a classificação de
risco e a evolução clínica, e ninguém tinha verificado que sobrevivem ao POST.

Cada teste aqui confere o VALOR GRAVADO, não o código de resposta. É a distinção
que a seção 9.2 da monografia declara e que revelou os defeitos acima.
"""
import pytest

from tests.conftest import PERFIS, autenticar


@pytest.fixture
def medico(app, dados_clinicos, sem_csrf):
    return autenticar(app, PERFIS["medico"][1])


@pytest.fixture
def paciente_id(app, medico):
    """Paciente no município da unidade do médico, restaurado ao final.

    O cadastro de paciente é nacional de propósito (fica fora do RLS), então o
    primeiro da base pode ser de outro município e as rotas clínicas recusam
    com 403 — o que mediria a autorização, não a persistência.
    """
    from extensions import db
    from models.paciente import Paciente
    from models.user import User

    with app.app_context():
        usuario = User.query.filter_by(email=PERFIS["medico"][1]).first()
        unidade = usuario.unidade
        assert unidade is not None, "o médico semeado precisa ter unidade"
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


# Sinais vitais como o formulário os envia: texto, com vírgula decimal onde o
# usuário brasileiro digita vírgula.
VITAIS = {
    "temperatura": "38,4",
    "saturacao_o2": "94",
    "peso": "72,5",
    "altura": "1,68",
    "glicemia": "110",
    "frequencia_cardiaca": "102",
    "frequencia_respiratoria": "22",
    "pressao_arterial": "140x90",
}

ESPERADO = {
    "temperatura": 38.4,
    "saturacao_o2": 94.0,
    "peso": 72.5,
    "altura": 1.68,
    "glicemia": 110.0,
    "frequencia_cardiaca": 102,
    "frequencia_respiratoria": 22,
    "pressao_arterial": "140x90",
}


def test_prontuario_grava_os_sinais_vitais(app, medico, paciente_id):
    """Os laços de conversão numérica nunca tinham sido executados.

    Se um deles descartasse o valor, o prontuário sairia sem sinais vitais e
    nada acusaria: os campos são opcionais, e vazio é estado válido.
    """
    from models.prontuario import Prontuario

    dados = {
        "paciente_id": paciente_id,
        "subjetivo": "Dor toracica ha duas horas",
        "objetivo": "Paciente alerta, orientado",
        "avaliacao": "Suspeita de sindrome coronariana",
        "plano": "ECG e troponina",
        **VITAIS,
    }
    resposta = medico.post(f"/prontuarios/novo/{paciente_id}", data=dados,
                           follow_redirects=True)
    assert resposta.status_code == 200, resposta.get_data(as_text=True)[:300]

    with app.app_context():
        p = (Prontuario.query.filter_by(paciente_id=paciente_id)
             .order_by(Prontuario.id.desc()).first())
        assert p is not None, "o prontuário não foi criado"
        assert p.subjetivo == "Dor toracica ha duas horas"
        for campo, valor in ESPERADO.items():
            obtido = getattr(p, campo)
            assert obtido == pytest.approx(valor) if isinstance(valor, float) \
                else obtido == valor, (
                f"{campo}: enviado {VITAIS[campo]!r}, gravado {obtido!r}")


def test_prontuario_recusa_vital_nao_numerico(app, medico, paciente_id):
    """Sem recusa explícita o valor cai no `except` e some sem aviso."""
    from models.prontuario import Prontuario

    with app.app_context():
        antes = Prontuario.query.filter_by(paciente_id=paciente_id).count()

    resposta = medico.post(f"/prontuarios/novo/{paciente_id}", data={
        "paciente_id": paciente_id,
        "subjetivo": "teste",
        "temperatura": "trinta e oito",
    }, follow_redirects=True)

    assert "numérico" in resposta.get_data(as_text=True), (
        "aceitou temperatura não numérica sem informar nada")
    with app.app_context():
        assert Prontuario.query.filter_by(paciente_id=paciente_id).count() == antes, (
            "criou o prontuário mesmo recusando o campo")


def test_triagem_grava_os_sinais_vitais(app, medico, paciente_id):
    """A triagem converte os mesmos campos por outro caminho — cada conversão
    escrita à mão é uma chance a mais de o valor se perder.

    Autenticado como ADMINISTRADOR e não como médico: a matriz de permissões dá
    ao perfil de medicina `triage:read` e não `triage:write`, de modo que um
    médico não consegue triar neste sistema. É coerente com o protocolo de
    Manchester, em que a triagem é da enfermagem, mas é decisão de produto — e
    aqui se mede a persistência dos sinais vitais, não a autorização.
    """
    from models.triagem import Triagem

    triador = autenticar(app, PERFIS["admin"][1])
    resposta = triador.post("/triagem/nova", data={
        "paciente_id": paciente_id,
        "classificacao": "amarelo",
        "queixa_principal": "Cefaleia intensa",
        **VITAIS,
    }, follow_redirects=True)
    assert resposta.status_code == 200, resposta.get_data(as_text=True)[:300]

    with app.app_context():
        t = (Triagem.query.filter_by(paciente_id=paciente_id)
             .order_by(Triagem.id.desc()).first())
        assert t is not None, "a triagem não foi criada"
        assert t.classificacao == "amarelo"
        for campo, valor in ESPERADO.items():
            obtido = getattr(t, campo, None)
            if obtido is None and campo == "pressao_arterial":
                continue
            assert obtido == pytest.approx(valor) if isinstance(valor, float) \
                else obtido == valor, (
                f"{campo}: enviado {VITAIS[campo]!r}, gravado {obtido!r}")


def test_vacina_aplicada_grava_o_que_foi_enviado(app, medico, paciente_id):
    """O cartão do Portal do Cidadão lê exatamente estes campos."""
    from models.vacina import Vacina, VacinaAplicada

    with app.app_context():
        vacina = Vacina.query.order_by(Vacina.id.asc()).first()
        if vacina is None:
            pytest.skip("sem imunobiológico semeado")
        vacina_id, nome = vacina.id, vacina.nome

    resposta = medico.post(f"/vacinas/cartao/{paciente_id}/dose", data={
        "vacina_id": vacina_id,
        "dose": "2a dose",
        "data_aplicacao": "2026-08-05",
        "profissional": "Enf. Responsavel",
        "observacao": "sem reacao adversa",
    }, follow_redirects=True)
    assert resposta.status_code == 200, resposta.get_data(as_text=True)[:300]

    with app.app_context():
        a = (VacinaAplicada.query.filter_by(paciente_id=paciente_id)
             .order_by(VacinaAplicada.id.desc()).first())
        assert a is not None, "a dose não foi registrada"
        assert a.dose == "2a dose", f"dose gravada como {a.dose!r}"
        assert a.nome_vacina or a.vacina_id, (
            "a dose não identifica o imunobiológico — nem por id, nem por nome")


# --- ramos apontados pela cobertura como nunca executados ------------------

def test_evolucao_de_internacao_aceita_virgula_decimal(app, medico):
    """Terceira escrita da mesma conversão. Esta fazia `int()` DEPOIS de trocar
    a vírgula por ponto, então "102,0" — que é inteiro — era recusado."""
    from extensions import db
    from models.internacao import EvolucaoInternacao, Internacao

    with app.app_context():
        intern = Internacao.query.order_by(Internacao.id.asc()).first()
        if intern is None:
            pytest.skip("sem internação semeada")
        ident = intern.id
        antes = EvolucaoInternacao.query.filter_by(internacao_id=ident).count()

    resposta = medico.post(f"/internacao/{ident}/evolucao", data={
        "subjetivo": "Refere melhora da dor",
        "objetivo": "Abdome flacido",
        "temperatura": "36,8",
        "saturacao_o2": "97,5",
        "frequencia_cardiaca": "78,0",
        "frequencia_respiratoria": "16",
        "diurese_ml": "1200",
    }, follow_redirects=True)
    assert resposta.status_code == 200, resposta.get_data(as_text=True)[:300]

    with app.app_context():
        assert EvolucaoInternacao.query.filter_by(internacao_id=ident).count() > antes, (
            "a evolução não foi criada")
        ev = (EvolucaoInternacao.query.filter_by(internacao_id=ident)
              .order_by(EvolucaoInternacao.id.desc()).first())
        assert ev.temperatura == pytest.approx(36.8)
        assert ev.saturacao_o2 == pytest.approx(97.5)
        assert ev.frequencia_cardiaca == 78, "'78,0' é inteiro e foi recusado"
        assert ev.frequencia_respiratoria == 16
        assert ev.diurese_ml == 1200


def test_resultado_de_exame_persiste(app, medico):
    """Ramo nunca executado. O resultado alimenta o sumário de alta e o PDF."""
    from extensions import db
    from models.exame import ExameSolicitado

    with app.app_context():
        e = ExameSolicitado.query.order_by(ExameSolicitado.id.asc()).first()
        if e is None:
            pytest.skip("sem exame semeado")
        e.status = "coletado"
        db.session.commit()
        ident = e.id

    resposta = medico.post(f"/exames/{ident}/resultado", data={
        "resultado_valor": "13,4",
        "resultado_unidade": "g/dL",
        "valor_referencia": "12 a 16",
        "interpretacao": "normal",
    }, follow_redirects=True)
    assert resposta.status_code == 200, resposta.get_data(as_text=True)[:300]

    with app.app_context():
        e = db.session.get(ExameSolicitado, ident)
        assert e.resultado_valor == "13,4", f"gravou {e.resultado_valor!r}"
        assert e.resultado_unidade == "g/dL"
        assert e.interpretacao == "normal"
        assert e.status == "concluido"
        assert e.data_resultado is not None, "concluiu sem carimbar a data"


def test_resultado_vazio_e_recusado(app, medico):
    """Exame concluído sem resultado é pior que exame pendente: sai da fila e
    ninguém volta a olhar."""
    from extensions import db
    from models.exame import ExameSolicitado

    with app.app_context():
        e = ExameSolicitado.query.order_by(ExameSolicitado.id.asc()).first()
        if e is None:
            pytest.skip("sem exame semeado")
        e.status = "coletado"
        db.session.commit()
        ident = e.id

    resposta = medico.post(f"/exames/{ident}/resultado", data={
        "resultado_texto": "", "resultado_valor": "",
    })
    assert "Informe o resultado" in resposta.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(ExameSolicitado, ident).status == "coletado", (
            "concluiu o exame sem resultado")


def test_negar_encaminhamento_exige_justificativa(app, dados_clinicos, sem_csrf):
    """A justificativa da negativa é o que a auditoria e o titular leem depois."""
    from extensions import db
    from models.encaminhamento import Encaminhamento

    gestor = autenticar(app, PERFIS["gestor"][1])
    with app.app_context():
        enc = Encaminhamento.query.order_by(Encaminhamento.id.asc()).first()
        if enc is None:
            pytest.skip("sem encaminhamento semeado")
        enc.status = "solicitado"
        db.session.commit()
        ident = enc.id

    sem_motivo = gestor.post(f"/regulacao/{ident}/parecer",
                             data={"decisao": "negado"}, follow_redirects=True)
    assert "justificativa" in sem_motivo.get_data(as_text=True)
    with app.app_context():
        assert db.session.get(Encaminhamento, ident).status == "solicitado", (
            "negou sem justificativa")

    com_motivo = gestor.post(f"/regulacao/{ident}/parecer", data={
        "decisao": "negado", "observacao": "Fora do perfil da referencia",
    }, follow_redirects=True)
    assert com_motivo.status_code == 200
    with app.app_context():
        enc = db.session.get(Encaminhamento, ident)
        assert enc.status == "negado"
        assert enc.retorno_info == "Fora do perfil da referencia", (
            "a justificativa não foi gravada")
