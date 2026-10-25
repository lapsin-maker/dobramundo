"""Resíduos, power-ups e obstáculos nativos em papel e aquarela.

Os pictogramas canônicos são desenhados uma única vez; a perspectiva só pede
reescalas cacheadas. Não usa assets, fontes, filtros externos ou animação.
"""

from __future__ import annotations

import random
from typing import Dict, Hashable, Tuple

import pygame

from .. import config as C
from ..content.items import POWERUP_COLORS, POWERUP_KINDS, WASTE_BY_KEY
from ..game.entities import Entity
from .cache import BoundedCache
from .sprites import project

Color = Tuple[int, int, int]
Size = Tuple[int, int]
INK: Color = (18, 43, 88)
PAPER: Color = (250, 245, 229)
PAPER_DARK: Color = (232, 221, 195)
TEAL: Color = (51, 151, 161)
GREEN: Color = (74, 151, 101)
OCHRE: Color = (188, 139, 75)
CORAL: Color = (232, 105, 73)
SUN: Color = (246, 195, 59)
HC_INK: Color = (8, 20, 44)

TOKEN_SIZE = 96
OBSTACLE_SIZE = (160, 160)
OBSTACLE_HEIGHT = 200.0


def _polygon(surface: pygame.Surface, points, color: Color, width: int = 4) -> None:
    pygame.draw.polygon(surface, color, points)
    pygame.draw.polygon(surface, INK, points, width)


