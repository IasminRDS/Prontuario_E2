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
import pathlib
import re

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
ATACADO = re.compile(r"request\.(?:form|values)\b(?!\s*(?:\.get|\.getlist|\[))")

# O CSRF é lido pelo Flask-WTF, não pela view.
IGNORAR = {"csrf_token"}

# Campos que o formulário manda e a rota não lê. Cada entrada precisa do motivo
# de ainda não ter sido corrigida; reduzir esta lista é trabalho pendente e
# aumentá-la exige justificar. O teste abaixo também reprova item já corrigido
# que continue aqui, senão a lista vira decoração.
PENDENCIAS = {
    # --- telas que são o formulário ERRADO, copiado de outra e nunca reescrito.
    # O `page_title` de cada uma anuncia a tela de origem. Corrigir é escrever o
    # formulário certo a partir do que a rota lê — é trabalho de tela inteira,
    # não renomeação de campo.
    # "Agendar cirurgia" renderiza o formulário de internação.
    "templates/cirurgia/form.html -> cirurgia.nova": {
        "aih_numero", "cid_principal", "data_prevista_alta", "hipotese_diag",
        "leito_id", "medico_id", "motivo", "tipo",
    },
    # Idêntico, byte a byte, a templates/triagem/form.html.
    "templates/encaminhamentos/form.html -> encaminhamentos.novo": {
        "classificacao", "discriminadores", "dor_escala", "queixa_principal",
    },
    # Também uma cópia da triagem.
    "templates/medicamentos/form.html -> medicamentos.prescrever": {
        "classificacao", "discriminadores", "dor_escala", "paciente_id",
        "queixa_principal",
    },

    # --- a AIH e a APAC pedem campos que o model não tem. Completar exige
    # decidir o schema de faturamento, não mexer no template.
    "templates/faturamento/aih_form.html -> faturamento.aih_form": {
        "carater_internacao", "cid_secundario", "competencia",
        "data_internacao", "data_saida", "dias_permanencia", "motivo_saida",
        "observacoes", "procedimento_secundario", "tipo_aih", "valor_sh",
        "valor_sp",
    },
    "templates/faturamento/aih_form.html -> faturamento.aih_editar": {
        "carater_internacao", "cid_secundario", "competencia",
        "data_internacao", "data_saida", "dias_permanencia", "motivo_saida",
        "observacoes", "procedimento_secundario", "tipo_aih", "valor_sh",
        "valor_sp",
    },
    "templates/faturamento/apac_form.html -> faturamento.apac_form": {
        "cid", "competencia", "justificativa", "procedimento", "tipo",
    },
    "templates/faturamento/apac_form.html -> faturamento.apac_editar": {
        "cid", "competencia", "justificativa", "procedimento", "tipo",
    },

    # --- campos soltos, cada um com sua decisão.
    # A entrada do PS descarta a classificação de risco escolhida na chegada e
    # o modo de chegada. A rota tenta suprir a classificação vinculando a
    # triagem mais recente do paciente; sem triagem, não fica nada — e
    # relatorios_hosp/ps.html agrupa por `AtendimentoPS.classificacao`.
    "templates/ps/entrada.html -> ps.entrada": {"classificacao", "modo_chegada"},
    # Cadastro de usuário: o "ativo" do formulário é ignorado e o usuário nasce
    # sempre com o padrão do model.
    "templates/admin/usuario_form.html -> admin.novo_usuario": {"ativo"},
    # O agendamento nasce e é editado sem que o status escolhido seja lido.
    "templates/agendamento/form.html -> agendamento.novo": {"status"},
    "templates/agendamento/form.html -> agendamento.editar": {"status"},
    "templates/vacinas/vacina_form.html -> vacinas.nova_vacina": {"descricao"},
}


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
