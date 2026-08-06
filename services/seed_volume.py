# -*- coding: utf-8 -*-
"""Gera volume sintético para medir o sistema sob carga.

O banco de desenvolvimento tem dezenas de linhas. Com esse volume, qualquer
consulta responde rápido e nenhuma decisão de índice ou paginação pode ser
tomada com base em evidência — o planejador do PostgreSQL sequer considera
índice em tabela pequena, porque varrer tudo é mais barato.

Este módulo existe para tornar a medição possível. Ele NÃO é seed de
demonstração: os dados são deliberadamente sintéticos e reconhecíveis
(`SINTETICO`), para nunca serem confundidos com registro clínico real.

**Distribuição realista importa mais que volume.** Distribuir pacientes
uniformemente entre unidades produziria seletividade artificialmente boa. O
mundo real é desbalanceado: uma capital concentra a maior parte do movimento.
Por isso a distribuição segue proporção decrescente entre as unidades — é ela
que revela se o índice ajuda no caso ruim, que é o da unidade grande.
"""
import random
from datetime import date, datetime, timedelta

from extensions import db

MARCA = "SINTETICO"

_NOMES = ("Ana", "Bruno", "Carla", "Diego", "Elisa", "Fabio", "Gisele",
          "Heitor", "Iara", "Joao", "Karla", "Lucas", "Marina", "Nelson",
          "Olivia", "Paulo", "Rita", "Sergio", "Tais", "Vitor")
_SOBRENOMES = ("Silva", "Souza", "Costa", "Santos", "Oliveira", "Pereira",
               "Lima", "Carvalho", "Rocha", "Almeida", "Barbosa", "Ribeiro")


def _pesos(n):
    """Proporção decrescente: a primeira unidade concentra o movimento."""
    brutos = [1 / (i + 1) for i in range(n)]
    total = sum(brutos)
    return [b / total for b in brutos]


def gerar(pacientes=50_000, semente=42, lote=2_000):
    """Cria pacientes e internações sintéticas. Devolve o que foi criado.

    Usa inserção em lote pelo core do SQLAlchemy, e não objetos do ORM: com
    50 mil linhas, o custo de materializar entidades domina o tempo e a medição
    passaria a medir o ORM em vez do banco.
    """
    from models.paciente import Paciente
    from models.unidade_saude import UnidadeSaude

    random.seed(semente)

    unidades = (UnidadeSaude.query.filter_by(ativo=True)
                .order_by(UnidadeSaude.id.asc()).all())
    if not unidades:
        raise RuntimeError("nenhuma unidade cadastrada; rode `flask seed` antes")

    pesos = _pesos(len(unidades))
    hoje = date.today()

    # --- pacientes
    criados = 0
    linhas = []
    for i in range(pacientes):
        nome = (f"{random.choice(_NOMES)} {random.choice(_SOBRENOMES)} "
                f"{random.choice(_SOBRENOMES)}")
        unidade = random.choices(unidades, weights=pesos, k=1)[0]
        linhas.append({
            "nome": f"{nome} [{MARCA}]",
            "data_nascimento": hoje - timedelta(days=random.randint(1, 36500)),
            "sexo": random.choice(("M", "F")),
            # Documento derivado do índice: único e reconhecível como sintético.
            "cpf": f"{90_000_000_000 + i:011d}",
            "cns": f"{800_000_000_000_000 + i:015d}",
            "municipio": unidade.cidade,
            "uf": unidade.uf,
            "ativo": True,
            "criado_em": datetime.utcnow(),
        })
        if len(linhas) >= lote:
            db.session.execute(Paciente.__table__.insert(), linhas)
            db.session.commit()
            criados += len(linhas)
            linhas = []
    if linhas:
        db.session.execute(Paciente.__table__.insert(), linhas)
        db.session.commit()
        criados += len(linhas)

    return {"pacientes": criados, "unidades": len(unidades)}


