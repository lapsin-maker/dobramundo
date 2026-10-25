"""Física do avião de papel e manobras (só visuais)."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from .. import config as C
from ..content.planes import MANEUVER_STYLES, ManeuverRow
from ..content.progress import PlaneStats
from ..util import clamp
from .entities import Hitbox


class Player:
    """Avião: posição (x lateral, y altura), velocidade, inclinação e câmera que o segue."""

    def __init__(
        self, stats: PlaneStats = PlaneStats(), maneuvers: Optional[Dict[str, List[ManeuverRow]]] = None
    ) -> None:
        self.stats = stats
        self.curves = maneuvers or {}
        self.reset()

    def reset(self) -> None:
        self.x = 0.0
        self.y = C.START_ALTITUDE
        self.vx = 0.0
        self.vy = 0.0
        self.roll = 0.0
        self.cam_x = 0.0
        self.maneuver: Optional[str] = None
        self.maneuver_time = 0.0

    # ----------------------------------------------------------------- voo
    def update(
        self, dt: float, ix: float, iy: float, target: Optional[Tuple[float, float]] = None, exact: bool = False
    ) -> None:
        """Velocidade (ix: -1 esquerda .. 1 direita; iy: -1 descer .. 1 subir) ou, com target,
        posição: (x, y) do mundo até onde o avião vai suavemente (exact: vai direto, no
        desvio guiado do momento de foco)."""
        stats = self.stats
        response = 1.0 - math.exp(-C.FLIGHT_RESPONSE * stats.response * dt)
        if target is not None and exact:
            self.place(dt, target)
        elif target is not None:
            self.steer_to(dt, target)
        else:
            ix = clamp(ix, -1.0, 1.0)
            iy = clamp(iy, -1.0, 1.0)
            self.vx += (ix * C.MAX_LATERAL_SPEED * stats.max_speed - self.vx) * response
            self.vy += (iy * C.MAX_VERTICAL_SPEED * stats.max_speed - self.vy) * response
            self.x += self.vx * dt
            self.y += self.vy * dt
        if abs(self.x) > C.MAX_PLAYER_X:
            self.x = clamp(self.x, -C.MAX_PLAYER_X, C.MAX_PLAYER_X)
            self.vx = 0.0
        if not C.MIN_ALTITUDE <= self.y <= C.MAX_ALTITUDE:
            self.y = clamp(self.y, C.MIN_ALTITUDE, C.MAX_ALTITUDE)
            self.vy = 0.0
        target_roll = -self.vx / C.MAX_LATERAL_SPEED * C.MAX_ROLL_DEG * stats.roll
        self.roll += (target_roll - self.roll) * response
        self.cam_x += (self.x * C.CAMERA_FOLLOW - self.cam_x) * response
        self.update_maneuver(dt)

    def steer_to(self, dt: float, target: Tuple[float, float]) -> None:
        """Aproxima o avião de target sem passar das velocidades máximas (sem ultrapassar o ponto)."""
        if dt <= 0:
            return
        stats = self.stats
        follow = 1.0 - math.exp(-C.POSITION_RESPONSE * stats.response * dt)
        step_x = C.MAX_LATERAL_SPEED * stats.max_speed * dt
        step_y = C.MAX_VERTICAL_SPEED * stats.max_speed * dt
        dx = clamp((target[0] - self.x) * follow, -step_x, step_x)
        dy = clamp((target[1] - self.y) * follow, -step_y, step_y)
        self.x += dx
        self.y += dy
        self.vx = dx / dt
        self.vy = dy / dt

    def place(self, dt: float, point: Tuple[float, float]) -> None:
        if dt > 0:
            self.vx = (point[0] - self.x) / dt
            self.vy = (point[1] - self.y) / dt
        self.x, self.y = point

    @staticmethod
    def command_target(ax: float, ay: float) -> Tuple[float, float]:
        """Comando corporal (-1..1, 0 na postura calibrada) -> ponto da pista (x, altura)."""
        ax = clamp(ax, -1.0, 1.0)
        ay = clamp(ay, -1.0, 1.0)
        top = C.MAX_ALTITUDE - C.REST_ALTITUDE if ay > 0 else C.REST_ALTITUDE - C.MIN_ALTITUDE
        return ax * C.MAX_PLAYER_X, C.REST_ALTITUDE + ay * top

    def hitbox(self) -> Hitbox:
        half_w = C.PLANE_WIDTH * 0.42 * self.stats.hitbox  # um pouco menor que o desenho
        half_h = C.PLANE_HEIGHT * 0.5 * self.stats.hitbox
        return Hitbox(
            self.x - half_w, self.x + half_w, self.y - half_h, self.y + half_h, C.PLAYER_Z - 27.0, C.PLAYER_Z + 27.0
        )

    # ------------------------------------------------------------ manobras
    def start_maneuver(self, name: Optional[str]) -> None:
        if name in MANEUVER_STYLES:
            self.maneuver = name
            self.maneuver_time = 0.0

    def update_maneuver(self, dt: float) -> None:
        if self.maneuver is None:
            return
        self.maneuver_time += dt
        if self.maneuver_time >= MANEUVER_STYLES[self.maneuver].duration:
            self.maneuver = None
            self.maneuver_time = 0.0

    def maneuver_pose(self) -> Optional[Tuple[float, float, float, float, float]]:
        """(roll, pitch, dx, dy, dz) da manobra atual, interpolados no tempo; None sem manobra."""
        if self.maneuver is None or self.maneuver not in self.curves:
            return None
        rows = self.curves[self.maneuver]
        u = clamp(self.maneuver_time / MANEUVER_STYLES[self.maneuver].duration, 0.0, 1.0)
        for j in range(1, len(rows)):
            if u <= rows[j][0] or j == len(rows) - 1:
                a, b = rows[j - 1], rows[j]
                f = clamp((u - a[0]) / max(1e-6, b[0] - a[0]), 0.0, 1.0)
                return (
                    a[1] + (b[1] - a[1]) * f,
                    a[2] + (b[2] - a[2]) * f,
                    a[3] + (b[3] - a[3]) * f,
                    a[4] + (b[4] - a[4]) * f,
                    a[5] + (b[5] - a[5]) * f,
                )
        return None
