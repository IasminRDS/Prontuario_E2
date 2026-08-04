# -*- coding: utf-8 -*-
"""Row-Level Security: o banco como última linha de defesa.

A aplicação já filtra por unidade em Python. Isso protege contra o operador
mal-intencionado, mas não contra o próprio código — uma consulta nova que esqueça
o filtro vaza registro clínico de outro município sem que nada acuse. Com RLS, a
regra passa a viver no banco: a consulta esquecida simplesmente não enxerga a
linha.

**Falha fechada.** Se o escopo não for definido na transação, as políticas não
liberam nada. É deliberado: uma aplicação que aparece vazia é um bug óbvio; uma
que mostra dados de todo o país porque alguém esqueceu de setar uma variável é um
incidente de privacidade que ninguém percebe.

Como o escopo chega ao banco: `SET LOCAL` disparado no início de CADA transação
(evento `after_begin`). Fazer isso no checkout da conexão não serviria — o
`SET LOCAL` morre no fim da transação, e as rotas dão commit no meio da
requisição. E o `SET` sem `LOCAL` vazaria pelo pool para o próximo usuário.
"""
import re

from flask import g, has_request_context
from flask_login import current_user
from sqlalchemy import event, text

# Tabelas com `unidade_id` que NÃO devem ser isoladas territorialmente.
#
# `users` é o caso crítico: proteger a tabela de usuários quebraria o próprio
# login, porque a consulta que carrega o usuário acontece antes de existir
# escopo. `medicos` acompanha `users`. `leitos` e `mov_estoque` são estrutura e
# movimento de apoio, alcançados pelo isolamento dos registros que os referenciam.
FORA_DO_ESCOPO = {"users", "medicos", "leitos", "mov_estoque"}

# `pacientes` não entra por não ter `unidade_id`, e isso é de propósito:
# cadastro de paciente é nacional — encontrar quem foi atendido em outro
# município é exatamente o ponto do prontuário longitudinal. O controle sobre o
# prontuário dele é vínculo assistencial e consentimento, não fronteira
# territorial.


def tabelas_protegidas(metadata):
    """Toda tabela com `unidade_id`, menos as exceções acima.

    Derivar do metadata em vez de manter lista à mão: uma tabela clínica nova
    nasce protegida, em vez de depender de alguém lembrar de acrescentá-la aqui.
    """
    return tuple(sorted(
        t.name for t in metadata.sorted_tables
        if "unidade_id" in t.columns and t.name not in FORA_DO_ESCOPO
    ))

NIVEIS = ("SISTEMA", "UNIDADE", "MUNICIPIO", "REGIONAL", "ESTADO")

# Escopo usado fora de requisição: migrations, CLI, tarefas de fundo. É código
# do servidor, já confiável — sem isto, `flask db upgrade` não enxergaria as
# próprias tabelas.
ESCOPO_SISTEMA = {"nivel": "SISTEMA"}


def _politica(tabela):
    """Uma política por tabela, cobrindo os quatro níveis territoriais.

    Nome de tabela não pode ser parâmetro em DDL, então a interpolação aqui é
    inevitável — o que a torna segura é a origem: nomes vindos do metadata,
    conferidos abaixo contra um formato estrito.
    """
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", tabela or ""):
        raise ValueError(f"nome de tabela inaceitável: {tabela!r}")
    return f"""
DROP POLICY IF EXISTS escopo_territorial ON {tabela};
CREATE POLICY escopo_territorial ON {tabela}
USING (
    current_setting('app.nivel', true) = 'SISTEMA'
    OR (
        current_setting('app.nivel', true) = 'UNIDADE'
        AND unidade_id = nullif(current_setting('app.unidade_id', true), '')::int
    )
    OR (
        current_setting('app.nivel', true) = 'MUNICIPIO'
        AND unidade_id IN (
            SELECT id FROM unidades_saude
            WHERE municipio_ibge = nullif(current_setting('app.municipio_ibge', true), '')
        )
    )
    OR (
        current_setting('app.nivel', true) = 'REGIONAL'
        AND unidade_id IN (
            SELECT id FROM unidades_saude
            WHERE regional_id = nullif(current_setting('app.regional_id', true), '')::int
        )
    )
    OR (
        current_setting('app.nivel', true) = 'ESTADO'
        AND unidade_id IN (
            SELECT id FROM unidades_saude
            WHERE uf = nullif(current_setting('app.uf', true), '')
        )
    )
);
ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY;
-- FORCE é indispensável aqui: o dono da tabela ignora RLS por padrão, e a
-- aplicação É a dona. Sem isto as políticas existiriam sem efeito nenhum.
ALTER TABLE {tabela} FORCE ROW LEVEL SECURITY;
"""


def aplicar_politicas(conexao, tabelas):
    """Cria as políticas. Idempotente. Usada pela migration e pelos testes."""
    for tabela in tabelas:
        conexao.exec_driver_sql(_politica(tabela))


def remover_politicas(conexao, tabelas):
    for tabela in tabelas:
        conexao.exec_driver_sql(
            f"ALTER TABLE {tabela} NO FORCE ROW LEVEL SECURITY;"
            f"ALTER TABLE {tabela} DISABLE ROW LEVEL SECURITY;"
            f"DROP POLICY IF EXISTS escopo_territorial ON {tabela};"
        )


# Cada nível depende de um campo do usuário. Se ele estiver vazio, o escopo é
# irresolúvel — e a política, que compara com NULL, nega tudo.
CAMPO_DO_NIVEL = {
    "UNIDADE": "unidade_id",
    "MUNICIPIO": "municipio_ibge",
    "REGIONAL": "regional_id",
    "ESTADO": "uf",
}


