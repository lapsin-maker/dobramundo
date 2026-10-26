"""Um voo (partida): mundo + avião + regras de pontuação, vidas e estrelas.

Não desenha nem lê o teclado: recebe os eixos de controle a cada quadro e
publica eventos (coleta, colisão, estágio, estrela, fim) que as cenas usam
para som, mensagens e efeitos.
"""

from __future__ import annotations

import hashlib
import math
import random
import secrets
from typing import Dict, List, Mapping, Optional, Tuple

from .. import config as C
from ..content.biomes import Biome
from ..content.items import POWERUP_KINDS, WASTE_BY_KEY, WASTE_KEYS
from ..content.planes import POWERUP_MANEUVERS, START_MANEUVER, ManeuverRow
from ..content.progress import RESOURCES_PER_WASTE, plane_stats, stars_for
from .entities import Beam, Entity, FloatingText, entity_hitbox
from .focus import FocusMoment, intended_point
from .missions import BONUS_POINTS, BONUS_RESOURCES, BONUS_RESTORATION, MissionTracker
from .player import Player
from .world import World

Event = Tuple[str, object]
SPLASH_S = 0.55  # respingo de aquarela da coleta
COMPLETE_GLIDE_S = 3.0  # depois de 100%, o avião segue voando para a criança ver a cidade


