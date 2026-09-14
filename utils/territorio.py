# -*- coding: utf-8 -*-
"""Concessão de alcance territorial: quem pode dar qual escopo, e até onde.

O escopo territorial (`nivel_acesso` + o campo correspondente) é o controle
central deste sistema: é ele que o Row-Level Security lê para decidir o que cada
usuário enxerga. Até aqui ele só existia no banco — nenhuma tela o editava, e
conceder alcance estadual exigia `UPDATE` manual. Abrir esse campo numa tela é
abrir uma porta, e este módulo é a fechadura.

**O risco que ele fecha.** Sem regra, um administrador de unidade que pode criar
usuários criaria um usuário com `nivel_acesso = 'ESTADO'`, entraria com ele e
leria o estado inteiro — saindo do próprio isolamento pela porta de gestão de
contas. É o mesmo argumento que `utils.rbac.perfis_atribuiveis` já usa para não
deixar ninguém conceder `SuperAdmin`, aplicado à outra metade da autorização.

**A regra é uma só, e não precisa de tabela de precedência**: o território
concedido tem de estar DENTRO do território de quem concede. Repare que isso já
resolve a ordem entre os níveis, sem que ela seja escrita em lugar nenhum — um
escopo de estado não está dentro de uma regional porque um estado não tem
regional a comparar, e a comparação falha sozinha. Escrever a ordem à mão seria
uma segunda fonte de verdade, que envelheceria em silêncio.

**Falha fechada, como no resto do sistema.** Quando o território do alvo não é
derivável — unidade sem município, regional sem UF —, a concessão é recusada em
vez de permitida. Dado faltando não é autorização.

`SISTEMA` não aparece aqui de propósito: `utils.rls.escopo_do_usuario` recusa
`SISTEMA` vindo do cadastro, porque é escopo de processo interno (CLI, migration,
backup) e não de gente. Oferecê-lo na tela criaria um valor que a tela promete e
o banco ignora.
"""
from models.municipio import uf_do_codigo
from utils.rls import CAMPO_DO_NIVEL

# A ordem é de apresentação, do mais restrito ao mais amplo. Ela NÃO decide
# nada: quem decide é `contido`.
NIVEIS_ATRIBUIVEIS = ("UNIDADE", "MUNICIPIO", "REGIONAL", "ESTADO")

# O rótulo diz o que o nível FAZ, não como se chama. "MUNICIPIO" não informa
# nada a quem cadastra; "enxerga todas as unidades do município" informa.
ROTULOS = {
    "UNIDADE": "Unidade — só a unidade de lotação",
    "MUNICIPIO": "Município — todas as unidades do município",
    "REGIONAL": "Regional de saúde — todas as unidades da regional",
    "ESTADO": "Estado — todas as unidades da UF",
}
# `SISTEMA` NÃO tem rótulo aqui, e a ausência é deliberada: rótulo pronto para
# um nível que este módulo proíbe oferecer é um convite a oferecê-lo.

# Perfil que atravessa o isolamento pelo próprio perfil não tem escopo a
# guardar. Zerar os quatro campos é melhor do que deixá-los preenchidos: valor
# guardado que nada lê é valor que volta a valer no dia em que alguém rebaixa o
# perfil, sem que ninguém tenha revisto o alcance.
SEM_TERRITORIO = {"nivel_acesso": "UNIDADE", "unidade_id": None,
                  "municipio_ibge": None, "regional_id": None, "uf": None}


# --------------------------------------------------------- territórios
# Cada objeto é reduzido às quatro coordenadas que o escopo conhece. O que não
# se sabe fica `None`, e `contido` trata `None` como "não posso afirmar" — que
# é recusa, não liberação.

def territorio_da_unidade(unidade):
    """A UF vem do código IBGE, não da coluna `uf` da unidade.

    `unidades_saude.uf` é texto digitado; o código IBGE carrega a UF nos dois
    primeiros dígitos e não admite divergência. Quando não há código, aceita-se
    a coluna — mas só então.
    """
    if unidade is None:
        return None
    return {
        "unidade_id": unidade.id,
        "municipio_ibge": unidade.municipio_ibge,
        "regional_id": unidade.regional_id,
        "uf": uf_do_codigo(unidade.municipio_ibge)
              or (unidade.uf or "").strip().upper() or None,
    }


def territorio_do_municipio(municipio):
    if municipio is None:
        return None
    return {
        "unidade_id": None,
        "municipio_ibge": municipio.codigo_ibge,
        "regional_id": municipio.regional_id,
        "uf": municipio.uf,
    }


def territorio_da_regional(regional):
    if regional is None:
        return None
    return {
        "unidade_id": None,
        "municipio_ibge": None,
        "regional_id": regional.id,
        "uf": (regional.uf or "").strip().upper() or None,
    }


def territorio_da_uf(uf):
    uf = (uf or "").strip().upper()
    if not uf:
        return None
    return {"unidade_id": None, "municipio_ibge": None, "regional_id": None,
            "uf": uf}


