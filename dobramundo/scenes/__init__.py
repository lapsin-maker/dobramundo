"""Telas do jogo e o registro que as cria pelo nome.

As cenas apontam umas para as outras (a vila abre o mapa, o resultado volta à
vila...). Em vez de cada uma importar as outras, todas pedem a troca pelo nome:
``scene.goto("vila")``. O registro é montado no fim deste módulo, depois de
``make_scene`` existir, porque algumas cenas também o usam.
"""

from __future__ import annotations

from typing import Callable, Dict

SCENES: Dict[str, Callable] = {}


def make_scene(app, name: str, *args, **kwargs):
    """Cria a cena registrada com esse nome (args vão para o construtor dela)."""
    return SCENES[name](app, *args, **kwargs)


from .about import AboutScene  # noqa: E402
from .calibration import CalibrationScene  # noqa: E402
from .consent import ConsentScene  # noqa: E402
from .flight import FlightScene  # noqa: E402
from .hangar import HangarScene  # noqa: E402
from .intro import IntroScene  # noqa: E402
from .map import MapScene  # noqa: E402
from .options import OptionsScene  # noqa: E402
from .pilot import PilotScene  # noqa: E402
from .projection import ProjectionScene  # noqa: E402
from .result import ResultScene  # noqa: E402
from .upgrades import UpgradesScene  # noqa: E402
from .village import VillageScene  # noqa: E402

SCENES.update(
    {
        "abertura": IntroScene,
        "aviso": ConsentScene,
        "calibracao": CalibrationScene,
        "vila": VillageScene,
        "mapa": MapScene,
        "voo": FlightScene,
        "resultado": ResultScene,
        "hangar": HangarScene,
        "piloto": PilotScene,
        "melhorias": UpgradesScene,
        "opcoes": OptionsScene,
        "projecao": ProjectionScene,
        "sobre": AboutScene,
    }
)
