# -*- coding: utf-8 -*-
"""Fluxos que atravessam rota, model e template — onde os defeitos se escondem.

Estes dois módulos passaram muito tempo quebrados sem que nada acusasse: a
prescrição hospitalar falhava com TypeError capturado por um `except` que virava
flash, e o pronto-socorro escondia a ação principal por comparar o status com
nomes que não existem.
"""
import re

import pytest

from extensions import db
from tests.conftest import PERFIS, autenticar


def _token(html):
    return re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html).group(1)


def _mensagem(resposta):
    achado = re.search(r'alert__body">([^<]+)', resposta.get_data(as_text=True))
    return (achado.group(1) if achado else "").strip()


class TestPrescricaoHospitalar:
    @pytest.fixture
    def contexto(self, app, dados_clinicos):
        from models.internacao import Internacao
        from models.medicamento import Medicamento

        with app.app_context():
            internacao = Internacao.query.first()
            medicamento = Medicamento.query.first()
            assert internacao and medicamento, "faltou dado semeado"
            return {"internacao_id": internacao.id,
                    "medicamento_id": medicamento.id,
                    "medicamento_nome": medicamento.nome_generico}

    def _dados(self, contexto, token):
        return {
            "csrf_token": token,
            "dieta": "Dieta branda hipossódica, via oral",
            "decubito": "Decúbito elevado 30 graus",
            "sinais_vitais": "PA, FC, FR e SpO2 de 6/6h",
            "observacoes": "Reavaliar em 24h",
            "assinar": "1",
            "item_nome": [contexto["medicamento_nome"], "Soro fisiológico 0,9%"],
            "item_med_id": [str(contexto["medicamento_id"]), ""],
            "item_dose": ["1 g", "500 mL"],
            "item_concentracao": ["500 mg/mL", ""],
            "item_diluicao": ["SF 0,9% 100 mL", ""],
            "item_via": ["EV", "EV"],
            "item_velocidade": ["60 mL/h", "125 mL/h"],
            "item_frequencia": ["8/8h", "contínuo"],
            "item_horarios": ["06 14 22", ""],
            "item_duracao": ["7 dias", "24h"],
            "item_obs": ["infundir em 1h", ""],
        }

    def test_formulario_e_de_prescricao_e_nao_de_internacao(self, app, contexto):
        cliente = autenticar(app, PERFIS["medico"][1])
        html = cliente.get(
            f"/prescricao-hosp/nova/{contexto['internacao_id']}").get_data(as_text=True)
        assert 'name="item_nome"' in html
        assert 'name="leito_id"' not in html, "ainda é o formulário de internação"
        for campo in ("dieta", "decubito", "sinais_vitais", "item_concentracao",
                      "item_diluicao", "item_velocidade", "item_horarios",
                      "item_duracao"):
            assert f'name="{campo}"' in html, f"falta o campo {campo}"

    def test_medico_cria_prescricao_completa_e_assinada(self, app, contexto):
        cliente = autenticar(app, PERFIS["medico"][1])
        html = cliente.get(
            f"/prescricao-hosp/nova/{contexto['internacao_id']}").get_data(as_text=True)
        resposta = cliente.post(f"/prescricao-hosp/nova/{contexto['internacao_id']}",
                                data=self._dados(contexto, _token(html)),
                                follow_redirects=True)
        assert "Erro" not in _mensagem(resposta), _mensagem(resposta)

        from models.prescricao_hospitalar import PrescricaoHospitalar

        with app.app_context():
            p = PrescricaoHospitalar.query.order_by(
                PrescricaoHospitalar.id.desc()).first()
            assert p.paciente_id is not None
            assert p.dieta and p.decubito and p.sinais_vitais
            assert p.validade_ate is not None
            assert p.assinada_em is not None and p.assinada_por is not None

            itens = list(p.itens)
            assert len(itens) == 2
            primeiro, segundo = itens
            assert primeiro.medicamento_id == contexto["medicamento_id"]
            assert primeiro.nome_exibicao == contexto["medicamento_nome"]
            assert primeiro.concentracao == "500 mg/mL"
            assert primeiro.diluicao == "SF 0,9% 100 mL"
            assert primeiro.horarios == "06 14 22"
            assert segundo.medicamento_id is None and segundo.nome_livre
            assert [primeiro.ordem, segundo.ordem] == [0, 1]

    def test_quem_nao_e_medico_nao_assina(self, app, contexto):
        """Assinatura sem responsável identificável seria pior que nenhuma.

        O admin não tem cadastro em `medicos`: a prescrição precisa ser salva,
        mas sem assinatura e dizendo por quê.
        """
        cliente = autenticar(app, PERFIS["admin"][1])
        html = cliente.get(
            f"/prescricao-hosp/nova/{contexto['internacao_id']}").get_data(as_text=True)
        resposta = cliente.post(f"/prescricao-hosp/nova/{contexto['internacao_id']}",
                                data=self._dados(contexto, _token(html)),
                                follow_redirects=True)
        assert "sem assinatura" in resposta.get_data(as_text=True)

        from models.prescricao_hospitalar import PrescricaoHospitalar

        with app.app_context():
            p = PrescricaoHospitalar.query.order_by(
                PrescricaoHospitalar.id.desc()).first()
            assert p.assinada_em is None
            assert not (p.assinada_em and not p.assinada_por), (
                "prescrição assinada por ninguém"
            )


