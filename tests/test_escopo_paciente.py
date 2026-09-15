# -*- coding: utf-8 -*-
"""O recorte de pacientes concorda com o RLS sobre quem atravessa o isolamento.

Pacientes NÃO são protegidos por RLS — o cadastro é nacional por decisão
(`utils.rls.FORA_DO_ESCOPO`). Então o recorte territorial deles mora inteiro no
Python, em `utils.security`, nos DOIS bancos. Isso torna a regra deste módulo a
única defesa, e por muito tempo ela divergiu do RLS num ponto perigoso:
`utils.security` honrava `nivel_acesso = 'SISTEMA'` vindo do cadastro e liberava
o paciente do país inteiro, enquanto `utils.rls.escopo_do_usuario` recusa esse
SISTEMA (rebaixa a UNIDADE), porque nível de acesso é campo editável e
atravessar o isolamento é decisão de PERFIL. Em PostgreSQL o RLS anulava o
efeito; em SQLite, sem RLS, o campo editável abria acesso nacional de verdade.

Estas funções não tinham teste direto — por isso a divergência passou. O teste
reprova nos dois sentidos: se `utils.security` voltar a ler o campo cru, o
SISTEMA de cadastro volta a abrir acesso nacional e o primeiro caso falha; se
alguém tirar do SuperAdmin a travessia do isolamento, o segundo falha.
"""
from utils.rls import escopo_do_usuario
from utils.security import pode_acessar_paciente, query_pacientes_no_escopo


class _Unidade:
    def __init__(self, municipio, uf):
        self.municipio, self.uf = municipio, uf


class _Usuario:
    def __init__(self, perfil, nivel_acesso, unidade=None):
        self.perfil, self.nivel_acesso = perfil, nivel_acesso
        self.unidade = unidade
        self.unidade_id = 1 if unidade else None
        self.municipio_ibge = None
        self.regional_id = None
        self.uf = unidade.uf if unidade else None


class _Paciente:
    def __init__(self, municipio, uf):
        self.municipio, self.uf, self.municipio_ibge = municipio, uf, None


def test_sistema_de_cadastro_nao_da_acesso_a_paciente_de_outra_unidade():
    unidade = _Unidade("Bom Jesus da Lapa", "BA")
    forasteiro = _Paciente("Salvador", "BA")
    usuario = _Usuario("recepcionista", "SISTEMA", unidade=unidade)

    # O RLS rebaixa SISTEMA de cadastro a UNIDADE...
    assert escopo_do_usuario(usuario)["nivel"] == "UNIDADE"
    # ...e o recorte de pacientes concorda: nega quem está fora da unidade.
    assert pode_acessar_paciente(forasteiro, usuario) is False


def test_super_admin_atravessa_o_isolamento_de_pacientes():
    unidade = _Unidade("Bom Jesus da Lapa", "BA")
    forasteiro = _Paciente("Salvador", "BA")
    # `nivel_acesso` de UNIDADE de propósito: a travessia tem de vir do PERFIL.
    usuario = _Usuario("SuperAdmin", "UNIDADE", unidade=unidade)

    assert escopo_do_usuario(usuario)["nivel"] == "SISTEMA"
    assert pode_acessar_paciente(forasteiro, usuario) is True


def test_query_no_escopo_nao_libera_base_nacional_por_sistema_de_cadastro(
        app, dados_clinicos):
    """A irmã de `pode_acessar_paciente`, que restringe o CONJUNTO. Um usuário
    comum com SISTEMA de cadastro, lotado num município sem paciente semeado,
    tem de ver a lista VAZIA — não a base inteira."""
    from models.paciente import Paciente

    with app.app_context():
        total_ativos = Paciente.query.filter_by(ativo=True).count()
        assert total_ativos > 0, "sem paciente semeado, o teste não prova nada"

        # Município que nenhum paciente semeado tem: se o recorte funcionar, a
        # lista vem vazia; se o SISTEMA de cadastro furar, vem a base inteira.
        fora = _Usuario("recepcionista", "SISTEMA",
                        unidade=_Unidade("Município Sem Paciente ZZ", "ZZ"))
        assert query_pacientes_no_escopo(fora).count() == 0

        # O SuperAdmin, lotado no mesmo município vazio, ainda vê todos —
        # a travessia vem do perfil, não da lotação.
        super_admin = _Usuario("SuperAdmin", "UNIDADE",
                               unidade=_Unidade("Município Sem Paciente ZZ", "ZZ"))
        assert query_pacientes_no_escopo(super_admin).count() == total_ativos
