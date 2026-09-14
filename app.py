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
    "routes.consentimentos:consentimentos_bp",
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
    from utils.sinais_vitais import atributos as limites_vitais

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
            # Os limites dos sinais vitais vindos da MESMA tabela que o
            # servidor consulta. Escritos à mão no HTML, os dois valores
            # divergiriam na primeira revisão de limite — e a metade
            # desatualizada seria a do formulário, que nenhum teste lê.
            "limites_vitais": limites_vitais,
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

        Colunas opcionais: populacao e populacao_ano. São o denominador dos
        indicadores — sem elas os relatórios contam, com elas calculam taxa por
        cem mil habitantes. Arquivo sem a coluna não apaga a população já
        carregada.
        """
        from database.municipios import importar_csv

        gravados, erros = importar_csv(caminho)
        print(f"municípios gravados: {gravados}")
        for problema in erros[:20]:
            print(f"  RECUSADO: {problema}")
        if len(erros) > 20:
            print(f"  ... e mais {len(erros) - 20} linha(s) recusada(s)")

    @app.cli.command("municipios-ibge")
    @click.option("--ano", type=int, default=2024, show_default=True,
                  help="Ano de referência dos eventos vitais.")
    @click.option("--populacao/--sem-populacao", default=True,
                  show_default=True, help="Atualiza também o denominador.")
    def municipios_ibge(ano, populacao):
        """Busca no IBGE os eventos vitais e a população dos municípios.

        Fonte: API de agregados do IBGE — tabelas 2609 (nascidos vivos), 2654
        (óbitos) e 6579 (população estimada). **Não é o DATASUS:** os eventos
        vêm do Registro Civil, e o SIM/SINASC conta os mesmos fatos por outra
        via, com totais que não coincidem.

        Roda sob demanda, nunca durante uma requisição: relatório que depende
        de API externa para renderizar quebra quando a rede da unidade cai.
        """
        from models.municipio import Municipio
        from services import ibge

        codigos = [c for (c,) in db.session.query(Municipio.codigo_ibge).all()]
        if not codigos:
            raise click.ClickException(
                "nenhum município cadastrado; rode `flask seed` antes")
        print(f"consultando o IBGE para {len(codigos)} município(s)...")

        try:
            vitais = ibge.eventos_vitais(codigos, ano)
            habitantes = ibge.populacao(codigos) if populacao else {}
        except ibge.ErroIBGE as erro:
            raise click.ClickException(str(erro))

        atualizados = 0
        for codigo in codigos:
            municipio = db.session.get(Municipio, codigo)
            dado = vitais.get(codigo)
            if dado:
                municipio.nascidos_vivos = dado["nascidos"]
                municipio.obitos = dado["obitos"]
                municipio.vitais_ano = ano
                municipio.vitais_fonte = "IBGE/Registro Civil"
                atualizados += 1
            if codigo in habitantes:
                municipio.populacao, municipio.populacao_ano = habitantes[codigo]
        db.session.commit()

        print(f"eventos vitais de {ano}: {atualizados} município(s)")
        if populacao:
            print(f"população: {len(habitantes)} município(s)")
        sem = len(codigos) - atualizados
        if sem:
            print(f"sem dado no IBGE para {ano}: {sem} — ficam como '—' na tela, "
                  "que é diferente de zero")

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
        # `ok is None` é "não verificável aqui", e NÃO conta como falha. Uma
        # verificação que reprova para sempre nesta máquina ensina quem a lê a
        # ignorar o comando inteiro — e aí o portão deixa de significar alguma
        # coisa exatamente antes de precisar significar.
        falhas = [a for a in achados if a.ok is False]
        indefinidos = [a for a in achados if a.ok is None]

        rotulos = {True: "OK   ", False: "FALHA", None: "?    "}
        for a in achados:
            print(f"  {rotulos[a.ok]} {a.nome}")
            if a.ok is not True:
                print(f"        {a.detalhe}")
                if a.correcao:
                    print(f"        corrigir: {a.correcao}")

        if falhas:
            print(f"\nRESULTADO: {len(falhas)} verificação(ões) falharam")
            sys.exit(1)
        print(f"\nRESULTADO: {len(achados) - len(indefinidos)} "
              "verificações passaram")
        if indefinidos:
            print(f"{len(indefinidos)} não pôde(puderam) ser verificada(s) "
                  "neste ambiente — ausência de reprovação não é aprovação.")

    @app.cli.command("auditoria-ancora")
    @click.option("--conferir", is_flag=True,
                  help="Confere o journal e a última âncora contra a trilha.")
    @click.option("--arquivo", default="backups/ancora_auditoria.jsonl",
                  help="Journal de âncoras. Uma linha por emissão, só acréscimo.")
    @click.option("--contra", default=None, metavar="TOTAL:ULTIMO_ID:HASH",
                  help="Confere contra valores informados, sem ler arquivo "
                       "algum desta máquina.")
    @click.option("--retida", default=None, metavar="HASH_ANCORA",
                  help="Hash de uma âncora guardada fora. Valida todo o "
                       "prefixo do journal até ela.")
    @click.option("--idade-maxima", type=int, default=None, metavar="DIAS",
                  help="Falha se a âncora mais recente for mais velha que "
                       "isto. Verificador que parou não acusa nada.")
    @click.option("--destino", type=click.Choice(["arquivo", "stdout"]),
                  default="arquivo", show_default=True,
                  help="'stdout' imprime só a linha, para canalizar a um "
                       "coletor externo.")
    def auditoria_ancora(conferir, arquivo, contra, retida, idade_maxima,
                         destino):
        """Emite ou confere a âncora da trilha de auditoria.

        O encadeamento por hash detecta alteração e remoção NO MEIO da cadeia.
        Não detecta truncamento do FIM: apagados os últimos eventos, os elos que
        sobram continuam consistentes e nada indica que a trilha já foi maior —
        e é o fim que interessa a quem quer ocultar o que acabou de fazer.

        As âncoras são gravadas num journal **encadeado e só de acréscimo**:
        cada linha referencia o hash da anterior. Isso não fecha o truncamento
        do fim do próprio journal — é a mesma recursão, e só custódia externa a
        fecha. O que fecha é o custo dessa custódia: guardada UMA linha qualquer
        fora do servidor, `--retida HASH` valida todo o prefixo até ela. A
        obrigação deixa de ser "guarde sempre a última" e passa a ser "guarde
        qualquer uma, uma vez".

        E o journal testemunha contra si mesmo sem depender de nada externo:
        `--conferir` compara âncoras CONSECUTIVAS e acusa a trilha que encolheu
        entre dois checkpoints, ainda que hoje esteja internamente consistente.

        `--destino stdout` imprime só a linha JSON, para canalizar a um coletor
        que a aplicação não controle — que é a única forma de a regra "quem
        escreve o log não guarda a âncora" ser verdade.
        """
        import json
        import pathlib
        import sys
        from datetime import datetime, timedelta

        from utils import ancora as ancora_mod
        from utils.audit import ancora_da_trilha, conferir_ancora

        caminho = pathlib.Path(arquivo)

        def _sair_com(problemas, titulo):
            print(titulo)
            for p in problemas:
                print(f"  {p}")
            # Uma linha estruturada em stderr, para que a falha apareça FORA
            # deste processo sem que ninguém precise ler a saída humana. Não vai
            # para a trilha de auditoria de propósito: registrar na trilha o
            # alerta de que a trilha foi adulterada é circular — quem apagou o
            # fim apaga o alerta junto.
            print(json.dumps({
                "evento": "ancora_verificacao_falhou",
                "em": datetime.utcnow().isoformat(timespec="seconds"),
                "journal": str(caminho),
                "problemas": problemas,
            }, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)

        if contra:
            try:
                total_txt, ultimo_txt, hash_esperado = contra.split(":", 2)
                esperados = (int(total_txt), int(ultimo_txt), hash_esperado.strip())
            except ValueError:
                sys.exit("--contra espera TOTAL:ULTIMO_ID:HASH")
            problemas = conferir_ancora(*esperados)
            if problemas:
                _sair_com(problemas, "ÂNCORA INFORMADA NÃO CONFERE:")
            print(f"trilha íntegra contra o valor informado: "
                  f"{esperados[0]} registros preservados")
            return

        linhas, defeitos = ancora_mod.ler(caminho)

        if conferir or retida:
            if not linhas:
                # Defeito de formato precisa vir ANTES do "vazio": journal
                # ilegível e journal inexistente são situações opostas, e
                # relatar a primeira como a segunda esconde a adulteração.
                if defeitos:
                    _sair_com(defeitos, "JOURNAL ILEGÍVEL:")
                sys.exit(f"journal ausente em {caminho} — emita uma âncora antes")
            problemas = defeitos + ancora_mod.verificar(linhas)

            if retida:
                indice = ancora_mod.localizar(linhas, retida.strip())
                if indice is None:
                    _sair_com(
                        [f"o hash informado não está neste journal — ou a "
                         f"âncora foi removida, ou o journal é outro"],
                        "ÂNCORA RETIDA NÃO ENCONTRADA:")
                prefixo = ancora_mod.verificar(linhas[:indice + 1])
                if prefixo:
                    _sair_com(prefixo, "O PREFIXO ATÉ A ÂNCORA RETIDA NÃO FECHA:")
                print(f"âncora retida confere: é a #{indice + 1} de "
                      f"{len(linhas)}, e todo o prefixo até ela fecha")

            ultima = linhas[-1]

            # Um verificador que deixou de rodar produz o mesmo silêncio que um
            # sistema íntegro. Sem esta pergunta, a falha do cron é invisível
            # justamente enquanto a janela sem checkpoint se alarga.
            if idade_maxima is not None:
                try:
                    emitida = datetime.fromisoformat(ultima["emitida_em"])
                except (KeyError, ValueError):
                    problemas.append("a última âncora não tem data legível")
                else:
                    limite = datetime.utcnow() - timedelta(days=idade_maxima)
                    if emitida < limite:
                        # Reportar a data, e não uma idade arredondada em dias:
                        # "0 dias, acima do limite de 0" é autocontraditório
                        # para quem lê, e diagnóstico que contradiz a si mesmo
                        # faz o operador duvidar do verificador em vez do
                        # sistema verificado.
                        horas = (datetime.utcnow() - emitida).total_seconds() / 3600
                        problemas.append(
                            f"a âncora mais recente é de {ultima['emitida_em']} "
                            f"({horas:.0f}h atrás) e o limite é de "
                            f"{idade_maxima} dia(s) — a emissão parou, e sem "
                            "checkpoint novo não há o que comparar")

            problemas += conferir_ancora(ultima["total"], ultima["ultimo_id"],
                                         ultima["hash_final"])
            if problemas:
                _sair_com(problemas, "A TRILHA NÃO CONFERE COM O JOURNAL:")
            print(f"journal íntegro: {len(linhas)} âncora(s) encadeadas, a "
                  f"última de {ultima['emitida_em']}")
            print(f"trilha preservada: {ultima['total']} registros")
            return

        # Emissão. Recusar acréscimo sobre journal inconsistente é deliberado:
        # apendar uma âncora boa sobre uma cadeia rompida produz um journal que
        # PARECE crescer e cujo prefixo já não vale — o pior dos dois mundos.
        if defeitos or (linhas and ancora_mod.verificar(linhas)):
            _sair_com(defeitos + ancora_mod.verificar(linhas),
                      "RECUSO ACRESCENTAR: o journal existente não fecha.")

        total, ultimo_id, hash_final = ancora_da_trilha()
        anterior = linhas[-1]["hash_ancora"] if linhas else None
        nova = ancora_mod.montar(total, ultimo_id, hash_final, anterior)
        linha_json = ancora_mod._canonico(nova)

        if destino == "stdout":
            print(linha_json)
            return

        caminho.parent.mkdir(parents=True, exist_ok=True)
        # Modo "a" e nunca "w": a aplicação não reescreve o journal. Isso é
        # convenção, não garantia — append-only de verdade é do sistema de
        # arquivos (`chattr +a` no Linux, ACL sem FILE_WRITE_DATA no Windows),
        # e é a metade que a aplicação não pode entregar sozinha.
        with caminho.open("a", encoding="utf-8") as destino_arquivo:
            destino_arquivo.write(linha_json + "\n")

        print(f"âncora #{len(linhas) + 1} emitida: {total} registros, "
              f"último id {ultimo_id}")
        print(f"acrescentada a {caminho}")
        print("\nGUARDE ESTE HASH FORA DESTE SERVIDOR (uma vez basta):")
        print(f"  {nova['hash_ancora']}")
        print(f"  flask auditoria-ancora --retida {nova['hash_ancora']}")
        print("Journal que a aplicação pode reescrever não prova nada; é a "
              "linha guardada noutro lugar que prova.")

    @app.cli.command("medir-desempenho")
    @click.option("--repeticoes", default=15, show_default=True,
                  help="Execuções que entram na estatística.")
    @click.option("--aquecimentos", default=3, show_default=True,
                  help="Execuções descartadas antes de medir.")
    def medir_desempenho(repeticoes, aquecimentos):
        """Mede as consultas críticas com protocolo, e não por observação.

        Os tempos relatados na monografia vinham de observação: sem número de
        repetições e sem medida de dispersão, com uma precisão decimal que
        sugeria repetibilidade que o dado não sustentava. Este comando fecha
        essa lacuna — descarta aquecimento, repete, e reporta MEDIANA com
        intervalo interquartil.

        Rode depois de `flask seed-volume`: com dezenas de linhas o planejador
        nem considera índice, e a medição não informa decisão nenhuma.
        """
        from sqlalchemy import func as sa_func

        from models.paciente import Paciente
        from models.prontuario import Prontuario
        from services.medicao import medir, relatorio

        termo = "%SILVA%"

        def listagem():
            return Paciente.query.filter_by(ativo=True).order_by(
                Paciente.nome).limit(20).all()

        def contagem():
            return db.session.query(sa_func.count(Paciente.id)).filter_by(
                ativo=True).scalar()

        def sugestao():
            return Paciente.query.filter(
                Paciente.ativo.is_(True),
                Paciente.nome.ilike(termo)).limit(10).all()

        def prontuarios_do_paciente():
            alvo = Paciente.query.filter_by(ativo=True).first()
            if alvo is None:
                return []
            return Prontuario.query.filter_by(paciente_id=alvo.id).order_by(
                Prontuario.id.desc()).limit(20).all()

        total = Paciente.query.count()
        if total < 1000:
            print(f"AVISO: só {total} pacientes na base. Com volume pequeno o "
                  "planejador não considera índice, e a medição não informa "
                  "decisão. Rode `flask seed-volume` antes.\n")

        medidas = [
            medir("listagem paginada de pacientes", listagem,
                  repeticoes, aquecimentos),
            medir("contagem para paginação", contagem,
                  repeticoes, aquecimentos),
            medir("sugestão de paciente (ILIKE)", sugestao,
                  repeticoes, aquecimentos),
            medir("prontuários de um paciente", prontuarios_do_paciente,
                  repeticoes, aquecimentos),
        ]
        print(f"base: {total:,} pacientes\n")
        print(relatorio(medidas))

    @app.cli.command("cnes-importar")
    @click.argument("municipios", nargs=-1, required=True)
    @click.option("--desativar-ausentes", is_flag=True,
                  help="Desativa as unidades do município que o CNES não trouxe.")
    def cnes_importar(municipios, desativar_ausentes):
        """Importa a rede REAL de um município, pelo CNES do Ministério da Saúde.

        Recebe códigos IBGE de sete dígitos. A chave é o `codigo_cnes`: rodar de
        novo ATUALIZA a unidade em vez de duplicá-la.

        O que vem daqui é a REDE — estabelecimento, código, tipo e município, que
        são fatos públicos. Paciente continua sintético: microdado de internação
        é registro individual de gente real, e semeá-lo aqui faria o sistema
        apresentar a internação de alguém como registro seu.
        """
        from models.municipio import Municipio
        from models.unidade_saude import UnidadeSaude
        from services import cnes as api_cnes

        total = {"criadas": 0, "atualizadas": 0, "desativadas": 0}
        for codigo in municipios:
            municipio = Municipio.query.get(str(codigo).strip())
            if municipio is None:
                print(f"  {codigo}: município não está na tabela — rode "
                      "`flask municipios-importar` ou confira o código.")
                continue

            try:
                achadas = api_cnes.estabelecimentos(codigo)
            except api_cnes.ErroCNES as erro:
                print(f"  {municipio.nome}: {erro}")
                continue

            vistas = set()
            for dados in achadas:
                vistas.add(dados["codigo_cnes"])
                unidade = UnidadeSaude.query.filter_by(
                    cnes=dados["codigo_cnes"]).first()
                novo = unidade is None
                if novo:
                    unidade = UnidadeSaude(cnes=dados["codigo_cnes"])
                    db.session.add(unidade)
                unidade.nome = dados["nome"]
                unidade.tipo = dados["tipo"]
                unidade.municipio_ibge = municipio.codigo_ibge
                unidade.cidade = municipio.nome
                unidade.uf = municipio.uf
                unidade.ativo = True
                total["criadas" if novo else "atualizadas"] += 1

            if desativar_ausentes:
                # Só dentro do município importado, e só desativa: unidade tem
                # registro clínico pendurado, e apagá-la levaria o histórico
                # junto. O mesmo argumento de `desativar_usuario`.
                for orfa in UnidadeSaude.query.filter_by(
                        municipio_ibge=municipio.codigo_ibge).all():
                    if orfa.cnes not in vistas and orfa.ativo:
                        orfa.ativo = False
                        total["desativadas"] += 1

            db.session.commit()
            print(f"  {municipio.nome}/{municipio.uf}: {len(achadas)} unidades "
                  "do CNES")

        print(f"{total}")
        print("Leitos: rode `flask seed` — os setores nascem nos hospitais que "
              "o CNES marca como tendo atendimento hospitalar.")

    @app.cli.command("seed-volume")
    @click.option("--pacientes", default=50_000, show_default=True)
    @click.option("--limpar", is_flag=True, help="Remove os dados sintéticos.")
    def seed_volume(pacientes, limpar):
        """Gera volume sintético para medir o sistema sob carga.

        NÃO use em produção: os registros são marcados como SINTETICO e existem
        para tornar possível medir plano de consulta e efeito de índice, o que
        não se faz com dezenas de linhas — o planejador nem considera índice em
        tabela pequena.

        **Pode ser repetido.** A numeração dos documentos continua de onde
        parou, em vez de recomeçar do zero e estourar o `UNIQUE` com uma
        `IntegrityError` crua. `--limpar` devolve o banco ao estado anterior.
        """
        from services import seed_volume as sv

        if limpar:
            print(f"removidos: {sv.limpar()}")
            return

        print(f"gerando {pacientes} pacientes sintéticos...")
        print(f"  {sv.gerar(pacientes=pacientes)}")
        print("gerando internações...")
        print(f"  {sv.gerar_internacoes()}")
        print("gerando registros clínicos (cirurgia, encaminhamento, PS, "
              "evolução, itens de prescrição)...")
        print(f"  {sv.gerar_clinicas()}")
        print("gerando o ambulatorial (triagem, prontuário, agenda, exames)...")
        print(f"  {sv.gerar_ambulatorial()}")
        print("pronto.")

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
