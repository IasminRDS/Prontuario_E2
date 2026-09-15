# -*- coding: utf-8 -*-
"""O recorte de registros clínicos concorda com o RLS sobre quem atravessa o
isolamento — para paciente E para prontuário.

As funções de recorte de `utils.security` traduzem em Python a mesma pergunta
que a política de RLS faz no banco: quem atravessa o isolamento territorial. Por
muito tempo elas divergiam do RLS, e essas funções não tinham teste direto — por
isso as divergências passaram. Estes testes as prendem nos dois sentidos.

**Paciente (9.4.26).** Paciente NÃO é protegido por RLS — o cadastro é nacional
por decisão (`utils.rls.FORA_DO_ESCOPO`), então o recorte em Python é a única
defesa nos DOIS bancos. `utils.security` honrava `nivel_acesso = 'SISTEMA'` de
cadastro e liberava o paciente do país inteiro; `escopo_do_usuario` recusa esse
SISTEMA (rebaixa a UNIDADE), porque atravessar o isolamento é decisão de PERFIL.

**Prontuário (9.4.27).** Prontuário TEM `unidade_id` e é protegido por RLS —
logo em PostgreSQL o RLS mascarava a divergência, e só o SQLite ficava exposto.
Ali o furo era `usuario.perfil == "admin"` cru, que liberava o Administrador de
hospital a ler prontuário de qualquer unidade, e `ESTADO` que devolvia acesso
nacional em vez de recorte por UF. A correção espelha a política de RLS,
derivando o nível da mesma `escopo_do_usuario`.
"""
from utils.rls import escopo_do_usuario
from utils.security import (pode_acessar_paciente, pode_acessar_prontuario,
                            query_pacientes_no_escopo)


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


# ------------------------------------------------------------- prontuário
class _UnidadeCompleta:
    """Unidade com os campos que a regra territorial do prontuário consulta."""
    def __init__(self, id, uf, municipio_ibge, regional_id):
        self.id = id
        self.uf = uf
        self.municipio_ibge = municipio_ibge
        self.regional_id = regional_id


class _UsuarioLotado:
    def __init__(self, perfil, nivel_acesso, unidade):
        self.perfil, self.nivel_acesso = perfil, nivel_acesso
        self.unidade = unidade
        self.unidade_id = unidade.id
        self.municipio_ibge = unidade.municipio_ibge
        self.regional_id = unidade.regional_id
        self.uf = unidade.uf


class _Prontuario:
    def __init__(self, unidade):
        self.unidade = unidade
        self.unidade_id = unidade.id


_UNID_A = _UnidadeCompleta(1, "BA", "2903201", 10)   # Bom Jesus da Lapa
_UNID_B = _UnidadeCompleta(2, "SP", "3550308", 20)   # São Paulo, outra UF


def test_administrador_de_hospital_nao_le_prontuario_de_outra_unidade():
    """O furo de 9.4.27: `perfil == "admin"` liberava prontuário de qualquer
    unidade. Administrador é escopo de unidade — só o operador da plataforma
    atravessa o hospital."""
    admin = _UsuarioLotado("admin", "UNIDADE", _UNID_A)
    assert pode_acessar_prontuario(_Prontuario(_UNID_A), admin) is True
    assert pode_acessar_prontuario(_Prontuario(_UNID_B), admin) is False


def test_super_admin_le_prontuario_de_qualquer_unidade():
    super_admin = _UsuarioLotado("SuperAdmin", "UNIDADE", _UNID_A)
    assert pode_acessar_prontuario(_Prontuario(_UNID_B), super_admin) is True


def test_escopo_estadual_de_prontuario_recorta_por_uf_e_nao_e_nacional():
    """O segundo furo de 9.4.27: ESTADO devolvia acesso nacional; a política de
    RLS recorta por UF, e agora a função também."""
    estadual = _UsuarioLotado("Gestor", "ESTADO", _UNID_A)
    assert pode_acessar_prontuario(_Prontuario(_UNID_A), estadual) is True   # mesma UF
    assert pode_acessar_prontuario(_Prontuario(_UNID_B), estadual) is False  # outra UF
