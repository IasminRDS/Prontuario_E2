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
    import sqlalchemy as sa

    from models.paciente import Paciente
    from models.unidade_saude import UnidadeSaude

    random.seed(semente)

    unidades = (UnidadeSaude.query.filter_by(ativo=True)
                .order_by(UnidadeSaude.id.asc()).all())
    if not unidades:
        raise RuntimeError("nenhuma unidade cadastrada; rode `flask seed` antes")

    pesos = _pesos(len(unidades))
    hoje = date.today()

    # De onde continuar a numerar os documentos.
    #
    # O CPF e o CNS eram derivados do ÍNDICE DO LAÇO, que recomeça em zero a
    # cada execução — então rodar o comando duas vezes produzia exatamente os
    # mesmos documentos e o `UNIQUE` estourava, com uma `IntegrityError` crua
    # que não dizia o que fazer. Continuar de onde parou é o comportamento que
    # o comando promete: ele existe para PÔR VOLUME, e pôr mais volume é a
    # operação natural de repeti-lo.
    ja_existem = db.session.execute(
        sa.select(sa.func.count(Paciente.id))
        .where(Paciente.nome.like(f"%[{MARCA}]%"))).scalar() or 0

    # --- pacientes
    criados = 0
    linhas = []
    for bruto in range(pacientes):
        i = ja_existem + bruto
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

    return {"pacientes": criados, "unidades": len(unidades),
            "ja_existiam": ja_existem}


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


# As quatro tabelas que a demonstração deixava VAZIAS, e o que isso custava.
#
# `gerar_clinicas` nasceu para exercitar o backfill das cinco tabelas que
# ganharam `unidade_id`, e cobre exatamente essas cinco. O resultado é um
# ambiente com vinte mil pacientes, oito mil internações — e triagem, agenda,
# exames e prontuário sem uma única linha. São quatro telas inteiras que abrem
# vazias, e prontuário é o artefato que dá nome ao sistema.
#
# Os valores clínicos aqui são plausíveis de propósito: `utils/sinais_vitais`
# recusaria o impossível na tela, e semente que gerasse o que a tela recusa
# produziria um banco que a própria aplicação não aceitaria criar.
CLASSIFICACOES = (
    # (cor, peso) — a distribuição de Manchester é uma pirâmide, não um sorteio
    # uniforme: emergência é rara e "pouco urgente" é a maioria.
    ("vermelho", 2), ("laranja", 8), ("amarelo", 25),
    ("verde", 45), ("azul", 20),
)

QUEIXAS = (
    "Dor torácica", "Febre há três dias", "Cefaleia intensa", "Dispneia",
    "Dor abdominal", "Tontura", "Vômitos", "Dor lombar", "Tosse produtiva",
    "Hipertensão descompensada",
)

CONDUTAS = (
    ("Consulta de rotina", "Paciente refere melhora dos sintomas.",
     "Bom estado geral, corado, hidratado.", "Quadro estável.",
     "Manter medicação; retorno em 30 dias."),
    ("Acompanhamento de hipertensão", "Refere cefaleia ocasional.",
     "PA aferida em consultório.", "Hipertensão em acompanhamento.",
     "Ajuste de dose; retorno em 60 dias."),
    ("Queixa respiratória", "Tosse há uma semana.",
     "Murmúrio vesicular presente, sem ruídos adventícios.",
     "Quadro viral autolimitado.", "Sintomáticos e hidratação."),
)


def _vitais_plausiveis(escolha):
    """Sinais vitais dentro do que a própria aplicação aceitaria digitar."""
    return {
        "pressao_arterial": f"{escolha(range(100, 160))}/{escolha(range(60, 100))}",
        "temperatura": round(35.8 + escolha(range(0, 30)) / 10, 1),
        "frequencia_cardiaca": escolha(range(52, 130)),
        "frequencia_respiratoria": escolha(range(12, 28)),
        "saturacao_o2": escolha(range(90, 100)),
        "glicemia": escolha(range(70, 180)),
        "peso": round(48 + escolha(range(0, 500)) / 10, 1),
        "altura": round(1.50 + escolha(range(0, 40)) / 100, 2),
    }


