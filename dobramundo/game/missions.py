"""Metas curtas dentro do voo (GDD, seção 7: "metas curtas" e "retorno imediato").

Uma meta por vez, de 20 a 60 segundos cada: coletar resíduos de um tipo, desviar
de obstáculos na faixa do avião, passar por baixo de portais ou pegar power-ups.
Cumprir uma meta rende um pouco de transformação, recursos e pontos, e a próxima
começa em seguida. Os alvos são menores no Normal.
"""

from __future__ import annotations

import random
from typing import Dict, NamedTuple, Optional

from ..content.items import WASTE_BY_KEY, WASTE_KEYS

KINDS = ("coletar", "desviar", "portal", "powerup")
TARGETS: Dict[str, Dict[str, int]] = {
    "normal": {"coletar": 2, "desviar": 3, "portal": 2, "powerup": 1},
    "dificil": {"coletar": 6, "desviar": 6, "portal": 3, "powerup": 2},
}
FIRST_DELAY_S = 4.0  # a primeira meta aparece depois da decolagem
NEXT_DELAY_S = 2.5  # pausa curta entre uma meta e a próxima
BONUS_RESTORATION = 0.5  # transformação extra por meta cumprida
BONUS_RESOURCES = 6  # recursos extras (do tipo da meta, ou um tipo qualquer)
BONUS_POINTS = 50


class Mission(NamedTuple):
    kind: str
    target: int
    waste: Optional[str] = None  # meta "coletar": o tipo de resíduo pedido

    def text(self, progress: int) -> str:
        count = f"({progress}/{self.target})"
        if self.kind == "coletar":
            return f"Colete {self.target} de {WASTE_BY_KEY[self.waste].name.lower()} {count}"
        if self.kind == "desviar":
            return f"Desvie de {self.target} obstáculos {count}"
        if self.kind == "portal":
            return f"Passe por baixo de {self.target} portais {count}"
        return f"Pegue {self.target} power-up{'s' if self.target > 1 else ''} {count}"


class MissionTracker:
    """Sorteia e acompanha as metas de um voo (determinístico com a mesma semente)."""

    def __init__(self, mode: str, rng: Optional[random.Random] = None) -> None:
        self.targets = TARGETS.get(mode, TARGETS["normal"])
        self.rng = rng or random.Random()
        self.current: Optional[Mission] = None
        self.progress = 0
        self.completed = 0
        self.wait = FIRST_DELAY_S
        self.last_kind = ""

    def update(self, dt: float) -> None:
        if self.current is None:
            self.wait -= dt
            if self.wait <= 0:
                self.current = self.pick()
                self.progress = 0

    def pick(self) -> Mission:
        kind = self.rng.choice([k for k in KINDS if k != self.last_kind])  # não repete o tipo seguido
        self.last_kind = kind
        waste = self.rng.choice(WASTE_KEYS) if kind == "coletar" else None
        return Mission(kind, self.targets[kind], waste)

    def record(self, kind: str, waste: Optional[str] = None) -> Optional[Mission]:
        """Conta um acontecimento; devolve a meta quando ela acaba de ser cumprida."""
        mission = self.current
        if mission is None or mission.kind != kind or (mission.waste and mission.waste != waste):
            return None
        self.progress += 1
        if self.progress < mission.target:
            return None
        self.current = None
        self.completed += 1
        self.wait = NEXT_DELAY_S
        return mission

    @property
    def text(self) -> str:
        return self.current.text(self.progress) if self.current else ""
