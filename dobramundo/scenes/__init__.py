"""Telas do jogo e o registro que as cria pelo nome.

As cenas apontam umas para as outras (a vila abre o mapa, o resultado volta à
vila...). Em vez de cada uma importar as outras dentro de funções, todas pedem a
troca pelo nome: ``scene.goto("vila")``. O módulo de cada cena só é importado
quando ela é criada pela primeira vez.
"""

from __future__ import annotations

import importlib
from typing import Dict, Tuple

SCENES: Dict[str, Tuple[str, str]] = {
    "abertura": ("intro", "IntroScene"),
    "aviso": ("consent", "ConsentScene"),
    "calibracao": ("calibration", "CalibrationScene"),
    "vila": ("village", "VillageScene"),
    "mapa": ("map", "MapScene"),
    "voo": ("flight", "FlightScene"),
    "resultado": ("result", "ResultScene"),
    "hangar": ("hangar", "HangarScene"),
    "piloto": ("pilot", "PilotScene"),
    "melhorias": ("upgrades", "UpgradesScene"),
    "opcoes": ("options", "OptionsScene"),
    "sobre": ("about", "AboutScene"),
}


def make_scene(app, name: str, *args, **kwargs):
    """Cria a cena registrada com esse nome (args vão para o construtor dela)."""
    module_name, class_name = SCENES[name]
    module = importlib.import_module(f"{__name__}.{module_name}")
    return getattr(module, class_name)(app, *args, **kwargs)
