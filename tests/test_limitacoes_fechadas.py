# -*- coding: utf-8 -*-
"""As quatro limitações do capítulo 12 que passaram a ser medidas.

Cada caso aqui existe porque a monografia declarava um limite que, verificado,
ou já não era verdade ou podia deixar de ser. Fechar uma limitação sem teste
seria trocar uma afirmação não verificada por outra.
"""
import pytest


# ── #4 — medição de desempenho com protocolo ───────────────────────────────

def test_medicao_descarta_aquecimento_e_reporta_dispersao():
    """A primeira execução mede a partida, não o regime.

    Sem descartá-la, um plano de consulta ainda não em cache entra na
    estatística e desloca o valor central — que é exatamente o defeito que a
    medição por observação tinha.
    """
    from services.medicao import medir

    chamadas = []

    def operacao():
        chamadas.append(1)

    m = medir("sonda", operacao, repeticoes=10, aquecimentos=3)

    assert len(chamadas) == 13, "aquecimento não foi executado"
    assert m.repeticoes == 10, "aquecimento entrou na estatística"
    assert len(m.amostras_ms) == 10
    assert m.q1_ms <= m.mediana_ms <= m.q3_ms
    assert m.iqr_ms >= 0


def test_medicao_usa_mediana_e_nao_media():
    """Uma pausa do coletor de lixo desloca a média e não a mediana."""
    from services.medicao import Medida

    # Nove execuções rápidas e uma travada — o caso real de uma pausa.
    m = Medida("x", repeticoes=10, aquecimentos=0,
               amostras_ms=[1.0] * 9 + [500.0])

    assert m.mediana_ms == 1.0, (
        "a medida central foi puxada pelo ponto fora da curva — é para isso "
        "que se usa mediana")
    assert m.maximo_ms == 500.0, "o extremo precisa continuar visível"


def test_medicao_acusa_quando_o_numero_nao_e_estavel():
    """Dispersão alta significa que o valor central não deve ser citado."""
    from services.medicao import Medida

    estavel = Medida("a", 10, 0, amostras_ms=[10.0, 10.2, 9.8, 10.1, 9.9])
    disperso = Medida("b", 10, 0, amostras_ms=[1.0, 50.0, 2.0, 80.0, 3.0])

    assert estavel.estavel
    assert not disperso.estavel, (
        "amostras que discordam entre si foram reportadas como se o valor "
        "central significasse alguma coisa")
    assert "disperso" in disperso.como_linha()


def test_relatorio_declara_o_protocolo():
    """O número sem o protocolo é o que a monografia tinha antes."""
    from services.medicao import Medida, relatorio

    texto = relatorio([Medida("consulta", 15, 3, amostras_ms=[1.0, 1.1, 1.2])])

    assert "PROTOCOLO" in texto
    assert "interquartil" in texto
    assert "sintético" in texto, (
        "o relatório precisa lembrar que o volume é sintético — protocolo não "
        "transforma dado sintético em dado real")


# ── #8 — limitação de tentativas fora da autenticação ──────────────────────

def test_verificacao_publica_e_limitada(anonimo):
    """A rota é pública e aceita código: é a superfície mais exposta.

    Ninguém confere trinta documentos em cinco minutos; um script confere
    trinta mil.
    """
    ultimo = None
    for _ in range(40):
        ultimo = anonimo.get("/verificar/AAAAAAAAAAAA")
        if ultimo.status_code == 429:
            break

    assert ultimo.status_code == 429, (
        "quarenta tentativas seguidas na verificação pública passaram sem "
        "limitação — a enumeração de códigos continua aberta")


def test_limite_nao_quebra_o_uso_normal_da_busca(cliente, dados_clinicos):
    """Restrição que barra o uso legítimo é indisponibilidade, não segurança.

    O autocomplete dispara a cada digitação, com 300 ms de espera no gabarito.
    Vinte buscas seguidas é uso corriqueiro de uma recepção.
    """
    for _ in range(20):
        r = cliente.get("/pacientes/buscar?q=ana")
        assert r.status_code != 429, (
            "o limite da busca pegou o uso normal: com autocomplete, isso "
            "trava a digitação de quem atende")


# ── #10 — retenção de cópias de segurança ──────────────────────────────────

def test_rotacao_mantem_as_mais_recentes_e_apaga_o_resto(tmp_path, monkeypatch):
    """Gerar sem expurgar enche o disco, e disco cheio derruba o banco.

    A ordenação é por data de modificação, e não por nome: nome com carimbo de
    tempo ordena bem por acaso, e o dia em que alguém renomear um arquivo à
    mão o critério passa a apagar o backup errado.
    """
    import os
    import time

    from routes import backup as mod

    for i in range(7):
        arquivo = tmp_path / f"backup_{i}.dump"
        arquivo.write_bytes(b"x" * 100)
        # datas crescentes: o de índice 6 é o mais novo
        carimbo = time.time() - (7 - i) * 60
        os.utime(arquivo, (carimbo, carimbo))

    monkeypatch.setattr(mod, "_pasta_destino", lambda: tmp_path)

    removidos = mod._rotacionar(manter=3)

    assert removidos == 4
    restantes = sorted(p.name for p in tmp_path.glob("backup_*"))
    assert restantes == ["backup_4.dump", "backup_5.dump", "backup_6.dump"], (
        f"a rotação apagou os arquivos errados: sobraram {restantes}")


def test_rotacao_desligada_nao_apaga_nada(tmp_path, monkeypatch):
    """`manter=0` é 'não expurgue', e não 'apague tudo'."""
    from routes import backup as mod

    for i in range(3):
        (tmp_path / f"backup_{i}.dump").write_bytes(b"x")
    monkeypatch.setattr(mod, "_pasta_destino", lambda: tmp_path)

    assert mod._rotacionar(manter=0) == 0
    assert len(list(tmp_path.glob("backup_*"))) == 3


# ── verificação de append-only, e a contraprova ────────────────────────────

def test_hardening_sonda_o_journal_nos_dois_sentidos(app):
    """As duas verificações do journal precisam existir, e serem opostas.

    Uma confirma que a escrita arbitrária está IMPEDIDA; a outra, que o
    acréscimo continua POSSÍVEL. É a lição de 9.4.15: endurecimento que
    interrompe o controle protegido é pior que a lacuna que ele fecha.
    """
    from services.hardening import verificar

    with app.app_context():
        nomes = [a.nome for a in verificar()]

    assert any("append-only" in n for n in nomes), (
        "sumiu a verificação de que o journal é de acréscimo")
    assert any("acrescentar ao journal" in n for n in nomes), (
        "sumiu a CONTRAPROVA: sem ela, endurecer a ACL pode parar a emissão "
        "de âncoras sem que nada acuse")


def test_sonda_de_acrescimo_nao_suja_o_journal(tmp_path, monkeypatch):
    """A sonda abre em modo de anexação e fecha: mede sem escrever."""
    from services import hardening

    journal = tmp_path / "ancoras.jsonl"
    journal.write_text('{"a": 1}\n', encoding="utf-8")
    monkeypatch.setenv("ANCORA_JOURNAL", str(journal))

    antes = journal.read_bytes()
    achado = hardening._journal_ainda_aceita_acrescimo()

    assert achado.ok is True
    assert journal.read_bytes() == antes, (
        "a sonda alterou o arquivo que existe para ser protegido")