def gerar_internacoes(por_paciente=0.4, semente=42, lote=2_000):
    """Internações sintéticas distribuídas entre as unidades.

    É a tabela em que o efeito do RLS mais aparece: toda consulta clínica passa
    por ela e ela carrega `unidade_id`.
    """
    import sqlalchemy as sa

    from models.internacao import Internacao, Leito
    from models.paciente import Paciente

    random.seed(semente + 1)

    ids_pacientes = db.session.execute(
        sa.select(Paciente.id).where(Paciente.nome.like(f"%[{MARCA}]%"))
    ).scalars().all()
    if not ids_pacientes:
        raise RuntimeError("gere os pacientes sintéticos primeiro")

    leitos = db.session.execute(
        sa.select(Leito.id, Leito.unidade_id)).all()
    if not leitos:
        raise RuntimeError("nenhum leito cadastrado; rode `flask seed` antes")

    agora = datetime.utcnow()
    criadas, linhas = 0, []
    for pid in ids_pacientes:
        if random.random() > por_paciente:
            continue
        leito_id, unidade_id = random.choice(leitos)
        entrada = agora - timedelta(days=random.randint(0, 730))
        linhas.append({
            "paciente_id": pid,
            "leito_id": leito_id,
            "unidade_id": unidade_id,
            "status": random.choice(("ativa", "alta", "alta", "alta")),
            "data_entrada": entrada,
            "motivo": f"Motivo {MARCA}",
        })
        if len(linhas) >= lote:
            db.session.execute(Internacao.__table__.insert(), linhas)
            db.session.commit()
            criadas += len(linhas)
            linhas = []
    if linhas:
        db.session.execute(Internacao.__table__.insert(), linhas)
        db.session.commit()
        criadas += len(linhas)

    return {"internacoes": criadas}


def gerar_clinicas(semente=42, lote=2_000):
    """Popula as cinco tabelas que ganharam `unidade_id` na migration b7f4c2e91a08.

    Existe para uma finalidade específica: **exercitar o backfill**. Enquanto
    essas tabelas estiverem vazias, "zero órfãos" não prova nada, e aplicar
    `NOT NULL` sobre elas seria declarar estável o que nunca foi testado.

    As linhas nasciam sem `unidade_id` enquanto a coluna aceitava nulo, para
    reproduzir o estado anterior à migration. Depois que d5e8a71c3f60 tornou a
    coluna obrigatória, esse estado deixou de ser representável — o backfill já
    foi exercitado e aprovado, e a finalidade aqui passou a ser só o volume.
    """
    import sqlalchemy as sa

    from models.cirurgia import Cirurgia
    from models.encaminhamento import Encaminhamento
    from models.internacao import EvolucaoInternacao, Internacao
    from models.medicamento import ItemPrescricao, Prescricao
    from models.paciente import Paciente
    from models.pronto_socorro import AtendimentoPS
    from models.unidade_saude import UnidadeSaude
    from models.user import User

    random.seed(semente + 2)
    agora = datetime.utcnow()

    pacientes = db.session.execute(
        sa.select(Paciente.id).where(Paciente.nome.like(f"%[{MARCA}]%")).limit(5_000)
    ).scalars().all()
    if not pacientes:
        raise RuntimeError("gere os pacientes sintéticos primeiro")

    internacoes = db.session.execute(
        sa.select(Internacao.id, Internacao.paciente_id).limit(5_000)).all()
    unidades = db.session.execute(sa.select(UnidadeSaude.id)).scalars().all()
    usuarios = db.session.execute(sa.select(User.id)).scalars().all()

    def _inserir(modelo, linhas):
        for i in range(0, len(linhas), lote):
            db.session.execute(modelo.__table__.insert(), linhas[i:i + lote])
        db.session.commit()
        return len(linhas)

    criados = {}

    # cirurgias: resolve por internacao_id, senão pelo criador
    criados["cirurgias"] = _inserir(Cirurgia, [
        {"paciente_id": p, "descricao": f"Procedimento {MARCA}",
         "status": "agendada", "data_agendada": agora,
         "internacao_id": random.choice(internacoes)[0] if internacoes and random.random() < 0.6 else None,
         "criado_por": random.choice(usuarios) if usuarios else None,
         "unidade_id": random.choice(unidades)}
        for p in random.sample(pacientes, min(1_500, len(pacientes)))
    ])

    # encaminhamentos: resolve por unidade_origem_id, que é NOT NULL
    criados["encaminhamentos"] = _inserir(Encaminhamento, [
        {"paciente_id": p, "unidade_origem_id": random.choice(unidades),
         "especialidade": "Cardiologia", "motivo": f"Motivo {MARCA}",
         "status": "solicitado", "data_solicitacao": agora,
         "unidade_id": random.choice(unidades)}
        for p in random.sample(pacientes, min(1_500, len(pacientes)))
    ])

    # atendimentos_ps: resolve pela triagem, senão pelo criador
    criados["atendimentos_ps"] = _inserir(AtendimentoPS, [
        {"paciente_id": p, "motivo_consulta": f"Queixa {MARCA}",
         "status": "em_espera", "data_chegada": agora,
         "criado_por": random.choice(usuarios) if usuarios else None,
         "unidade_id": random.choice(unidades)}
        for p in random.sample(pacientes, min(1_500, len(pacientes)))
    ])

    # evolucoes: resolve pela internação
    criados["evolucoes_internacao"] = _inserir(EvolucaoInternacao, [
        {"internacao_id": i, "tipo": "medica", "subjetivo": f"Evolucao {MARCA}",
         "unidade_id": random.choice(unidades)}
        for i, _p in random.sample(internacoes, min(2_000, len(internacoes)))
    ]) if internacoes else 0

    # prescrições e itens: o item resolve pela prescrição
    linhas_presc = [{"paciente_id": p, "tipo": "ambulatorial", "status": "ativa",
                     "unidade_id": random.choice(unidades)}
                    for p in random.sample(pacientes, min(1_500, len(pacientes)))]
    _inserir(Prescricao, linhas_presc)
    ids_presc = db.session.execute(
        sa.select(Prescricao.id).order_by(Prescricao.id.desc())
        .limit(len(linhas_presc))).scalars().all()
    criados["itens_prescricao"] = _inserir(ItemPrescricao, [
        {"prescricao_id": pid, "nome_livre": f"Medicamento {MARCA}",
         "dose": "500 mg", "via": "Oral",
         "unidade_id": random.choice(unidades)}
        for pid in ids_presc for _ in range(random.randint(1, 3))
    ])

    return criados


