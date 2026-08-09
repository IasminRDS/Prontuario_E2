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
    nome: str
    ok: bool
    detalhe: str = ""
    correcao: str = ""


def verificar():
    """Roda todas as verificações. Devolve lista de `Achado`."""
    import sqlalchemy as sa

    from extensions import db
    from utils import rls

    achados = []

    if db.engine.dialect.name != "postgresql":
        return [Achado("dialeto", False,
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
