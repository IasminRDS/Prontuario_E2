# -*- coding: utf-8 -*-
"""Navegação lateral — porte de `frontend/src/modules/shared/rbac/nav.ts`.

Orientada ao fluxo clínico e agrupada por domínio: o operador acha a função pelo
contexto, não numa lista plana.

Os grupos Dashboard, Atendimento, Vigilância e Regulação, Gestão e Conta são os
mesmos do monorepo NestJS+Next (mesmos rótulos, ícones e permissões). Assistência
hospitalar, Apoio diagnóstico, Faturamento e Administração cobrem módulos que
existem só nesta versão Flask; sem eles essas telas ficariam sem porta de entrada.

"Conta" fica no fim, e não na posição do monorepo, porque aqui há o dobro de
grupos — empurrar o que menos se acessa para baixo deixa o fluxo clínico no
topo, sem rolagem.

Um item só aparece se (a) o endpoint estiver registrado no app E (b) o usuário
tiver a permissão. A checagem (a) evita link morto quando um blueprint sai.
"""
from collections import namedtuple

Item = namedtuple("Item", "endpoint label icone descricao perms perfis")
Grupo = namedtuple("Grupo", "titulo itens")


def _i(endpoint, label, icone, descricao="", perms=(), perfis=()):
    return Item(endpoint, label, icone, descricao, tuple(perms), tuple(perfis))


