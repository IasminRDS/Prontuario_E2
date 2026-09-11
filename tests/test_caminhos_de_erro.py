# -*- coding: utf-8 -*-
"""Os ramos que a suíte nunca executava — e o que eles rendem.

A medição de cobertura apontou blocos contíguos grandes jamais executados, todos
com o mesmo perfil do ramo de exportação que escondia dois erros internos: corpo
de POST alcançado só por condição específica.

Dois deles merecem atenção própria:

**Troca de senha.** Fluxo de segurança com cobertura zero. Nada garantia que a
senha antiga fosse conferida, que a confirmação fosse comparada, nem que a troca
deixasse rastro na auditoria.

**Re-render de erro.** Quando a validação recusa, a rota devolve a mesma tela
com `render_template(...)` — e esse caminho passa contexto DIFERENTE do GET que
montou a tela originalmente. O detector de acessos indefinidos varre apenas
rotas GET, de modo que o contexto do re-render nunca foi verificado por
ninguém: a tela pode voltar sem as listas de seleção, e o usuário perde o
formulário inteiro no momento em que erra um campo.
"""
import io

import pytest

from tests.conftest import PERFIS, SENHA, autenticar


@pytest.fixture
def admin(app, dados_clinicos, sem_csrf):
    return autenticar(app, PERFIS["admin"][1])


# --- troca de senha: cobertura era ZERO -----------------------------------


def _restaurar_senha(app):
    from extensions import db
    from models.user import User

    with app.app_context():
        u = User.query.filter_by(email=PERFIS["admin"][1]).first()
        u.set_password(SENHA)
        db.session.commit()


def test_troca_de_senha_exige_a_senha_atual_correta(app, admin):
    from models.user import User

    resposta = admin.post("/conta/senha", data={
        "senha_atual": "senha-que-nao-e-a-dele",
        "senha_nova": "outraSenhaForte123",
        "senha_confirma": "outraSenhaForte123",
    }, follow_redirects=True)

    assert "Senha atual incorreta" in resposta.get_data(as_text=True)
    with app.app_context():
        u = User.query.filter_by(email=PERFIS["admin"][1]).first()
        assert u.check_password(SENHA), "a senha mudou sem conferir a atual"


@pytest.mark.parametrize("nova,confirma,esperado", [
    ("curta1", "curta1", "ao menos 8 caracteres"),
    ("SenhaForte123", "SenhaDiferente123", "não corresponde"),
    (SENHA, SENHA, "diferente da atual"),
])
def test_troca_de_senha_recusa_o_invalido(app, admin, nova, confirma, esperado):
    from models.user import User

    resposta = admin.post("/conta/senha", data={
        "senha_atual": SENHA, "senha_nova": nova, "senha_confirma": confirma,
    }, follow_redirects=True)

    assert esperado in resposta.get_data(as_text=True)
    with app.app_context():
        u = User.query.filter_by(email=PERFIS["admin"][1]).first()
        assert u.check_password(SENHA), f"trocou a senha aceitando {nova!r}"


def test_troca_de_senha_valida_muda_e_deixa_rastro(app, admin):
    """Alteração de credencial sem rastro é lacuna de auditoria por definição."""
    from models.audit_log import AuditLog
    from models.user import User

    with app.app_context():
        antes = AuditLog.query.filter_by(tabela="users", acao="update").count()

    try:
        resposta = admin.post("/conta/senha", data={
            "senha_atual": SENHA,
            "senha_nova": "SenhaNovaForte123",
            "senha_confirma": "SenhaNovaForte123",
        }, follow_redirects=True)
        assert "Senha alterada" in resposta.get_data(as_text=True)

        with app.app_context():
            u = User.query.filter_by(email=PERFIS["admin"][1]).first()
            assert u.check_password("SenhaNovaForte123"), "a senha não mudou"
            assert not u.check_password(SENHA), "a senha antiga continua valendo"
            depois = AuditLog.query.filter_by(tabela="users",
                                              acao="update").count()
            assert depois > antes, "troca de senha sem evento de auditoria"
    finally:
        _restaurar_senha(app)


# --- re-render de erro: o contexto nunca conferido ------------------------

def test_erro_no_estoque_devolve_o_formulario_utilizavel(app, admin):
    from models.estoque import ItemEstoque

    with app.app_context():
        item = ItemEstoque.query.order_by(ItemEstoque.id.asc()).first()
        if item is None:
            pytest.skip("sem item de estoque semeado")
        ident, nome = item.id, item.nome

    resposta = admin.post(f"/estoque/{ident}/editar", data={
        "nome": nome,
        "estoque_minimo": "nao-e-numero",
    })
    assert resposta.status_code == 200
    html = resposta.get_data(as_text=True)
    assert "numérico" in html, "a recusa não foi informada"
    # O formulário precisa VOLTAR utilizável: sem isto o usuário perde tudo o
    # que digitou e não tem como corrigir.
    assert 'name="nome"' in html, "o formulário não voltou no re-render de erro"
    assert nome in html, "o re-render perdeu os dados do próprio item"


