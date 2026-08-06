# -*- coding: utf-8 -*-
"""Fábrica da aplicação Flask."""
import os

import click
from dotenv import load_dotenv
from flask import Flask, render_template

load_dotenv()

from config import get_config_class  # noqa: E402
from extensions import csrf, db, login_manager, migrate  # noqa: E402

# Blueprints, na ordem de registro. Formato "modulo:atributo".
#
# A ordem importa em dois casos: `dashboard` responde por "/" e precisa vir antes
# de qualquer outro blueprint com regra em "/"; `internacao` precisa vir antes de
# `leitos`, que só redireciona para `internacao.leitos`.
BLUEPRINTS = (
    "routes.auth:auth_bp",
    "routes.dashboard:dashboard_bp",
    # Assistencial
    "routes.pacientes:pacientes_bp",
    "routes.duplicatas:duplicatas_bp",
    "routes.prontuario:prontuario_bp",
    "routes.triagem:triagem_bp",
    "routes.atendimento:atendimento_bp",
    "routes.pronto_socorro:pronto_socorro_bp",
    "routes.ps:ps_bp",
    "routes.internacao:internacao_bp",
    "routes.leitos:leitos_bp",
    "routes.cirurgia:cirurgia_bp",
    "routes.agenda:agenda_bp",
    "routes.agendamento:agendamento_bp",
    "routes.encaminhamentos:encaminhamentos_bp",
    # Apoio diagnóstico e medicação
    "routes.exames:exames_bp",
    "routes.catalogo_exames:catalogo_exames_bp",
    "routes.catalogo_vacinas:catalogo_vacinas_bp",
    "routes.vacinas:vacinas_bp",
    "routes.medicamentos:medicamentos_bp",
    "routes.prescricao_hosp:pres_hosp_bp",
    "routes.estoque:estoque_bp",
    "routes.farmacia:farmacia_bp",
    "routes.faturamento:faturamento_bp",
    # Vigilância, regulação e interoperabilidade
    "routes.vigilancia:vigilancia_bp",
    "routes.regulacao:regulacao_bp",
    "routes.epidemiologia:epidemiologia_bp",
    "routes.rnds:rnds_bp",
    "routes.terminologia:terminologia_bp",
    # Cidadão e conformidade
    "routes.portal_cidadao:portal_cidadao_bp",
    "routes.documentos:documentos_bp",
    # Gestão e plataforma
    "routes.relatorios:relatorios_bp",
    "routes.relatorios_hosp:rel_hosp_bp",
    "routes.unidades:unidades_bp",
    "routes.admin:admin_bp",
    "routes.auditoria:auditoria_bp",
    "routes.alertas:alertas_bp",
    "routes.configuracoes:configuracoes_bp",
    "routes.importacao:importacao_bp",
    "routes.exportacao:exportacao_bp",
    "routes.backup:backup_bp",
    "routes.pdf:pdf_bp",
    # Conta do usuário
    "routes.conta:conta_bp",
    "routes.sobre:sobre_bp",
)


def _importar(caminho):
    modulo, _, atributo = caminho.partition(":")
    mod = __import__(modulo, fromlist=[atributo])
    try:
        return getattr(mod, atributo)
    except AttributeError as exc:
        raise RuntimeError(f"{modulo} não define {atributo}") from exc


