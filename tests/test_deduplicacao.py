# -*- coding: utf-8 -*-
"""Índice mestre de pacientes: detecção e unificação de duplicatas.

A unificação é a operação de maior risco deste sistema. Ela move o histórico
clínico inteiro de um cadastro para outro, e errar significa misturar o
prontuário de duas pessoas — dano que nenhum desfazer conserta bem. Por isso os
testes aqui cobrem tanto o caminho feliz quanto as recusas.
"""
from datetime import date

import pytest

from extensions import db
from models.duplicata import CandidatoDuplicata
from models.paciente import Paciente
from models.prontuario import Prontuario
from services import deduplicacao
from utils.identidade import (
    LIMIAR_CANDIDATO,
    chave_bloqueio,
    codigo_fonetico,
    normalizar_nome,
    pontuar,
    so_digitos,
)


# ------------------------------------------------------------- normalização
@pytest.mark.parametrize("bruto,esperado", [
    ("123.456.789-00", "12345678900"),
    (" 700 0000 0000 0000 ", "700000000000000"),
    (None, ""),
])
def test_so_digitos(bruto, esperado):
    assert so_digitos(bruto) == esperado


@pytest.mark.parametrize("a,b", [
    ("José da Silva", "JOSE SILVA"),
    ("Maria dos Santos", "maria santos"),
    ("João  de   Souza", "JOAO SOUZA"),
])
def test_nomes_equivalentes_normalizam_igual(a, b):
    assert normalizar_nome(a) == normalizar_nome(b)


@pytest.mark.parametrize("a,b", [
    ("SOUZA", "SOUSA"),
    ("MENDONCA", "MENDONÇA"),
    ("KATIA", "CATIA"),
])
def test_grafias_do_mesmo_som_caem_no_mesmo_codigo(a, b):
    assert codigo_fonetico(a) == codigo_fonetico(b)


def test_nomes_diferentes_nao_colidem():
    assert codigo_fonetico("SILVA") != codigo_fonetico("PEREIRA")


def test_bloqueio_agrupa_por_nascimento_e_som_do_primeiro_nome():
    nascimento = date(1990, 5, 10)
    assert (chave_bloqueio("José Souza", nascimento)
            == chave_bloqueio("Jose Sousa da Costa", nascimento))
    assert (chave_bloqueio("José Souza", nascimento)
            != chave_bloqueio("José Souza", date(1991, 5, 10)))


# ------------------------------------------------------------------ pontuação
def _paciente(**campos):
    padrao = dict(nome="Maria Aparecida Souza", data_nascimento=date(1985, 3, 12),
                  sexo="F", cpf=None, cns=None, nome_mae=None)
    padrao.update(campos)
    return Paciente(**padrao)


def test_mesmo_cpf_e_prova():
    score, evidencias = pontuar(_paciente(cpf="52998224725"),
                                _paciente(nome="M A SOUZA", cpf="52998224725"))
    assert score == 1.0
    assert "mesmo CPF" in evidencias


def test_documentos_diferentes_derrubam_o_par():
    """Duas pessoas com CPFs distintos não são a mesma, por mais parecidas."""
    score, evidencias = pontuar(_paciente(cpf="52998224725"),
                                _paciente(cpf="11144477735"))
    assert score == 0.0
    assert "CPFs diferentes" in evidencias


def test_datas_diferentes_derrubam_o_par():
    score, _ = pontuar(_paciente(), _paciente(data_nascimento=date(1985, 3, 13)))
    assert score == 0.0


def test_mae_claramente_diferente_derruba_o_par():
    """É o campo que melhor separa homônimos nascidos no mesmo dia."""
    score, evidencias = pontuar(
        _paciente(nome_mae="Ana Paula Souza"),
        _paciente(nome_mae="Terezinha de Jesus Oliveira"))
    assert score == 0.0
    assert "mães diferentes" in " ".join(evidencias) or "mãe" in " ".join(evidencias)


def test_nome_parecido_e_mesma_data_viram_candidato():
    score, _ = pontuar(_paciente(nome="Maria Aparecida Souza"),
                       _paciente(nome="Maria Aparecida de Sousa"))
    assert score >= LIMIAR_CANDIDATO


def test_indicio_fraco_nunca_vira_certeza():
    """Sem documento coincidente, o score não pode chegar a 1.0."""
    score, _ = pontuar(_paciente(nome_mae="Ana Souza"),
                       _paciente(nome_mae="Ana Souza"))
    assert score < 1.0


# -------------------------------------------------------------------- varredura
@pytest.fixture
def base_limpa(app):
    with app.app_context():
        CandidatoDuplicata.query.delete()
        db.session.commit()
    yield
    with app.app_context():
        CandidatoDuplicata.query.delete()
        db.session.commit()


def _gravar(app, **campos):
    p = _paciente(**campos)
    db.session.add(p)
    db.session.commit()
    return p


