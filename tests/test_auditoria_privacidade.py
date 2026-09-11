# -*- coding: utf-8 -*-
"""A trilha de auditoria não pode identificar o paciente nem contar o caso dele.

Requisito NGS1.07.06 da certificação SBIS: *"Dados clínicos ou dados de
identificação do paciente não poderão ser registrados na trilha de auditoria."*

A razão é de projeto, não de burocracia. A trilha é lida por quem audita — perfil
que precisa saber **quem acessou o quê e quando**, e que não precisa, e muitas
vezes não pode, saber o conteúdo clínico. Uma trilha que repete o prontuário
transforma o controle de acesso em porta dos fundos: quem não pode abrir o
prontuário lê a mesma informação no log.

O sistema já apontava o registro pelo par (`tabela`, `registro_id`), que é o que
o NGS1.07.05 exige — o nome na descrição era, além de proibido, redundante.
Dezesseis chamadas o gravavam; uma delas, em `routes/ps.py`, gravava nome e
queixa clínica na mesma linha.

**A fronteira que este teste desenha:** sai o *conteúdo do registro clínico*
(nome, documento, CID, agravo, queixa, laudo); fica o *metadado da operação*
(situação, prioridade, leito, contagem) e a *justificativa de quem operou*, que
outros requisitos exigem — o NGS1.12.03 pede justificativa para inativação de
registro. Justificativa é texto livre e depende de quem escreve; o teste a
permite por decisão, não por descuido, e é por isso que ela está nomeada abaixo.
"""
import ast
import io
import pathlib

import pytest
import sqlalchemy as sa

from extensions import db

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FONTES = ["routes", "services", "utils"]

# Conteúdo que não pode aparecer na descrição de um evento sobre paciente.
CAMPOS_PROIBIDOS = {
    # identificação
    "nome", "nome_mae", "nome_social", "nome_paciente", "nome_vacina",
    "cpf", "cns", "rg", "data_nascimento", "telefone", "celular", "email",
    "endereco", "logradouro",
    # conteúdo do registro clínico
    "cid", "cid_principal", "cid_secundario", "agravo", "queixa",
    "queixa_principal", "interpretacao", "laudo", "diagnostico", "alergias",
    "sintomas", "subjetivo", "objetivo", "avaliacao", "plano", "prescricao",
    "evolucao", "resultado", "conduta", "anamnese",
}

# Justificativas escritas pelo operador. Entram por decisão: o NGS1.12.03 exige
# justificativa para inativar registro clínico, e guardá-la fora da trilha
# esvaziaria a responsabilização. Quem escreve deve saber que ali não vai
# conteúdo clínico — é regra de uso, que nenhum teste alcança.
JUSTIFICATIVAS_PERMITIDAS = {"motivo", "observacao", "retorno", "justificativa"}


# --------------------------------------------------------------- coleta
def _do_fonte(rotulo, codigo):
    """Extrai as chamadas de um texto-fonte. Separado para poder ser testado."""
    achadas = []
    arvore = ast.parse(codigo)
    for no in ast.walk(arvore):
        if not isinstance(no, ast.Call):
            continue
        nome = getattr(no.func, "id", None) or getattr(no.func, "attr", None)
        if nome != "registrar" or len(no.args) < 4:
            continue

        tabela = no.args[0].value if isinstance(no.args[0], ast.Constant) else None
        identificadores = set()
        for parte in ast.walk(no.args[3]):
            if not isinstance(parte, ast.FormattedValue):
                continue
            for dentro in ast.walk(parte.value):
                if isinstance(dentro, ast.Attribute):
                    identificadores.add(dentro.attr)
                elif isinstance(dentro, ast.Name):
                    identificadores.add(dentro.id)

        achadas.append({
            "arquivo": rotulo,
            "linha": no.lineno,
            "tabela": tabela,
            "identificadores": identificadores,
            "fonte": ast.unparse(no.args[3])[:110],
        })
    return achadas


def _proibidos(chamada, tabelas_de_paciente):
    if chamada["tabela"] not in tabelas_de_paciente:
        return set()  # catálogo, estoque, usuário: nome ali não identifica paciente
    return (chamada["identificadores"] & CAMPOS_PROIBIDOS) - JUSTIFICATIVAS_PERMITIDAS


def _chamadas_registrar():
    """Toda chamada a `registrar(...)` do código, com o que ela interpola."""
    achadas = []
    for pasta in FONTES:
        for caminho in sorted((RAIZ / pasta).glob("*.py")):
            achadas += _do_fonte(f"{pasta}/{caminho.name}",
                                 io.open(caminho, encoding="utf-8").read())
    return achadas


@pytest.fixture(scope="module")
def tabelas_de_paciente(app):
    """Tabelas que guardam dado de paciente, tiradas do metadata.

    Sai do metadata e não de uma lista à mão pelo mesmo motivo que a lista de
    RLS: tabela clínica nova nasce coberta, sem ninguém lembrar de incluí-la.
    """
    with app.app_context():
        alvo = {"pacientes"}
        for nome, tabela in db.metadata.tables.items():
            if "paciente_id" in tabela.columns:
                alvo.add(nome)
        return alvo


