# -*- coding: utf-8 -*-
"""O que os PDFs clínicos REALMENTE contêm.

Última camada da família. Aqui o silêncio é ainda mais fácil: um PDF que gera
sem erro devolve 200 e um arquivo válido, e ninguém abre para conferir. O dado
que faltar simplesmente não está na folha que o paciente leva para casa.

Estes documentos saem da unidade assinados — atestado, receituário, guia de
encaminhamento e sumário de alta valem como documento do SUS. O teste extrai o
texto de cada um e confere que o dado clínico do banco aparece.

Dois defeitos que este teste tranca, e que só apareceram ao ler o texto gerado:

- **mês em inglês**: `strftime("%d de %B de %Y")` sai na locale do processo, e
  os documentos vinham datados de "06 de August de 2026";
- **glifo fora da fonte**: `⚠` (U+26A0) e `₂` (U+2082) não existem no WinAnsi
  das fontes padrão do reportlab e saíam como quadrado preto — o `⚠` estava
  justamente na linha de ALERGIAS dos três documentos que a exibem.
"""
import io
import re

import pytest
from PyPDF2 import PdfReader

from tests.conftest import PERFIS, autenticar
from utils.datas import MESES

# Meses em inglês que `%B` produziria na locale C.
MESES_EN = ("January", "February", "March", "April", "May", "June", "July",
            "August", "September", "October", "November", "December")


def _texto_do_pdf(resposta):
    assert resposta.status_code == 200, f"gerou {resposta.status_code}"
    assert "application/pdf" in (resposta.headers.get("Content-Type") or ""), (
        "a resposta não é um PDF")
    leitor = PdfReader(io.BytesIO(resposta.get_data()))
    assert len(leitor.pages) >= 1, "PDF sem páginas"
    return "\n".join((p.extract_text() or "") for p in leitor.pages)


@pytest.fixture(scope="module")
def medico(app, ids_reais):
    return autenticar(app, PERFIS["medico"][1])


@pytest.fixture(scope="module")
def documentos(app, medico, ids_reais):
    """Texto de cada PDF clínico, gerado uma vez."""
    def _id(tabela):
        return ids_reais.get(tabela) or 1

    saida = {}
    saida["prontuario"] = _texto_do_pdf(
        medico.get(f"/pdf/prontuario/{_id('prontuarios')}"))
    saida["receituario"] = _texto_do_pdf(
        medico.get(f"/pdf/receituario/{_id('prontuarios')}"))
    saida["encaminhamento"] = _texto_do_pdf(
        medico.get(f"/pdf/encaminhamento/{_id('encaminhamentos')}"))
    saida["alta"] = _texto_do_pdf(
        medico.get(f"/pdf/alta/{_id('internacoes')}"))

    url = f"/pdf/atestado/{_id('pacientes')}"
    pagina = medico.get(url).get_data(as_text=True)
    achado = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', pagina)
    saida["atestado"] = _texto_do_pdf(medico.post(url, data={
        "csrf_token": achado.group(1) if achado else "",
        "dias": "3", "cid": "j11", "observacao": "repouso domiciliar",
    }))
    return saida


@pytest.mark.parametrize("documento", [
    "prontuario", "receituario", "encaminhamento", "alta", "atestado",
])
def test_pdf_traz_o_nome_do_paciente(app, documentos, ids_reais, documento):
    """Documento clínico sem o nome de quem ele trata não vale nada."""
    from models.paciente import Paciente

    with app.app_context():
        nome = Paciente.query.get(ids_reais.get("pacientes") or 1).nome_exibicao

    assert nome in documentos[documento], (
        f"o {documento} não traz o nome do paciente ({nome!r})")


@pytest.mark.parametrize("documento", [
    "receituario", "encaminhamento", "atestado",
])
def test_data_por_extenso_sai_em_portugues(documentos, documento):
    """Documento oficial do SUS datado de "06 de August de 2026" é defeito."""
    texto = documentos[documento]
    achados = [m for m in MESES_EN if re.search(rf"de {m} de", texto)]
    assert not achados, (
        f"o {documento} traz o mês em inglês: {achados}. "
        "Use utils.datas.por_extenso, não strftime('%B')."
    )
    assert any(f"de {m} de" in texto for m in MESES), (
        f"o {documento} não traz nenhuma data por extenso em português")


@pytest.mark.parametrize("documento", [
    "prontuario", "receituario", "encaminhamento", "alta", "atestado",
])
def test_pdf_nao_tem_glifo_quebrado(documentos, documento):
    """Caractere fora do WinAnsi vira quadrado preto na folha impressa."""
    texto = documentos[documento]
    for proibido in ("⚠", "₂", "�", "■"):
        assert proibido not in texto, (
            f"o {documento} contém U+{ord(proibido):04X}, que as fontes padrão "
            "do reportlab não têm e imprimem como quadrado preto"
        )


def test_sumario_de_alta_nao_informa_permanencia_negativa(documentos):
    """`timedelta.days` trunca para baixo: alta com hora anterior à entrada
    devolvia -1, e o mesmo valor entra no `permanencia_media` dos relatórios."""
    achado = re.search(r"(-?\d+)\s*dias", documentos["alta"])
    assert achado, "o sumário de alta não informa os dias de internação"
    assert int(achado.group(1)) >= 0, (
        f"sumário de alta com permanência negativa: {achado.group(0)!r}")


def test_alergias_aparecem_no_sumario_de_alta(app, documentos, ids_reais):
    """A alergia é o dado do sumário que mais custa caro se sumir."""
    from models.paciente import Paciente

    with app.app_context():
        alergias = Paciente.query.get(ids_reais.get("pacientes") or 1).alergias

    if not alergias:
        pytest.skip("paciente semeado sem alergia registrada")
    assert alergias in documentos["alta"], "a alergia não saiu no sumário de alta"
    assert "ALERGIAS" in documentos["alta"], "sumiu o rótulo de alergias"
