"""Resíduos coletáveis, power-ups e especificação dos obstáculos."""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Tuple

from ..util import Color, rgb


class WasteType(NamedTuple):
    """Resíduo que vira recurso na vila. Cores da coleta seletiva (CONAMA nº 275/2001)."""

    key: str
    name: str
    color: Color  # cor da lixeira, usada no HUD e no alto contraste
    sprite: str  # assets/waste_sprites/<sprite>.png


WASTE_TYPES: Tuple[WasteType, ...] = (
    WasteType("papel", "Papel", rgb("1e6fd9"), "papel"),
    WasteType("plastico", "Plástico", rgb("e53935"), "plastico"),
    WasteType("metal", "Metal", rgb("fbc02d"), "metal"),
    WasteType("vidro", "Vidro", rgb("2e9e44"), "vidro"),
)
WASTE_KEYS = tuple(w.key for w in WASTE_TYPES)
WASTE_BY_KEY: Dict[str, WasteType] = {w.key: w for w in WASTE_TYPES}

POWERUP_KINDS = ("shield", "magnet", "repair")
POWERUP_NAMES = {"shield": "Escudo", "magnet": "Ímã", "repair": "Reparo"}
POWERUP_COLORS = {"shield": rgb("40c4ff"), "magnet": rgb("e040fb"), "repair": rgb("69f0ae")}


class ObstacleSpec(NamedTuple):
    """Obstáculo: cada tipo pede uma manobra.

    low -> passe POR CIMA; gate -> passe POR BAIXO; tower -> desvie PARA O LADO.
    A colisão foi medida nos próprios sprites (alfa): low usa ~90% do topo visível,
    gate usa o vão livre medido no centro, tower usa a largura na metade da altura.
    """

    kind: str
    sprite: str
    visual_height: float  # altura do sprite no mundo
    width: float  # largura da colisão no mundo
    y_min: float  # faixa de altura que colide
    y_max: float


OBSTACLE_KINDS = ("low", "gate", "tower")
ObstacleTable = Dict[str, List[ObstacleSpec]]


def obstacle_table(*specs: ObstacleSpec) -> ObstacleTable:
    table: ObstacleTable = {kind: [] for kind in OBSTACLE_KINDS}
    for spec in specs:
        table[spec.kind].append(spec)
    return table


def low(sprite: str, visual: float, width: float, top: float) -> ObstacleSpec:
    return ObstacleSpec("low", sprite, visual, width, 0.0, top)


def gate(sprite: str, visual: float, width: float, clearance: float) -> ObstacleSpec:
    return ObstacleSpec("gate", sprite, visual, width, clearance, 400.0)


def tower(sprite: str, visual: float, width: float) -> ObstacleSpec:
    return ObstacleSpec("tower", sprite, visual, width, 0.0, 400.0)