class FlightRun:
    def __init__(
        self,
        biome: Biome,
        mode: str = "normal",
        parts: Optional[Mapping[str, int]] = None,
        maneuvers: Optional[Dict[str, List[ManeuverRow]]] = None,
        rng: Optional[random.Random] = None,
        intro: bool = False,
        focus: bool = True,
        seed: Optional[int] = None,
        session_limit_s: int = 0,
        exploration: bool = False,
        predictable_assistance: bool = False,
        community_challenge: bool = False,
        mission_preferred_waste: Optional[str] = None,
        city_restoration: float = C.START_RESTORATION,
        starting_stars: int = 0,
        spawn_enabled: bool = True,
        active_recovery: bool = True,
    ) -> None:
        self.biome = biome
        self.mode = mode
        self.parts = dict(parts or {})
        if seed is None:
            if rng is None:
                seed = secrets.randbits(32)
            else:
                # Deriva uma seed reproduzível do estado sem avançar o RNG fornecido.
                state = repr(rng.getstate()).encode("ascii")
                seed = int.from_bytes(hashlib.blake2s(state, digest_size=4).digest(), "big")
        self.seed = int(seed) & 0xFFFFFFFF
        self.intro = bool(intro)
        self.world = World(
            biome,
            mode,
            random.Random(self.seed),
            self.intro,
            restoration=city_restoration,
            challenge_seed=self.seed if community_challenge else None,
            spawn_enabled=spawn_enabled,
        )
        self.community_challenge = self.world.challenge_theme is not None
        self.focus = FocusMoment(mode, focus)
        self.mission_preferred_waste = (
            mission_preferred_waste if mission_preferred_waste in WASTE_KEYS and self.community_challenge else None
        )
        self.missions = MissionTracker(
            mode,
            random.Random(self.world.rng.random()),
            intro=intro,
            preferred_waste=self.mission_preferred_waste,
        )
        self.player = Player(plane_stats(self.parts), maneuvers)
        self.exploration = bool(exploration)
        self.active_recovery = bool(active_recovery and spawn_enabled)
        self.predictable_assistance = bool(predictable_assistance)
        self.max_lives = C.ASSISTED_MAX_LIVES if self.predictable_assistance else C.MAX_LIVES
        self.invulnerable_duration = C.ASSISTED_INVULNERABLE_S if self.predictable_assistance else C.INVULNERABLE_S
        self.lives = self.max_lives
        requested_limit = max(0, int(session_limit_s))
        self.session_limit_s = requested_limit if requested_limit in C.SESSION_LIMITS_S else 0
        self.timeout = False
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
        self.city_restoration_at_start = self.world.restoration
        self.local_restoration = C.START_RESTORATION
        # Um voo interrompido guarda as recompensas obtidas, mas não conclui a fase.
        self.interrupted = False
        self.finished = False  # pronto para a tela de resultado
        # Estado em memória do assentamento. Resultado pode ser reaberto ou salvo de novo.
        self.settlement = None
        self.settlement_callback_sent = False
        self.complete_timer = 0.0
        self.stars = min(3, max(0, int(starting_stars)))
        self.stage = self.world.stage
        self.beams: List[Beam] = []
        self.floating: List[FloatingText] = []
        self.events: List[Event] = []
        # medida de movimento (resultado e histórico): só com controle corporal
        self.flight_time = 0.0  # segundos reais de voo (sem pausas)
        self.active_time = 0.0  # segundos com o comando corporal em movimento
        self.travel = 0.0  # caminho do comando: 1 = de um extremo ao outro do alcance
        self.body_time = 0.0  # segundos com o corpo controlando
        self.last_command: Optional[Tuple[float, float]] = None
        self.hits = 0
        self.waste_collected = 0
        self.pause_count = 0
        self.pause_duration_s = 0.0
        self.player.start_maneuver(START_MANEUVER)

    # --------------------------------------------------------------- regras
    @property
    def restoration(self) -> float:
        """Transformação da cidade, de 0 a 100%."""
        return self.world.restoration

    @property
    def speed(self) -> float:
        """Velocidade da pista: base + transformação + rampa de dificuldade (metade no Normal)."""
        factor = C.NORMAL_SPEED_FACTOR if self.mode == "normal" else 1.0
        return (
            C.BASE_SPEED
            + self.local_restoration * C.RESTORATION_SPEED_GAIN
            + self.world.difficulty * C.DIFFICULTY_SPEED_GAIN
        ) * factor

    def emit(self, name: str, data: object = None) -> None:
        """Publica um acontecimento do voo para a cena (som, avisos, efeitos)."""
        self.events.append((name, data))

    def take_events(self) -> List[Event]:
        """Entrega e esvazia os acontecimentos desde a última chamada."""
        events, self.events = self.events, []
        return events

    def add_restoration(self, amount: float, speed_amount: Optional[float] = None, *, earned: bool = True) -> None:
        """Transforma a cidade e publica mudança de estágio, estrelas e fase completa."""
        previous = self.world.restoration
        self.world.add_restoration(amount, earned=earned)
        speed_gain = amount if speed_amount is None else speed_amount
        self.local_restoration = min(100.0, self.local_restoration + max(0.0, speed_gain))
        stage = self.world.stage
        if stage > self.stage:
            self.stage = stage
            self.emit("stage", stage)
        stars = stars_for(self.world.restoration, self.biome.required_parts, self.parts)
        while self.stars < stars:
            self.stars += 1
            self.emit("star", self.stars)
        if previous < 100.0 <= self.world.restoration and not self.complete:
            self.complete = True
            self.emit("complete", self.stars)

    def add_active_recovery(self, dt: float) -> None:
        """Recupera a cidade enquanto este voo está ativo, sem dar recursos ou acelerar o avião."""
        if self.world.restoration >= 100.0:
            return
        if self.active_recovery and dt > 0.0:
            self.add_restoration(C.ACTIVE_RECOVERY_PER_S * dt, speed_amount=0.0, earned=False)

    def collect_waste(self, entity: Entity) -> None:
        if entity.collected:
            return
        entity.collected = True
        self.waste_collected += 1
        normal = self.mode == "normal"
        value = C.NORMAL_TRASH_POINTS if normal else C.HARD_TRASH_POINTS * self.combo
        self.score += value
        self.resources[entity.sprite] = self.resources.get(entity.sprite, 0) + RESOURCES_PER_WASTE[self.mode]
        if normal:
            gain = C.NORMAL_RESTORATION_PER_TRASH
            speed_gain = C.NORMAL_SPEED_RESTORATION_PER_TRASH
        else:
            gain = C.RESTORATION_PER_TRASH + (C.RESTORATION_COMBO_BONUS if self.combo >= C.COMBO_BONUS_FROM else 0.0)
            speed_gain = C.DIFFICULT_SPEED_RESTORATION_PER_TRASH + (
                C.RESTORATION_COMBO_BONUS if self.combo >= C.COMBO_BONUS_FROM else 0.0
            )
        self.streak += 1
        self.combo_timer = C.COMBO_WINDOW_S
        if not normal and self.streak % C.COMBO_STEP == 0:  # Normal: pontos fixos, sem combo
            self.combo = min(C.MAX_COMBO, self.combo + 1)
        self.beams.append(Beam(entity.x, entity.z, WASTE_BY_KEY[entity.sprite].color, SPLASH_S))
        self.floating.append(FloatingText(f"+{value}", entity.x, entity.y + 35.0))
        self.emit("collect", entity.sprite)
        self.mission_event("coletar", entity.sprite)
        self.add_restoration(gain, speed_gain)

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
        elif self.lives < self.max_lives:
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
        self.hits += 1
        self.invulnerable_timer = self.invulnerable_duration
        self.hit_flash_timer = C.HIT_FLASH_S
        self.combo = 1
        self.streak = 0
        self.combo_timer = 0.0
        self.emit("hit", self.lives)
        if self.lives == 0 and self.exploration:
            self.lives = self.max_lives
            self.emit("exploration_continue", self.hits)
        elif self.lives == 0:
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
    def update(self, dt: float, ix: float = 0.0, iy: float = 0.0, target: Optional[Tuple[float, float]] = None) -> None:
        """Um quadro de tempo real. ix, iy: velocidade (-1..1); target: comando de posição
        (-1..1 nos dois eixos, 0 na postura calibrada), que tem prioridade sobre ix e iy."""
        if self.finished:
            return
        real_dt = min(dt, C.MAX_DT)
        if self.session_limit_s:
            remaining = max(0.0, self.session_limit_s - self.flight_time)
            if remaining <= 1e-9:
                self.timeout = True
                self.interrupted = not self.complete
                self.finished = True
                self.emit("session_end", self.flight_time)
                return
            real_dt = min(real_dt, remaining)
        self.flight_time += real_dt
        self.add_active_recovery(real_dt)
        player = self.player
        aim = None if target is None else player.command_target(*target)
        command = target if target is not None else (ix, iy)
        self.focus.update(self, real_dt, command, intended_point(player, aim))
        dt = real_dt * self.focus.time_scale  # tempo do mundo (lento no momento de foco)
        had_shield = self.shield_timer > 0
        self.shield_timer = max(0.0, self.shield_timer - dt)
        if had_shield and self.shield_timer == 0:
            self.emit("shield_end")
        self.magnet_timer = max(0.0, self.magnet_timer - dt)
        self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt)
        self.hit_flash_timer = max(0.0, self.hit_flash_timer - dt)
        self.update_combo(dt)
        guide = self.focus.guide_point()
        if guide is not None:
            player.update(dt, 0.0, 0.0, guide, exact=True)
        else:
            player.update(dt, ix, iy, aim)
        self.world.advance(dt, self.speed * dt)
        self.announce_lessons()
        self.check_collisions()
        self.count_passes()
        if self.missions.current is None and self.missions.wait <= dt:
            expired = self.missions.update(dt, self.mission_supply())
        else:
            expired = self.missions.update(dt)
        if expired:
            self.emit("mission_expired")
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
        if self.session_limit_s and self.flight_time >= self.session_limit_s - 1e-9 and not self.finished:
            self.timeout = True
            self.interrupted = not self.complete
            self.finished = True
            self.emit("session_end", self.flight_time)

    def mission_supply(self) -> Dict[str, object]:
        """Oferta concreta à frente do avião para evitar metas sem alvo no percurso."""
        cutoff = C.PLAYER_Z + max(120.0, self.speed * 3.0)
        supply: Dict[str, object] = {"coletar": {}, "desviar": 0, "portal": 0, "powerup": 0}
        collect = supply["coletar"]
        for entity in self.world.entities:
            if entity.collected or entity.passed or entity.z <= cutoff:
                continue
            if entity.kind == "waste":
                collect[entity.sprite] = collect.get(entity.sprite, 0) + 1
            elif entity.kind in ("shield", "magnet", "repair"):
                supply["powerup"] += 1
            elif entity.spec is not None:
                supply["desviar"] += 1
                if entity.kind == "gate":
                    supply["portal"] += 1
        return supply

    def announce_lessons(self) -> None:
        """Legenda de cada objeto da abertura didática, LESSON_LEAD_S antes de ele chegar."""
        reach = self.speed * C.LESSON_LEAD_S
        for entity in self.world.entities:
            if entity.lesson and not entity.announced and entity.z - C.PLAYER_Z <= reach:
                entity.announced = True
                self.emit("lesson", entity.lesson)

    def record_movement(self, dt: float, command: Tuple[float, float]) -> None:
        """Comando corporal do quadro (-1..1) para a medida de movimento do resultado."""
        self.body_time += dt
        last, self.last_command = self.last_command, command
        if last is None or dt <= 0:
            return
        step = math.hypot(command[0] - last[0], command[1] - last[1])
        self.travel += step / 2.0
        if step / dt >= C.ACTIVE_COMMAND_SPEED:
            self.active_time += dt

    def summary(self) -> Dict[str, object]:
        """Resumo do voo para o histórico do perfil (supervisor, terapeuta, cartucho)."""
        return {
            "fase": self.biome.key,
            "modo": self.mode,
            "abertura_didatica": int(self.intro),
            "desafio_comunitario": int(self.community_challenge),
            "material_preferido_missao": self.mission_preferred_waste or "",
            "exploracao": int(self.exploration),
            "assistencia_previsivel": int(self.predictable_assistance),
            "limite_s": self.session_limit_s,
            "semente": self.seed,
            "tempo_esgotado": int(self.timeout),
            "vidas_maximas": self.max_lives,
            "vidas_finais": self.lives,
            "concluida": int(self.complete),
            "interrompida": int(self.interrupted),
            "transformacao": round(self.restoration, 1),
            "estrelas": self.stars,
            "pontos": self.score,
            "batidas": self.hits,
            "coletas": self.waste_collected,
            "recursos_total": sum(self.resources.values()),
            "recurso_papel": self.resources["papel"],
            "recurso_plastico": self.resources["plastico"],
            "recurso_metal": self.resources["metal"],
            "recurso_vidro": self.resources["vidro"],
            "pausas": self.pause_count,
            "pausa_s": round(self.pause_duration_s, 1),
            "foco_acertos": self.focus.successes,
            "foco_total": self.focus.total,
            "duracao_s": round(self.flight_time, 1),
            "corpo_s": round(self.body_time, 1),
            "movimento_s": round(self.active_time, 1),
            "alcances": round(self.travel, 1),
        }

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
                    and abs(entity.z - C.PLAYER_Z) <= C.MAGNET_REACH_Z
                    and abs(player.x - entity.x) < C.LANE_WIDTH * C.MAGNET_REACH_LANES
                    and abs(player.y - entity.y) < C.MAGNET_REACH_Y
                )
                if overlaps or reaches:
                    self.collect_waste(entity)
            elif entity.kind in POWERUP_KINDS:
                if overlaps:
                    self.collect_powerup(entity)
            elif overlaps and not entity.dodged:
                entity.hit = True
                self.take_hit()
                if self.game_over:
                    break
