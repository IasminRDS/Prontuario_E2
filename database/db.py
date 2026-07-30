"""Compatibilidade de import.

Historicamente este módulo criava uma SEGUNDA instância de ``SQLAlchemy()``,
enquanto os models faziam ``from extensions import db``. Resultado: os 20
blueprints que importavam daqui escreviam numa instância nunca inicializada e
toda mutação falhava com "not registered with this SQLAlchemy instance".

Agora ele só re-exporta as extensões reais. Prefira importar de ``extensions``
em código novo; este módulo existe para não quebrar os imports antigos.
"""

from extensions import db, login_manager, migrate

__all__ = ["db", "login_manager", "migrate"]
