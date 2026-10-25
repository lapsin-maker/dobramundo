"""Registro de avisos e erros em dobramundo.log (pasta de dados do jogador).

Asset corrompido, som que não carrega, câmera que falha ou perfil que não grava
não interrompem o jogo (ele segue com uma alternativa), mas ficam anotados aqui
para o supervisor ou a equipe investigarem.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

LOGGER_NAME = "dobramundo"
MAX_BYTES = 256 * 1024

log = logging.getLogger(LOGGER_NAME)


def setup_logging() -> None:
    """Liga o arquivo de log (uma vez por execução; sem pasta gravável, só o console)."""
    if log.handlers:
        return
    from .paths import user_data_dir

    log.setLevel(logging.INFO)
    try:
        handler: logging.Handler = RotatingFileHandler(
            str(user_data_dir() / "dobramundo.log"), maxBytes=MAX_BYTES, backupCount=1, encoding="utf-8"
        )
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(handler)
