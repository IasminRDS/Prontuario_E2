# -*- coding: utf-8 -*-
"""Verificação pública de documento assinado.

Porte de `modules/documentos` + da página `/verificar/[id]` do frontend Next.

A rota de verificação é PÚBLICA de propósito: quem recebe um atestado ou laudo
precisa poder conferir a autenticidade sem ter conta no sistema. Por isso ela
expõe o mínimo — tipo, data, emissor e validade — e nunca conteúdo clínico.
"""
import hashlib

from flask import Blueprint, render_template, request
from flask_login import login_required

from models.lgpd import DocumentoAssinado
from models.user import User
from utils.rbac import requer_permissao

documentos_bp = Blueprint("documentos", __name__)


def novo_codigo():
    """Código de verificação. Gerado ANTES do PDF, porque sai impresso nele."""
    import uuid

    return uuid.uuid4().hex[:12].upper()


def registrar_documento(tipo, conteudo, paciente_id=None, referencia_tabela=None,
                        referencia_id=None, assinante=None, codigo=None):
    """Cria o registro de um documento emitido e devolve a instância.

    `conteudo` são os bytes do PDF. O chamador é responsável pelo commit — assim o
    documento e a mutação que o originou caem na mesma transação.

    `codigo` vem de fora quando o documento já foi gerado com ele impresso no
    rodapé, que é o caso das rotas de PDF: o resumo criptográfico precisa cobrir
    o arquivo que a pessoa tem em mãos, código incluído, e para isso o código
    tem de existir antes da geração.
    """
    from extensions import db

    doc = DocumentoAssinado(
        codigo=codigo or novo_codigo(),
        tipo=tipo,
        paciente_id=paciente_id,
        referencia_tabela=referencia_tabela,
        referencia_id=referencia_id,
        hash_conteudo=hashlib.sha256(conteudo).hexdigest(),
    )
    if assinante is not None:
        doc.assinado_por = assinante.id
        doc.assinante_nome = assinante.nome
        # Escopo territorial: o documento pertence à unidade de quem o assinou.
        # É a única origem disponível — o paciente é nacional de propósito.
        doc.unidade_id = getattr(assinante, "unidade_id", None)
        medico = getattr(assinante, "medico_perfil", None)
        if medico:
            doc.assinante_registro = getattr(medico, "crm", None)

    db.session.add(doc)
    return doc


@documentos_bp.get("/verificar/<codigo>")
def verificar(codigo):
    """Página PÚBLICA de verificação — sem login."""
    doc = DocumentoAssinado.query.filter_by(codigo=(codigo or "").strip().upper()).first()
    return render_template("documentos/verificar.html", doc=doc, codigo=codigo)


@documentos_bp.get("/documentos")
@login_required
@requer_permissao("clinical:read")
def listar():
    tipo = (request.args.get("tipo") or "").strip()

    query = DocumentoAssinado.query
    if tipo:
        query = query.filter(DocumentoAssinado.tipo == tipo)

    docs = query.order_by(DocumentoAssinado.emitido_em.desc()).limit(200).all()

    ids = {d.assinado_por for d in docs if d.assinado_por}
    assinantes = (
        {u.id: u for u in User.query.filter(User.id.in_(ids)).all()} if ids else {}
    )

    tipos = sorted(
        v[0]
        for v in DocumentoAssinado.query.with_entities(DocumentoAssinado.tipo).distinct().all()
        if v[0]
    )

    return render_template(
        "documentos/lista.html",
        docs=docs,
        assinantes=assinantes,
        tipo=tipo,
        tipos=tipos,
    )
