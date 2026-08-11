# -*- coding: utf-8 -*-
"""O ciclo do documento verificável, medido de ponta a ponta.

Este arquivo existe por causa de um achado: `registrar_documento` era o único
escritor de `documentos_assinados` e ninguém a chamava. A tabela nunca era
escrita, e a rota PÚBLICA de verificação — que existe para quem recebeu um
atestado conferir se ele é autêntico — respondia "não encontrado" para todo
código, inclusive os legítimos.

É a mesma classe do achado 9.4.16 da monografia: estrutura completa, e nenhum
caminho de execução que a alcance. A varredura de rota sem porta de entrada não
o pegava, porque as rotas existiam e eram alcançáveis; o que faltava era a
ESCRITA que daria conteúdo a elas.

O que se mede aqui é o ciclo, e não as partes: emitir o PDF, achar o registro,
conferir que o código saiu impresso no arquivo, e verificar publicamente — sem
sessão, como faria quem recebeu o documento.
"""
import pytest

from extensions import db
from models.lgpd import DocumentoAssinado


@pytest.fixture
def limpar_documentos(app):
    """A tabela é global ao teste; começa e termina vazia."""
    with app.app_context():
        DocumentoAssinado.query.delete()
        db.session.commit()
    yield
    with app.app_context():
        DocumentoAssinado.query.delete()
        db.session.commit()


def _texto_do_pdf(conteudo):
    from PyPDF2 import PdfReader
    from io import BytesIO

    leitor = PdfReader(BytesIO(conteudo))
    return "\n".join((p.extract_text() or "") for p in leitor.pages)


def test_emitir_prontuario_registra_documento_verificavel(
        app, cliente, dados_clinicos, limpar_documentos):
    """Emitir o PDF precisa deixar rastro verificável — não só devolver bytes."""
    with app.app_context():
        from models.prontuario import Prontuario
        prontuario_id = Prontuario.query.first().id

    resposta = cliente.get(f"/pdf/prontuario/{prontuario_id}")
    assert resposta.status_code == 200
    assert resposta.mimetype == "application/pdf"

    with app.app_context():
        doc = DocumentoAssinado.query.filter_by(tipo="prontuario").first()
        assert doc is not None, (
            "o PDF foi emitido e nada foi registrado — a rota pública de "
            "verificação não teria o que verificar")
        assert doc.hash_conteudo, "documento registrado sem resumo do conteúdo"
        assert doc.referencia_tabela == "prontuarios"
        assert doc.referencia_id == prontuario_id
        codigo = doc.codigo

    # O código PRECISA sair impresso: quem recebe o documento não tem outra
    # origem para ele. Registrar sem imprimir deixa o ciclo pela metade.
    assert codigo in _texto_do_pdf(resposta.data), (
        "o código de verificação não saiu no PDF — o destinatário não teria "
        "o que digitar na tela de verificação")


def test_verificacao_e_publica_e_encontra_o_documento(
        app, cliente, anonimo, dados_clinicos, limpar_documentos):
    """Sem sessão, como faria quem recebeu o atestado em mãos."""
    with app.app_context():
        from models.prontuario import Prontuario
        prontuario_id = Prontuario.query.first().id

    cliente.get(f"/pdf/prontuario/{prontuario_id}")

    with app.app_context():
        codigo = DocumentoAssinado.query.first().codigo

    resposta = anonimo.get(f"/verificar/{codigo}")
    assert resposta.status_code == 200, (
        "a verificação exigiu sessão — ela é pública de propósito, porque "
        "quem recebe o documento não tem conta no sistema")
    assert codigo in resposta.get_data(as_text=True)


def test_codigo_inexistente_nao_confirma_nada(anonimo, limpar_documentos):
    """Falso positivo aqui transformaria a verificação em teatro."""
    resposta = anonimo.get("/verificar/CODIGOQUENAOEXISTE")
    assert resposta.status_code == 200
    corpo = resposta.get_data(as_text=True).lower()
    assert "não encontrado" in corpo or "nao encontrado" in corpo or \
        "inválido" in corpo or "invalido" in corpo, (
        "código inexistente precisa ser recusado de forma legível")


def test_cada_emissao_gera_um_codigo_distinto(
        app, cliente, dados_clinicos, limpar_documentos):
    """Código repetido faria uma emissão herdar a autenticidade de outra."""
    with app.app_context():
        from models.prontuario import Prontuario
        prontuario_id = Prontuario.query.first().id

    for _ in range(3):
        cliente.get(f"/pdf/prontuario/{prontuario_id}")

    with app.app_context():
        codigos = [d.codigo for d in DocumentoAssinado.query.all()]
    assert len(codigos) == 3
    assert len(set(codigos)) == 3, f"códigos repetidos: {codigos}"


def test_documento_registrado_herda_a_unidade_de_quem_assina(
        app, cliente, dados_clinicos, limpar_documentos):
    """Sem `unidade_id`, o registro fica invisível sob a política de RLS.

    A coluna nasce nula e a política é de falha fechada: documento sem unidade
    resolvida some da tela para todo escopo que não seja SISTEMA.
    """
    with app.app_context():
        from models.prontuario import Prontuario
        prontuario_id = Prontuario.query.first().id

    cliente.get(f"/pdf/prontuario/{prontuario_id}")

    with app.app_context():
        doc = DocumentoAssinado.query.first()
        assert doc.assinado_por is not None, "documento sem autoria registrada"
        assert doc.unidade_id is not None, (
            "documento sem unidade: sob a política de isolamento ele fica "
            "invisível para todo escopo que não seja SISTEMA")
