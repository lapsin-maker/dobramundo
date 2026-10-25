"""Objetos do mundo e caixas de colisão."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..config import LANE_WIDTH
from ..content.items import ObstacleSpec


@dataclass
class Entity:
    z: float
    lane: int
    kind: str  # waste | low | gate | tower | shield | magnet | repair
    y: float = 0.0  # altura (resíduos e power-ups flutuam)
    sprite: str = ""  # modelo usado no desenho (resíduo: tipo)
    spec: Optional[ObstacleSpec] = None  # obstáculos: medidas de colisão
    solar: bool = False  # obstáculo do estágio solarpunk (alerta no chão)
    collected: bool = False
    hit: bool = False  # obstáculo que acertou o avião (não conta como desviado)
    passed: bool = False  # já passou pelo avião (contado nas metas)
    focused: bool = False  # já abriu um momento de foco (não abre outro)
    dodged: bool = False  # desviado no momento de foco: não bate mais
    lesson: str = ""  # objeto da abertura didática (tipo apresentado na legenda)
    announced: bool = False  # a legenda da lição já apareceu

    @property
    def x(self) -> float:
        return self.lane * LANE_WIDTH


@dataclass
class Beam:
    x: float
    z: float
    color: tuple = (255, 245, 157)
    ttl: float = 0.18


@dataclass
class FloatingText:
    text: str
    x: float
    y: float
    color: tuple = (255, 245, 157)
    ttl: float = 0.9


@dataclass(frozen=True)
class Hitbox:
    """Caixa de colisão no mundo 3D (x lateral, y altura, z profundidade)."""

    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float

    def intersects(self, other: Hitbox) -> bool:
        return (
            self.x_min <= other.x_max
            and self.x_max >= other.x_min
            and self.y_min <= other.y_max
            and self.y_max >= other.y_min
            and self.z_min <= other.z_max
            and self.z_max >= other.z_min
        )


def entity_hitbox(entity: Entity) -> Hitbox:
    x = entity.x
    if entity.spec is not None:
        spec = entity.spec
        return Hitbox(x - spec.width / 2, x + spec.width / 2, spec.y_min, spec.y_max, entity.z - 16.0, entity.z + 16.0)
    r = 30.0 if entity.kind == "waste" else 28.0
    return Hitbox(x - r, x + r, entity.y - r, entity.y + r, entity.z - 18.0, entity.z + 18.0)
