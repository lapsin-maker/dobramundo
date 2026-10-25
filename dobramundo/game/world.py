"""Pista, trechos e objetos de uma fase.

A pista é uma fila de trechos de SEGMENT_LENGTH unidades que andam em direção
ao avião; quando um trecho passa pela câmera, ele volta para o fim da fila e
recebe novos objetos. A transformação da cidade chega DO HORIZONTE PARA O AVIÃO:
a partir de cada limiar, uma parcela crescente dos trechos que entram lá longe
(na neblina) já vem no estágio novo, e a peça antiga afunda enquanto a nova
cresce. Assim o cenário muda aos poucos, sem "brotar" na frente do jogador.
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional

from .. import config as C
from ..content.biomes import Biome
from ..content.items import OBSTACLE_KINDS, POWERUP_KINDS, WASTE_KEYS, ObstacleSpec
from ..util import clamp, smoothstep
from .entities import Entity

GOLDEN = 0.6180339887498949  # ordem espalhada em que os trechos viram verdes
PLASTIC = 0.7548776662466927  # outra sequência para o estágio solarpunk


class World:
    """Estado da pista: trechos, transformação e objetos."""

    def __init__(self, biome: Biome, mode: str = "normal", rng: Optional[random.Random] = None) -> None:
        self.biome = biome
        self.mode = mode
        self.rng = rng or random.Random()
        self.reset()

    # ------------------------------------------------------------ início
    def reset(self, restoration: float = C.START_RESTORATION) -> None:
        self.distance = 0.0
        self.elapsed = 0.0
        self.segments: List[float] = [
            float(z) for z in range(int(C.SEGMENT_LENGTH), int(C.TRACK_LENGTH) + 1, int(C.SEGMENT_LENGTH))
        ]
        self.segment_base = 0  # índice absoluto de segments[0] na pista
        self.entities: List[Entity] = []
        self.waste_counter = 0
        self.waste_roll = 0
        self.obstacle_counters: Dict[str, int] = {
            f"{s}:{k}": 0 for s in ("industrial", "solar") for k in OBSTACLE_KINDS
        }
        self.green_since: Dict[int, float] = {}
        self.final_since: Dict[int, float] = {}
        self.set_restoration(restoration)
        z = 520.0
        while z <= C.TRACK_LENGTH:
            self.spawn_pattern(z)
            z += self.rng.choice((100.0, 120.0, 140.0))

    def set_restoration(self, value: float) -> None:
        """Atribuição direta (início, testes): o cenário fica no estado final na hora."""
        self.restoration = clamp(float(value), 0.0, 100.0)
        self.visual = self.restoration
        self.green_since = {}
        self.final_since = {}
        for i in range(len(self.segments)):
            seg = self.segment_base + i
            if self.green_rank(seg) < self.green_share():
                self.green_since[seg] = -1e12
            if self.final_rank(seg) < self.final_share():
                self.final_since[seg] = -1e12

    # ------------------------------------------------------- transformação
    def add_restoration(self, amount: float) -> None:
        self.restoration = clamp(self.restoration + amount, 0.0, 100.0)

    @property
    def stage(self) -> int:
        """Estágio da jogabilidade (0, 1 ou 2), pela transformação real."""
        return min(2, int((self.restoration + 1e-6) // C.ERA_SPAN))

    def visual_stage_pair(self):
        """(estágio de origem, estágio de destino, mistura 0..1) pela transformação visual."""
        stages = self.biome.stages
        value = self.visual
        for i in range(len(stages) - 1):
            low, high = i * C.ERA_SPAN, (i + 1) * C.ERA_SPAN
            if low <= value < high:
                return stages[i], stages[i + 1], (value - low) / C.ERA_SPAN
        return stages[-1], stages[-1], 1.0

    def ease_visual(self, dt: float) -> None:
        """O cenário (cores, céu, frentes) alcança a transformação real aos poucos."""
        k = 1.0 - math.exp(-dt / C.VISUAL_RESTORATION_TIME)
        self.visual += (self.restoration - self.visual) * k
        if abs(self.restoration - self.visual) < 0.01:
            self.visual = self.restoration

    @staticmethod
    def green_rank(seg: int) -> float:
        return (seg * GOLDEN) % 1.0

    @staticmethod
    def final_rank(seg: int) -> float:
        return (seg * PLASTIC + 0.31) % 1.0

    def green_share(self) -> float:
        if self.visual < C.GRASS_START_RESTORATION:
            return 0.0
        return smoothstep((self.visual - C.GRASS_START_RESTORATION) / C.GREEN_SWEEP_RESTORATION)

    def final_share(self) -> float:
        if self.visual < C.FINAL_START_RESTORATION:
            return 0.0
        return smoothstep((self.visual - C.FINAL_START_RESTORATION) / C.FINAL_SWEEP_RESTORATION)

    def _sweep(self, since: Dict[int, float], rank, share: float) -> None:
        for seg in [s for s in since if s < self.segment_base]:
            del since[seg]
        if share <= 0.0:
            return
        for i, z in enumerate(self.segments):
            seg = self.segment_base + i
            if z >= C.GREEN_CONVERT_Z and seg not in since and rank(seg) < share:
                since[seg] = self.distance

    def segment_green(self, seg: int) -> float:
        """0 = indústria, 1 = flora crescida; cresce enquanto o trecho vem chegando."""
        since = self.green_since.get(seg)
        if since is None:
            return 0.0
        return smoothstep((self.distance - since) / C.GREEN_GROW_DISTANCE)

    def segment_final(self, seg: int) -> float:
        """0 = estágio anterior, 1 = peça solarpunk crescida."""
        since = self.final_since.get(seg)
        if since is None:
            return 0.0
        return smoothstep((self.distance - since) / C.FINAL_GROW_DISTANCE)

    def segment_index(self, z: float) -> Optional[int]:
        if not self.segments:
            return None
        i = int((z - self.segments[0]) // C.SEGMENT_LENGTH)
        return i if 0 <= i < len(self.segments) else None

    def segment_at(self, z: float) -> Optional[int]:
        i = self.segment_index(z)
        return None if i is None else self.segment_base + i

    def final_at(self, z: float) -> bool:
        seg = self.segment_at(z)
        return seg is not None and self.segment_final(seg) > 0.0

    def spawn_is_final(self, z: float) -> bool:
        """Objeto novo em z: usa os obstáculos solarpunk se o trecho dele chega no estágio 3."""
        seg = self.segment_at(z)
        if seg is None:
            seg = self.segment_base + len(self.segments)
        return seg in self.final_since or self.final_rank(seg) < self.final_share()

    def stage_flags(self):
        """Por trecho: (chão verde, estágio solarpunk), calculados uma vez por quadro."""
        green = (
            [self.segment_green(self.segment_base + i) > 0.0 for i in range(len(self.segments))]
            if self.green_since
            else None
        )
        final = (
            [self.segment_final(self.segment_base + i) > 0.0 for i in range(len(self.segments))]
            if self.final_since
            else None
        )
        return green, final

    # -------------------------------------------------------------- spawn
    @property
    def difficulty(self) -> float:
        return clamp(self.elapsed / C.DIFFICULTY_RAMP_S, 0.0, 1.0)

    def waste_allowed(self) -> bool:
        """Normal: só 1 de cada NORMAL_TRASH_EVERY resíduos sorteados aparece."""
        if self.mode != "normal":
            return True
        self.waste_roll += 1
        return (self.waste_roll - 1) % C.NORMAL_TRASH_EVERY == 0

    def next_waste(self) -> str:
        """Os quatro tipos se alternam em ordem fixa: recursos equilibrados."""
        kind = WASTE_KEYS[self.waste_counter % len(WASTE_KEYS)]
        self.waste_counter += 1
        return kind

    def next_obstacle(self, kind: str, solar: bool) -> ObstacleSpec:
        """Modelos de cada tipo aparecem sempre na mesma ordem (não sorteados)."""
        table = self.biome.solar_obstacles if solar else self.biome.industrial_obstacles
        options = table[kind]
        key = f"{'solar' if solar else 'industrial'}:{kind}"
        spec = options[self.obstacle_counters[key] % len(options)]
        self.obstacle_counters[key] += 1
        return spec

    def spawn_pattern(self, z: float) -> None:
        rng = self.rng
        lanes = [-1, 0, 1]
        waste_lane = rng.choice(lanes)
        waste_y = rng.choice(C.TRASH_HEIGHTS)
        if self.waste_allowed():
            self.entities.append(Entity(z, waste_lane, "waste", waste_y, self.next_waste()))
        available = [lane for lane in lanes if lane != waste_lane]
        if rng.random() < 0.45:
            lane2, y2 = rng.choice(available), rng.choice(C.TRASH_HEIGHTS)
            if self.waste_allowed():
                self.entities.append(Entity(z + 45.0, lane2, "waste", y2, self.next_waste()))
        if rng.random() < 0.35 + self.difficulty * 0.30:
            roll = rng.random()
            kind = "low" if roll < 0.45 else ("gate" if roll < 0.75 else "tower")
            solar = self.spawn_is_final(z)
            spec = self.next_obstacle(kind, solar)
            self.entities.append(Entity(z, rng.choice(available), kind, 0.0, spec.sprite, spec, solar))
        if rng.random() < 0.13:
            kind = rng.choice(POWERUP_KINDS)
            self.entities.append(Entity(z + 30.0, rng.choice(lanes), kind, rng.choice(C.TRASH_HEIGHTS)))

    # -------------------------------------------------------------- avanço
    def advance(self, dt: float, dz: float) -> None:
        """Move a pista dz unidades em direção ao avião e recicla os trechos que passaram."""
        self.elapsed += dt
        self.distance += dz
        self.ease_visual(dt)
        self._sweep(self.green_since, self.green_rank, self.green_share())
        self._sweep(self.final_since, self.final_rank, self.final_share())
        segments = self.segments
        for i in range(len(segments)):
            segments[i] -= dz
        while segments and segments[0] < -40.0:
            segments.pop(0)
            self.segment_base += 1
            self.final_since.pop(self.segment_base - 1, None)
            new_z = (segments[-1] if segments else C.SEGMENT_LENGTH) + C.SEGMENT_LENGTH
            segments.append(new_z)
            self.spawn_pattern(new_z + 20.0)
        for entity in self.entities:
            entity.z -= dz

    def prune(self) -> None:
        """Remove o que já passou pelo avião ou foi coletado (não cobre a visão)."""
        limit = C.PLAYER_Z - 70.0
        self.entities = [e for e in self.entities if e.z > limit and not e.collected]
