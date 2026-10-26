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
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .. import config as C
from ..content.biomes import Biome
from ..content.items import OBSTACLE_KINDS, POWERUP_KINDS, WASTE_KEYS, ObstacleSpec
from ..content.progress import plane_stats
from ..util import clamp, smoothstep
from .challenges import ChallengeTheme, challenge_theme_for
from .entities import Entity

GOLDEN = 0.6180339887498949  # ordem espalhada em que os trechos viram verdes
PLASTIC = 0.7548776662466927  # outra sequência para o estágio solarpunk

# Contrato do gerador: uma rota de referência deve existir no modelo discreto,
# partindo do avião centrado, com 0,35 s de reação + 0,15 s de reversão e só
# 75% da velocidade máxima comum. O limite é o menor deslocamento possível entre
# (a) d'=min(v,r*(D-d)), calibrado para o dt máximo de Player.steer_to, e (b) a
# aceleração exponencial do comando de velocidade. Obstáculos sobrepostos mantêm
# o mesmo ponto seguro durante toda a janela de colisão.
# Isso protege contra sequências geométricas ruins, não garante alcançabilidade
# física para toda pessoa/controle.
ROUTE_REACTION_MARGIN_S = 0.35
ROUTE_REVERSAL_MARGIN_S = 0.15
ROUTE_CONTROL_FACTOR = 0.75
ROUTE_X_STEP = 10.0
ROUTE_Y_STEP = 11.0
ROUTE_Z_HALF = 16.0 + 27.0
ROUTE_POSITION_RESPONSE = (1.0 - math.exp(-C.POSITION_RESPONSE * C.MAX_DT)) / C.MAX_DT


def _route_grid() -> Tuple[List[float], List[float]]:
    xs = [float(value) for value in range(int(-C.MAX_PLAYER_X), int(C.MAX_PLAYER_X) + 1, int(ROUTE_X_STEP))]
    if xs[-1] != C.MAX_PLAYER_X:
        xs.append(float(C.MAX_PLAYER_X))
    ys = [float(value) for value in range(int(C.MIN_ALTITUDE), int(C.MAX_ALTITUDE) + 1, int(ROUTE_Y_STEP))]
    ys.extend((float(C.START_ALTITUDE), float(C.REST_ALTITUDE), float(C.MAX_ALTITUDE)))
    return sorted(set(xs)), sorted(set(ys))