def gerar_ambulatorial(semente=42, lote=2_000):
    """Triagens, prontuários, agendamentos e exames — as telas que abriam vazias.

    Devolve o que foi criado. Como o resto deste módulo, tudo carrega a marca
    `SINTETICO` no texto livre, de modo que `limpar()` alcance.

    A distribuição temporal acompanha a das internações: espalhada pelos últimos
    dois anos, e não amontoada num mês. Um relatório de série histórica sobre
    dado concentrado num ponto não demonstra série histórica nenhuma.
    """
    import sqlalchemy as sa

    from models.agendamento import Agendamento
    from models.exame import ExameSolicitado, TipoExame
    from models.medico import Medico
    from models.paciente import Paciente
    from models.prontuario import Prontuario
    from models.triagem import Triagem
    from models.unidade_saude import UnidadeSaude
    from models.user import User

    random.seed(semente + 3)
    agora = datetime.utcnow()

    pacientes = db.session.execute(
        sa.select(Paciente.id).where(Paciente.nome.like(f"%[{MARCA}]%")).limit(5_000)
    ).scalars().all()
    if not pacientes:
        raise RuntimeError("gere os pacientes sintéticos primeiro")

    unidades = db.session.execute(
        sa.select(UnidadeSaude.id).where(UnidadeSaude.ativo.is_(True))).scalars().all()
    usuarios = db.session.execute(sa.select(User.id)).scalars().all()
    medicos = db.session.execute(sa.select(Medico.id)).scalars().all()
    tipos_exame = db.session.execute(sa.select(TipoExame.id)).scalars().all()

    cores = [c for c, _peso in CLASSIFICACOES]
    pesos_cor = [p for _c, p in CLASSIFICACOES]

    def _quando():
        """Instante nos últimos dois anos, como as internações já fazem."""
        return agora - timedelta(days=random.randint(0, 730),
                                 minutes=random.randint(0, 1440))

    def _inserir(modelo, linhas):
        for i in range(0, len(linhas), lote):
            db.session.execute(modelo.__table__.insert(), linhas[i:i + lote])
        db.session.commit()
        return len(linhas)

    criados = {}

    amostra = random.sample(pacientes, min(2_000, len(pacientes)))
    criados["triagens"] = _inserir(Triagem, [
        dict(
            paciente_id=p,
            unidade_id=random.choice(unidades),
            realizado_por=random.choice(usuarios) if usuarios else None,
            classificacao=random.choices(cores, weights=pesos_cor, k=1)[0],
            queixa_principal=f"{random.choice(QUEIXAS)} [{MARCA}]",
            dor_escala=random.randint(0, 10),
            status="finalizado",
            criado_em=_quando(),
            **_vitais_plausiveis(lambda faixa: random.choice(list(faixa))),
        )
        for p in amostra
    ])

    amostra = random.sample(pacientes, min(2_000, len(pacientes)))
    prontuarios = []
    for p in amostra:
        titulo, subjetivo, objetivo, avaliacao, plano = random.choice(CONDUTAS)
        instante = _quando()
        prontuarios.append(dict(
            paciente_id=p,
            unidade_id=random.choice(unidades),
            medico_id=random.choice(medicos) if medicos else None,
            subjetivo=f"{subjetivo} [{MARCA}]",
            objetivo=objetivo,
            avaliacao=f"{titulo}: {avaliacao}",
            plano=plano,
            assinado=False,
            criado_em=instante,
            atualizado_em=instante,
            **_vitais_plausiveis(lambda faixa: random.choice(list(faixa))),
        ))
    criados["prontuarios"] = _inserir(Prontuario, prontuarios)

    # A agenda olha para a FRENTE: agendamento só no passado deixa a tela do dia
    # vazia, que é o sintoma que este gerador veio corrigir.
    amostra = random.sample(pacientes, min(1_200, len(pacientes)))
    criados["agendamentos"] = _inserir(Agendamento, [
        dict(
            paciente_id=p,
            unidade_id=random.choice(unidades),
            medico_id=random.choice(medicos) if medicos else None,
            criado_por=random.choice(usuarios) if usuarios else None,
            data_hora=agora + timedelta(days=random.randint(-60, 45),
                                        hours=random.randint(8, 17)),
            tipo=random.choice(("consulta", "retorno", "exame")),
            status=random.choices(("agendado", "realizado", "cancelado"),
                                  weights=(55, 40, 5), k=1)[0],
            observacoes=f"Agendamento {MARCA}",
            criado_em=agora,
        )
        for p in amostra
    ])

    if tipos_exame:
        amostra = random.sample(pacientes, min(1_500, len(pacientes)))
        criados["exames_solicitados"] = _inserir(ExameSolicitado, [
            dict(
                paciente_id=p,
                unidade_id=random.choice(unidades),
                medico_id=random.choice(medicos) if medicos else None,
                criado_por=random.choice(usuarios) if usuarios else None,
                tipo_exame_id=random.choice(tipos_exame),
                status=random.choices(("solicitado", "coletado", "concluido"),
                                      weights=(30, 20, 50), k=1)[0],
                urgencia=random.choices(("rotina", "urgente"),
                                        weights=(85, 15), k=1)[0],
                indicacao_clinica=f"Investigação diagnóstica [{MARCA}]",
                data_solicitacao=_quando(),
            )
            for p in amostra
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
    from models.agendamento import Agendamento
    from models.exame import ExameSolicitado
    from models.prontuario import Prontuario
    from models.triagem import Triagem

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

    # As quatro últimas entraram com `gerar_ambulatorial`. Elas precisam sair
    # AQUI, e não noutro comando: limpeza que deixa resto faz a execução seguinte
    # medir um banco que ninguém sabe o tamanho — e `--limpar` existe justamente
    # para devolver o banco ao estado anterior à carga.
    #
    # `exames_solicitados` vai antes de `prontuarios` porque aponta para ele.
    for modelo, nome in ((Cirurgia, "cirurgias"),
                         (Encaminhamento, "encaminhamentos"),
                         (AtendimentoPS, "atendimentos_ps"),
                         (Prescricao, "prescricoes"),
                         (ExameSolicitado, "exames_solicitados"),
                         (Prontuario, "prontuarios"),
                         (Triagem, "triagens"),
                         (Agendamento, "agendamentos"),
                         (Internacao, "internacoes")):
        removidos[nome] = db.session.execute(
            sa.delete(modelo).where(modelo.paciente_id.in_(ids))).rowcount

    removidos["pacientes"] = db.session.execute(
        sa.delete(Paciente).where(Paciente.id.in_(ids))).rowcount
    db.session.commit()
    return removidos