def _registrar_models():
    """Importa todos os models para que o metadata do SQLAlchemy os conheça.

    Sem isso o autogenerate do Alembic não enxerga as tabelas.
    """
    from models import (  # noqa: F401
        agenda_evento, agendamento, atendimento, audit_log, catalogo_exame,
        catalogo_vacina, cirurgia, configuracao, duplicata, encaminhamento,
        estoque, exame, faturamento, internacao, lgpd, medicamento, medico,
        municipio, notificacao, paciente, prescricao_hospitalar,
        pronto_socorro, prontuario, regional, triagem, unidade_saude, user,
        vacina,
    )


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(get_config_class())

    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # O escopo territorial precisa acompanhar TODA transação, inclusive as que
    # começam depois de um commit no meio da requisição. Registrar aqui, e não
    # num before_request, é o que garante isso.
    from utils.rls import registrar as registrar_rls
    registrar_rls(db, app)

    _registrar_models()

    for caminho in BLUEPRINTS:
        app.register_blueprint(_importar(caminho))

    from utils.seguranca_http import registrar_cabecalhos
    registrar_cabecalhos(app)

    _registrar_context(app)
    _registrar_handlers(app)
    _registrar_cli(app)

    return app


APP_VERSAO = "v2.0.0-flask"


def _registrar_context(app):
    """Injeta no Jinja o que todo template precisa."""
    from flask_login import current_user

    from models.configuracao import PADROES, Configuracao
    from utils.nav import grupos_visiveis
    from utils.rbac import pode

    @app.context_processor
    def injetar():
        endpoints = set(app.view_functions.keys())
        return {
            # Conjunto de endpoints REGISTRADOS. O base.html usa isso para só
            # renderizar item de menu cuja rota existe de fato. Sem este
            # context_processor a sidebar renderiza VAZIA.
            "available_endpoints": endpoints,
            # Espelho do RBAC no template: {% if pode('patient:create') %}
            "pode": pode,
            "app_versao": APP_VERSAO,
            # Navegação já filtrada por RBAC + endpoints existentes.
            "nav_grupos": (
                grupos_visiveis(endpoints, pode, getattr(current_user, "perfil", None))
                if getattr(current_user, "is_authenticated", False)
                else []
            ),
        }

    @app.context_processor
    def injetar_config():
        # Antes da primeira migration a tabela não existe, e a tela de erro não
        # pode depender dela.
        try:
            return {"cfg": Configuracao.todas()}
        except Exception:
            return {"cfg": dict(PADROES)}