def _prontuario(paciente_id):
    """`prontuarios.unidade_id` é obrigatório.

    Precisa ser a unidade dos usuários de teste: com RLS ligado, prontuário de
    outra unidade fica invisível — e a unificação não moveria o que não vê.
    """
    from models.unidade_saude import UnidadeSaude

    unidade = UnidadeSaude.query.order_by(UnidadeSaude.id.asc()).first()
    return Prontuario(paciente_id=paciente_id,
                      unidade_id=unidade.id if unidade else None)


def _candidato_de(a_id, b_id):
    """O candidato daquele par exato — não "o primeiro pendente"."""
    return CandidatoDuplicata.query.filter(
        CandidatoDuplicata.paciente_menor_id == min(a_id, b_id),
        CandidatoDuplicata.paciente_maior_id == max(a_id, b_id)).one()


def test_varredura_encontra_o_par(app, base_limpa):
    with app.app_context():
        a = _gravar(app, nome="Carlos Eduardo Lima", cpf="52998224725",
                    data_nascimento=date(1977, 9, 2))
        b = _gravar(app, nome="Carlos Eduardo de Lima", cns="700000000000001",
                    data_nascimento=date(1977, 9, 2))

        _analisados, novos = deduplicacao.varrer()
        assert novos >= 1

        par = CandidatoDuplicata.query.filter(
            CandidatoDuplicata.paciente_menor_id == min(a.id, b.id),
            CandidatoDuplicata.paciente_maior_id == max(a.id, b.id)).one()
        assert par.status == "pendente"
        assert par.score >= LIMIAR_CANDIDATO


def test_varredura_e_idempotente(app, base_limpa):
    with app.app_context():
        _gravar(app, nome="Ana Beatriz Rocha", data_nascimento=date(1993, 1, 4))
        _gravar(app, nome="Ana Beatriz da Rocha", data_nascimento=date(1993, 1, 4))

        deduplicacao.varrer()
        antes = CandidatoDuplicata.query.count()
        deduplicacao.varrer()
        assert CandidatoDuplicata.query.count() == antes


def test_par_marcado_distinto_nao_volta_a_fila(app, base_limpa):
    """Sem persistir a decisão, a fila viraria ruído que ninguém olha."""
    with app.app_context():
        a = _gravar(app, nome="Pedro Henrique Alves",
                    data_nascimento=date(1988, 7, 20))
        b = _gravar(app, nome="Pedro Henrique Alves",
                    data_nascimento=date(1988, 7, 20))

        deduplicacao.varrer()
        candidato = _candidato_de(a.id, b.id)
        deduplicacao.marcar_distintos(candidato)
        db.session.commit()

        deduplicacao.varrer()
        # Só este par: outros testes deixam candidatos na mesma base.
        assert _candidato_de(a.id, b.id).status == "distintos"
        assert CandidatoDuplicata.query.filter(
            CandidatoDuplicata.paciente_menor_id == min(a.id, b.id),
            CandidatoDuplicata.paciente_maior_id == max(a.id, b.id),
            CandidatoDuplicata.status == "pendente").count() == 0


