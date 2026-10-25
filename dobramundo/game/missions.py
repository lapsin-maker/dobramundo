"""Metas curtas dentro do voo (GDD, seção 7: "metas curtas" e "retorno imediato").

Uma meta por vez, de 20 a 60 segundos cada: coletar resíduos de um tipo, desviar
de obstáculos na faixa do avião, passar por baixo de portais ou pegar power-ups.
Cumprir uma meta rende um pouco de transformação, recursos e pontos, e a próxima
começa em seguida. Os alvos são menores no Normal.
"""

from __future__ import annotations

import random
from typing import Dict, Mapping, NamedTuple, Optional

from .. import config as C
from ..content.items import WASTE_BY_KEY, WASTE_KEYS

KINDS = ("coletar", "desviar", "portal", "powerup")
TARGETS: Dict[str, Dict[str, int]] = {
    "normal": {"coletar": 2, "desviar": 3, "portal": 2, "powerup": 1},
    "dificil": {"coletar": 6, "desviar": 6, "portal": 3, "powerup": 2},
}
FIRST_DELAY_S = 4.0  # voo sem abertura didática
NEXT_DELAY_S = 2.5  # pausa curta entre uma meta e a próxima
NO_SUPPLY_RETRY_S = 0.5  # não varre entidades em todos os quadros enquanto espera oferta
MISSION_TIMEOUT_S = 60.0  # metas não cumpridas saem sem prêmio ou punição
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

    def __init__(
        self,
        mode: str,
        rng: Optional[random.Random] = None,
        intro: bool = False,
        preferred_waste: Optional[str] = None,
    ) -> None:
        self.targets = TARGETS.get(mode, TARGETS["normal"])
        self.rng = rng or random.Random()
        self.intro = intro
        self.preferred_waste = preferred_waste if preferred_waste in WASTE_KEYS else None
        self.current: Optional[Mission] = None
        self.progress = 0
        self.completed = 0
        self.expired = 0
        self.current_age = 0.0
        # Não compete com as quatro demonstrações iniciais; a primeira meta aparece
        # depois do último ensino e só usa alvos presentes à frente do avião.
        self.wait = C.INTRO_END_S + 0.5 if intro else FIRST_DELAY_S
        self.last_kind = ""

    def update(self, dt: float, available: Optional[Mapping[str, object]] = None) -> bool:
        """Avança o tempo da meta; devolve True quando uma meta expira sem recompensa."""
        if self.current is not None:
            self.current_age += dt
            if self.current_age >= MISSION_TIMEOUT_S:
                self.current = None
                self.progress = 0
                self.current_age = 0.0
                self.expired += 1
                self.wait = NEXT_DELAY_S
                return True
            return False
        if self.current is None:
            self.wait -= dt
            if self.wait <= 0:
                mission = self.pick(available) if available is not None else self.pick()
                if mission is not None:
                    self.current = mission
                    self.progress = 0
                    self.current_age = 0.0
        return False

    def pick(self, available: Optional[Mapping[str, object]] = None) -> Optional[Mission]:
        if available is None:
            kind = self.rng.choice([k for k in KINDS if k != self.last_kind])
            waste = self.rng.choice(WASTE_KEYS) if kind == "coletar" else None
            self.last_kind = kind
            return Mission(kind, self.targets[kind], waste)

        offered = []
        supplies = available.get("coletar", {})
        if isinstance(supplies, Mapping):
            for waste in WASTE_KEYS:
                count = int(supplies.get(waste, 0))
                if count > 0:
                    offered.append(Mission("coletar", min(self.targets["coletar"], count), waste))
        for kind in ("desviar", "portal", "powerup"):
            count = int(available.get(kind, 0))
            if count > 0:
                offered.append(Mission(kind, min(self.targets[kind], count)))
        if not offered:
            # Reavaliar no próximo quadro; não oferecer uma meta sem alvos no percurso.
            self.wait = NO_SUPPLY_RETRY_S
            return None
        candidates = [mission for mission in offered if mission.kind != self.last_kind]
        preferred = [
            mission for mission in candidates
            if mission.kind == "coletar" and mission.waste == self.preferred_waste
        ]
        if preferred and self.rng.random() < 0.5:
            mission = self.rng.choice(preferred)
        else:
            mission = self.rng.choice(candidates or offered)
        self.last_kind = mission.kind
        return mission

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
        self.current_age = 0.0
        self.wait = NEXT_DELAY_S
        return mission

    @property
    def text(self) -> str:
        return self.current.text(self.progress) if self.current else ""
