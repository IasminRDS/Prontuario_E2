# -*- coding: utf-8 -*-
"""Verifica no BANCO os controles que a aplicação não consegue garantir sozinha.

O código da aplicação garante o que está escrito nele. Não garante o que
depende de administração do PostgreSQL — e é justamente aí que o isolamento
territorial pode ser desativado sem que nada na aplicação mude de
comportamento. Esta é a diferença entre "garantia da aplicação" e "dependência
de infraestrutura", e ela precisa ser verificável, não confiada.

Cada verificação corresponde a uma falha real ou observada nesta base:

- **FORCE ausente** — o dono da tabela ignora políticas por padrão, e a
  aplicação É a dona. Sem FORCE, as políticas existem e não valem nada.
- **BYPASSRLS no papel** — atributo que dispensa o papel de toda política.
- **Escopo pré-definido** — `PGOPTIONS=-c app.nivel=SISTEMA` no ambiente do
  serviço, ou `ALTER ROLE ... SET app.nivel`, deixa toda sessão nascer com
  escopo amplo. Aconteceu de verdade: um operador copiou o comando de backup
  para o terminal e as duas garantias de falha fechada caíram junto.
- **Auditoria pertencente a quem ela audita** — enquanto o papel da aplicação
  for dono de `audit_logs`, ele pode alterá-la. O encadeamento por hash torna
  isso detectável, não impossível.
- **Tabela clínica fora do escopo** — a lista de protegidas sai do metadata;
  esta verificação confronta a lista com o que o banco realmente tem.
"""
from dataclasses import dataclass


@dataclass
class Achado:
    """Resultado de uma verificação. `ok` tem TRÊS estados, não dois.

    `True` passou, `False` falhou e `None` é **não verificável neste ambiente**
    — que não é a mesma coisa que falhar. Confundir os dois tem consequência
    prática: uma verificação que reprova para sempre numa máquina de
    desenvolvimento treina quem a lê a ignorar o comando inteiro, e aí o dia em
    que uma reprovação de verdade aparecer ela não será vista. Reportar sem
    reprovar é o que mantém o portão significando alguma coisa.
    """
    nome: str
    ok: bool | None
    detalhe: str = ""
    correcao: str = ""


