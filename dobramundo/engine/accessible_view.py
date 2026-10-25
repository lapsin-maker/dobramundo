"""Lupa do mundo de jogo: desenho e caixas de colisão ampliam juntos.

O HUD permanece em resolução nativa. Uma transformação única evita aumentar
silhuetas mantendo passagens ou colisões com um tamanho visual diferente.
"""

from __future__ import annotations

import pygame

from .. import config as C
from ..util import clamp


def viewport(scale: float, focus: tuple, plane_size: tuple) -> pygame.Rect:
    scale = clamp(scale, 1.0, 1.6)
    if scale <= 1.0:
        return pygame.Rect(0, 0, C.WIDTH, C.HEIGHT)
    w, h = round(C.WIDTH / scale), round(C.HEIGHT / scale)
    x, y = focus
    half_w = min(C.WIDTH * 0.4, plane_size[0] * scale / 2 + 18)
    half_h = min(180, plane_size[1] * scale / 2 + 12)
    target_x = clamp(x, half_w, C.WIDTH - half_w)
    target_y = clamp(y, 162 + half_h, C.HEIGHT - half_h - 8)
    return pygame.Rect(
        round(clamp(x - target_x / scale, 0, C.WIDTH - w)), round(clamp(y - target_y / scale, 0, C.HEIGHT - h)), w, h
    )


def screen_point(point: tuple, rect: pygame.Rect) -> tuple:
    return ((point[0] - rect.x) * C.WIDTH / rect.width, (point[1] - rect.y) * C.HEIGHT / rect.height)