# ------------------------------------------------------------------ unificação
class TestUnificacao:
    def test_move_todo_o_historico_clinico(self, app, base_limpa):
        with app.app_context():
            sobrevivente = _gravar(app, nome="Joana Prado",
                                   data_nascimento=date(1970, 2, 2))
            absorvido = _gravar(app, nome="Joana Prado",
                                data_nascimento=date(1970, 2, 2))

            db.session.add(_prontuario(absorvido.id))
            db.session.add(_prontuario(absorvido.id))
            db.session.commit()

            resumo = deduplicacao.unificar(sobrevivente, absorvido)
            db.session.commit()

            assert Prontuario.query.filter_by(paciente_id=absorvido.id).count() == 0
            assert Prontuario.query.filter_by(paciente_id=sobrevivente.id).count() == 2
            assert resumo["registros_movidos"]["prontuarios.paciente_id"] == 2

    def test_absorvido_nao_e_apagado(self, app, base_limpa):
        """Em prontuário, apagar é perder rastro."""
        with app.app_context():
            sobrevivente = _gravar(app, nome="Luiz Otavio",
                                   data_nascimento=date(1965, 4, 4))
            absorvido = _gravar(app, nome="Luis Otavio",
                                data_nascimento=date(1965, 4, 4))
            absorvido_id = absorvido.id

            deduplicacao.unificar(sobrevivente, absorvido)
            db.session.commit()

            ainda_existe = db.session.get(Paciente, absorvido_id)
            assert ainda_existe is not None
            assert ainda_existe.ativo is False
            assert ainda_existe.unificado_para_id == sobrevivente.id
            assert ainda_existe.unificado_em is not None
            assert ainda_existe.foi_unificado is True

    def test_sobrevivente_herda_o_documento_que_faltava(self, app, base_limpa):
        """O ganho principal: um cadastro tem só CPF, o outro só CNS."""
        with app.app_context():
            # CPF distinto do usado nos outros testes: a coluna é UNIQUE e a
            # base é compartilhada pela sessão de teste.
            sobrevivente = _gravar(app, nome="Rita Camargo", cpf="11144477735",
                                   data_nascimento=date(1982, 8, 8))
            absorvido = _gravar(app, nome="Rita Camargo", cns="700000000000002",
                                telefone="7130001111",
                                data_nascimento=date(1982, 8, 8))

            resumo = deduplicacao.unificar(sobrevivente, absorvido)
            db.session.commit()

            assert sobrevivente.cpf == "11144477735", "não pode perder o que já tinha"
            assert sobrevivente.cns == "700000000000002"
            assert sobrevivente.telefone == "7130001111"
            assert "cns" in resumo["campos_herdados"]

    def test_nao_sobrescreve_dado_existente(self, app, base_limpa):
        with app.app_context():
            sobrevivente = _gravar(app, nome="Marcos Vinicius",
                                   telefone="7133334444",
                                   data_nascimento=date(1991, 6, 6))
            absorvido = _gravar(app, nome="Marcos Vinicius",
                                telefone="7199998888",
                                data_nascimento=date(1991, 6, 6))

            deduplicacao.unificar(sobrevivente, absorvido)
            db.session.commit()
            assert sobrevivente.telefone == "7133334444"

    def test_identificador_unico_e_liberado_do_absorvido(self, app, base_limpa):
        """Sem liberar, o UNIQUE de `cns` impediria o sobrevivente de assumi-lo."""
        with app.app_context():
            sobrevivente = _gravar(app, nome="Clara Nunes",
                                   data_nascimento=date(1975, 5, 5))
            absorvido = _gravar(app, nome="Clara Nunes", cns="700000000000003",
                                data_nascimento=date(1975, 5, 5))

            deduplicacao.unificar(sobrevivente, absorvido)
            db.session.commit()

            assert sobrevivente.cns == "700000000000003"
            assert absorvido.cns is None

    def test_recusa_unificar_com_ele_mesmo(self, app, base_limpa):
        with app.app_context():
            p = _gravar(app, nome="Solo Teste", data_nascimento=date(2000, 1, 1))
            with pytest.raises(ValueError):
                deduplicacao.unificar(p, p)

    def test_recusa_unificar_cadastro_ja_unificado(self, app, base_limpa):
        with app.app_context():
            a = _gravar(app, nome="Um Teste", data_nascimento=date(2000, 1, 2))
            b = _gravar(app, nome="Um Teste", data_nascimento=date(2000, 1, 2))
            c = _gravar(app, nome="Um Teste", data_nascimento=date(2000, 1, 2))

            deduplicacao.unificar(a, b)
            db.session.commit()

            with pytest.raises(ValueError):
                deduplicacao.unificar(c, b)

    def test_nenhuma_coluna_fk_fica_para_tras(self, app):
        """A lista de colunas é descoberta pelo metadata, não escrita à mão.

        Se alguém criar uma tabela nova com `paciente_id` e a unificação não a
        conhecer, sobra registro clínico apontando para um cadastro inativo.
        """
        with app.app_context():
            colunas = deduplicacao._colunas_que_apontam_para_paciente()
            nomes = {f"{t.name}.{c.name}" for t, c in colunas}

            esperadas = {"prontuarios.paciente_id", "atendimentos.paciente_id",
                         "internacoes.paciente_id", "triagens.paciente_id",
                         "exames_solicitados.paciente_id",
                         "prescricoes.paciente_id", "agendamentos.paciente_id",
                         "atendimentos_ps.paciente_id"}
            assert esperadas <= nomes, f"faltando: {esperadas - nomes}"


# ----------------------------------------------------------------- pela tela
def test_tela_lista_e_unifica(app, base_limpa, autenticado_confirmado):
    import re

    cliente = autenticado_confirmado
    with app.app_context():
        a = _gravar(app, nome="Helena Martins", data_nascimento=date(1996, 11, 11))
        b = _gravar(app, nome="Helena Martinz", data_nascimento=date(1996, 11, 11))
        db.session.add(_prontuario(b.id))
        db.session.commit()
        ids = (a.id, b.id)

    html = cliente.get("/pacientes/duplicatas/").get_data(as_text=True)
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)
    cliente.post("/pacientes/duplicatas/varrer", data={"csrf_token": token},
                 follow_redirects=True)

    with app.app_context():
        candidato_id = _candidato_de(*ids).id

    html = cliente.get(f"/pacientes/duplicatas/{candidato_id}").get_data(as_text=True)
    assert "Qual cadastro preservar" in html
    token = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)

    resposta = cliente.post(f"/pacientes/duplicatas/{candidato_id}/unificar",
                            data={"csrf_token": token, "sobrevivente_id": ids[0]},
                            follow_redirects=True)
    assert resposta.status_code == 200

    with app.app_context():
        assert Prontuario.query.filter_by(paciente_id=ids[0]).count() == 1
        assert db.session.get(Paciente, ids[1]).unificado_para_id == ids[0]
        assert db.session.get(CandidatoDuplicata, candidato_id).status == "unificado"


def test_unificacao_exige_permissao(clientes, sem_csrf):
    for perfil in ("medico", "gestor"):
        resposta = clientes[perfil].post("/pacientes/duplicatas/1/unificar",
                                         data={"sobrevivente_id": 1})
        assert resposta.status_code in (401, 403, 404), perfil
