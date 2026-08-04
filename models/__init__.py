"""Bootstrap do pacote de models.

Importa cada model e re-exporta as classes num namespace único, para que
`from models import Paciente` funcione.

Antes isso era feito com `try/except Exception: continue`, o que engolia erros de
import de verdade: o mapa apontava para o módulo ``"regionais"`` quando o arquivo
é ``regional.py``, então ``Regional`` nunca era exportado e ninguém percebia.
Também faltavam no mapa 6 módulos (cirurgia, faturamento, medicamento,
prescricao_hospitalar, pronto_socorro, agenda_evento). Agora um módulo declarado
que não importa é erro explícito.
"""
from importlib import import_module

# módulo -> classes esperadas
_MODEL_IMPORTS = {
    "agenda_evento": ["AgendaEvento"],
    "agendamento": ["Agendamento"],
    "atendimento": ["Atendimento"],
    "audit_log": ["AuditLog"],
    "catalogo_exame": ["CatalogoExame"],
    "catalogo_vacina": ["CatalogoVacina"],
    "cirurgia": ["SalaCirurgica", "Cirurgia"],
    "configuracao": ["Configuracao"],
    "duplicata": ["CandidatoDuplicata"],
    "encaminhamento": ["Encaminhamento"],
    "estoque": ["ItemEstoque", "MovEstoque"],
    "exame": ["TipoExame", "ExameSolicitado"],
    "faturamento": ["AIH", "APAC"],
    "internacao": ["Setor", "Leito", "Internacao", "EvolucaoInternacao"],
    "lgpd": ["ConsentimentoLgpd", "DocumentoAssinado", "EnvioRnds"],
    "medicamento": ["Medicamento", "Prescricao", "ItemPrescricao"],
    "medico": ["Medico"],
    "municipio": ["Municipio"],
    "notificacao": ["NotificacaoCompulsoria"],
    "paciente": ["Paciente"],
    "prescricao_hospitalar": [
        "PrescricaoHospitalar",
        "ItemPrescricaoHosp",
        "AdministracaoMed",
    ],
    "pronto_socorro": ["AtendimentoPS"],
    "prontuario": ["Prontuario"],
    "regional": ["Regional"],
    "triagem": ["Triagem"],
    "unidade_saude": ["UnidadeSaude"],
    "user": ["User"],
    "vacina": ["Vacina", "VacinaAplicada"],
}

__all__ = []

for _modulo, _classes in _MODEL_IMPORTS.items():
    _mod = import_module(f"{__name__}.{_modulo}")
    for _cls in _classes:
        if not hasattr(_mod, _cls):
            raise ImportError(f"models.{_modulo} não define {_cls}")
        globals()[_cls] = getattr(_mod, _cls)
        __all__.append(_cls)

# Compatibilidade legada: relationship("Unidade") e models/unidade.py.
Unidade = globals()["UnidadeSaude"]
__all__.append("Unidade")

del import_module, _modulo, _classes, _mod, _cls