def verificar():
    """Roda todas as verificações. Devolve lista de `Achado`."""
    import sqlalchemy as sa

    from extensions import db
    from utils import rls

    # As duas verificações do journal são de SISTEMA DE ARQUIVOS e não têm
    # relação com o dialeto do banco. Ficavam depois do retorno antecipado
    # abaixo, de modo que em SQLite ninguém as executava — o portão silenciava
    # justamente na configuração em que ele é mais fácil de esquecer.
    achados = [_journal_append_only(), _journal_ainda_aceita_acrescimo()]

    if db.engine.dialect.name != "postgresql":
        return achados + [Achado("dialeto", False,
                       f"banco é {db.engine.dialect.name}, não PostgreSQL",
                       "RLS e estas verificações só existem em PostgreSQL")]

    esperadas = set(rls.tabelas_protegidas(db.metadata))

    with db.engine.connect() as c:
        papel = c.execute(sa.text("select current_user")).scalar()

        # 1. políticas presentes em todas as tabelas esperadas
        com_politica = set(c.execute(sa.text(
            "select tablename from pg_policies "
            "where schemaname = 'public' and policyname = 'escopo_territorial'"
        )).scalars().all())
        faltando = esperadas - com_politica
        achados.append(Achado(
            "toda tabela com unidade_id tem política de RLS",
            not faltando,
            f"sem política: {sorted(faltando)}" if faltando else "",
            "flask db upgrade"))

        # 2. FORCE ativo
        sem_force = set(c.execute(sa.text(
            "select c.relname from pg_class c "
            "join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' and c.relname = any(:t) "
            "and (not c.relrowsecurity or not c.relforcerowsecurity)"
        ), {"t": list(esperadas)}).scalars().all())
        achados.append(Achado(
            "RLS em modo FORCE (o dono também obedece)",
            not sem_force,
            f"sem FORCE: {sorted(sem_force)}" if sem_force else "",
            "ALTER TABLE <t> FORCE ROW LEVEL SECURITY"))

        # 3. papel da aplicação sem BYPASSRLS
        bypass = c.execute(sa.text(
            "select rolbypassrls from pg_roles where rolname = current_user"
        )).scalar()
        achados.append(Achado(
            "papel da aplicação sem BYPASSRLS",
            not bypass,
            f"{papel} tem BYPASSRLS: nenhuma política se aplica a ele" if bypass else "",
            f"ALTER ROLE {papel} NOBYPASSRLS"))

        # 4. papel da aplicação não é superusuário
        superusuario = c.execute(sa.text(
            "select rolsuper from pg_roles where rolname = current_user")).scalar()
        achados.append(Achado(
            "papel da aplicação não é superusuário",
            not superusuario,
            f"{papel} é superusuário e ignora RLS" if superusuario else "",
            f"ALTER ROLE {papel} NOSUPERUSER"))

        # 5. nenhum escopo pré-definido na sessão
        escopo = c.execute(sa.text(
            "select current_setting('app.nivel', true)")).scalar()
        achados.append(Achado(
            "sessão nasce sem escopo (falha fechada preservada)",
            not escopo,
            f"app.nivel já vem como {escopo!r} — provavelmente PGOPTIONS no "
            "ambiente ou ALTER ROLE ... SET" if escopo else "",
            "remova PGOPTIONS do ambiente do serviço; "
            f"ALTER ROLE {papel} RESET app.nivel"))

        # 6. auditoria não pertence a quem ela audita
        dono_auditoria = c.execute(sa.text(
            "select tableowner from pg_tables "
            "where schemaname = 'public' and tablename = 'audit_logs'")).scalar()
        achados.append(Achado(
            "audit_logs não pertence ao papel da aplicação",
            dono_auditoria != papel,
            f"audit_logs pertence a {dono_auditoria}, que é o papel da própria "
            "aplicação: a trilha é alterável por quem ela audita"
            if dono_auditoria == papel else "",
            "CREATE ROLE auditoria_owner NOLOGIN; "
            "ALTER TABLE audit_logs OWNER TO auditoria_owner; "
            f"REVOKE ALL ON audit_logs FROM {papel}; "
            f"GRANT INSERT, SELECT ON audit_logs TO {papel}; "
            # A SEQUÊNCIA vai junto no ALTER TABLE ... OWNER, e sem USAGE nela o
            # INSERT falha com "permissão negada para sequência". Esta linha
            # faltava na receita, e o resultado foi um endurecimento que passava
            # na própria verificação e impedia a aplicação de auditar.
            f"GRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq TO {papel}"))

        # 7. a aplicação não pode apagar a própria trilha
        pode_apagar = c.execute(sa.text(
            "select has_table_privilege(current_user, 'audit_logs', 'DELETE')"
        )).scalar()
        achados.append(Achado(
            "aplicação não pode apagar registros de auditoria",
            not pode_apagar,
            f"{papel} tem DELETE em audit_logs" if pode_apagar else "",
            f"REVOKE UPDATE, DELETE, TRUNCATE ON audit_logs FROM {papel}"))

        # 8. ...e AINDA CONSEGUE ESCREVER.
        #
        # Esta verificação nasceu de um erro concreto: a receita do item 6
        # transferia a tabela e concedia INSERT, mas não a USAGE na SEQUÊNCIA,
        # que muda de dono junto. O INSERT passou a falhar com "permissão
        # negada para sequência" — e as sete verificações continuaram passando,
        # porque nenhuma delas perguntava se a aplicação ainda auditava.
        #
        # **Endurecimento que impede o registro é pior que a lacuna que ele
        # fecha:** a trilha para de crescer, nada acusa, e a ausência de
        # eventos é indistinguível de ausência de acessos. Verificar o
        # privilégio da tabela não basta; é preciso perguntar pela sequência,
        # que é a outra metade do que um INSERT exige.
        pode_inserir = c.execute(sa.text(
            "select has_table_privilege(current_user, 'audit_logs', 'INSERT')"
        )).scalar()
        sequencia = c.execute(sa.text(
            "select pg_get_serial_sequence('audit_logs', 'id')")).scalar()
        usa_sequencia = True
        if sequencia:
            usa_sequencia = c.execute(sa.text(
                "select has_sequence_privilege(current_user, :s, 'USAGE')"
            ), {"s": sequencia}).scalar()

        motivos = []
        if not pode_inserir:
            motivos.append("sem INSERT na tabela")
        if not usa_sequencia:
            motivos.append(f"sem USAGE na sequência {sequencia}")
        achados.append(Achado(
            "aplicação ainda consegue registrar auditoria",
            pode_inserir and usa_sequencia,
            (f"{papel} não consegue auditar: {', '.join(motivos)} — "
             "a trilha parou de crescer e nada acusa")
            if motivos else "",
            f"GRANT INSERT ON audit_logs TO {papel}; "
            f"GRANT USAGE, SELECT ON SEQUENCE audit_logs_id_seq TO {papel}"))

    return achados