def territorio_do_usuario(usuario):
    """O território que um cadastro JÁ alcança — pelo nível dele, não pela lotação.

    Nasceu de um furo na primeira versão desta tela. A edição comparava só a
    unidade de lotação (`if user.unidade_id and not contido(...)`), então quem
    **não tem lotação** escapava da verificação inteira — e gestor estadual é
    exatamente o caso: alcance de UF, unidade nenhuma. Para o administrador de
    uma unidade bastava abrir esse cadastro e definir uma senha nova.

    Devolve `None` quando o nível não tem o campo que ele exige. `contido` lê
    isso como recusa, que é o certo: cadastro cujo alcance não se sabe medir só
    pode ser tocado por quem opera a plataforma.
    """
    from utils.rbac import SUPER_ADMIN, _normalizar

    if _normalizar(getattr(usuario, "perfil", None)) == SUPER_ADMIN:
        # Atravessa o isolamento pelo perfil: não há território que o contenha.
        return None

    nivel = (getattr(usuario, "nivel_acesso", None) or "UNIDADE").upper()
    if nivel not in NIVEIS_ATRIBUIVEIS:
        nivel = "UNIDADE"   # inclui o `SISTEMA` que o RLS já rebaixa

    if nivel == "UNIDADE":
        return territorio_da_unidade(getattr(usuario, "unidade", None))
    if nivel == "MUNICIPIO":
        codigo = getattr(usuario, "municipio_ibge", None)
        if not codigo:
            return None
        return {"unidade_id": None, "municipio_ibge": codigo,
                "regional_id": None, "uf": uf_do_codigo(codigo)}
    if nivel == "REGIONAL":
        rid = getattr(usuario, "regional_id", None)
        if rid is None:
            return None
        return {"unidade_id": None, "municipio_ibge": None,
                "regional_id": rid, "uf": None}
    return territorio_da_uf(getattr(usuario, "uf", None))


def contido(territorio, escopo):
    """O território cabe dentro do escopo de quem concede?

    `escopo` é o que `utils.rls.escopo_do_usuario` devolve — a MESMA função que
    o RLS usa para montar a consulta. Se a tela lesse o escopo de outro jeito,
    ela autorizaria uma concessão que o banco depois trataria de outra maneira,
    e a divergência só apareceria como comportamento estranho meses depois.
    """
    if escopo.get("nivel") == "SISTEMA":
        return True
    if not territorio:
        return False

    campo = CAMPO_DO_NIVEL.get(escopo.get("nivel"))
    if not campo:
        return False

    meu = escopo.get(campo)
    dele = territorio.get(campo)
    if meu is None or dele is None:
        # Um dos lados não tem a coordenada que este nível compara. Não é
        # empate — é impossibilidade de afirmar, e o sistema falha fechado.
        return False
    return str(meu) == str(dele)


# ------------------------------------------------------------- oferta
def _consultas():
    from extensions import db
    from models.municipio import Municipio
    from models.regional import Regional
    from models.unidade_saude import UnidadeSaude

    return db, Municipio, Regional, UnidadeSaude


def opcoes(escopo):
    """O que a tela pode oferecer a quem tem este escopo.

    Duas decisões que a tela precisa explicar ao usuário:

    1. **Só território com unidade cadastrada.** Escopo sobre município onde a
       rede não tem unidade nenhuma não alcança registro algum — seria conceder
       um acesso que não abre nada e deixar quem concedeu achando que abriu. A
       lista fica limitada pela pegada da rede, não pelos 5.570 municípios do
       país, e por isso não cresce com a importação do IBGE.
    2. **Filtrada pelo próprio escopo.** O backend recusaria a concessão de
       qualquer forma; oferecer para depois recusar é desenhar uma armadilha.
    """
    db, Municipio, Regional, UnidadeSaude = _consultas()

    unidades = (UnidadeSaude.query.filter_by(ativo=True)
                .order_by(UnidadeSaude.nome).all())
    unidades = [u for u in unidades
                if contido(territorio_da_unidade(u), escopo)]

    municipios = (
        db.session.query(Municipio)
        .join(UnidadeSaude, UnidadeSaude.municipio_ibge == Municipio.codigo_ibge)
        .distinct().order_by(Municipio.uf, Municipio.nome).all()
    )
    municipios = [m for m in municipios
                  if contido(territorio_do_municipio(m), escopo)]

    regionais = (
        db.session.query(Regional)
        .join(UnidadeSaude, UnidadeSaude.regional_id == Regional.id)
        .distinct().order_by(Regional.uf, Regional.nome).all()
    )
    regionais = [r for r in regionais
                 if contido(territorio_da_regional(r), escopo)]

    ufs = sorted({m.uf for m in municipios if m.uf})
    ufs = [u for u in ufs if contido(territorio_da_uf(u), escopo)]

    disponivel = {
        "UNIDADE": bool(unidades),
        "MUNICIPIO": bool(municipios),
        "REGIONAL": bool(regionais),
        "ESTADO": bool(ufs),
    }
    niveis = [(n, ROTULOS[n]) for n in NIVEIS_ATRIBUIVEIS if disponivel[n]]

    return {"niveis": niveis, "unidades": unidades, "municipios": municipios,
            "regionais": regionais, "ufs": ufs}