def _registrar_handlers(app):
    @app.url_build_error_handlers.append
    def _endpoint_ausente(erro, endpoint, valores):
        """Degrada url_for() para link morto quando o endpoint não existe.

        Há telas herdadas que apontam para rotas nunca implementadas (o módulo
        tem o template, mas não a view). Sem isto, UMA referência quebrada
        derruba a página inteira com 500 e o restante da tela — que funciona —
        fica inacessível.

        O aviso no log é intencional: o link morto precisa aparecer para ser
        corrigido, não ser varrido para debaixo do tapete.
        """
        app.logger.warning(
            "url_for('%s') falhou: endpoint não registrado. Link renderizado como '#'.",
            endpoint,
        )
        return "#"

    @app.errorhandler(401)
    def nao_autenticado(_e):
        return render_template("errors/403.html", codigo=401,
                               mensagem="Faça login para continuar."), 401

    @app.errorhandler(403)
    def sem_permissao(_e):
        return render_template("errors/403.html", codigo=403,
                               mensagem="Seu perfil não tem permissão para esta ação."), 403

    @app.errorhandler(429)
    def excesso_de_tentativas(e):
        return render_template("errors/403.html", codigo=429,
                               mensagem=getattr(e, "description",
                                                "Muitas tentativas. Aguarde e tente de novo.")), 429

    @app.errorhandler(413)
    def arquivo_grande(_e):
        return render_template("errors/403.html", codigo=413,
                               mensagem="Arquivo maior que o limite permitido."), 413

    @app.errorhandler(404)
    def nao_encontrado(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def erro_interno(_e):
        db.session.rollback()
        return render_template("errors/500.html"), 500


def _registrar_cli(app):
    @app.cli.command("seed")
    def seed():
        """Popula catálogos e usuários de demonstração (idempotente)."""
        from database.seeds import seed_data

        seed_data()
        print("Seed concluído.")

    @app.cli.command("rnds-processar")
    @click.option("--limite", default=50, show_default=True,
                  help="Máximo de envios por execução.")
    def rnds_processar(limite):
        """Drena a fila de envios à RNDS.

        Feito para rodar em cron (a cada poucos minutos). É seguro rodar em
        paralelo: em PostgreSQL o lote é travado com SKIP LOCKED, então dois
        processos pegam envios diferentes em vez do mesmo.
        """
        from services import rnds_cliente, rnds_fila

        if not rnds_cliente.esta_configurado():
            print("AVISO: RNDS sem certificado configurado — usando cliente "
                  "simulado. Defina RNDS_AUTH_URL, RNDS_EHR_URL e "
                  "RNDS_CERTIFICADO para enviar de verdade.")

        resumo = rnds_fila.processar(limite=limite)
        print(f"enviados={resumo['enviados']} adiados={resumo['adiados']} "
              f"recusados={resumo['recusados']}")

    @app.cli.command("criar-admin")
    @click.option("--nome", prompt="Nome", help="Nome do administrador.")
    @click.option("--email", prompt="E-mail", help="E-mail de acesso.")
    @click.option("--unidade-id", type=int, default=None,
                  help="Unidade do administrador. Sem isto, usa a primeira.")
    @click.option("--perfil", default="admin", show_default=True,
                  help="Use SuperAdmin para acesso que atravessa unidades.")
    @click.password_option("--senha", prompt="Senha",
                           help="Mínimo de 8 caracteres.")
    def criar_admin(nome, email, unidade_id, perfil, senha):
        """Cria um administrador — necessário numa instalação nova.

        A senha é pedida pelo terminal, com confirmação, e não aparece no
        histórico do shell nem na lista de processos, como aconteceria se
        viesse por argumento.
        """
        from database.administrador import ErroBootstrap, criar_administrador

        try:
            usuario = criar_administrador(nome, email, senha,
                                          unidade_id=unidade_id, perfil=perfil)
        except ErroBootstrap as erro:
            raise click.ClickException(str(erro))

        db.session.commit()
        print(f"Administrador criado: {usuario.email} "
              f"(perfil {usuario.perfil}, unidade {usuario.unidade_id})")

    @app.cli.command("municipios-importar")
    @click.argument("caminho", type=click.Path(exists=True, dir_okay=False))
    def municipios_importar(caminho):
        """Carrega a relação de municípios do IBGE a partir de um CSV.

        Colunas obrigatórias: codigo_ibge, nome, uf. A UF é conferida contra os
        dois primeiros dígitos do código — linha divergente é recusada em vez de
        contaminar a tabela territorial.
        """
        from database.municipios import importar_csv

        gravados, erros = importar_csv(caminho)
        print(f"municípios gravados: {gravados}")
        for problema in erros[:20]:
            print(f"  RECUSADO: {problema}")
        if len(erros) > 20:
            print(f"  ... e mais {len(erros) - 20} linha(s) recusada(s)")

    @app.cli.command("pacientes-deduplicar")
    def pacientes_deduplicar():
        """Procura cadastros duplicados e enfileira para revisão humana.

        Não unifica nada: unificar dois pacientes errados mistura o histórico
        clínico de duas pessoas. A decisão fica na tela de revisão.
        """
        from services import deduplicacao

        analisados, novos = deduplicacao.varrer()
        print(f"pares analisados={analisados} novos candidatos={novos}")

    @app.cli.command("hardening-check")
    def hardening_check():
        """Confere no BANCO os controles que a aplicação não consegue garantir.

        A aplicação garante o que está no seu código. Não garante que o DBA
        ligou FORCE, que o papel não tem BYPASSRLS, que a trilha de auditoria
        não pertence a quem ela audita, nem que ninguém deixou um escopo
        pré-definido no ambiente. Esta é a lista dessas coisas — e o comando sai
        com código 1 se alguma falhar, para entrar em verificação periódica.
        """
        import sys

        from services.hardening import verificar

        achados = verificar()
        falhas = [a for a in achados if not a.ok]

        for a in achados:
            print(f"  {'OK  ' if a.ok else 'FALHA'} {a.nome}")
            if not a.ok:
                print(f"        {a.detalhe}")
                if a.correcao:
                    print(f"        corrigir: {a.correcao}")

        if falhas:
            print(f"\nRESULTADO: {len(falhas)} verificação(ões) falharam")
            sys.exit(1)
        print(f"\nRESULTADO: {len(achados)} verificações passaram")

    @app.cli.command("seed-volume")
    @click.option("--pacientes", default=50_000, show_default=True)
    @click.option("--limpar", is_flag=True, help="Remove os dados sintéticos.")
    def seed_volume(pacientes, limpar):
        """Gera volume sintético para medir o sistema sob carga.

        NÃO use em produção: os registros são marcados como SINTETICO e existem
        para tornar possível medir plano de consulta e efeito de índice, o que
        não se faz com dezenas de linhas — o planejador nem considera índice em
        tabela pequena.
        """
        from services import seed_volume as sv

        if limpar:
            print(f"removidos: {sv.limpar()}")
            return

        print(f"gerando {pacientes} pacientes sintéticos...")
        print(f"  {sv.gerar(pacientes=pacientes)}")
        print("gerando internações...")
        print(f"  {sv.gerar_internacoes()}")
        print("pronto. Rode `flask medir-consultas` para os planos.")

    @app.cli.command("backup-validar")
    @click.argument("caminho", type=click.Path(exists=True, dir_okay=False))
    @click.option("--apenas-restore", is_flag=True,
                  help="Só verifica se restaura; não compara com o banco atual.")
    def backup_validar(caminho, apenas_restore):
        """Restaura um backup num schema temporário e confere as contagens.

        Backup que nunca foi restaurado é um arquivo, não um backup. Feito para
        rodar em cron logo depois da rotina de backup: sai com código 1 quando
        diverge, então o agendador acusa sozinho.

        A comparação é contra o banco COMO ESTÁ AGORA, o que só faz sentido para
        um backup recém-tirado. Para conferir um arquivo antigo — cujo conteúdo
        legitimamente difere do banco de hoje — use `--apenas-restore`, que
        verifica se ele aplica sem erro e ignora as contagens.

        O schema temporário é destruído no fim, mesmo se a validação falhar.
        """
        import sys

        from services.backup_validacao import BackupInvalido, validar

        try:
            comparacoes, erros = validar(caminho)
        except BackupInvalido as e:
            print(f"BACKUP INVÁLIDO: {e}")
            sys.exit(1)

        if apenas_restore:
            for tabela, _origem, restaurado in comparacoes:
                print(f"  restaurado {tabela:22} {restaurado} linha(s)")
            if erros:
                print(f"\nerros durante o restore: {len(erros)}")
                for linha in erros[:10]:
                    print(f"   {linha[:160]}")
                print("\nRESULTADO: NÃO RESTAURA")
                sys.exit(1)
            print(f"\nRESULTADO: restaura sem erro "
                  f"({len(comparacoes)} tabelas conferidas; contagens não comparadas)")
            return

        divergentes = [(t, a, b) for t, a, b in comparacoes if a != b]

        for tabela, origem, restaurado in comparacoes:
            marca = "ok " if origem == restaurado else "DIVERGE"
            print(f"  {marca:8} {tabela:22} origem={origem} restaurado={restaurado}")

        if erros:
            print(f"\nerros durante o restore: {len(erros)}")
            for linha in erros[:10]:
                print(f"   {linha[:160]}")

        if divergentes or erros:
            print("\nRESULTADO: BACKUP NÃO CONFIÁVEL")
            sys.exit(1)

        print(f"\nRESULTADO: íntegro ({len(comparacoes)} tabelas conferidas)")


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