def limpar():
    """Remove tudo que carrega a marca. Ordem: filhas antes das mães."""
    import sqlalchemy as sa

    from models.cirurgia import Cirurgia
    from models.encaminhamento import Encaminhamento
    from models.internacao import EvolucaoInternacao, Internacao
    from models.medicamento import ItemPrescricao, Prescricao
    from models.paciente import Paciente
    from models.pronto_socorro import AtendimentoPS

    ids = db.session.execute(
        sa.select(Paciente.id).where(Paciente.nome.like(f"%[{MARCA}]%"))
    ).scalars().all()
    if not ids:
        return {}

    removidos = {}
    internacoes = db.session.execute(
        sa.select(Internacao.id).where(Internacao.paciente_id.in_(ids))
    ).scalars().all()
    prescricoes = db.session.execute(
        sa.select(Prescricao.id).where(Prescricao.paciente_id.in_(ids))
    ).scalars().all()

    # Netas antes das filhas, filhas antes das mães: a FK não perdoa ordem.
    if prescricoes:
        removidos["itens_prescricao"] = db.session.execute(sa.delete(ItemPrescricao)
            .where(ItemPrescricao.prescricao_id.in_(prescricoes))).rowcount
    if internacoes:
        removidos["evolucoes_internacao"] = db.session.execute(
            sa.delete(EvolucaoInternacao)
            .where(EvolucaoInternacao.internacao_id.in_(internacoes))).rowcount

    for modelo, nome in ((Cirurgia, "cirurgias"),
                         (Encaminhamento, "encaminhamentos"),
                         (AtendimentoPS, "atendimentos_ps"),
                         (Prescricao, "prescricoes"),
                         (Internacao, "internacoes")):
        removidos[nome] = db.session.execute(
            sa.delete(modelo).where(modelo.paciente_id.in_(ids))).rowcount

    removidos["pacientes"] = db.session.execute(
        sa.delete(Paciente).where(Paciente.id.in_(ids))).rowcount
    db.session.commit()
    return removidos