# ------------------------------------------------------------ validação
def resolver(nivel, formulario, escopo):
    """Traduz o formulário nos campos do usuário, ou explica por que não dá.

    Devolve `(campos, erro)`. `campos` traz os QUATRO campos territoriais, com
    os que não pertencem ao nível escolhido zerados — deixar valor antigo de
    outro nível guardado faz com que uma simples troca de nível reative um
    escopo que ninguém reviu. O valor fica invisível no banco até o dia em que
    volta a valer.
    """
    _, Municipio, Regional, UnidadeSaude = _consultas()

    nivel = (nivel or "").strip().upper()
    if nivel not in NIVEIS_ATRIBUIVEIS:
        return None, ("Nível de acesso inválido. Os níveis possíveis são: "
                      + ", ".join(NIVEIS_ATRIBUIVEIS) + ".")

    campos = {"nivel_acesso": nivel, "unidade_id": None,
              "municipio_ibge": None, "regional_id": None, "uf": None}

    # A unidade de lotação é onde o usuário ESCREVE, e é exigida em todos os
    # níveis: um gestor estadual sem lotação registraria eventos clínicos sem
    # unidade, e registro com `unidade_id` nulo some de toda tela sob RLS.
    # `ativo` também é conferido AQUI, e não só na lista que a tela oferece:
    # esconder a opção nunca foi a defesa. Lotar alguém numa unidade desativada
    # produz um cadastro que não registra nada em lugar nenhum.
    unidade_id = (formulario.get("unidade_id") or "").strip()
    unidade = UnidadeSaude.query.get(int(unidade_id)) if unidade_id.isdigit() else None
    if unidade is not None and not unidade.ativo:
        return None, (f"A unidade {unidade.nome} está desativada. Escolha uma "
                      "unidade ativa para lotar o usuário.")
    if unidade is None:
        return None, ("Selecione a unidade de lotação: sem ela o usuário não "
                      "tem onde registrar atendimento, e o que ele registrar "
                      "fica invisível para todo mundo.")
    if not contido(territorio_da_unidade(unidade), escopo):
        return None, (f"A unidade {unidade.nome} está fora do seu território. "
                      "Você só pode lotar usuários onde o seu próprio acesso "
                      "alcança.")
    campos["unidade_id"] = unidade.id

    if nivel == "UNIDADE":
        return campos, None

    if nivel == "MUNICIPIO":
        codigo = (formulario.get("municipio_ibge") or "").strip()
        municipio = Municipio.query.get(codigo) if codigo else None
        if municipio is None:
            return None, "Selecione o município do escopo."
        if not contido(territorio_do_municipio(municipio), escopo):
            return None, (f"{municipio.nome}/{municipio.uf} está fora do seu "
                          "território.")
        campos["municipio_ibge"] = municipio.codigo_ibge
        return campos, None

    if nivel == "REGIONAL":
        bruto = (formulario.get("regional_id") or "").strip()
        regional = Regional.query.get(int(bruto)) if bruto.isdigit() else None
        if regional is None:
            return None, "Selecione a regional de saúde do escopo."
        if not contido(territorio_da_regional(regional), escopo):
            return None, f"A regional {regional.nome} está fora do seu território."
        campos["regional_id"] = regional.id
        return campos, None

    uf = (formulario.get("uf") or "").strip().upper()
    if len(uf) != 2:
        return None, "Selecione a UF do escopo."
    if not contido(territorio_da_uf(uf), escopo):
        return None, f"A UF {uf} está fora do seu território."
    campos["uf"] = uf
    return campos, None


def descrever(usuario):
    """O escopo de um usuário em uma linha, para a listagem.

    Existe porque a tela de administração mostrava a unidade de lotação e nada
    mais — e alcance estadual era indistinguível de alcance de unidade na
    listagem, justamente o que mais importa saber de relance.
    """
    from utils.rbac import SUPER_ADMIN, _normalizar

    if _normalizar(getattr(usuario, "perfil", None)) == SUPER_ADMIN:
        return "Plataforma (todo o território)"

    nivel = (getattr(usuario, "nivel_acesso", None) or "UNIDADE").upper()
    if nivel not in NIVEIS_ATRIBUIVEIS:
        # Inclui o `SISTEMA` que possa ter sido gravado antes desta tela
        # existir: `escopo_do_usuario` o rebaixa para UNIDADE, e a listagem
        # precisa mostrar o que VALE, não o que está guardado.
        nivel = "UNIDADE"

    if nivel == "UNIDADE":
        return usuario.unidade.nome if usuario.unidade else "Unidade não definida"
    if nivel == "MUNICIPIO":
        from models.municipio import Municipio

        m = Municipio.query.get(usuario.municipio_ibge) if usuario.municipio_ibge else None
        return f"Município: {m.nome}/{m.uf}" if m else "Município não definido"
    if nivel == "REGIONAL":
        from models.regional import Regional

        r = Regional.query.get(usuario.regional_id) if usuario.regional_id else None
        return f"Regional: {r.nome}" if r else "Regional não definida"
    return f"Estado: {usuario.uf}" if usuario.uf else "UF não definida"
