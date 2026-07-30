# -*- coding: utf-8 -*-
"""Fábrica da aplicação Flask."""
import os

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
    "routes.prontuario:prontuario_bp",
    "routes.triagem:triagem_bp",
    "routes.atendimento:atendimento_bp",
    "routes.pronto_socorro:pronto_socorro_bp",
    "routes.internacao:internacao_bp",
    "routes.leitos:leitos_bp",
    "routes.cirurgia:cirurgia_bp",
    "routes.agenda:agenda_bp",
    "routes.agendamento:agendamento_bp",
    # Apoio diagnóstico e medicação
    "routes.exames:exames_bp",
    "routes.catalogo_exames:catalogo_exames_bp",
    "routes.catalogo_vacinas:catalogo_vacinas_bp",
    "routes.medicamentos:medicamentos_bp",
    "routes.prescricao_hosp:pres_hosp_bp",
    "routes.estoque:estoque_bp",
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
        catalogo_vacina, cirurgia, configuracao, encaminhamento, estoque, exame,
        faturamento, internacao, lgpd, medicamento, medico, notificacao,
        paciente, prescricao_hospitalar, pronto_socorro, prontuario, regional,
        triagem, unidade_saude, user, vacina,
    )


def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(get_config_class())

    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    _registrar_models()

    for caminho in BLUEPRINTS:
        app.register_blueprint(_importar(caminho))

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


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
