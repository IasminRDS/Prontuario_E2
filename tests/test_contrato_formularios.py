# -*- coding: utf-8 -*-
"""O contrato entre o que o formulário ENVIA e o que a rota LÊ.

Terceira camada da mesma família de defeitos. No Jinja, `{{ obj.inexistente }}`
rende vazio; no `fetch`, uma URL que não existe rejeita em silêncio; aqui, um
`<input name="x">` que a rota nunca lê é **preenchido pelo usuário e descartado
sem aviso**. O formulário responde, redireciona e mostra "salvo com sucesso" —
só que o campo não foi para lugar nenhum.

Este é o mais perigoso dos três, porque o dado passa pelas mãos de quem atende.
Foi assim que a classificação de risco escolhida na entrada do pronto-socorro
virou nada, enquanto o relatório de PS agrupa exatamente por esse campo.

Como o alvo é resolvido:

- formulário com `action="{{ url_for('x.y') }}"` → o endpoint é `x.y`;
- formulário sem `action` → posta na própria URL, então o alvo é a regra de
  mesmo caminho que aceite POST. Quem renderiza cada template vem do sinal
  `template_rendered`, colhido numa varredura real de todas as rotas GET — não
  de adivinhação pelo nome do arquivo.

Formulário **sem `method="post"`** fica de fora: em HTML o padrão é GET, a rota
lê de `request.args`, e comparar filtro de busca com a rota POST da mesma URL só
gera falso positivo.
"""
import inspect
import io
import pathlib
import re
import tokenize

import pytest
from flask import template_rendered

from tests.conftest import PERFIS, autenticar
from tests.test_integridade_rotas import _rotas_get, _url_concreta

RAIZ = pathlib.Path(__file__).resolve().parent.parent

FORM = re.compile(r"<form\b(.*?)</form>", re.S | re.I)
ACAO = re.compile(r"""action\s*=\s*["']([^"']*)["']""", re.I)
METODO = re.compile(r"""\bmethod\s*=\s*["']?(\w+)""", re.I)
URLFOR = re.compile(r"""url_for\(\s*['"]([^'"]+)['"]""")
CAMPO = re.compile(
    r"""<(?:input|select|textarea|button)\b[^>]*?\bname\s*=\s*["']([^"']+)["']""",
    re.I | re.S,
)
LEITURA = re.compile(
    r"""request\.(?:form|values)(?:\.get|\.getlist)?\(\s*["']([^"']+)["']"""
    r"""|request\.(?:form|values)\[\s*["']([^"']+)["']\s*\]"""
)
# `request.form` usado inteiro (dict(), .to_dict(), iteração): não dá para saber
# quais chaves são lidas, então a view fica fora da comparação.
#
# A chave lida por VARIÁVEL — `request.form.get(campo)` dentro de um laço —
# entra aqui pelo mesmo motivo: a análise é estática e não sabe o que a variável
# vale. Sem esta cláusula o detector acusava campo lido em laço como descartado,
# que é o inverso do que ele existe para encontrar. Apareceu ao unificar a
# conversão de sinais vitais da triagem, que passou a ler os oito campos por
# laço em vez de um a um.
ATACADO = re.compile(
    r"request\.(?:form|values)\b(?!\s*(?:\.get|\.getlist|\[))"
    r"|request\.(?:form|values)(?:\.get|\.getlist)?\(\s*(?!['\"])[A-Za-z_]"
)

# O CSRF é lido pelo Flask-WTF, não pela view.
IGNORAR = {"csrf_token"}