_ROUTE_XS, _ROUTE_YS = _route_grid()
_ROUTE_Y_COUNT = len(_ROUTE_YS)
# Um bit por célula (x * alturas + y). Estas máscaras repetem uma coluna de
# alturas em intervalos de x; multiplicá-las pela máscara y forma o retângulo.
_ROUTE_X_MASKS = tuple(
    tuple(
        (((1 << (_ROUTE_Y_COUNT * (end - start))) - 1) // ((1 << _ROUTE_Y_COUNT) - 1)) << (_ROUTE_Y_COUNT * start)
        if end > start
        else 0
        for end in range(len(_ROUTE_XS) + 1)
    )
    for start in range(len(_ROUTE_XS) + 1)
)


def _axis_reach_limit(
    start: float,
    direction: float,
    elapsed: float,
    speed: float,
    minimum: float,
    maximum: float,
    position_response: float,
    velocity_response: float,
) -> float:
    if abs(direction) < 1e-9 or elapsed <= 0.0:
        return 0.0
    target_limit = maximum if direction > 0.0 else minimum
    target_distance = abs(target_limit - start)
    saturation_time = max(0.0, (target_distance - speed / position_response) / speed)
    if elapsed <= saturation_time:
        distance = speed * elapsed
    else:
        distance = target_distance - min(target_distance, speed / position_response) * math.exp(
            -position_response * (elapsed - saturation_time)
        )
    velocity_distance = speed * (elapsed - (1.0 - math.exp(-velocity_response * elapsed)) / velocity_response)
    return min(distance, velocity_distance)


def _axis_reachable(
    start: float,
    end: float,
    elapsed: float,
    speed: float,
    minimum: float,
    maximum: float,
    position_response: float,
    velocity_response: float,
) -> bool:
    if abs(end - start) < 1e-9:
        return True
    direction = 1.0 if end > start else -1.0
    return (
        abs(end - start)
        <= _axis_reach_limit(start, direction, elapsed, speed, minimum, maximum, position_response, velocity_response)
        + 1e-9
    )


def _route_threat_groups(entities: List[Entity]) -> List[Tuple[float, float, List[Entity]]]:
    """Agrupa janelas de colisão sobrepostas sem reordenar a pista por outro critério."""
    threats = [
        entity
        for entity in entities
        if entity.spec is not None
        and not entity.collected
        and not entity.hit
        and not entity.dodged
        and entity.z - C.PLAYER_Z >= -ROUTE_Z_HALF
    ]
    intervals = sorted(
        [(entity.z - C.PLAYER_Z - ROUTE_Z_HALF, entity.z - C.PLAYER_Z + ROUTE_Z_HALF, entity) for entity in threats],
        key=lambda item: (item[0], item[1]),
    )
    groups: List[Tuple[float, float, List[Entity]]] = []
    for start, end, entity in intervals:
        if groups and start <= groups[-1][1]:
            old_start, old_end, members = groups[-1]
            members.append(entity)
            groups[-1] = (old_start, max(old_end, end), members)
        else:
            groups.append((start, end, [entity]))
    return groups


def _free_route_cells(members: List[Entity], half_w: float, half_h: float) -> set[Tuple[int, int]]:
    """Células discretas cuja hitbox expandida não intercepta nenhum membro do grupo."""
    safe = set()
    for xi, x in enumerate(_ROUTE_XS):
        for yi, y in enumerate(_ROUTE_YS):
            blocked = any(
                abs(x - entity.x) <= entity.spec.width * 0.5 + half_w
                and y + half_h >= entity.spec.y_min
                and y - half_h <= entity.spec.y_max
                for entity in members
            )
            if not blocked:
                safe.add((xi, yi))
    return safe


def _point_reachable(
    start: Tuple[float, float],
    end: Tuple[float, float],
    elapsed: float,
    speed: Tuple[float, float],
    position_response: float,
    velocity_response: float,
) -> bool:
    """Os dois eixos devem caber no mesmo intervalo, com seus limites físicos."""
    return _axis_reachable(
        start[0],
        end[0],
        elapsed,
        speed[0],
        -C.MAX_PLAYER_X,
        C.MAX_PLAYER_X,
        position_response,
        velocity_response,
    ) and _axis_reachable(
        start[1],
        end[1],
        elapsed,
        speed[1],
        C.MIN_ALTITUDE,
        C.MAX_ALTITUDE,
        position_response,
        velocity_response,
    )


def find_reachable_route(entities: List[Entity], mode: str) -> Optional[List[Tuple[float, float]]]:
    """Planeja uma rota de referência por grupos de obstáculos no eixo x/altura.

    Cada obstáculo bloqueia a caixa real expandida pela hitbox comum do avião.
    Grupos com janelas de colisão sobrepostas são resolvidos juntos; entre grupos,
    o movimento usa o controlador de posição exponencial, 75% da velocidade
    comum e margens explícitas de reação/reversão. A rota retorna um ponto seguro por
    grupo ou None. É um filtro geométrico determinístico, não uma simulação de
    câmera, input, latência, dinâmica contínua ou habilidade individual.
    """
    stats = plane_stats({})
    half_w = C.PLANE_WIDTH * 0.42 * stats.hitbox
    half_h = C.PLANE_HEIGHT * 0.5 * stats.hitbox
    groups = _route_threat_groups(entities)
    if not groups:
        return []

    factor = C.NORMAL_SPEED_FACTOR if mode == "normal" else 1.0
    worst_case_speed = (C.BASE_SPEED + 100.0 * C.RESTORATION_SPEED_GAIN + C.DIFFICULTY_SPEED_GAIN) * factor
    move_x = C.MAX_LATERAL_SPEED * stats.max_speed * ROUTE_CONTROL_FACTOR
    move_y = C.MAX_VERTICAL_SPEED * stats.max_speed * ROUTE_CONTROL_FACTOR
    position_response = ROUTE_POSITION_RESPONSE * stats.response
    velocity_response = C.FLIGHT_RESPONSE * stats.response
    movement_margin = ROUTE_REACTION_MARGIN_S + ROUTE_REVERSAL_MARGIN_S

    parents: List[Dict[Tuple[int, int], Optional[Tuple[int, int]]]] = []
    previous: set[Tuple[int, int]] = set()
    previous_end = 0.0
    for index, (start, end, members) in enumerate(groups):
        safe = _free_route_cells(members, half_w, half_h)
        if not safe:
            return None
        if index == 0:
            available = max(0.0, start / worst_case_speed - movement_margin)
            reachable = {
                (xi, yi)
                for xi, x in enumerate(_ROUTE_XS)
                for yi, y in enumerate(_ROUTE_YS)
                if _point_reachable(
                    (0.0, C.START_ALTITUDE),
                    (x, y),
                    available,
                    (move_x, move_y),
                    position_response,
                    velocity_response,
                )
            }
            current = {cell: None for cell in safe & reachable}
        else:
            available = max(0.0, (start - previous_end) / worst_case_speed - movement_margin)
            current: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {}
            for px, py in previous:
                if len(current) == len(safe):
                    break  # todas as células já têm um predecessor válido
                x0 = bisect_left(_ROUTE_XS, _ROUTE_XS[px] - move_x * available)
                x1 = bisect_right(_ROUTE_XS, _ROUTE_XS[px] + move_x * available)
                y0 = bisect_left(_ROUTE_YS, _ROUTE_YS[py] - move_y * available)
                y1 = bisect_right(_ROUTE_YS, _ROUTE_YS[py] + move_y * available)
                for xi in range(x0, x1):
                    for yi in range(y0, y1):
                        cell = (xi, yi)
                        if (
                            cell not in current
                            and cell in safe
                            and _point_reachable(
                                (_ROUTE_XS[px], _ROUTE_YS[py]),
                                (_ROUTE_XS[xi], _ROUTE_YS[yi]),
                                available,
                                (move_x, move_y),
                                position_response,
                                velocity_response,
                            )
                        ):
                            current.setdefault(cell, (px, py))
            current = current or {}
        if not current:
            return None
        parents.append(current)
        previous = set(current)
        previous_end = end

    cell = next(iter(previous))
    route: List[Tuple[float, float]] = []
    for layer in reversed(parents):
        route.append((_ROUTE_XS[cell[0]], _ROUTE_YS[cell[1]]))
        parent = layer[cell]
        if parent is not None:
            cell = parent
    route.reverse()
    return route


@dataclass
class _RouteGroup:
    start: float
    end: float
    members: List[Entity]
    before_frontier: set[Tuple[int, int]]
    before_end: float
    frontier: set[Tuple[int, int]]


class RoutePlanner:
    """Mantém o corredor de uma sequência em append; não recomeça do centro no voo."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.factor = C.NORMAL_SPEED_FACTOR if mode == "normal" else 1.0
        self.speed = (C.BASE_SPEED + 100.0 * C.RESTORATION_SPEED_GAIN + C.DIFFICULTY_SPEED_GAIN) * self.factor
        self.stats = plane_stats({})
        self.move_x = C.MAX_LATERAL_SPEED * self.stats.max_speed * ROUTE_CONTROL_FACTOR
        self.move_y = C.MAX_VERTICAL_SPEED * self.stats.max_speed * ROUTE_CONTROL_FACTOR
        self.response = ROUTE_POSITION_RESPONSE * self.stats.response
        self.velocity_response = C.FLIGHT_RESPONSE * self.stats.response
        self.margin = ROUTE_REACTION_MARGIN_S + ROUTE_REVERSAL_MARGIN_S
        self.reset()

    def reset(self, base_player_global: float = C.PLAYER_Z) -> None:
        self.base_player_global = base_player_global
        center_x = bisect_left(_ROUTE_XS, 0.0)
        start_y = bisect_left(_ROUTE_YS, C.START_ALTITUDE)
        self.frontier: set[Tuple[int, int]] = {(center_x, start_y)}
        self.end = 0.0
        self.last_group: Optional[_RouteGroup] = None

    def _safe_cells(self, members: List[Entity]) -> set[Tuple[int, int]]:
        half_w = C.PLANE_WIDTH * 0.42 * self.stats.hitbox
        half_h = C.PLANE_HEIGHT * 0.5 * self.stats.hitbox
        safe = set()
        for xi, x in enumerate(_ROUTE_XS):
            for yi, y in enumerate(_ROUTE_YS):
                if not any(
                    abs(x - entity.x) <= entity.spec.width * 0.5 + half_w
                    and y + half_h >= entity.spec.y_min
                    and y - half_h <= entity.spec.y_max
                    for entity in members
                ):
                    safe.add((xi, yi))
        return safe

    def _extend(
        self,
        start: float,
        end: float,
        members: List[Entity],
        before_frontier: set[Tuple[int, int]],
        before_end: float,
    ) -> Optional[_RouteGroup]:
        safe = self._safe_cells(members)
        if not safe:
            return None
        available = max(0.0, (start - before_end) / self.speed - self.margin)
        axis_masks = []
        for grid, speed, minimum, maximum, horizontal in (
            (_ROUTE_XS, self.move_x, -C.MAX_PLAYER_X, C.MAX_PLAYER_X, True),
            (_ROUTE_YS, self.move_y, C.MIN_ALTITUDE, C.MAX_ALTITUDE, False),
        ):
            masks = []
            for value in grid:
                lower = _axis_reach_limit(
                    value, -1.0, available, speed, minimum, maximum, self.response, self.velocity_response
                )
                upper = _axis_reach_limit(
                    value, 1.0, available, speed, minimum, maximum, self.response, self.velocity_response
                )
                lo = bisect_left(grid, value - lower - 1e-9)
                hi = bisect_right(grid, value + upper + 1e-9)
                masks.append(_ROUTE_X_MASKS[lo][hi] if horizontal else ((1 << (hi - lo)) - 1) << lo)
            axis_masks.append(masks)
        safe_mask = sum(1 << (xi * _ROUTE_Y_COUNT + yi) for xi, yi in safe)
        reachable = 0
        for px, py in before_frontier:
            # Y tem menos de 2**ny: a multiplicação replica bits em blocos
            # disjuntos, sem carry entre colunas nem novas células.
            reachable |= axis_masks[0][px] * axis_masks[1][py]
            if reachable & safe_mask == safe_mask:
                break
        remaining = reachable & safe_mask
        if not remaining:
            return None
        current: set[Tuple[int, int]] = set()
        while remaining:
            bit = remaining & -remaining
            current.add(divmod(bit.bit_length() - 1, _ROUTE_Y_COUNT))
            remaining ^= bit
        return _RouteGroup(start, end, members, set(before_frontier), before_end, current)

    def try_add(self, entity: Entity, entity_global_z: float) -> bool:
        """Acrescenta um perigo futuro sem descartar o corredor já validado."""
        if entity.spec is None or entity.collected or entity.hit or entity.dodged:
            return True
        start = entity_global_z - self.base_player_global - ROUTE_Z_HALF
        end = entity_global_z - self.base_player_global + ROUTE_Z_HALF
        if end < 0.0:
            return True

        last = self.last_group
        if last is not None and start < last.start:
            return False  # preserva a ordem planejada; não reancora num estado inventado
        if last is not None and start <= last.end:
            group = self._extend(
                last.start,
                max(last.end, end),
                last.members + [entity],
                last.before_frontier,
                last.before_end,
            )
        else:
            group = self._extend(start, end, [entity], self.frontier, self.end)
        if group is None:
            return False
        self.last_group = group
        self.frontier = set(group.frontier)
        self.end = group.end
        return True


class World:
    """Estado da pista: trechos, transformação e objetos."""

    def __init__(
        self,
        biome: Biome,
        mode: str = "normal",
        rng: Optional[random.Random] = None,
        intro: bool = False,
        restoration: Optional[float] = None,
        challenge_seed: Optional[int] = None,
        spawn_enabled: bool = True,
    ) -> None:
        self.biome = biome
        self.mode = mode
        self.intro = intro  # abertura didática: uma coisa por vez antes do sorteio
        self.spawn_enabled = bool(spawn_enabled)
        self.challenge_theme: Optional[ChallengeTheme] = challenge_theme_for(biome.key, challenge_seed)
        self.rng = rng or random.Random()
        self.route_planner = RoutePlanner(mode)
        self.restoration = C.START_RESTORATION  # transformação real (jogabilidade)
        self.visual = C.START_RESTORATION  # transformação desenhada (alcança a real aos poucos)
        self.spawn_restoration = C.START_RESTORATION  # avanço de voo ganho; não inclui recuperação passiva
        self.segments: List[float] = []
        self.segment_base = 0
        self.entities: List[Entity] = []
        self.green_since: Dict[int, float] = {}
        self.solar_since: Dict[int, float] = {}
        self.reset(C.START_RESTORATION if restoration is None else restoration)

    # ------------------------------------------------------------ início
    def reset(self, restoration: float = C.START_RESTORATION) -> None:
        self.distance = 0.0
        self.elapsed = 0.0
        self.route_planner.reset(self.distance + C.PLAYER_Z)
        self.segments: List[float] = [
            float(z) for z in range(int(C.SEGMENT_LENGTH), int(C.TRACK_LENGTH) + 1, int(C.SEGMENT_LENGTH))
        ]
        self.segment_base = 0  # índice absoluto de segments[0] na pista
        self.entities: List[Entity] = []
        self.waste_counter = 0
        self.waste_roll = 0
        self.route_obstacles_requested = 0
        self.route_obstacles_kept = 0
        self.route_obstacles_adjusted = 0
        self.route_obstacles_skipped = 0
        self.route_tutorial_failures = 0
        self.obstacle_counters: Dict[str, int] = {
            f"{s}:{k}": 0 for s in ("industrial", "solar") for k in OBSTACLE_KINDS
        }
        self.green_since: Dict[int, float] = {}
        self.solar_since: Dict[int, float] = {}
        self.set_restoration(restoration)
        self.plan_intro()
        z = 520.0
        if self.spawn_enabled:
            while z <= C.TRACK_LENGTH:
                self.spawn_pattern(z)
                z += self.rng.choice((100.0, 120.0, 140.0))
        if self.intro and self.spawn_enabled:
            self.spawn_lessons()

    def set_restoration(self, value: float) -> None:
        """Atribuição direta (início, testes): o cenário fica no estado final na hora."""
        self.restoration = clamp(float(value), 0.0, 100.0)
        self.spawn_restoration = self.restoration
        self.visual = self.restoration
        self.green_since = {}
        self.solar_since = {}
        for i in range(len(self.segments)):
            seg = self.segment_base + i
            if self.green_rank(seg) < self.green_share():
                self.green_since[seg] = -1e12
            if self.solar_rank(seg) < self.solar_share():
                self.solar_since[seg] = -1e12

    # ------------------------------------------------------- transformação
    def add_restoration(self, amount: float, *, earned: bool = True) -> None:
        self.restoration = clamp(self.restoration + amount, 0.0, 100.0)
        if earned:
            self.spawn_restoration = clamp(self.spawn_restoration + amount, 0.0, 100.0)

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
    def solar_rank(seg: int) -> float:
        return (seg * PLASTIC + 0.31) % 1.0

    def green_share(self) -> float:
        if self.visual < C.GRASS_START_RESTORATION:
            return 0.0
        return smoothstep((self.visual - C.GRASS_START_RESTORATION) / C.GREEN_SWEEP_RESTORATION)

    def solar_share(self) -> float:
        if self.visual < C.SOLAR_START_RESTORATION:
            return 0.0
        return smoothstep((self.visual - C.SOLAR_START_RESTORATION) / C.SOLAR_SWEEP_RESTORATION)

    def spawn_solar_share(self) -> float:
        """Share de ameaças solares baseado apenas no progresso ganho em jogo."""
        if self.spawn_restoration < C.SOLAR_START_RESTORATION:
            return 0.0
        return smoothstep((self.spawn_restoration - C.SOLAR_START_RESTORATION) / C.SOLAR_SWEEP_RESTORATION)

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

    def segment_solar(self, seg: int) -> float:
        """0 = estágio anterior, 1 = peça solarpunk crescida."""
        since = self.solar_since.get(seg)
        if since is None:
            return 0.0
        return smoothstep((self.distance - since) / C.SOLAR_GROW_DISTANCE)

    def segment_index(self, z: float) -> Optional[int]:
        if not self.segments:
            return None
        i = int((z - self.segments[0]) // C.SEGMENT_LENGTH)
        return i if 0 <= i < len(self.segments) else None

    def segment_at(self, z: float) -> Optional[int]:
        i = self.segment_index(z)
        return None if i is None else self.segment_base + i

    def solar_at(self, z: float) -> bool:
        seg = self.segment_at(z)
        return seg is not None and self.segment_solar(seg) > 0.0

    def spawn_is_solar(self, z: float) -> bool:
        """Objeto novo em z: usa os obstáculos solarpunk se o trecho dele chega no estágio 3."""
        seg = self.segment_at(z)
        if seg is None:
            seg = self.segment_base + len(self.segments)
        return self.solar_rank(seg) < self.spawn_solar_share()

    def stage_flags(self):
        """Por trecho: (chão verde, estágio solarpunk), calculados uma vez por quadro."""
        green = (
            [self.segment_green(self.segment_base + i) > 0.0 for i in range(len(self.segments))]
            if self.green_since
            else None
        )
        solar = (
            [self.segment_solar(self.segment_base + i) > 0.0 for i in range(len(self.segments))]
            if self.solar_since
            else None
        )
        return green, solar

    # ------------------------------------------------- abertura didática
    def plan_intro(self) -> None:
        """Converte os tempos da abertura em posições absolutas da pista (velocidade inicial)."""
        factor = C.NORMAL_SPEED_FACTOR if self.mode == "normal" else 1.0
        speed = (C.BASE_SPEED + self.restoration * C.RESTORATION_SPEED_GAIN) * factor

        def at(seconds: float) -> float:
            return C.PLAYER_Z + seconds * speed

        self.intro_waste_from = at(C.INTRO_FIRST_WASTE_S) if self.intro else 0.0
        self.intro_until = at(C.INTRO_END_S) if self.intro else 0.0
        self.pending_lessons = [(kind, at(seconds)) for kind, seconds in C.INTRO_LESSONS] if self.intro else []
        self.first_waste_taught = not self.intro

    def in_intro(self, z: float) -> bool:
        return self.distance + z < self.intro_until

    def spawn_lessons(self) -> None:
        """Põe na pista cada obstáculo da abertura quando a posição dele entra no alcance."""
        while self.pending_lessons and self.pending_lessons[0][1] - self.distance <= C.TRACK_LENGTH:
            kind, position = self.pending_lessons.pop(0)
            z = position - self.distance
            solar = self.spawn_is_solar(z)
            spec = self.next_obstacle(kind, solar)
            obstacle = Entity(z, 0, kind, 0.0, spec.sprite, spec, solar, lesson=kind)
            if not self.route_planner.try_add(obstacle, position):
                self.route_tutorial_failures += 1
            self.entities.append(obstacle)
            # um resíduo no caminho certo mostra a resposta: por cima, por baixo ou ao lado
            lane, height = {"low": (0, C.TRASH_HEIGHTS[2]), "gate": (0, C.TRASH_HEIGHTS[0])}.get(
                kind, (self.rng.choice((-1, 1)), C.TRASH_HEIGHTS[1])
            )
            self.entities.append(Entity(z, lane, "waste", height, self.next_waste()))

    def intro_pattern(self, z: float) -> None:
        """Trecho da abertura: só resíduos, longe do caminho dos obstáculos apresentados."""
        position = self.distance + z
        if position < self.intro_waste_from:
            return
        lane = self.rng.choice((-1, 1))  # a faixa do meio fica para as lições
        if self.waste_allowed() or not self.first_waste_taught:
            entity = Entity(z, lane, "waste", C.TRASH_HEIGHTS[1], self.next_waste())
            if not self.first_waste_taught:
                entity.lesson = "waste"
                self.first_waste_taught = True
            self.entities.append(entity)

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

    def add_reachable_obstacle(self, z: float, preferred_lane: int, preferred_kind: str, solar: bool) -> bool:
        """Mantém desafio e procura variante com rota segura no modelo de referência."""
        self.route_obstacles_requested += 1
        alternate_lanes = [lane for lane in (-1, 0, 1) if lane != preferred_lane]
        self.rng.shuffle(alternate_lanes)
        lanes = [preferred_lane] + alternate_lanes
        alternate_kinds = [kind for kind in OBSTACLE_KINDS if kind != preferred_kind]
        self.rng.shuffle(alternate_kinds)
        kinds = [preferred_kind] + alternate_kinds
        for kind in kinds:
            table = self.biome.solar_obstacles if solar else self.biome.industrial_obstacles
            options = table[kind]
            counter_key = f"{'solar' if solar else 'industrial'}:{kind}"
            spec = options[self.obstacle_counters[counter_key] % len(options)]
            for lane in lanes:
                candidate = Entity(z, lane, kind, 0.0, spec.sprite, spec, solar)
                if not self.route_planner.try_add(candidate, self.distance + z):
                    continue
                self.entities.append(candidate)
                self.obstacle_counters[counter_key] += 1
                self.route_obstacles_kept += 1
                if lane != preferred_lane or kind != preferred_kind:
                    self.route_obstacles_adjusted += 1
                return True
        self.route_obstacles_skipped += 1
        return False

    def spawn_pattern(self, z: float) -> None:
        if not self.spawn_enabled:
            return
        if self.in_intro(z):
            self.intro_pattern(z)
            return
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
            kind = self.choose_obstacle_kind(rng.random())
            solar = self.spawn_is_solar(z)
            self.add_reachable_obstacle(z, rng.choice(available), kind, solar)
        if rng.random() < 0.13:
            kind = rng.choice(POWERUP_KINDS)
            self.entities.append(Entity(z + 30.0, rng.choice(lanes), kind, rng.choice(C.TRASH_HEIGHTS)))

    def choose_obstacle_kind(self, roll: float) -> str:
        """Desafios regionais inclinam a sequência sem remover variedades nem planner."""
        if self.challenge_theme is None:
            return "low" if roll < 0.45 else ("gate" if roll < 0.75 else "tower")
        preferred = self.challenge_theme.preferred_obstacle
        alternatives = [kind for kind in OBSTACLE_KINDS if kind != preferred]
        if roll < 0.55:
            return preferred
        return alternatives[0] if roll < 0.55 + 0.225 else alternatives[1]

    # -------------------------------------------------------------- avanço
    def advance(self, dt: float, dz: float) -> None:
        """Move a pista dz unidades em direção ao avião e recicla os trechos que passaram."""
        self.elapsed += dt
        self.distance += dz
        self.ease_visual(dt)
        self._sweep(self.green_since, self.green_rank, self.green_share())
        self._sweep(self.solar_since, self.solar_rank, self.solar_share())
        # Atualize a pista existente antes de adicionar objetos novos: o z local
        # usado pelo planner deve ser o mesmo que a entidade manterá neste quadro.
        for entity in self.entities:
            entity.z -= dz
        if self.intro and self.spawn_enabled:
            self.spawn_lessons()
        segments = self.segments
        for i in range(len(segments)):
            segments[i] -= dz
        while segments and segments[0] < -40.0:
            segments.pop(0)
            self.segment_base += 1
            self.solar_since.pop(self.segment_base - 1, None)
            new_z = (segments[-1] if segments else C.SEGMENT_LENGTH) + C.SEGMENT_LENGTH
            segments.append(new_z)
            if self.spawn_enabled:
                self.spawn_pattern(new_z + 20.0)

    def prune(self) -> None:
        """Remove o que já passou pelo avião ou foi coletado (não cobre a visão)."""
        limit = C.PLAYER_Z - 70.0
        self.entities = [e for e in self.entities if e.z > limit and not e.collected]
