# -*- coding: utf-8 -*-
"""Detecção e unificação de cadastros duplicados de paciente.

Duas operações bem diferentes moram aqui. A **varredura** é barata, automática e
não decide nada: agrupa candidatos e os coloca numa fila de revisão. A
**unificação** é irreversível na prática e por isso só acontece por ação humana
explícita — nenhum par é fundido automaticamente, nem com score 1.0.

Essa separação é deliberada. Unificar dois pacientes errados mistura o histórico
clínico de duas pessoas, e desfazer isso depois é muito pior do que revisar uma
fila.
"""
from collections import defaultdict
from datetime import datetime

import sqlalchemy as sa

from extensions import db
from models.duplicata import CandidatoDuplicata
from models.paciente import Paciente
from utils.identidade import (
    LIMIAR_CANDIDATO,
    chave_bloqueio,
    pontuar,
)

# Campos que o sobrevivente pode herdar do absorvido quando estiverem vazios.
# Nunca sobrescrevem: na dúvida, o dado do cadastro escolhido prevalece.
CAMPOS_HERDAVEIS = (
    "cns", "cpf", "rg", "nome_social", "nome_mae", "nome_pai",
    "telefone", "telefone2", "email",
    "cep", "logradouro", "numero", "complemento", "bairro",
    "municipio", "municipio_ibge", "uf",
    "raca_cor", "tipo_sanguineo", "alergias",
)


def _par_ordenado(a_id, b_id):
    return (a_id, b_id) if a_id < b_id else (b_id, a_id)


def varrer(limite_blocos=None):
    """Procura candidatos e enfileira os que passam do limiar.

    Devolve (analisados, novos). Idempotente: par já decidido não volta, e par
    pendente tem apenas o score atualizado.

    O agrupamento por chave de bloqueio é o que torna isto viável — comparar
    todos contra todos seria O(N²).
    """
    pacientes = (
        Paciente.query
        .filter(Paciente.unificado_para_id.is_(None))
        .all()
    )

    blocos = defaultdict(list)
    for p in pacientes:
        chave = chave_bloqueio(p.nome, p.data_nascimento)
        if chave:
            blocos[chave].append(p)

    decididos = {
        _par_ordenado(c.paciente_menor_id, c.paciente_maior_id)
        for c in CandidatoDuplicata.query.filter(
            CandidatoDuplicata.status != "pendente").all()
    }
    pendentes = {
        _par_ordenado(c.paciente_menor_id, c.paciente_maior_id): c
        for c in CandidatoDuplicata.query.filter_by(status="pendente").all()
    }

    analisados = novos = 0
    for indice, (_chave, grupo) in enumerate(blocos.items()):
        if limite_blocos and indice >= limite_blocos:
            break
        if len(grupo) < 2:
            continue

        for i, a in enumerate(grupo):
            for b in grupo[i + 1:]:
                analisados += 1
                par = _par_ordenado(a.id, b.id)
                if par in decididos:
                    continue

                score, evidencias = pontuar(a, b)
                if score < LIMIAR_CANDIDATO:
                    continue

                existente = pendentes.get(par)
                if existente:
                    existente.score = score
                    existente.evidencias = "; ".join(evidencias)
                    continue

                candidato = CandidatoDuplicata(
                    paciente_menor_id=par[0],
                    paciente_maior_id=par[1],
                    score=score,
                    evidencias="; ".join(evidencias),
                    status="pendente",
                )
                db.session.add(candidato)
                pendentes[par] = candidato
                novos += 1

    db.session.commit()
    return analisados, novos


def _colunas_que_apontam_para_paciente():
    """Toda coluna FK para `pacientes.id`, descoberta pelo metadata.

    Enumerar à mão as 21 colunas de hoje seria errado amanhã: a que for
    esquecida deixa registro clínico órfão apontando para um cadastro inativo.
    """
    alvo = Paciente.__table__.c.id
    encontradas = []
    for tabela in db.metadata.sorted_tables:
        for coluna in tabela.columns:
            for fk in coluna.foreign_keys:
                if fk.column is alvo:
                    encontradas.append((tabela, coluna))
    return encontradas


def unificar(sobrevivente, absorvido, usuario_id=None):
    """Move tudo do `absorvido` para o `sobrevivente`.

    Devolve o resumo do que foi movido, por tabela. Não apaga nada: o absorvido
    fica inativo e apontando para o sobrevivente.
    """
    if sobrevivente.id == absorvido.id:
        raise ValueError("sobrevivente e absorvido são o mesmo cadastro")
    if absorvido.unificado_para_id:
        raise ValueError("este cadastro já foi unificado a outro")

    movidos = {}
    for tabela, coluna in _colunas_que_apontam_para_paciente():
        if tabela.name == CandidatoDuplicata.__tablename__:
            continue  # tratado à parte, logo abaixo
        resultado = db.session.execute(
            sa.update(tabela)
            .where(coluna == absorvido.id)
            .values({coluna.name: sobrevivente.id})
        )
        if resultado.rowcount:
            movidos[f"{tabela.name}.{coluna.name}"] = resultado.rowcount

    # Completa lacunas do sobrevivente com o que só o absorvido tinha. Os
    # identificadores oficiais são o ganho principal: é comum um cadastro ter
    # só CPF e o outro só CNS.
    herdados = [
        campo for campo in CAMPOS_HERDAVEIS
        if not getattr(sobrevivente, campo, None)
        and getattr(absorvido, campo, None)
    ]

    # `cpf` e `cns` são UNIQUE. Precisam SAIR do absorvido antes de entrarem no
    # sobrevivente — os dois não podem carregar o mesmo documento nem por um
    # instante, e o flush intermediário do SQLAlchemy expõe exatamente esse
    # instante ao banco.
    guardados = {}
    for campo in ("cpf", "cns"):
        if campo in herdados:
            guardados[campo] = getattr(absorvido, campo)
            setattr(absorvido, campo, None)
    if guardados:
        db.session.flush()

    for campo in herdados:
        valor = guardados[campo] if campo in guardados else getattr(absorvido, campo)
        setattr(sobrevivente, campo, valor)

    absorvido.ativo = False
    absorvido.unificado_para_id = sobrevivente.id
    absorvido.unificado_em = datetime.utcnow()

    # Pares pendentes que envolvem o absorvido perdem o sentido.
    CandidatoDuplicata.query.filter(
        sa.or_(CandidatoDuplicata.paciente_menor_id == absorvido.id,
               CandidatoDuplicata.paciente_maior_id == absorvido.id),
        CandidatoDuplicata.status == "pendente",
    ).update({"status": "unificado",
              "sobrevivente_id": sobrevivente.id,
              "decidido_em": datetime.utcnow(),
              "decidido_por": usuario_id},
             synchronize_session=False)

    return {"registros_movidos": movidos, "campos_herdados": herdados}


def marcar_distintos(candidato, usuario_id=None):
    """Registra que o par foi revisado e são pessoas diferentes.

    Precisa persistir: sem isso o mesmo par voltaria em toda varredura e a fila
    de revisão viraria ruído que ninguém olha.
    """
    candidato.status = "distintos"
    candidato.decidido_em = datetime.utcnow()
    candidato.decidido_por = usuario_id
    return candidato
