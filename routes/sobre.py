# -*- coding: utf-8 -*-
"""Sobre o sistema — versão, recursos e conformidade.

Equivalente à página `/sobre` do frontend Next. Serve também de mapa do site.
"""
from flask import Blueprint, current_app, render_template
from flask_login import login_required

from utils.nav import GRUPOS
from utils.rbac import TODAS_PERMISSOES

sobre_bp = Blueprint("sobre", __name__, url_prefix="/sobre")

CONFORMIDADE = (
    ("LGPD (Lei 13.709/2018)", "Trilha de auditoria de todo acesso a prontuário, "
     "registro de consentimento e verificação de integridade por hash-chain."),
    ("eMAG / WCAG 2.1 AA", "Skip-link, foco visível em todo controle, contraste "
     "verificado nos temas claro e escuro e VLibras."),
    ("Padrão Digital de Governo (DSGov)", "Barra gov.br, paleta institucional "
     "(#1351B4 / #FFCD07), tipografia e componentes do padrão."),
    ("FHIR R4 / RNDS", "Envio de Patient, Encounter e Observation à Rede "
     "Nacional de Dados em Saúde, por fila durável com reenvio."),
    ("Classificação de risco Manchester", "Cinco níveis com cores oficiais e "
     "tempo-alvo de atendimento."),
    ("Notificação compulsória (SINAN)", "Detecção automática de agravos a partir "
     "do CID-10 registrado no prontuário."),
)


@sobre_bp.get("/")
@login_required
def index():
    endpoints = set(current_app.view_functions.keys())
    return render_template(
        "sobre/index.html",
        grupos=GRUPOS,
        endpoints=endpoints,
        conformidade=CONFORMIDADE,
        total_permissoes=len(TODAS_PERMISSOES),
        total_rotas=len(list(current_app.url_map.iter_rules())),
        total_blueprints=len(current_app.blueprints),
    )
