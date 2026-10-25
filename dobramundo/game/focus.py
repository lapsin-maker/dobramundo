"""Momento de foco: perto de uma batida, o tempo desacelera e uma seta pede um movimento.

Quando um obstáculo vai atingir o avião em pouco tempo e a criança ainda não
reagiu, o mundo passa a andar a FOCUS_SLOW da velocidade e a cena mostra uma seta
com o movimento que resolve: subir (obstáculo baixo), descer (portal) ou ir para
o lado livre (torre). Os relógios do momento correm em tempo real, então a janela
dura o mesmo por mais lento que o mundo esteja.

Só vale um movimento novo, medido a partir do comando que havia quando a seta
apareceu: já estar inclinado antes não conta. Acertou: o avião faz um desvio
guiado até um ponto seguro, espera ali o obstáculo passar e o obstáculo não bate.
Não deu: o tempo volta ao normal e o obstáculo só bate se o avião continuar no
caminho.

Não desenha nem toca som: publica eventos no voo ("foco", "foco_ok", "foco_quase").
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, List, Optional, Tuple

from .. import config as C
from ..util import clamp, smoothstep
from .entities import Entity, Hitbox, entity_hitbox

if TYPE_CHECKING:  # evita importação circular (o voo cria o momento de foco)
    from .run import FlightRun

Point = Tuple[float, float]
DIRECTIONS = ("up", "down", "left", "right")
# Movimento que cada tipo de obstáculo ensina; os lados ficam como alternativa.
PREFERRED = {"low": ("up", "left", "right"), "gate": ("down", "left", "right"), "tower": ("left", "right")}


def time_to_contact(entity: Entity, speed: float) -> Optional[float]:
    """Segundos de mundo até a frente do obstáculo tocar a caixa do avião (None se já tocou)."""
    gap = (entity.z - 16.0) - (C.PLAYER_Z + 27.0)
    if gap < 0 or speed <= 0:
        return None
    return gap / speed


def overlaps_across(a: Hitbox, b: Hitbox) -> bool:
    """Sobreposição só em x e y (a profundidade é o tempo até a batida)."""
    return a.x_min <= b.x_max and a.x_max >= b.x_min and a.y_min <= b.y_max and a.y_max >= b.y_min


def box_at(box: Hitbox, x: float, y: float) -> Hitbox:
    """A caixa do avião deslocada para o ponto (x, y)."""
    cx, cy = (box.x_min + box.x_max) / 2, (box.y_min + box.y_max) / 2
    return Hitbox(box.x_min + x - cx, box.x_max + x - cx, box.y_min + y - cy, box.y_max + y - cy, box.z_min, box.z_max)


def safe_point(entity: Entity, box: Hitbox, start: Point, direction: str) -> Optional[Point]:
    """Ponto do avião que passa livre do obstáculo indo na direção pedida (None se não couber)."""
    obstacle = entity_hitbox(entity)
    half_w = (box.x_max - box.x_min) / 2
    half_h = (box.y_max - box.y_min) / 2
    x, y = start
    if direction == "up":
        y = obstacle.y_max + half_h + C.FOCUS_MARGIN
        ok = y <= C.MAX_ALTITUDE
    elif direction == "down":
        y = obstacle.y_min - half_h - C.FOCUS_MARGIN
        ok = y >= C.MIN_ALTITUDE
    elif direction == "left":
        x = obstacle.x_min - half_w - C.FOCUS_MARGIN
        ok = x >= -C.MAX_PLAYER_X
    else:
        x = obstacle.x_max + half_w + C.FOCUS_MARGIN
        ok = x <= C.MAX_PLAYER_X
    return (x, y) if ok else None


def choose_escape(entity: Entity, box: Hitbox, start: Point) -> Optional[Tuple[str, Point]]:
    """Direção e ponto seguro para o obstáculo; nos lados, primeiro o mais perto."""
    options = list(PREFERRED.get(entity.kind, ("left", "right")))
    sides = [d for d in options if d in ("left", "right")]
    if start[0] > entity.x:  # o lado em que o avião já está vem primeiro
        sides.reverse()
    options = [d for d in options if d not in ("left", "right")] + sides
    for direction in options:
        point = safe_point(entity, box, start, direction)
        if point is not None:
            return direction, point
    return None


def moved_towards(direction: str, baseline: Point, command: Point, step: float = C.FOCUS_STEP) -> bool:
    """O comando andou ao menos step na direção pedida desde baseline."""
    dx, dy = command[0] - baseline[0], command[1] - baseline[1]
    return {"up": dy, "down": -dy, "left": -dx, "right": dx}[direction] >= step


class FocusMoment:
    """Estados: None (voo normal), "pending" (seta esperando), "success" ou "miss" (legenda)."""

    def __init__(self, mode: str = "normal", enabled: bool = True) -> None:
        self.enabled = enabled
        self.window = C.FOCUS_WINDOW_S.get(mode, C.FOCUS_WINDOW_S["normal"])
        self.state: Optional[str] = None
        self.remaining = 0.0  # segundos reais da seta ou da legenda
        self.cooldown = C.FOCUS_FIRST_S
        self.direction = "up"
        self.target: Optional[Entity] = None
        self.baseline: Optional[Point] = None
        self.guide_from: Point = (0.0, 0.0)
        self.guide_to: Optional[Point] = None
        self.planned: Point = (0.0, 0.0)  # ponto seguro calculado ao abrir a seta
        self.guide_time = 0.0  # segundos reais desde o início do desvio guiado
        self.successes = 0
        self.misses = 0

    # ---------------------------------------------------------- consultas
    @property
    def time_scale(self) -> float:
        """Fração da velocidade normal em que o mundo anda agora."""
        if self.state == "pending":
            return C.FOCUS_SLOW
        if self.guide_to is not None and self.guide_time < C.FOCUS_GUIDE_S:
            return C.FOCUS_GUIDE_SLOW
        return 1.0

    @property
    def progress(self) -> float:
        """Parte da janela que ainda resta (1 -> 0) enquanto a seta espera."""
        return self.remaining / self.window if self.state == "pending" else 0.0

    @property
    def guiding(self) -> bool:
        return self.guide_to is not None

    @property
    def total(self) -> int:
        return self.successes + self.misses

    def guide_point(self) -> Optional[Point]:
        """Onde o avião deve estar agora no desvio guiado (None fora dele)."""
        if self.guide_to is None:
            return None
        t = smoothstep(self.guide_time / C.FOCUS_GUIDE_S)
        (x0, y0), (x1, y1) = self.guide_from, self.guide_to
        return x0 + (x1 - x0) * t, y0 + (y1 - y0) * t

    # ------------------------------------------------------------ quadro
    def update(self, run: FlightRun, real_dt: float, command: Point, intended: Point) -> None:
        """Um quadro em tempo real. command: comando atual (-1..1); intended: aonde o avião
        está indo (alvo do controle por posição ou projeção da velocidade)."""
        if run.finished or run.complete or run.game_over:
            self.cancel()
            return
        self.cooldown = max(0.0, self.cooldown - real_dt)
        if self.guide_to is not None:
            self.update_guide(real_dt)
        if self.state == "pending":
            self.remaining = max(0.0, self.remaining - real_dt)
            if self.baseline is not None and moved_towards(self.direction, self.baseline, command):
                self.succeed(run)
            elif self.remaining == 0.0:
                self.miss(run)
        elif self.state is not None:
            self.remaining = max(0.0, self.remaining - real_dt)
            if self.remaining == 0.0:
                self.state = None
        elif self.can_open(run):
            self.find_threat(run, command, intended)

    def can_open(self, run: FlightRun) -> bool:
        return (
            self.enabled
            and self.guide_to is None
            and not run.invincible
            and run.invulnerable_timer == 0.0
            and run.shield_timer == 0.0
        )

    def find_threat(self, run: FlightRun, command: Point, intended: Point) -> None:
        """Abre o momento para o obstáculo que bateria primeiro, dentro de FOCUS_IMPACT_S."""
        player = run.player
        box = player.hitbox()
        here = (player.x, player.y)
        best: Optional[Entity] = None
        soonest = C.FOCUS_IMPACT_S[1]
        for entity in self.obstacles(run.world.entities):
            if self.cooldown > 0.0 and not entity.lesson:
                continue  # os obstáculos da abertura didática sempre têm o seu momento
            contact = time_to_contact(entity, run.speed)
            if contact is None or not C.FOCUS_IMPACT_S[0] <= contact <= soonest:
                continue
            obstacle = entity_hitbox(entity)
            # só se bate onde o avião está E aonde ele está indo (a criança não reagiu)
            if overlaps_across(box, obstacle) and overlaps_across(box_at(box, *intended), obstacle):
                best, soonest = entity, contact
        if best is None:
            return
        escape = choose_escape(best, box, here)
        if escape is None:
            return
        self.direction, self.guide_to = escape[0], None
        self.planned = escape[1]
        best.focused = True
        self.target = best
        self.baseline = command
        self.state, self.remaining = "pending", self.window
        self.cooldown = C.FOCUS_COOLDOWN_S
        run.emit("foco", self.direction)

    @staticmethod
    def obstacles(entities: Iterable[Entity]) -> List[Entity]:
        return [e for e in entities if e.spec is not None and not (e.hit or e.passed or e.dodged or e.focused)]

    def succeed(self, run: FlightRun) -> None:
        self.successes += 1
        self.state, self.remaining = "success", C.FOCUS_CAPTION_S
        player = run.player
        self.guide_from = (player.x, player.y)
        self.guide_to = self.planned
        self.guide_time = 0.0
        if self.target is not None:
            self.target.dodged = True  # o desvio guiado garante a passagem
        run.score += C.FOCUS_POINTS
        run.emit("foco_ok", self.direction)

    def miss(self, run: FlightRun) -> None:
        self.misses += 1
        self.state, self.remaining = "miss", C.FOCUS_CAPTION_S
        self.target = None
        run.emit("foco_quase", self.direction)

    def update_guide(self, real_dt: float) -> None:
        """Desvio guiado e espera no ponto seguro até o obstáculo passar."""
        self.guide_time += real_dt
        target = self.target
        passed = target is None or target.z < C.PLAYER_Z - 40.0
        if self.guide_time >= C.FOCUS_GUIDE_S and (passed or self.guide_time >= C.FOCUS_GUIDE_S + C.FOCUS_GUIDE_HOLD_S):
            self.guide_to = None
            self.target = None

    def cancel(self) -> None:
        self.state = None
        self.guide_to = None
        self.target = None


def intended_point(player, target: Optional[Point]) -> Point:
    """Aonde o avião vai: o alvo do controle por posição ou a projeção da velocidade atual."""
    if target is not None:
        return target
    lead = C.FOCUS_IMPACT_S[1]
    return (
        clamp(player.x + player.vx * lead, -C.MAX_PLAYER_X, C.MAX_PLAYER_X),
        clamp(player.y + player.vy * lead, C.MIN_ALTITUDE, C.MAX_ALTITUDE),
    )