def escopo_do_usuario(usuario):
    """Traduz o usuário no escopo que o banco entende.

    Devolve também `irresoluvel`, que quem chama usa para avisar em vez de
    deixar o operador diante de um sistema misteriosamente vazio.
    """
    from utils.rbac import SUPER_ADMIN, _normalizar

    # O operador da plataforma atravessa o isolamento territorial — é o que o
    # próprio RBAC já diz ao dar-lhe `hospital:manage`. Sem espelhar isso aqui,
    # o RLS contradiria a autorização da aplicação.
    if _normalizar(getattr(usuario, "perfil", None)) == SUPER_ADMIN:
        return {"nivel": "SISTEMA", "irresoluvel": False}

    nivel = (getattr(usuario, "nivel_acesso", None) or "UNIDADE").upper()
    if nivel not in NIVEIS or nivel == "SISTEMA":
        # `SISTEMA` não pode vir do cadastro do usuário: é escopo de processo
        # interno, não de gente.
        nivel = "UNIDADE"

    escopo = {
        "nivel": nivel,
        "unidade_id": getattr(usuario, "unidade_id", None),
        "municipio_ibge": getattr(usuario, "municipio_ibge", None),
        "regional_id": getattr(usuario, "regional_id", None),
        "uf": getattr(usuario, "uf", None),
    }
    escopo["irresoluvel"] = not escopo.get(CAMPO_DO_NIVEL[nivel])
    return escopo


def escopo_atual():
    """Escopo da transação que está começando.

    Lê apenas `g`, NUNCA `current_user`. Tocar em `current_user` aqui provoca
    recursão: o proxy dispara o carregador do Flask-Login, que consulta o banco,
    que abre transação, que chama este mesmo hook. O escopo é resolvido uma vez
    por requisição em `definir_escopo_da_requisicao`.

    Fora de requisição é SISTEMA (CLI, migration, backup). Dentro de requisição
    sem escopo definido, devolve vazio — que não libera nada, o que é correto:
    quem não se identificou não tem escopo.
    """
    if not has_request_context():
        return ESCOPO_SISTEMA
    return getattr(g, "escopo_rls", None) or {"nivel": None}


def definir_escopo_da_requisicao(db):
    """Resolve o usuário e guarda o escopo em `g`. Chamar em `before_request`.

    Consultar `users` aqui é seguro porque essa tabela fica fora do escopo
    territorial — se estivesse protegida, o login não teria como acontecer.
    """
    if getattr(current_user, "is_authenticated", False):
        escopo = escopo_do_usuario(current_user)
        if escopo.get("irresoluvel"):
            # Falhar fechado é o certo, mas em silêncio é armadilha: o operador
            # vê um sistema vazio e conclui que perdeu os dados. O cadastro é
            # que está incompleto — e isso precisa aparecer para quem investiga.
            from flask import current_app

            current_app.logger.warning(
                "usuário %s tem nível %s sem o campo %s preenchido: não verá "
                "nenhum registro clínico até o cadastro ser corrigido",
                getattr(current_user, "email", "?"), escopo["nivel"],
                CAMPO_DO_NIVEL[escopo["nivel"]])
        g.escopo_rls = escopo
    else:
        g.escopo_rls = {"nivel": None}

    # A transação que carregou o usuário começou antes de existir escopo, e
    # duraria o resto da requisição servindo consultas sem permissão nenhuma.
    # Descartá-la faz a próxima nascer já com o escopo correto.
    db.session.rollback()


def _aplicar_escopo(conexao, escopo):
    """Define os parâmetros do escopo para a transação corrente.

    Usa `set_config(nome, valor, is_local => true)` em vez de `SET LOCAL`
    montado por interpolação: a função aceita nome e valor como parâmetros de
    verdade, então não há SQL construído com f-string. O `true` no terceiro
    argumento é o que faz o valor morrer junto com a transação — sem ele, o
    escopo vazaria pelo pool para o próximo usuário.
    """
    valores = {
        "app.nivel": escopo.get("nivel") or "",
        "app.unidade_id": escopo.get("unidade_id"),
        "app.municipio_ibge": escopo.get("municipio_ibge") or "",
        "app.regional_id": escopo.get("regional_id"),
        "app.uf": escopo.get("uf") or "",
    }
    comando = text("SELECT set_config(:nome, :valor, true)")
    for chave, valor in valores.items():
        conexao.execute(comando,
                        {"nome": chave, "valor": "" if valor is None else str(valor)})


def registrar(db, app=None):
    """Liga o escopo ao início de toda transação da sessão.

    `after_begin` e não checkout de conexão: o `SET LOCAL` morre no fim da
    transação, e as rotas dão commit no meio da requisição — o escopo precisa
    ser reposto a cada transação nova. Um `SET` sem `LOCAL` resolveria isso mas
    vazaria pelo pool para o próximo usuário, que é o pior resultado possível.
    """
    if app is not None:
        @app.before_request
        def _resolver_escopo():
            definir_escopo_da_requisicao(db)

    @event.listens_for(db.session, "after_begin")
    def _ao_iniciar_transacao(sessao, _transacao, conexao):
        if conexao.dialect.name != "postgresql":
            return  # SQLite não tem RLS; o filtro em Python continua valendo
        try:
            _aplicar_escopo(conexao, escopo_atual())
        except Exception:
            # Não derruba a transação — sem os parâmetros as políticas negam
            # tudo, que já é o comportamento seguro. Mas REGISTRA: falha
            # silenciosa de um controle de acesso aparece depois como "sumiram
            # os dados", e ninguém liga uma coisa à outra.
            from flask import current_app

            if current_app:
                current_app.logger.exception(
                    "não foi possível aplicar o escopo territorial; "
                    "a transação vai enxergar zero linhas")