# Campos que o formulário manda e a rota não lê. Cada entrada precisa do motivo
# de ainda não ter sido corrigida; reduzir esta lista é trabalho pendente e
# aumentá-la exige justificar. O teste abaixo também reprova item já corrigido
# que continue aqui, senão a lista vira decoração.
PENDENCIAS = {
    # As três telas que eram o formulário de OUTRA rota, copiado no andaime e
    # nunca reescrito — cirurgia, encaminhamento e prescrição — já foram
    # corrigidas. Se aparecer uma nova, o sintoma é este mesmo: um punhado de
    # campos de um domínio alheio caindo no vazio, e um `page_title` que
    # denuncia a tela de origem.

    # A AIH e a APAC estavam aqui com 34 campos descartados. O schema foi
    # decidido e implementado em `e2f7b48c9d13`; o que sobrou não é campo
    # descartado, é campo derivado ou renomeado — ver a docstring da migration.

    # A entrada do PS descartava `classificacao` e `modo_chegada`. Resolvido em
    # dois lugares diferentes de propósito: a classificação passou a CRIAR uma
    # triagem (o dado já tinha dono — duplicá-lo numa coluna nova em
    # `atendimentos_ps` seria a mesma replicação que a seção 9.4.14 documenta),
    # e o modo de chegada virou coluna, porque não existia em lugar nenhum.

    # --- FALSO POSITIVO da análise estática, não defeito.
    # O campo existe no arquivo mas é renderizado só no OUTRO modo da tela, e
    # a rota que o recebe de fato o lê. O detector é estático e não avalia o
    # `{% if %}` que decide isso; deixar registrado evita que alguém "corrija"
    # duas vezes o que já funciona.
    #
    # `ativo` está dentro de `{% if usuario %}` — só aparece na edição, e
    # `admin.editar_usuario` lê (`user.ativo = "ativo" in request.form`).
    "templates/admin/usuario_form.html -> admin.novo_usuario": {"ativo"},
    # `status` está dentro de `{% if edicao %}` — só aparece na edição, e
    # `agendamento.editar` passou a lê-lo.
    "templates/agendamento/form.html -> agendamento.novo": {"status"},
}


