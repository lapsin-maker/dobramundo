"""Um voo (partida): mundo + avião + regras de pontuação, vidas e estrelas.

Não desenha nem lê o teclado: recebe os eixos de controle a cada quadro e
publica eventos (coleta, colisão, estágio, estrela, fim) que as cenas usam
para som, mensagens e efeitos.
"""

from __future__ import annotations

import random
from typing import Dict, List, Mapping, Optional, Tuple

from .. import config as C
from ..content.biomes import Biome
from ..content.items import POWERUP_KINDS, WASTE_KEYS
from ..content.planes import POWERUP_MANEUVERS, START_MANEUVER, ManeuverRow
from ..content.progress import RESOURCES_PER_WASTE, plane_stats, stars_for
from .entities import Beam, Entity, FloatingText, entity_hitbox
from .missions import BONUS_POINTS, BONUS_RESOURCES, BONUS_RESTORATION, MissionTracker
from .player import Player
from .world import World

Event = Tuple[str, object]
COMPLETE_GLIDE_S = 3.0  # depois de 100%, o avião segue voando para a criança ver a cidade


class FlightRun:
    def __init__(
        self,
        biome: Biome,
        mode: str = "normal",
        parts: Optional[Mapping[str, int]] = None,
        maneuvers: Optional[Dict[str, List[ManeuverRow]]] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.biome = biome
        self.mode = mode
        self.parts = dict(parts or {})
        self.world = World(biome, mode, rng)
        self.missions = MissionTracker(mode, random.Random(self.world.rng.random()))
        self.player = Player(plane_stats(self.parts), maneuvers)
        self.lives = C.MAX_LIVES
        self.score = 0
        self.resources: Dict[str, int] = {k: 0 for k in WASTE_KEYS}
        self.combo = 1
        self.combo_timer = 0.0
        self.streak = 0
        self.shield_timer = 0.0
        self.magnet_timer = 0.0
        self.invulnerable_timer = 0.0
        self.hit_flash_timer = 0.0
        self.invincible = False  # modo de demonstração do supervisor (F2)
        self.game_over = False
        self.complete = False
        self.finished = False  # pronto para a tela de resultado
        self.complete_timer = 0.0
        self.stars = 0
        self.stage = self.world.stage
        self.beams: List[Beam] = []
        self.floating: List[FloatingText] = []
        self.events: List[Event] = []
        self.player.start_maneuver(START_MANEUVER)

    # --------------------------------------------------------------- regras
    @property
    def restoration(self) -> float:
        return self.world.restoration

    @property
    def speed(self) -> float:
        factor = C.NORMAL_SPEED_FACTOR if self.mode == "normal" else 1.0
        return (
            C.BASE_SPEED
            + self.world.restoration * C.RESTORATION_SPEED_GAIN
            + self.world.difficulty * C.DIFFICULTY_SPEED_GAIN
        ) * factor

    def emit(self, name: str, data: object = None) -> None:
        self.events.append((name, data))

    def take_events(self) -> List[Event]:
        events, self.events = self.events, []
        return events

    def add_restoration(self, amount: float) -> None:
        self.world.add_restoration(amount)
        stage = self.world.stage
        if stage > self.stage:
            self.stage = stage
            self.emit("stage", stage)
        stars = stars_for(self.world.restoration, self.biome.required_parts, self.parts)
        while self.stars < stars:
            self.stars += 1
            self.emit("star", self.stars)
        if self.world.restoration >= 100.0 and not self.complete:
            self.complete = True
            self.emit("complete", self.stars)

    def collect_waste(self, entity: Entity) -> None:
        if entity.collected:
            return
        entity.collected = True
        normal = self.mode == "normal"
        value = C.NORMAL_TRASH_POINTS if normal else C.HARD_TRASH_POINTS * self.combo
        self.score += value
        self.resources[entity.sprite] = self.resources.get(entity.sprite, 0) + RESOURCES_PER_WASTE[self.mode]
        if normal:
            gain = C.NORMAL_RESTORATION_PER_TRASH
        else:
            gain = C.RESTORATION_PER_TRASH + (C.RESTORATION_COMBO_BONUS if self.combo >= C.COMBO_BONUS_FROM else 0.0)
        self.streak += 1
        self.combo_timer = C.COMBO_WINDOW_S
        if not normal and self.streak % C.COMBO_STEP == 0:  # Normal: pontos fixos, sem combo
            self.combo = min(C.MAX_COMBO, self.combo + 1)
        self.beams.append(Beam(entity.x, entity.z))
        self.floating.append(FloatingText(f"+{value}", entity.x, entity.y + 35.0))
        self.emit("collect", entity.sprite)
        self.mission_event("coletar", entity.sprite)
        self.add_restoration(gain)

    def collect_powerup(self, entity: Entity) -> None:
        if entity.collected:
            return
        entity.collected = True
        bonus = 0.0
        if entity.kind == "shield":
            self.shield_timer = max(self.shield_timer, C.SHIELD_S)
            label = "ESCUDO"
        elif entity.kind == "magnet":
            self.magnet_timer = max(self.magnet_timer, C.MAGNET_S)
            label = "ÍMÃ"
        elif self.lives < C.MAX_LIVES:
            self.lives += 1
            label = "+1 VIDA"
        else:  # reparo com vidas cheias: transforma a cidade
            bonus = C.REPAIR_RESTORATION
            label = f"+{bonus:g}%"
        self.floating.append(FloatingText(label, entity.x, entity.y + 48.0, (178, 255, 210)))
        self.player.start_maneuver(POWERUP_MANEUVERS.get(entity.kind))
        self.emit("powerup", entity.kind)
        self.mission_event("powerup")
        if bonus:
            self.add_restoration(bonus)

    def take_hit(self) -> None:
        if self.invincible or self.complete or self.shield_timer > 0 or self.invulnerable_timer > 0:
            return
        self.lives = max(0, self.lives - 1)
        self.invulnerable_timer = C.INVULNERABLE_S
        self.hit_flash_timer = C.HIT_FLASH_S
        self.combo = 1
        self.streak = 0
        self.combo_timer = 0.0
        self.emit("hit", self.lives)
        if self.lives == 0:
            self.game_over = True
            self.finished = True
            self.emit("game_over", self.stars)

    def update_combo(self, dt: float) -> None:
        if self.combo_timer > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo = 1
                self.streak = 0

    # ---------------------------------------------------------------- quadro
    def update(self, dt: float, ix: float = 0.0, iy: float = 0.0) -> None:
        if self.finished:
            return
        dt = min(dt, C.MAX_DT)
        had_shield = self.shield_timer > 0
        self.shield_timer = max(0.0, self.shield_timer - dt)
        if had_shield and self.shield_timer == 0:
            self.emit("shield_end")
        self.magnet_timer = max(0.0, self.magnet_timer - dt)
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)
        self.update_combo(dt)
        self.player.update(dt, ix, iy)
        self.world.advance(dt, self.speed * dt)
        self.check_collisions()
        self.count_passes()
        self.missions.update(dt)
        self.world.prune()
        for beam in self.beams:
            beam.z -= self.speed * dt
            beam.ttl -= dt
        self.beams = [b for b in self.beams if b.ttl > 0]
        for text in self.floating:
            text.y += 48.0 * dt
            text.ttl -= dt
        self.floating = [t for t in self.floating if t.ttl > 0]
        if self.complete:
            self.complete_timer += dt
            if self.complete_timer >= COMPLETE_GLIDE_S:
                self.finished = True

    def mission_event(self, kind: str, waste: Optional[str] = None) -> None:
        """Conta para a meta atual; cumprida, dá a recompensa e avisa a cena."""
        mission = self.missions.record(kind, waste)
        if mission is None:
            return
        bonus_type = mission.waste or WASTE_KEYS[self.missions.completed % len(WASTE_KEYS)]
        self.resources[bonus_type] = self.resources.get(bonus_type, 0) + BONUS_RESOURCES
        self.score += BONUS_POINTS
        self.emit("mission", mission)
        self.add_restoration(BONUS_RESTORATION)

    def count_passes(self) -> None:
        """Obstáculos que passaram pelo avião sem acertá-lo: desvios e portais atravessados."""
        player = self.player
        for entity in self.world.entities:
            if entity.spec is None or entity.passed or entity.z > C.PLAYER_Z - 30.0:
                continue
            entity.passed = True
            if entity.hit or abs(entity.x - player.x) > C.LANE_WIDTH * 0.75:
                continue  # bateu, ou o obstáculo estava longe da faixa do avião
            self.mission_event("desviar")
            if entity.kind == "gate":
                self.mission_event("portal")

    def check_collisions(self) -> None:
        player = self.player
        box = player.hitbox()
        magnet = self.magnet_timer > 0
        for entity in self.world.entities:
            if entity.collected:
                continue
            overlaps = box.intersects(entity_hitbox(entity))
            if entity.kind == "waste":
                reaches = (
                    magnet
                    and abs(entity.z - C.PLAYER_Z) <= 45.0
                    and abs(player.x - entity.x) < C.LANE_WIDTH * 1.1
                    and abs(player.y - entity.y) < 110.0
                )
                if overlaps or reaches:
                    self.collect_waste(entity)
            elif entity.kind in POWERUP_KINDS:
                if overlaps:
                    self.collect_powerup(entity)
            elif overlaps:
                entity.hit = True
                self.take_hit()
                if self.game_over:
                    break
