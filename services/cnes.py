# -*- coding: utf-8 -*-
"""A rede de unidades, vinda do CNES real — pela API do Ministério da Saúde.

`https://apidadosabertos.saude.gov.br` é a API de dados abertos do DEMAS/MS.
Diferente dos microdados do DATASUS, que vêm em `.DBC` e exigem descompressor
binário (ver `docs/datasus_levantamento.md`), esta entrega JSON por HTTPS e
aceita filtro por município — o que a torna utilizável sem ferramenta externa.

**O que vem daqui é a REDE, não os pacientes.** A distinção é a que decide se a
demonstração é honesta:

- estabelecimento, código CNES, tipo e município são **fatos públicos** sobre
  serviços de saúde, e trazê-los faz a demonstração parar de inventar hospital;
- os microdados de internação (SIH) são **registros individuais de internações
  reais de pessoas reais**. Semeá-los como pacientes desta rede faria o sistema
  apresentar a internação de alguém como registro seu, e poria dado de saúde
  passível de religação num banco de demonstração que se apaga e se refaz. O
  paciente sintético continua sintético, e `seed-volume` continua marcando tudo
  com `SINTETICO`.

**A contagem de leitos não vem daqui, e é importante dizer por quê.** A API
publica `assistencia-a-saude/hospitais-e-leitos` com leitos por hospital — mas
esse conjunto **não traz o código CNES**, e o `codigo_ibge_do_municipio` veio
preenchido em 3 de 1000 registros na amostra conferida. Os únicos elos seriam o
nome do hospital e o do município, em texto livre. É exatamente o que a seção de
território do `AGENTS.md` abre dizendo que não agrega — e a amostra traz
"FEIRA DE SANTANA", o exemplo citado lá. Juntar por nome construiria a
demonstração sobre o defeito que a monografia critica.

O que este módulo usa do CNES para decidir leito são os **atributos do próprio
estabelecimento**, que vêm chaveados por CNES e são confiáveis:
`estabelecimento_possui_atendimento_hospitalar` e os indicadores de centro
cirúrgico, obstétrico e neonatal. Eles dizem QUEM interna e QUE setores existem.
A quantidade por setor permanece parâmetro declarado de demonstração — e está
declarada em `database/seeds.SETORES_DO_HOSPITAL`, não escondida aqui.

**Nada disto é consultado durante uma requisição**, pela mesma razão do
`services/ibge.py`: a carga é por comando e o resultado fica no banco.
"""
import requests

BASE = "https://apidadosabertos.saude.gov.br"
TEMPO_LIMITE = 60
POR_PAGINA = 1000

# Limites do laço de paginação. Ver o comentário em `estabelecimentos`: existem
# porque a API não sinaliza fim de lista de forma confiável, e laço sem fim num
# comando operacional é pior do que trazer menos unidades.
PAGINAS_MAXIMAS = 60
PAGINAS_SEM_NOVIDADE = 5

# Código CNES de tipo de unidade -> o vocabulário que este sistema usa em
# `unidades_saude.tipo`. A tabela oficial tem mais de 40 tipos; aqui só os que
# a aplicação sabe representar. Tipo não mapeado é IGNORADO na importação, e
# não convertido em "Hospital" por descuido: unidade móvel, farmácia e central
# de regulação não atendem paciente na tela deste sistema.
TIPOS = {
    1: "UBS",                  # Posto de saúde
    2: "UBS",                  # Centro de saúde / unidade básica
    4: "Clínica Pública",      # Policlínica
    5: "Hospital",             # Hospital geral
    7: "Hospital",             # Hospital especializado
    15: "Hospital",            # Unidade mista
    20: "Pronto Socorro",      # Pronto socorro geral
    21: "Pronto Socorro",      # Pronto socorro especializado
    36: "Clínica Pública",     # Clínica / centro de especialidade
    62: "Hospital",            # Hospital/dia
}


class ErroCNES(RuntimeError):
    """Falha ao consultar a API. Quem chama decide se aborta ou segue."""


def _codigo_de_seis(codigo_ibge):
    """O CNES filtra por município SEM o dígito verificador.

    O sistema guarda o código IBGE de sete dígitos, que é o que o SUS usa em
    SIA/SIH e o que a tabela `municipios` tem como chave. A API quer os seis
    primeiros. Mandar os sete devolve lista vazia — sem erro, o que é pior: a
    importação diria "nenhuma unidade encontrada" e ninguém saberia por quê.
    """
    codigo = "".join(c for c in str(codigo_ibge or "") if c.isdigit())
    if len(codigo) not in (6, 7):
        raise ErroCNES(f"código IBGE inválido: {codigo_ibge!r}")
    return codigo[:6]