def _sem_comentarios(fonte):
    """O código da view sem os comentários — e o motivo é constrangedor.

    O detector desiste da comparação quando vê o dicionário do formulário usado
    em atacado, porque aí não há como saber quais chaves a view lê. Só que ele
    procurava isso no texto bruto do arquivo, comentários inclusive: **um
    comentário que EXPLICASSE por que a view não usa o dicionário inteiro
    desligava o detector para aquela view**. Nada acusava; a tela simplesmente
    saía da vigilância.

    É o defeito que este arquivo existe para caçar, aplicado a ele próprio.
    Comentário é prosa, não código, e a análise estática não pode confundir os
    dois. Só os comentários caem: a docstring fica, e continua sendo texto que
    não lê formulário nenhum.
    """
    # Os comentários são APAGADOS NO LUGAR, preenchidos com espaços, em vez de
    # o código ser remontado a partir dos tokens: as expressões procuradas aqui
    # (`request.form.get("x")`) são várias tokens seguidas, e qualquer
    # remontagem que mudasse o espaçamento faria as expressões regulares
    # pararem de casar — desligando o detector pelo outro lado.
    try:
        linhas = fonte.splitlines(keepends=True)
        for tok in tokenize.generate_tokens(io.StringIO(fonte).readline):
            if tok.type != tokenize.COMMENT:
                continue
            linha, inicio = tok.start
            fim = tok.end[1]
            texto = linhas[linha - 1]
            linhas[linha - 1] = texto[:inicio] + " " * (fim - inicio) + texto[fim:]
        return "".join(linhas)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Fonte que não tokeniza (recorte de `inspect.getsource` com indentação
        # própria, por exemplo): volta ao texto bruto. Perder o recorte dos
        # comentários é aceitável; perder a análise inteira não.
        return fonte


@pytest.fixture(scope="module")
def campos_descartados(app, ids_reais):
    """{"template -> endpoint": {campos enviados e nunca lidos}}."""
    renderizado_por = {}

    def registrar(sender, template, context, **extra):
        from flask import request as req

        if template.name:
            renderizado_por.setdefault(template.name, set()).add(req.endpoint)

    template_rendered.connect(registrar, app)
    try:
        cliente = autenticar(app, PERFIS["admin"][1])
        assert cliente.get("/pacientes/").status_code == 200, "login falhou"
        for regra in _rotas_get(app):
            try:
                cliente.get(_url_concreta(regra, ids_reais))
            except Exception:
                pass
    finally:
        template_rendered.disconnect(registrar, app)

    regras = list(app.url_map.iter_rules())
    por_endpoint = {}
    for r in regras:
        por_endpoint.setdefault(r.endpoint, r)

    def lidos(endpoint):
        vf = app.view_functions.get(endpoint)
        if vf is None:
            return set(), True
        try:
            fonte = inspect.getsource(inspect.unwrap(vf))
        except Exception:
            return set(), True
        fonte = _sem_comentarios(fonte)
        return ({a or b for a, b in LEITURA.findall(fonte)},
                bool(ATACADO.search(fonte)))

    achados = {}
    for arquivo in sorted(RAIZ.glob("templates/**/*.html")):
        rel = arquivo.relative_to(RAIZ).as_posix()
        nome_jinja = rel.split("templates/", 1)[-1]
        texto = arquivo.read_text(encoding="utf-8", errors="replace")

        for bloco in FORM.findall(texto):
            cabecalho = bloco.split(">", 1)[0]
            metodo = METODO.search(cabecalho)
            if not metodo or metodo.group(1).lower() != "post":
                continue

            campos = {c for c in CAMPO.findall(bloco)
                      if c not in IGNORAR and "{" not in c}
            if not campos:
                continue

            alvos = set()
            acao = ACAO.search(cabecalho)
            if acao and acao.group(1).strip():
                achado = URLFOR.search(acao.group(1))
                if achado:
                    alvos.add(achado.group(1))
            else:
                for ep in renderizado_por.get(nome_jinja, ()):
                    regra = por_endpoint.get(ep)
                    if regra is None:
                        continue
                    for outra in regras:
                        if str(outra) == str(regra) and (
                                {"POST", "PUT", "PATCH"} & outra.methods):
                            alvos.add(outra.endpoint)

            for alvo in alvos:
                chaves, atacado = lidos(alvo)
                if atacado:
                    continue
                descartados = campos - chaves
                if descartados:
                    achados.setdefault(f"{rel} -> {alvo}", set()).update(descartados)

    return achados


def test_nenhum_campo_novo_descartado(campos_descartados):
    novos = []
    for chave, campos in sorted(campos_descartados.items()):
        inesperados = campos - PENDENCIAS.get(chave, set())
        for campo in sorted(inesperados):
            novos.append(f"  {chave}: {campo}")
    assert not novos, (
        "campo que o formulário envia e a rota nunca lê — o usuário preenche e "
        "o dado é descartado sem aviso:\n" + "\n".join(novos)
    )


def test_pendencias_de_formulario_nao_apodrecem(campos_descartados):
    """Campo que passou a ser lido precisa sair da lista."""
    resolvidos = []
    for chave, campos in sorted(PENDENCIAS.items()):
        ainda = campos_descartados.get(chave, set())
        for campo in sorted(campos - ainda):
            resolvidos.append(f"  {chave}: {campo}")
    assert not resolvidos, (
        "já é lido pela rota — remova de PENDENCIAS:\n" + "\n".join(resolvidos))


# --- os achados desta análise, agora como teste de comportamento -----------

def test_edicao_de_agendamento_grava_a_situacao(app, dados_clinicos, sem_csrf):
    """Mudar "Situação" na edição e salvar precisa mudar o registro.

    O seletor aparecia na tela, a rota não lia o campo, e a mensagem de sucesso
    aparecia igual: a pessoa marcava "realizado", via "Agendamento atualizado!"
    e o registro continuava "agendado". Contrato de formulário quebrado não
    gera erro — ele confirma uma coisa e grava outra.
    """
    from extensions import db
    from models.agendamento import Agendamento
    from tests.conftest import PERFIS, autenticar

    cliente = autenticar(app, PERFIS["admin"][1])

    with app.app_context():
        ag = Agendamento.query.order_by(Agendamento.id.asc()).first()
        assert ag is not None, "sem agendamento semeado"
        ag.status = "agendado"
        db.session.commit()
        ident, paciente_id = ag.id, ag.paciente_id
        quando = ag.data_hora.strftime("%Y-%m-%dT%H:%M")

    resposta = cliente.post(f"/agendamento/{ident}/editar", data={
        "paciente_id": paciente_id,
        "data_hora": quando,
        "tipo": "consulta",
        "status": "atendido",
    }, follow_redirects=True)
    assert resposta.status_code == 200

    with app.app_context():
        assert db.session.get(Agendamento, ident).status == "atendido", (
            "a situação escolhida na edição não foi gravada")


def test_formulario_de_vacina_oferece_lote_e_validade(app, dados_clinicos):
    """O caso inverso: a rota lê o campo e o formulário nunca o enviava.

    `vacinas.nova_vacina` lê `lote` e `validade` — e chega a VALIDAR a data —
    mas o formulário não tinha os campos. Toda vacina nascia sem lote e sem
    validade, e é disso que depende o controle de vencimento.
    """
    from tests.conftest import PERFIS, autenticar

    cliente = autenticar(app, PERFIS["admin"][1])
    html = cliente.get("/vacinas/catalogo/nova").get_data(as_text=True)
    for campo in ("lote", "validade"):
        assert f'name="{campo}"' in html, (
            f"a rota lê {campo!r} e o formulário não envia")