class TestFluxoProntoSocorro:
    """A tela precisa obedecer à máquina de estados de `routes/ps.py`."""

    @pytest.fixture
    def atendimento(self, app, dados_clinicos):
        from models.pronto_socorro import AtendimentoPS

        with app.app_context():
            ps = AtendimentoPS.query.first()
            assert ps, "faltou atendimento semeado"
            ps.status = "em_espera"
            ps.data_atendimento = None
            ps.data_liberacao = None
            db.session.commit()
            return ps.id

    def _estado(self, app, ps_id):
        from models.pronto_socorro import AtendimentoPS

        with app.app_context():
            return db.session.get(AtendimentoPS, ps_id).status

    def _opcoes_desfecho(self, html):
        bloco = re.search(r'<select name="desfecho".*?</select>', html, re.S)
        return re.findall(r'value="([^"]+)"', bloco.group(0)) if bloco else []

    def test_percurso_completo(self, app, atendimento, autenticado_confirmado):
        cliente = autenticado_confirmado
        ps_id = atendimento

        # em_espera: chamar é possível, observação não
        html = cliente.get(f"/ps/{ps_id}").get_data(as_text=True)
        assert "Chamar Paciente" in html, "a ação principal do PS não aparece"
        assert "Colocar em observação" not in html
        assert self._opcoes_desfecho(html) == ["evadiu"]

        cliente.post(f"/ps/{ps_id}/chamar",
                     data={"csrf_token": _token(html), "medico_id": ""},
                     follow_redirects=True)
        assert self._estado(app, ps_id) == "em_atendimento"

        # em_atendimento: agora observação é alcançável
        html = cliente.get(f"/ps/{ps_id}").get_data(as_text=True)
        assert "Colocar em observação" in html
        assert sorted(self._opcoes_desfecho(html)) == sorted(
            ["alta", "internado", "obito", "transferido"])

        cliente.post(f"/ps/{ps_id}/observacao", data={"csrf_token": _token(html)},
                     follow_redirects=True)
        assert self._estado(app, ps_id) == "em_observacao"

        html = cliente.get(f"/ps/{ps_id}").get_data(as_text=True)
        cliente.post(f"/ps/{ps_id}/desfecho",
                     data={"csrf_token": _token(html), "desfecho": "alta",
                           "hipotese_diag": "Faringite viral",
                           "conduta": "Sintomáticos"},
                     follow_redirects=True)
        assert self._estado(app, ps_id) == "alta"

        html = cliente.get(f"/ps/{ps_id}").get_data(as_text=True)
        assert "Chamar Paciente" not in html, "atendimento encerrado ainda oferece ação"
        assert "Faringite viral" in html


def test_cadeia_de_auditoria_permanece_integra(app, dados_clinicos):
    """Cada log carrega o hash do anterior; alterar uma linha rompe a cadeia."""
    from utils.audit import verificar_integridade

    with app.app_context():
        total, problemas = verificar_integridade()
        assert not problemas, f"{len(problemas)} inconsistência(s) em {total}: {problemas[:3]}"
