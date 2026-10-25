"""Dados lidos pelo desenho; nenhuma importação das regras ou plataformas.

Objetos do jogo satisfazem estes Protocols estruturalmente. O desenho não
constrói partidas nem recalcula colisões: recebe seus limites já definidos.
Não copiar todo o mundo a cada quadro; os contratos descrevem uma leitura.
"""

from __future__ import annotations

from typing import Optional, Protocol, Sequence, Tuple

from ..content.biomes import Biome
from ..content.items import ObstacleSpec
from ..util import Color


class BoundsView(Protocol):
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float


class EntityView(Protocol):
    x: float
    y: float
    z: float
    kind: str
    sprite: str
    spec: Optional[ObstacleSpec]
    solar: bool
    collected: bool
    hit: bool
    dodged: bool

    def hitbox(self) -> BoundsView: ...


class ChallengeView(Protocol):
    key: str
    title: str
    preferred_obstacle: str
    decorations: Tuple[str, ...]


class WorldStateView(Protocol):
    biome: Biome
    distance: float
    visual: float
    entities: Sequence[EntityView]
    challenge_theme: Optional[ChallengeView]
    segments: Sequence[float]
    segment_base: int

    def segment_green(self, seg: int) -> float: ...
    def segment_solar(self, seg: int) -> float: ...
    def solar_share(self) -> float: ...
    def stage_flags(self) -> tuple: ...
    def visual_stage_pair(self) -> tuple: ...


class PlayerView(Protocol):
    x: float
    y: float
    vy: float
    cam_x: float
    roll: float
    maneuver: object

    def hitbox(self) -> BoundsView: ...
    def maneuver_pose(self) -> Optional[tuple]: ...


class BeamView(Protocol):
    x: float
    z: float
    color: Color
    ttl: float


class FloatingTextView(Protocol):
    x: float
    y: float
    text: str
    color: Color
    ttl: float


class FlightView(Protocol):
    world: WorldStateView
    player: PlayerView
    mode: str
    invulnerable_timer: float
    shield_timer: float
    magnet_timer: float
    beams: Sequence[BeamView]
    floating: Sequence[FloatingTextView]


class PlaneLook:
    """O que o jogador escolheu para o avião (modelo, pintura, piloto)."""

    def __init__(
        self, plane: str, color: str = "original", pattern: str = "jornal", pilot: Optional[dict] = None
    ) -> None:
        self.plane = plane
        self.color = color
        self.pattern = pattern
        self.pilot = pilot
