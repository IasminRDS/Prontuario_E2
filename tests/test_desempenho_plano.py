# -*- coding: utf-8 -*-
"""O plano de execucao da listagem de pacientes, medido em vez de suposto.

`ix_pacientes_listagem_nome` (migration `e7a3c9d21f84`) existe para um caminho
so: a listagem SEM recorte territorial, do operador da plataforma (escopo
SISTEMA/ESTADO). Sem ele, `... WHERE ativo ORDER BY nome LIMIT 20` cai em Seq
Scan da tabela inteira mais um Sort, porque o indice territorial tem (municipio,
uf) na cabeca e nao serve uma consulta que so ordena por nome.

Este teste le o EXPLAIN e reprova se o indice deixar de ser usado — que e o que
aconteceria se alguem removesse o indice do model ou da migration sem remover o
outro. E a versao executavel da afirmacao que a monografia faz: o numero medido
(55,8ms -> 1,2ms a 50 mil linhas) nao vale nada se o plano que o produz nao
puder ser reproduzido.

**So roda em PostgreSQL.** O formato do EXPLAIN e o proprio conceito de Index
Scan sao do PostgreSQL; o SQLite planeja de outro jeito e nao tem volume no banco
de teste. E precisa de volume ate em PostgreSQL: com as poucas linhas do seed, o
planejador varre tudo porque varrer uma tabela de uma pagina sai mais barato que
abrir um indice — o mesmo motivo pelo qual `seed-volume` existe. Por isso o teste
insere a carga num savepoint e a desfaz ao final, sem tocar no que os outros
testes semeiam.
"""
import pytest
import sqlalchemy as sa

from database.db import db

# Acima deste volume o planejador prefere o indice a varrer-e-ordenar a tabela
# inteira para um LIMIT 20. A sondagem mostrou a virada bem abaixo disto ate numa
# tabela estreita; a real e mais larga, entao cruza antes. 2000 e folga, nao
# limiar apertado.
VOLUME = 2000


@pytest.fixture
def _so_postgres(app):
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            pytest.skip("EXPLAIN e Index Scan sao especificos do PostgreSQL")
        yield


def test_listagem_sem_recorte_usa_indice_medido(_so_postgres, app):
    with app.app_context():
        savepoint = db.session.begin_nested()
        try:
            # Carga sintetica so para esta medicao. `cpf`/`cns` ficam nulos: sao
            # UNIQUE mas aceitam varios nulos, e a listagem nao os le. `nome`
            # zero-preenchido para uma ordenacao estavel e realista.
            db.session.execute(sa.text(
                "INSERT INTO pacientes (nome, data_nascimento, sexo, ativo) "
                "SELECT 'Paciente ' || lpad(g::text, 7, '0'), "
                "date '1990-01-01', 'I', true "
                "FROM generate_series(1, :n) g"), {"n": VOLUME})
            # Sem ANALIZE o planejador decide pela estimativa velha, de antes da
            # carga, e o teste mediria um plano que a producao nao veria.
            db.session.execute(sa.text("ANALYZE pacientes"))

            linhas = db.session.execute(sa.text(
                "EXPLAIN SELECT * FROM pacientes "
                "WHERE ativo ORDER BY nome LIMIT 20")).fetchall()
            plano = "\n".join(linha[0] for linha in linhas)
        finally:
            savepoint.rollback()

    assert "ix_pacientes_listagem_nome" in plano, (
        "a listagem nao recortada deixou de usar o indice medido — o plano foi:\n"
        + plano)
    assert "Seq Scan" not in plano, (
        "voltou a varrer a tabela inteira em vez de usar o indice:\n" + plano)
    # O ganho do indice e eliminar a ordenacao: se um Sort reaparece, o indice
    # nao esta servindo a ordem, ainda que seu nome apareca no plano.
    assert "Sort" not in plano, (
        "o indice foi lido mas a ordenacao voltou como Sort:\n" + plano)