def test_erro_na_importacao_devolve_os_motivos_por_linha(app, admin):
    """Cada linha ruim precisa dizer POR QUE. Contador anônimo de erros obriga
    a conferir o arquivo inteiro à mão."""
    csv = (
        "nome;data_nascimento;sexo\n"
        ";1990-01-01;F\n"                       # nome vazio
        "Fulano de Tal;;M\n"                    # nascimento vazio
        "Beltrano;31/12/1990;M\n"               # formato errado
    )
    dados = {
        "arquivo": (io.BytesIO(csv.encode("utf-8-sig")), "pacientes.csv"),
    }
    resposta = admin.post("/importacao/csv", data=dados,
                          content_type="multipart/form-data",
                          follow_redirects=True)
    assert resposta.status_code == 200, resposta.get_data(as_text=True)[:300]

    html = resposta.get_data(as_text=True)
    assert "nome vazio" in html
    assert "data_nascimento vazia" in html
    assert "AAAA-MM-DD" in html, "o formato esperado não é informado"


# ---------------------------------------------------------------------------
# Codificação do arquivo importado
#
# O leitor decodificava com `errors="ignore"`, e nenhum teste percebia porque
# todos os CSVs da suíte eram escritos em UTF-8 — a suíte confirmava o único
# caso que já funcionava. Planilha salva pelo Excel em português sai em cp1252,
# e ali `errors="ignore"` descartava cada byte acentuado: o paciente entrava no
# banco com o nome mutilado, sem exceção e sem aviso.
#
# Os dois primeiros casos existem para essa correção não regredir; o terceiro
# guarda o lado oposto, que é onde uma "correção" de codificação costuma quebrar
# o que estava certo.
# ---------------------------------------------------------------------------
def _importar(admin, bruto, nome="pacientes.csv"):
    return admin.post(
        "/importacao/csv",
        data={"arquivo": (io.BytesIO(bruto), nome)},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_csv_do_excel_brasileiro_preserva_os_acentos(app, admin):
    """cp1252 é o que o Excel em português grava. Antes desta correção,
    "José Antônio Conceição" era gravado como "Jos Antnio Conceio"."""
    csv = (
        "nome;data_nascimento;sexo\n"
        "José Antônio Conceição;1985-04-12;M\n"
    )
    resposta = _importar(admin, csv.encode("cp1252"))
    assert resposta.status_code == 200

    from models.paciente import Paciente
    with app.app_context():
        salvo = Paciente.query.filter(
            Paciente.nome.like("Jos%Conceiç%")).first()
        assert salvo is not None, "o paciente não foi importado"
        assert salvo.nome == "José Antônio Conceição", (
            "acentos perdidos na importação: %r" % salvo.nome)


def test_a_codificacao_reconhecida_aparece_para_o_usuario(admin):
    """Ler em silêncio é o que causou o defeito. O relatório precisa dizer
    COMO o arquivo foi interpretado, para o usuário desconfiar antes de nós."""
    csv = "nome;data_nascimento;sexo\nMaria Antônia;1990-01-01;F\n"
    html = _importar(admin, csv.encode("cp1252")).get_data(as_text=True)
    assert "Windows-1252" in html, "a codificação usada não é informada"


def test_utf8_continua_sendo_lido_como_utf8(admin):
    """A rede de segurança não pode virar o caminho principal: latin-1 aceita
    qualquer byte, e se fosse tentado antes o acento em UTF-8 viraria 'Ã§'."""
    csv = "nome;data_nascimento;sexo\nAntônio Gonçalves;1979-03-08;M\n"
    html = _importar(admin, csv.encode("utf-8-sig")).get_data(as_text=True)
    assert "UTF-8" in html
    assert "Ã" not in html, "UTF-8 foi lido como latin-1"


def test_arquivo_binario_e_recusado_em_vez_de_virar_lixo(admin):
    """latin-1 decodifica qualquer byte, inclusive os de um .xlsx renomeado.
    Sem a guarda de byte nulo, o cabeçalho viraria lixo silencioso."""
    binario = b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + bytes(range(256)) * 4
    html = _importar(admin, binario).get_data(as_text=True)
    assert "binário" in html, "arquivo binário não foi recusado"