GRUPOS = (
    Grupo(None, (
        _i("dashboard.index", "Dashboard", "layout-dashboard",
           "Visão operacional do dia e acesso rápido às funcionalidades."),
    )),
    Grupo("Atendimento", (
        _i("pacientes.listar_pacientes", "Pacientes", "users",
           "Cadastro, busca e Sumário do Paciente.", ["patient:read"]),
        _i("duplicatas.index", "Cadastros duplicados", "users",
           "Revisão e unificação de cadastros da mesma pessoa.",
           ["patient:update"]),
        _i("pronto_socorro.index", "Pronto-Socorro", "ambulance",
           "Fila e atendimento de urgência e emergência.", ["emergency:write"]),
        _i("triagem.index", "Triagem", "clipboard-list",
           "Sinais vitais e classificação de risco Manchester.", ["triage:write"]),
        _i("atendimento.index", "Atendimentos", "stethoscope",
           "Consultas e evolução clínica ambulatorial.", ["clinical:write"]),
        _i("prontuario.listar_prontuarios", "Prontuário", "file-text",
           "Histórico clínico longitudinal do paciente.", ["clinical:read"]),
        _i("portal_cidadao.index", "Portal do Cidadão", "id-card",
           'Cartão de vacinas e "quem acessou meu prontuário" (LGPD).', ["clinical:read"]),
        _i("medicamentos.index", "Prescrição", "pill",
           "Prescrição com catálogo nacional de medicamentos (RENAME).",
           ["prescription:create"]),
        _i("internacao.leitos", "Internação", "bed-double",
           "Leitos, internações, evoluções e altas.", ["internment:write"]),
    )),
    Grupo("Vigilância e Regulação", (
        _i("vigilancia.index", "Vigilância (SINAN)", "siren",
           "Fila de notificações compulsórias geradas por CID notificável.",
           ["surveillance:read"]),
        _i("regulacao.index", "Regulação de vagas", "arrow-left-right",
           "Fila de encaminhamentos entre unidades com parecer do regulador.",
           ["regulation:read"]),
        _i("epidemiologia.index", "Epidemiologia", "map",
           "Painel regional: agravos, leitos, regulação e Manchester.",
           ["reports:read"]),
        _i("rnds.index", "Integrações RNDS", "network",
           "Envio de registros clínicos (FHIR) à Rede Nacional de Dados em Saúde.",
           ["reports:read"]),
    )),
    Grupo("Gestão", (
        _i("relatorios.index", "Relatórios", "bar-chart-3",
           "Indicadores e relatórios gerenciais.", ["reports:read"]),
        _i("importacao.csv_form", "Importar CSV", "upload",
           "Importação de pacientes em lote (validação estrita).", ["patient:create"]),
        # A tela detalhada da importação de pacientes — a que documenta os
        # campos obrigatórios e o formato da data — existia sem entrada no
        # menu. As duas enviam para `importacao.csv_importar`; a diferença é a
        # orientação, e era justamente a orientada que ninguém alcançava.
        _i("importacao.pacientes", "Importar pacientes", "user-plus",
           "Importação de pacientes com o formato dos campos documentado.",
           ["patient:create"]),
        _i("exportacao.index", "Exportação", "download-cloud",
           "Exportação de dados e backup — auditados (LGPD).",
           perfis=["Administrador", "Recepcao", "SuperAdmin"]),
        _i("auditoria.index", "Auditoria", "shield-check",
           "Trilha de auditoria com verificação de integridade (hash-chain).",
           ["audit:read"]),
        _i("terminologia.index", "Tabelas oficiais", "table",
           "Consulta a CID-10, RENAME, CBO, SIGTAP e CNES."),
    )),
    Grupo("Assistência hospitalar", (
        _i("ps.painel", "Painel do PS", "activity",
           "Ciclo completo: chegada, chamada, observação e desfecho.",
           ["emergency:write"]),
        _i("internacao.painel", "Painel de internação", "bed-double",
           "Mapa de leitos e internações ativas.", ["internment:write"]),
        _i("cirurgia.painel", "Centro cirúrgico", "scissors",
           "Mapa cirúrgico e agendamento de procedimentos.", ["surgery:write"]),
        _i("encaminhamentos.painel", "Encaminhamentos", "arrow-left-right",
           "Solicitação de vaga em outro serviço.", ["regulation:read"]),
        _i("agenda.index", "Agenda", "calendar-days",
           "Agenda de consultas e procedimentos.", ["patient:read"]),
        _i("agendamento.index", "Agendamentos", "clipboard-check",
           "Marcação de consultas por profissional.", ["patient:read"]),
    )),
    Grupo("Apoio diagnóstico", (
        _i("exames.index", "Exames", "flask-conical",
           "Solicitação, coleta e resultado de exames.", ["exam:write"]),
        _i("exames.catalogo", "Catálogo de exames", "clipboard-check",
           "Tipos de exame e instruções de preparo.", ["exam:write"]),
        _i("vacinas.index", "Vacinas", "syringe",
           "Cartão de vacinas e registro de doses.", ["clinical:read"]),
        _i("catalogo_vacinas.index", "Catálogo de vacinas", "syringe",
           "Imunobiológicos do calendário nacional.", ["clinical:read"]),
        _i("farmacia.index", "Farmácia", "pill",
           "Dispensação e saldo de medicamentos.", ["med-admin:write", "clinical:read"]),
        _i("estoque.index", "Estoque", "package",
           "Itens, movimentações e alertas de reposição.", ["clinical:read"]),
    )),
    Grupo("Faturamento", (
        _i("faturamento.aih_lista", "AIH", "receipt",
           "Autorização de Internação Hospitalar.", ["reports:read", "admin:full"]),
        _i("faturamento.apac_lista", "APAC", "receipt",
           "Autorização de Procedimentos de Alta Complexidade.",
           ["reports:read", "admin:full"]),
        _i("rel_hosp.index", "Relatórios hospitalares", "bar-chart-3",
           "Ocupação, produção e pronto-socorro.", ["reports:read"]),
    )),
    Grupo("Administração", (
        _i("unidades.index", "Unidades de saúde", "building-2",
           "Cadastro de unidades e CNES.", ["admin:full"]),
        _i("admin.index", "Usuários", "user-cog",
           "Contas, perfis e ativação.", ["user:manage", "admin:full"]),
        _i("alertas.index", "Alertas", "bell",
           "Pendências operacionais do dia.", ["reports:read"]),
        _i("configuracoes.index", "Configurações", "settings",
           "Parâmetros do sistema.", ["admin:full"]),
        _i("backup.index", "Backup", "database",
           "Cópia de segurança do banco.", ["admin:full"]),
        _i("pdf.ferramentas", "Ferramentas PDF", "files",
           "Compactar, proteger e reorganizar documentos.", ["clinical:read"]),
        # A tela existia e não estava no menu: os documentos emitidos, com o
        # código e a impressão digital que `/verificar/<código>` confere, só
        # eram alcançáveis por URL digitada à mão.
        _i("documentos.listar", "Documentos emitidos", "file-check",
           "Documentos assinados, com código de verificação pública.",
           ["clinical:read"]),
    )),
    # Fica por último de propósito: é o que menos se acessa no dia a dia.
    Grupo("Conta", (
        _i("conta.index", "Minha conta", "user-cog",
           "Identificação e verificação em duas etapas (MFA)."),
        _i("sobre.index", "Sobre o sistema", "info",
           "Versão, recursos e conformidade do SNPE."),
    )),
)


def grupos_visiveis(endpoints_disponiveis, pode_fn, perfil=None):
    """Filtra os grupos pelo RBAC e pelos endpoints realmente registrados.

    `endpoints_disponiveis` é o conjunto de `app.view_functions`; `pode_fn` é o
    `pode()` de utils.rbac. Grupo sem item visível desaparece inteiro.
    """
    from utils.rbac import _normalizar

    perfil_atual = _normalizar(perfil)
    saida = []

    for grupo in GRUPOS:
        visiveis = []
        for item in grupo.itens:
            if item.endpoint not in endpoints_disponiveis:
                continue
            if item.perfis:
                if perfil_atual != "SuperAdmin" and perfil_atual not in {
                    _normalizar(p) for p in item.perfis
                }:
                    continue
            elif item.perms and not pode_fn(*item.perms):
                continue
            elif not item.perms and not pode_fn():
                continue
            visiveis.append(item)
        if visiveis:
            saida.append(Grupo(grupo.titulo, tuple(visiveis)))

    return saida
