# -*- coding: utf-8 -*-
"""Fila durável de envios à RNDS.

A tela **enfileira**; quem envia é o drenador. É o que separa "a RNDS estava fora
do ar naquele segundo" de "o registro clínico se perdeu": o documento fica
gravado com o payload, e a retentativa acontece depois, sozinha.

A fila mora na própria tabela `envios_rnds` — não há Redis nem broker aqui, e
introduzir um por causa disto seria desproporcional. Postgres com `SELECT ...
FOR UPDATE SKIP LOCKED` dá exclusão mútua suficiente para vários drenadores
concorrentes, que é o único requisito real.
"""
import json
from datetime import datetime, timedelta

import sqlalchemy as sa

from extensions import db
from flask_login import current_user

from models.lgpd import EnvioRnds
from services.rnds_cliente import (
    RndsIndisponivel,
    RndsRejeitou,
    chave_idempotencia,
    obter_cliente,
)

# Depois disto o envio para de ser retentado sozinho. Oito tentativas com o
# recuo abaixo cobrem cerca de 8 horas de indisponibilidade.
MAX_TENTATIVAS = 8

# Recuo exponencial em minutos, com teto — sem teto, a nona tentativa cairia
# semanas depois e o registro ficaria parado sem ninguém perceber.
RECUO_MAXIMO_MIN = 60


def _recuo(tentativas):
    return timedelta(minutes=min(2 ** max(tentativas - 1, 0), RECUO_MAXIMO_MIN))


def enfileirar(tipo, recurso, tabela, entidade_id, paciente_id=None,
               usuario_id=None):
    """Coloca um recurso FHIR na fila. Idempotente por conteúdo.

    Reenfileirar o mesmo documento devolve o envio existente em vez de criar
    outro — inclusive quando o primeiro já foi enviado, caso em que não há nada
    a fazer.
    """
    payload = json.dumps(recurso, ensure_ascii=False, sort_keys=True)
    chave = chave_idempotencia(tipo, tabela, entidade_id, payload)

    existente = EnvioRnds.query.filter_by(chave_idempotencia=chave).first()
    if existente:
        return existente, False

    envio = EnvioRnds(
        tipo=tipo,
        entidade_tabela=tabela,
        entidade_id=entidade_id,
        paciente_id=paciente_id,
        # O payload é o conteúdo clínico serializado: sem escopo, a fila da
        # RNDS seria legível de qualquer município.
        unidade_id=getattr(current_user, 'unidade_id', None),
        payload=payload,
        chave_idempotencia=chave,
        status="pendente",
        tentativas=0,
        proxima_tentativa=datetime.utcnow(),
        criado_por=usuario_id,
    )
    db.session.add(envio)
    return envio, True


def _pendentes(limite):
    """Envios liberados para tentativa, travados contra outro drenador."""
    agora = datetime.utcnow()
    consulta = (
        EnvioRnds.query
        .filter(EnvioRnds.status == "pendente")
        .filter(sa.or_(EnvioRnds.proxima_tentativa.is_(None),
                       EnvioRnds.proxima_tentativa <= agora))
        .order_by(EnvioRnds.criado_em.asc())
        .limit(limite)
    )
    if db.engine.dialect.name == "postgresql":
        # SKIP LOCKED: dois drenadores em paralelo pegam lotes diferentes em vez
        # de um esperar o outro ou, pior, enviarem o mesmo documento.
        consulta = consulta.with_for_update(skip_locked=True)
    return consulta.all()


def processar(limite=50):
    """Tenta enviar o lote liberado. Devolve o resumo do que aconteceu.

    Cada envio é confirmado isoladamente: uma rejeição no meio do lote não pode
    desfazer os sucessos anteriores.
    """
    cliente = obter_cliente()
    resumo = {"enviados": 0, "adiados": 0, "recusados": 0, "simulado": cliente.simulado}

    for envio in _pendentes(limite):
        envio.tentativas = (envio.tentativas or 0) + 1

        # Payload ilegível é defeito do que está gravado, não da rede: retentar
        # daria exatamente o mesmo erro daqui a uma hora.
        try:
            recurso = json.loads(envio.payload or "{}")
        except (TypeError, ValueError) as exc:
            envio.status = "erro"
            envio.erro = f"payload gravado não é JSON válido: {exc}"[:2000]
            envio.proxima_tentativa = None
            resumo["recusados"] += 1
            db.session.commit()
            continue

        try:
            envio.protocolo = cliente.enviar(envio.tipo, recurso,
                                             envio.chave_idempotencia or "")
            envio.status = "enviado"
            envio.enviado_em = datetime.utcnow()
            envio.erro = None
            envio.proxima_tentativa = None
            resumo["enviados"] += 1

        except RndsRejeitou as exc:
            # A RNDS entendeu e recusou: retentar o mesmo conteúdo não muda nada.
            envio.status = "erro"
            envio.erro = str(exc)[:2000]
            envio.proxima_tentativa = None
            resumo["recusados"] += 1

        except (RndsIndisponivel, Exception) as exc:  # noqa: BLE001
            envio.erro = str(exc)[:2000]
            if envio.tentativas >= MAX_TENTATIVAS:
                # Para de tentar sozinho, mas fica visível para reenvio manual.
                envio.status = "erro"
                envio.proxima_tentativa = None
                resumo["recusados"] += 1
            else:
                envio.status = "pendente"
                envio.proxima_tentativa = datetime.utcnow() + _recuo(envio.tentativas)
                resumo["adiados"] += 1

        db.session.commit()

    return resumo


def reenfileirar(envio):
    """Devolve um envio já encerrado à fila, para tentativa manual."""
    envio.status = "pendente"
    envio.erro = None
    envio.tentativas = 0
    envio.proxima_tentativa = datetime.utcnow()
    return envio