def _paper_texture(surface: pygame.Surface, seed: int, count: int = 24) -> None:
    """Pequenas manchas determinísticas, clippeadas à forma, calculadas no build."""
    rng = random.Random(seed)
    width, height = surface.get_size()
    marks = pygame.Surface((width, height), pygame.SRCALPHA)
    for _ in range(count):
        x, y = rng.randrange(width), rng.randrange(height)
        rx, ry = rng.randint(2, 7), rng.randint(2, 5)
        shade = rng.choice(((255, 255, 255, 23), (198, 166, 113, 16), (77, 112, 138, 13)))
        pygame.draw.ellipse(marks, shade, (x - rx, y - ry, 2 * rx, 2 * ry))
    alpha = pygame.mask.from_surface(surface, 1).to_surface(
        setcolor=(255, 255, 255, 255), unsetcolor=(255, 255, 255, 0)
    )
    marks.blit(alpha, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surface.blit(marks, (0, 0))


def _paper_token(key: str, rim: Color) -> pygame.Surface:
    surface = pygame.Surface((TOKEN_SIZE, TOKEN_SIZE), pygame.SRCALPHA)
    center = (TOKEN_SIZE // 2, TOKEN_SIZE // 2)
    pygame.draw.circle(surface, INK, center, 46)
    pygame.draw.circle(surface, rim, center, 42)
    pygame.draw.circle(surface, PAPER, center, 35)
    pygame.draw.circle(surface, (222, 211, 185), center, 31, 1)

    if key == "papel":
        page = [(28, 22), (55, 22), (70, 37), (70, 75), (28, 75)]
        _polygon(surface, page, (255, 253, 241), 3)
        pygame.draw.polygon(surface, (222, 230, 220), [(55, 23), (55, 37), (69, 37)])
        pygame.draw.line(surface, INK, (55, 23), (55, 38), 2)
        pygame.draw.line(surface, INK, (55, 38), (69, 38), 2)
        pygame.draw.line(surface, (105, 148, 172), (35, 49), (62, 61), 2)
        pygame.draw.line(surface, (105, 148, 172), (35, 62), (57, 71), 2)
    elif key == "plastico":
        bottle = [(39, 23), (57, 23), (57, 32), (63, 38), (66, 68), (61, 76), (35, 76), (30, 68), (33, 38), (39, 32)]
        _polygon(surface, bottle, (197, 235, 237), 4)
        pygame.draw.rect(surface, CORAL, (39, 18, 18, 8), border_radius=2)
        pygame.draw.rect(surface, INK, (39, 18, 18, 8), 2, border_radius=2)
        pygame.draw.line(surface, (255, 255, 255), (38, 43), (37, 63), 4)
        pygame.draw.line(surface, CORAL, (33, 49), (64, 49), 3)
        pygame.draw.line(surface, (85, 179, 185), (37, 66), (60, 66), 2)
    elif key == "metal":
        pygame.draw.ellipse(surface, INK, (29, 20, 38, 15))
        pygame.draw.rect(surface, (194, 203, 197), (29, 27, 38, 43))
        pygame.draw.ellipse(surface, (216, 224, 216), (29, 62, 38, 15))
        pygame.draw.ellipse(surface, (236, 240, 231), (32, 22, 32, 9))
        pygame.draw.ellipse(surface, INK, (32, 22, 32, 9), 2)
        pygame.draw.ellipse(surface, (164, 176, 174), (42, 23, 12, 5), 2)
        pygame.draw.line(surface, INK, (29, 29), (29, 67), 3)
        pygame.draw.line(surface, INK, (67, 29), (67, 67), 3)
        pygame.draw.line(surface, (255, 255, 255), (37, 34), (37, 59), 3)
        pygame.draw.line(surface, SUN, (31, 35), (65, 35), 2)
    elif key == "vidro":
        jar = [(39, 23), (57, 23), (57, 32), (64, 37), (64, 68), (59, 75), (37, 75), (32, 68), (32, 37), (39, 32)]
        _polygon(surface, jar, (175, 222, 194), 4)
        pygame.draw.rect(surface, GREEN, (39, 18, 18, 8), border_radius=2)
        pygame.draw.rect(surface, INK, (39, 18, 18, 8), 2, border_radius=2)
        pygame.draw.line(surface, (255, 255, 255), (38, 42), (38, 63), 4)
        pygame.draw.line(surface, (111, 184, 136), (35, 50), (61, 50), 3)
        pygame.draw.line(surface, (111, 184, 136), (35, 55), (61, 55), 2)
    elif key == "shield":
        shield = [(48, 17), (72, 25), (69, 53), (49, 76), (27, 53), (24, 25)]
        _polygon(surface, shield, (87, 193, 219), 5)
        pygame.draw.polygon(surface, (214, 249, 245), [(48, 27), (62, 32), (60, 50), (48, 63), (35, 50), (34, 32)])
        pygame.draw.line(surface, (69, 161, 192), (39, 42), (47, 50), 4)
        pygame.draw.line(surface, (69, 161, 192), (47, 50), (59, 36), 4)
    elif key == "magnet":
        magnet = [
            (26, 21), (39, 21), (39, 46), (42, 54), (48, 58), (54, 54), (57, 46), (57, 21),
            (70, 21), (70, 47), (65, 61), (56, 70), (48, 73), (39, 70), (30, 61), (26, 47),
        ]
        _polygon(surface, magnet, (196, 111, 202), 5)
        pygame.draw.rect(surface, CORAL, (26, 18, 13, 13), border_radius=2)
        pygame.draw.rect(surface, INK, (26, 18, 13, 13), 2, border_radius=2)
        pygame.draw.rect(surface, (84, 151, 216), (57, 18, 13, 13), border_radius=2)
        pygame.draw.rect(surface, INK, (57, 18, 13, 13), 2, border_radius=2)
    elif key == "repair":
        # Chave inglesa com remendo central: leitura simples de conserto.
        pygame.draw.line(surface, INK, (32, 65), (60, 36), 15)
        pygame.draw.line(surface, (110, 190, 145), (32, 65), (60, 36), 9)
        pygame.draw.circle(surface, INK, (30, 67), 10)
        pygame.draw.circle(surface, PAPER, (30, 67), 5)
        pygame.draw.circle(surface, INK, (63, 32), 14, 6)
        pygame.draw.arc(surface, PAPER, (51, 20, 24, 24), 0.2, 2.9, 5)
        pygame.draw.rect(surface, CORAL, (38, 45, 22, 13), border_radius=3)
        pygame.draw.rect(surface, INK, (38, 45, 22, 13), 2, border_radius=3)
        pygame.draw.line(surface, PAPER, (43, 51), (55, 51), 2)

    _paper_texture(surface, sum(ord(ch) for ch in key) + 17, 18)
    return surface


def _arrow(surface: pygame.Surface, direction: str, color: Color = SUN, center=(80, 80), scale: float = 1.0) -> None:
    cx, cy = center
    if direction == "up":
        pts = [(cx, cy - 38 * scale), (cx - 28 * scale, cy - 5 * scale), (cx - 12 * scale, cy - 5 * scale),
               (cx - 12 * scale, cy + 31 * scale), (cx + 12 * scale, cy + 31 * scale),
               (cx + 12 * scale, cy - 5 * scale), (cx + 28 * scale, cy - 5 * scale)]
    elif direction == "down":
        pts = [(cx, cy + 38 * scale), (cx - 28 * scale, cy + 5 * scale), (cx - 12 * scale, cy + 5 * scale),
               (cx - 12 * scale, cy - 31 * scale), (cx + 12 * scale, cy - 31 * scale),
               (cx + 12 * scale, cy + 5 * scale), (cx + 28 * scale, cy + 5 * scale)]
    else:  # lateral: duas setas para deixar claro que o caminho é ao lado
        pygame.draw.polygon(surface, INK, [(cx - 40, cy), (cx - 17, cy - 19), (cx - 17, cy - 8), (cx - 4, cy - 8),
                                          (cx - 4, cy + 8), (cx - 17, cy + 8), (cx - 17, cy + 19)])
        pygame.draw.polygon(surface, color, [(cx - 36, cy), (cx - 18, cy - 14), (cx - 18, cy - 5), (cx, cy - 5),
                                             (cx, cy + 5), (cx - 18, cy + 5), (cx - 18, cy + 14)])
        pygame.draw.polygon(surface, INK, [(cx + 40, cy), (cx + 17, cy - 19), (cx + 17, cy - 8), (cx + 4, cy - 8),
                                          (cx + 4, cy + 8), (cx + 17, cy + 8), (cx + 17, cy + 19)])
        pygame.draw.polygon(surface, color, [(cx + 36, cy), (cx + 18, cy - 14), (cx + 18, cy - 5), (cx, cy - 5),
                                             (cx, cy + 5), (cx + 18, cy + 5), (cx + 18, cy + 14)])
        return
    pygame.draw.polygon(surface, INK, pts)
    inner = [(cx + (x - cx) * 0.72, cy + (y - cy) * 0.72) for x, y in pts]
    pygame.draw.polygon(surface, color, inner)


def _obstacle_sprite(kind: str, solar: bool) -> pygame.Surface:
    surface = pygame.Surface(OBSTACLE_SIZE, pygame.SRCALPHA)
    fill = (75, 151, 111) if solar else OCHRE
    shadow = (40, 108, 80) if solar else (137, 91, 47)
    warn = CORAL if solar else SUN
    surface.fill(fill)
    # Broad paper wash on the main object; a warning strip remains in both eras.
    pygame.draw.rect(surface, shadow, (0, 0, 160, 15))
    for x in range(-4, 164, 30):
        pygame.draw.polygon(surface, warn, [(x, 0), (x + 13, 0), (x - 2, 15), (x - 15, 15)])
    pygame.draw.rect(surface, INK, (2, 2, 156, 156), 5)
    if kind == "low":
        pygame.draw.line(surface, shadow, (5, 55), (155, 55), 6)
        pygame.draw.line(surface, shadow, (5, 105), (155, 105), 6)
        for x in (12, 148):
            pygame.draw.rect(surface, (PAPER_DARK if not solar else (188, 224, 190)), (x - 5, 24, 10, 119))
            pygame.draw.rect(surface, INK, (x - 5, 24, 10, 119), 2)
        _arrow(surface, "up", SUN if solar else (250, 228, 146), center=(80, 83), scale=0.72)
    elif kind == "gate":
        pygame.draw.line(surface, shadow, (4, 88), (156, 88), 10)
        pygame.draw.line(surface, PAPER, (10, 92), (150, 92), 3)
        _arrow(surface, "down", (255, 247, 216), center=(80, 81), scale=0.7)
    else:  # tower
        pygame.draw.rect(surface, shadow, (54, 15, 52, 140), border_radius=7)
        pygame.draw.rect(surface, fill, (61, 18, 38, 136), border_radius=5)
        pygame.draw.rect(surface, INK, (61, 18, 38, 136), 4, border_radius=5)
        pygame.draw.line(surface, (PAPER_DARK if not solar else (192, 229, 199)), (69, 28), (69, 142), 5)
        _arrow(surface, "side", warn, center=(80, 83), scale=0.8)
    _paper_texture(surface, (sum(ord(ch) for ch in kind) + (97 if solar else 11)), 30)
    return surface


class PaperItems:
    """Desenha entidades em papel 2D, projetadas pelas mesmas unidades do hitbox."""

    def __init__(self, cache_limit: int = 192) -> None:
        self.canonical: Dict[Hashable, pygame.Surface] = {}
        for waste in WASTE_BY_KEY.values():
            self.canonical[("waste", waste.key)] = _paper_token(waste.key, waste.color)
        for kind in POWERUP_KINDS:
            self.canonical[("powerup", kind)] = _paper_token(kind, POWERUP_COLORS[kind])
        for kind in ("low", "gate", "tower"):
            for solar in (False, True):
                self.canonical[("obstacle", kind, solar)] = _obstacle_sprite(kind, solar)
        self._scaled: BoundedCache = BoundedCache(cache_limit)
        self._shadows: BoundedCache = BoundedCache(64)

    def _scale(self, key: Hashable, size: Size) -> pygame.Surface:
        size = (max(1, int(size[0])), max(1, int(size[1])))
        cache_key = (key, size)
        hit = self._scaled.get(cache_key)
        if hit is not None:
            return hit
        source = self.canonical[key]
        if source.get_size() == size:
            result = source
        else:
            result = pygame.transform.smoothscale(source, size)
        self._scaled[cache_key] = result
        return result

    def _shadow(self, size: Size) -> pygame.Surface:
        size = (max(2, int(size[0])), max(2, int(size[1])))
        hit = self._shadows.get(size)
        if hit is not None:
            return hit
        source = pygame.Surface((96, 32), pygame.SRCALPHA)
        pygame.draw.ellipse(source, (20, 32, 59, 62), (2, 2, 92, 28))
        result = pygame.transform.smoothscale(source, size)
        self._shadows[size] = result
        return result

    def _draw_token(self, screen: pygame.Surface, entity: Entity, cam: float, high_contrast: bool) -> None:
        if entity.kind == "waste":
            key = ("waste", entity.sprite if entity.sprite in WASTE_BY_KEY else "papel")
            radius = 30.0
            color = WASTE_BY_KEY[key[1]].color
        else:
            key = ("powerup", entity.kind)
            radius = 28.0
            color = POWERUP_COLORS[entity.kind]
        sx, sy, scale = project(entity.x, entity.y, entity.z, cam)
        diameter = max(2, int(2 * radius * scale))
        if diameter > C.HEIGHT * 2:
            return
        ground_x, ground_y, _ = project(entity.x, 0.0, entity.z, cam)
        shadow_w = max(3, int(2 * radius * scale * 1.25))
        shadow_h = max(2, int(shadow_w * 0.28))
        screen.blit(self._shadow((shadow_w, shadow_h)), (int(ground_x - shadow_w / 2), int(ground_y - shadow_h / 2)))
        if high_contrast:
            rim = diameter // 2 + max(2, int(3 * scale))
            pygame.draw.circle(screen, HC_INK, (int(sx), int(sy)), rim + 2)
            pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), rim)
            pygame.draw.circle(screen, color, (int(sx), int(sy)), rim - 2, max(2, int(3 * scale)))
        sprite = self._scale(key, (diameter, diameter))
        screen.blit(sprite, (int(sx - diameter / 2), int(sy - diameter / 2)))

    def _draw_obstacle(self, screen: pygame.Surface, entity: Entity, cam: float, high_contrast: bool) -> None:
        spec = entity.spec
        if spec is None:
            return
        kind = spec.kind if spec.kind in ("low", "gate", "tower") else entity.kind
        if kind == "low":
            y_bottom, y_top = 0.0, max(1.0, min(OBSTACLE_HEIGHT, spec.y_max))
        elif kind == "gate":
            y_bottom, y_top = max(0.0, min(OBSTACLE_HEIGHT - 1.0, spec.y_min)), OBSTACLE_HEIGHT
        else:
            y_bottom, y_top = 0.0, OBSTACLE_HEIGHT

        z = max(20.0, entity.z)
        center_x = entity.x
        sx, _, scale = project(center_x, 0.0, z, cam)
        left, _, _ = project(center_x - spec.width / 2, 0.0, z, cam)
        right, _, _ = project(center_x + spec.width / 2, 0.0, z, cam)
        _, sy_top, _ = project(center_x, y_top, z, cam)
        _, sy_bottom, _ = project(center_x, y_bottom, z, cam)
        width = max(2, int(right - left))
        height = max(2, int(sy_bottom - sy_top))
        if width > C.WIDTH * 2 or height > C.HEIGHT * 2:
            return
        rect = pygame.Rect(int(sx - width / 2), int(sy_top), width, height)
        if rect.right < 0 or rect.left >= C.WIDTH or rect.bottom < 0 or rect.top >= C.HEIGHT:
            return
        key = ("obstacle", kind, bool(entity.solar))
        if high_contrast:
            warning = CORAL if entity.solar else SUN
            pygame.draw.rect(screen, HC_INK, rect.inflate(8, 8), border_radius=5)
            pygame.draw.rect(screen, warning, rect.inflate(4, 4), width=max(2, int(2 * scale)), border_radius=4)
        sprite = self._scale(key, (width, height))
        screen.blit(sprite, rect)

        # Seta abaixo da travessa: mostra o espaço livre sem cobrir a hitbox do gate.
        if kind == "gate":
            arrow_h = max(7, min(40, int(30 * scale)))
            arrow_w = max(7, int(22 * scale))
            arrow_key = ("arrow", "down", bool(entity.solar))
            arrow = self._scaled.get((arrow_key, (arrow_w, arrow_h)))
            if arrow is None:
                arrow_surface = pygame.Surface((48, 72), pygame.SRCALPHA)
                _arrow(arrow_surface, "down", (255, 255, 255), (24, 36), 0.85)
                self.canonical[arrow_key] = arrow_surface
                arrow = self._scale(arrow_key, (arrow_w, arrow_h))
            arrow_y = int(sy_bottom + 1)
            screen.blit(arrow, (int(sx - arrow_w / 2), arrow_y))

    def draw(self, screen: pygame.Surface, entity: Entity, cam: float, high_contrast: bool = False) -> None:
        """Desenha entidade no centro projetado, sem alterar seu tipo ou hitbox.

        Waste e power-ups usam o centro de sua hitbox (raios 30/28 do mundo);
        obstáculos usam largura e alturas definidas no ``ObstacleSpec``.
        """
        if entity.kind == "waste" or (entity.kind in POWERUP_KINDS and entity.spec is None):
            self._draw_token(screen, entity, cam, high_contrast)
        elif entity.spec is not None:
            self._draw_obstacle(screen, entity, cam, high_contrast)
