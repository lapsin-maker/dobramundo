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
    def update(self, dt: float, ix: float, iy: float) -> None:
        """ix: -1 (esquerda) .. 1 (direita); iy: -1 (descer) .. 1 (subir)."""
        ix = clamp(ix, -1.0, 1.0)
        iy = clamp(iy, -1.0, 1.0)
        stats = self.stats
        response = 1.0 - math.exp(-C.FLIGHT_RESPONSE * stats.response * dt)
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