# ------------------------------------------------------------- os testes
def test_ha_chamadas_para_conferir():
    """Detector que não encontra nada para medir não está medindo."""
    chamadas = _chamadas_registrar()
    assert len(chamadas) > 50, f"só {len(chamadas)} chamadas — a varredura quebrou?"


def test_trilha_nao_identifica_o_paciente(tabelas_de_paciente):
    """NGS1.07.06, estaticamente: nome, documento e conteúdo clínico fora."""
    violacoes = []
    for c in _chamadas_registrar():
        proibidos = _proibidos(c, tabelas_de_paciente)
        if proibidos:
            violacoes.append(
                f"{c['arquivo']}:{c['linha']} grava {sorted(proibidos)} "
                f"na trilha de `{c['tabela']}` — {c['fonte']}")

    assert not violacoes, (
        "descrição de auditoria com dado de paciente (NGS1.07.06):\n  "
        + "\n  ".join(violacoes))


def test_justificativa_do_operador_continua_permitida(tabelas_de_paciente):
    """A permissão é decisão, e some se ninguém mais a usar.

    Reprova nos dois sentidos, como as listas `PENDENCIAS` dos outros
    detectores: se nenhuma chamada usa mais justificativa, a exceção virou
    decoração e deve sair de `JUSTIFICATIVAS_PERMITIDAS`.
    """
    usadas = set()
    for c in _chamadas_registrar():
        if c["tabela"] in tabelas_de_paciente:
            usadas |= c["identificadores"] & JUSTIFICATIVAS_PERMITIDAS

    assert usadas, ("nenhuma chamada usa justificativa do operador — a exceção "
                    "em JUSTIFICATIVAS_PERMITIDAS não protege mais nada")


def test_nome_do_paciente_nao_aparece_na_trilha_gravada(
        app, autenticado_confirmado, dados_clinicos):
    """O mesmo, medido no banco: abre telas de paciente e lê a trilha.

    O teste estático olha o código; este olha o que foi gravado. Um `registrar`
    montado por concatenação, fora do padrão que o AST reconhece, escaparia do
    primeiro e cai neste.
    """
    from models.audit_log import AuditLog
    from models.paciente import Paciente

    with app.app_context():
        paciente = Paciente.query.order_by(Paciente.id.asc()).first()
        assert paciente and paciente.nome, "sem paciente semeado não se mede"
        paciente_id = paciente.id
        nome = paciente.nome
        primeiro_nome = nome.split()[0]
        marco = db.session.query(sa.func.max(AuditLog.id)).scalar() or 0

    for rota in (f"/pacientes/{paciente_id}",
                 f"/prontuario/paciente/{paciente_id}",
                 f"/vacinas/cartao/{paciente_id}",
                 f"/consentimentos/paciente/{paciente_id}/"):
        autenticado_confirmado.get(rota)

    with app.app_context():
        novos = AuditLog.query.filter(AuditLog.id > marco).all()
        assert novos, "nenhum evento gravado — as rotas não auditaram nada"

        vazando = [f"#{log.id} ({log.tabela}): {log.descricao}"
                   for log in novos
                   if log.descricao and (nome in log.descricao
                                         or primeiro_nome in log.descricao)]
        assert not vazando, (
            "nome do paciente gravado na trilha:\n  " + "\n  ".join(vazando))


class TestODetectorReprova:
    """Detector que nunca reprova é decoração.

    Cada caso abaixo é uma forma real que o defeito teve antes da correção.
    """

    def test_pega_o_nome_do_paciente(self, tabelas_de_paciente):
        codigo = ('registrar("prontuarios", p.id, "read", '
                  'f"Histórico consultado ({paciente.nome})")')
        chamada = _do_fonte("plantado.py", codigo)[0]
        assert _proibidos(chamada, tabelas_de_paciente) == {"nome"}

    def test_pega_dado_clinico_sem_nome(self, tabelas_de_paciente):
        codigo = ('registrar("atendimentos_ps", a.id, "create", '
                  'f"Entrada no PS — {queixa[:80]}")')
        chamada = _do_fonte("plantado.py", codigo)[0]
        assert _proibidos(chamada, tabelas_de_paciente) == {"queixa"}

    def test_pega_o_cid(self, tabelas_de_paciente):
        codigo = 'registrar("prontuarios", p.id, "create", f"CID {p.cid_principal}")'
        chamada = _do_fonte("plantado.py", codigo)[0]
        assert _proibidos(chamada, tabelas_de_paciente) == {"cid_principal"}

    def test_nao_reclama_de_catalogo(self, tabelas_de_paciente):
        """`nome` de um imunobiológico no catálogo não identifica ninguém."""
        codigo = 'registrar("catalogo_vacinas", v.id, "create", f"Cadastrado: {nome}")'
        chamada = _do_fonte("plantado.py", codigo)[0]
        assert _proibidos(chamada, tabelas_de_paciente) == set()

    def test_nao_reclama_de_justificativa(self, tabelas_de_paciente):
        codigo = 'registrar("vacinas_aplicadas", pid, "delete", f"Removida: {motivo}")'
        chamada = _do_fonte("plantado.py", codigo)[0]
        assert _proibidos(chamada, tabelas_de_paciente) == set()