def _pagina(caminho, parametros):
    try:
        resposta = requests.get(f"{BASE}{caminho}", params=parametros,
                                timeout=TEMPO_LIMITE)
    except requests.RequestException as erro:
        raise ErroCNES(f"não consegui falar com a API do CNES: {erro}") from erro

    if resposta.status_code != 200:
        raise ErroCNES(
            f"a API do CNES respondeu {resposta.status_code} em {caminho}")
    try:
        corpo = resposta.json()
    except ValueError as erro:
        raise ErroCNES("a API do CNES devolveu algo que não é JSON") from erro

    # A resposta é um objeto com UMA lista dentro, e o nome da chave muda de
    # endpoint para endpoint ("estabelecimentos", "hospitais_leitos", ...).
    for valor in corpo.values():
        if isinstance(valor, list):
            return valor
    raise ErroCNES(f"resposta sem lista de resultados em {caminho}")


def _ativo(estabelecimento):
    """Estabelecimento desabilitado tem motivo de desabilitação preenchido."""
    return not estabelecimento.get("codigo_motivo_desabilitacao_estabelecimento")


def _nome(estabelecimento):
    """O nome de fantasia é o que a população conhece; a razão social é o dono.

    "MUNICIPIO DE BOM JESUS DA LAPA" é razão social de dezenas de unidades da
    mesma cidade — usá-la faria a rede inteira aparecer com o mesmo nome.
    """
    fantasia = (estabelecimento.get("nome_fantasia") or "").strip()
    return fantasia or (estabelecimento.get("nome_razao_social") or "").strip()


def estabelecimentos(codigo_ibge, tipos=None):
    """Unidades reais de um município, já traduzidas para o vocabulário local.

    `tipos` restringe aos códigos CNES desejados; o padrão é tudo que `TIPOS`
    sabe representar. Devolve lista de dicionários prontos para virar
    `UnidadeSaude`, com `codigo_cnes` como chave natural.
    """
    aceitos = set(tipos) if tipos else set(TIPOS)
    municipio = _codigo_de_seis(codigo_ibge)
    codigo_sete = str(codigo_ibge).strip()

    # A paginação desta API é instável, e isso foi medido antes de programar
    # em volta: `limit` é ignorado (a página vem com 20 registros, peça-se o que
    # pedir) e páginas consecutivas se sobrepõem — 80 registros de quatro
    # páginas trouxeram 23 códigos distintos. Daí as duas defesas: deduplicar
    # por `codigo_cnes`, que é a chave real, e parar quando várias páginas
    # seguidas não trazem nada de novo. Sem a segunda, o laço não termina.
    achados, vistos, deslocamento, estéreis = [], set(), 0, 0
    while deslocamento < PAGINAS_MAXIMAS and estéreis < PAGINAS_SEM_NOVIDADE:
        pagina = _pagina("/cnes/estabelecimentos",
                         {"codigo_municipio": municipio,
                          "limit": POR_PAGINA, "offset": deslocamento})
        deslocamento += 1
        if not pagina:
            break
        antes = len(vistos)
        for e in pagina:
            codigo = str(e.get("codigo_cnes") or "").strip()
            if not codigo or codigo in vistos:
                continue
            vistos.add(codigo)
            tipo_cnes = e.get("codigo_tipo_unidade")
            try:
                tipo_cnes = int(tipo_cnes)
            except (TypeError, ValueError):
                continue
            if tipo_cnes not in aceitos or not _ativo(e):
                continue
            achados.append({
                "codigo_cnes": codigo,
                "nome": _nome(e),
                "tipo": TIPOS[tipo_cnes],
                "municipio_ibge": codigo_sete if len(codigo_sete) == 7 else None,
                "bairro": (e.get("bairro_estabelecimento") or "").strip() or None,
                # Os indicadores que decidem leito. Vêm como 0/1 ou "SIM"/"NAO".
                "interna": _sim(e.get("estabelecimento_possui_atendimento_hospitalar")),
                "centro_cirurgico": _sim(e.get("estabelecimento_possui_centro_cirurgico")),
                "centro_obstetrico": _sim(e.get("estabelecimento_possui_centro_obstetrico")),
                "centro_neonatal": _sim(e.get("estabelecimento_possui_centro_neonatal")),
            })
        estéreis = 0 if len(vistos) > antes else estéreis + 1

    return [e for e in achados if e["nome"]]


def _sim(valor):
    """A API mistura 0/1 e "SIM"/"NAO" no mesmo conjunto de indicadores."""
    if isinstance(valor, str):
        return valor.strip().upper() in ("SIM", "S", "1", "TRUE")
    return bool(valor)