def _journal_append_only():
    """O journal de âncoras é só de acréscimo no SISTEMA DE ARQUIVOS?

    A aplicação abre o arquivo em modo de anexação, e isso é convenção: o mesmo
    processo poderia abri-lo em modo de escrita. Acréscimo efetivo é atributo do
    sistema de arquivos, aplicado por quem administra a máquina e — este é o
    ponto — **não removível pelo usuário da aplicação**. Se fosse removível por
    ela, não seria garantia.

    Por isso a verificação existe e a aplicação NÃO tenta aplicar o atributo:
    aplicar exigiria o privilégio cuja ausência é justamente o que se quer
    provar. É a mesma fronteira das outras oito, do lado do sistema de
    arquivos em vez do banco.
    """
    import os
    import pathlib

    caminho = pathlib.Path(
        os.environ.get("ANCORA_JOURNAL", "backups/ancora_auditoria.jsonl"))

    if not caminho.is_file():
        return Achado(
            NOME_APPEND_ONLY,
            False,
            f"não existe journal em {caminho} — sem âncora não há o que "
            "proteger nem o que comparar",
            "flask auditoria-ancora")

    if os.name == "nt":
        return _append_only_windows(caminho)

    if os.name != "posix":
        return Achado(
            NOME_APPEND_ONLY, None,
            f"não verificável neste sistema operacional ({os.name})",
            "")

    import subprocess
    try:
        saida = subprocess.run(["lsattr", "-d", str(caminho)],
                               capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        return Achado(
            NOME_APPEND_ONLY,
            None, f"não consegui ler os atributos: {exc}",
            f"chattr +a {caminho}")

    # `lsattr` devolve "-----a--------- caminho"; o 'a' é o append-only.
    atributos = (saida.stdout.split() or [""])[0]
    tem_append_only = "a" in atributos

    return Achado(
        NOME_APPEND_ONLY,
        tem_append_only,
        "" if tem_append_only else
        (f"{caminho} pode ser reescrito e truncado — o modo de anexação da "
         "aplicação é convenção, não garantia"),
        f"sudo chattr +a {caminho}")


NOME_APPEND_ONLY = "journal de âncoras é append-only no sistema de arquivos"

# Direito de ESCRITA em posição arbitrária. É o que precisa estar NEGADO para
# que o arquivo seja de acréscimo: sem ele, sobra `AD` (append) e o conteúdo já
# gravado não pode ser reescrito nem truncado.
_ESCRITA_ARBITRARIA = ("WD", "WDAC", "(W)", "(M)", "(F)")

_REMEDIO_WINDOWS = (
    'icacls "{caminho}" /deny "{usuario}:(WD)" '
    '/grant "{usuario}:(AD,RD)"'
)


def _append_only_windows(caminho):
    """Lê a ACL com `icacls` e procura a NEGAÇÃO da escrita arbitrária.

    A leitura é deliberadamente conservadora, e convém dizer por quê: ACL do
    Windows tem herança, ordenação entre negações e concessões, e grupos que se
    sobrepõem. Interpretar tudo isso aqui produziria uma resposta que parece
    precisa e não é.

    Então a verificação responde uma pergunta estreita e honesta: **existe uma
    entrada de NEGAÇÃO cobrindo escrita arbitrária para o usuário corrente ou
    para um grupo que o contenha?** Havendo, aprova. Não havendo, REPROVA — e
    reprovar é o resultado correto na dúvida, porque o custo de confirmar uma
    proteção inexistente é maior que o de pedir uma conferência a mais.
    """
    import getpass
    import subprocess

    try:
        saida = subprocess.run(["icacls", str(caminho)], capture_output=True,
                               text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        return Achado(NOME_APPEND_ONLY, None,
                      f"não consegui executar icacls: {exc}", "")

    if saida.returncode != 0:
        return Achado(NOME_APPEND_ONLY, None,
                      f"icacls falhou: {(saida.stderr or '').strip()[:120]}", "")

    usuario = getpass.getuser()
    remedio = _REMEDIO_WINDOWS.format(caminho=caminho, usuario=usuario)

    negacoes = [l.strip() for l in saida.stdout.splitlines() if "(DENY)" in l]
    nega_escrita = any(
        any(d in l for d in _ESCRITA_ARBITRARIA) for l in negacoes)

    if nega_escrita:
        return Achado(NOME_APPEND_ONLY, True, "", remedio)

    return Achado(
        NOME_APPEND_ONLY, False,
        f"{caminho} não tem negação de escrita arbitrária na ACL: o arquivo "
        "pode ser reescrito e truncado, e o modo de anexação da aplicação é "
        "convenção, não garantia",
        remedio)


def _journal_ainda_aceita_acrescimo():
    """A aplicação ainda consegue ACRESCENTAR ao journal?

    De sinal contrário à verificação anterior, e pela mesma razão que a oitava
    existe: o endurecimento prescrito ali pode quebrar o que protege. Negar
    escrita arbitrária sem conceder acréscimo deixa a emissão de âncoras
    falhando em silêncio — e journal que parou de crescer produz o mesmo
    arquivo que um sistema sem uso.

    A sonda ABRE em modo de anexação e fecha sem escrever nada: mede a
    permissão sem sujar o artefato que se pretende proteger.
    """
    import os
    import pathlib

    caminho = pathlib.Path(
        os.environ.get("ANCORA_JOURNAL", "backups/ancora_auditoria.jsonl"))
    nome = "aplicação ainda consegue acrescentar ao journal"

    if not caminho.is_file():
        return Achado(nome, None, f"não há journal em {caminho} para sondar", "")

    try:
        with caminho.open("a", encoding="utf-8"):
            pass
    except OSError as exc:
        return Achado(
            nome, False,
            f"não consigo abrir {caminho} para acréscimo: {exc} — o "
            "endurecimento da ACL foi longe demais e a emissão de âncoras "
            "vai falhar",
            'icacls "%s" /grant "%s:(AD,RD)"' % (caminho, os.getlogin()))

    return Achado(nome, True, "", "")
