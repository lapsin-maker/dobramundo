"""Resíduos, power-ups e obstáculos em papel, com fallback vetorial local.

Atlas transparentes opcionais são recortados uma vez; a perspectiva só pede
reescalas cacheadas. Não usa filtros externos nem animação.
"""

from __future__ import annotations

import random
from typing import Dict, Hashable, Tuple

import pygame

from .. import config as C
from ..content.items import POWERUP_COLORS, POWERUP_KINDS, WASTE_BY_KEY
from ..paths import find_asset_file
from .cache import BoundedCache
from .contracts import EntityView
from .sprites import project

Color = Tuple[int, int, int]
Size = Tuple[int, int]
INK: Color = (18, 43, 88)
PAPER: Color = (250, 245, 229)
TEAL: Color = (51, 151, 161)
GREEN: Color = (74, 151, 101)
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
            (26, 21),
            (39, 21),
            (39, 46),
            (42, 54),
            (48, 58),
            (54, 54),
            (57, 46),
            (57, 21),
            (70, 21),
            (70, 47),
            (65, 61),
            (56, 70),
            (48, 73),
            (39, 70),
            (30, 61),
            (26, 47),
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


def _atlas_cells(filename: str, columns: int, rows: int) -> Tuple[pygame.Surface, ...]:
    """Recorta uma grade RGBA do diretório de assets, sem carregar nada por quadro."""
    path = find_asset_file("watercolor", filename)
    if path is None:
        return ()
    try:
        atlas = pygame.image.load(str(path)).convert_alpha()
    except (OSError, pygame.error):
        return ()
    width, height = atlas.get_size()
    if width < columns * 24 or height < rows * 24:
        return ()
    alpha_count = pygame.mask.from_surface(atlas, 1).count()
    if alpha_count == 0 or alpha_count == width * height:
        return ()
    cells = []
    for row in range(rows):
        top = row * height // rows
        bottom = (row + 1) * height // rows
        for col in range(columns):
            left = col * width // columns
            right = (col + 1) * width // columns
            cells.append(atlas.subsurface((left, top, right - left, bottom - top)).copy())
    return tuple(cells)


def _obstacle_atlas_cells() -> Tuple[pygame.Surface, ...]:
    """Recorta arte útil, sem cordas acima nem folhagem abaixo do vão do portal."""
    path = find_asset_file("watercolor", "obstacles_refined.png")
    if path is None:
        return ()
    try:
        atlas = pygame.image.load(str(path)).convert_alpha()
    except (OSError, pygame.error):
        return ()
    # Rects absolutos (x0, y0, x1, y1) no atlas 1536x1024. Para os portais,
    # o limite inferior é a borda física da travessa; corda/vinha ficam de fora.
    crops = (
        (56, 297, 512, 472),  # low industrial: barreira e pés, sem névoa transparente
        (548, 174, 1078, 270),  # gate industrial: vigas e suportes, sem cordas
        (1258, 23, 1412, 480),  # torre industrial
        (31, 655, 512, 953),  # low solar: canteiro até a base
        (548, 646, 1145, 742),  # gate solar: travessa; corta folhas pendentes
        (1223, 513, 1455, 977),  # torre solar
    )
    width, height = atlas.get_size()
    if any(x1 > width or y1 > height or x1 <= x0 or y1 <= y0 for x0, y0, x1, y1 in crops):
        return ()
    try:
        cells = tuple(atlas.subsurface((x0, y0, x1 - x0, y1 - y0)).copy() for x0, y0, x1, y1 in crops)
    except ValueError:
        return ()
    return cells if _valid_atlas(cells, 6) else ()


def _valid_atlas(cells: Tuple[pygame.Surface, ...], count: int) -> bool:
    return len(cells) == count and all(cell.get_bounding_rect(min_alpha=1).size != (0, 0) for cell in cells)


def _compose_atlas_token(base: pygame.Surface, art: pygame.Surface, powerup: bool) -> pygame.Surface:
    """Aplica a arte recortada numa ficha: resíduo circular, benefício hexagonal."""
    result = pygame.Surface((TOKEN_SIZE, TOKEN_SIZE), pygame.SRCALPHA)
    center = (TOKEN_SIZE // 2, TOKEN_SIZE // 2)
    if powerup:
        points = [(48, 5), (84, 26), (84, 69), (48, 91), (12, 69), (12, 26)]
        pygame.draw.polygon(result, INK, points)
        pygame.draw.polygon(result, (104, 178, 181), [(48, 10), (79, 29), (79, 66), (48, 86), (17, 66), (17, 29)])
        pygame.draw.polygon(result, PAPER, [(48, 16), (73, 32), (73, 63), (48, 80), (23, 63), (23, 32)])
        size = (64, 64)
    else:
        result.blit(base, (0, 0))
        size = (66, 66)
    bounds = art.get_bounding_rect(min_alpha=16)
    if bounds.size != (0, 0):
        art = art.subsurface(bounds).copy()
    icon = pygame.transform.smoothscale(art, size)
    if not powerup:
        clip = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.circle(clip, (255, 255, 255, 255), (size[0] // 2, size[1] // 2), size[0] // 2)
        icon.blit(clip, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    result.blit(icon, icon.get_rect(center=center))
    _paper_texture(result, 137 + art.get_width() * 17 + art.get_height(), 15)
    return result


def _silhouette_obstacle(kind: str, solar: bool) -> pygame.Surface:
    """Fallback de suporte: peças estruturais com alpha, nunca placas preenchidas."""
    surface = pygame.Surface(OBSTACLE_SIZE, pygame.SRCALPHA)
    ink = INK
    wood = (106, 116, 99) if solar else (141, 101, 62)
    accent = (85, 171, 137) if solar else (201, 146, 83)
    if kind == "low":
        pygame.draw.line(surface, ink, (0, 159), (79, 0), 12)
        pygame.draw.line(surface, ink, (159, 159), (81, 0), 12)
        pygame.draw.line(surface, wood, (1, 158), (79, 1), 7)
        pygame.draw.line(surface, wood, (158, 158), (81, 1), 7)
        pygame.draw.line(surface, ink, (17, 91), (143, 91), 22)
        pygame.draw.line(surface, accent, (18, 89), (142, 89), 14)
        pygame.draw.line(surface, ink, (80, 28), (80, 20), 12)
    elif kind == "gate":
        pygame.draw.line(surface, ink, (15, 155), (15, 18), 16)
        pygame.draw.line(surface, ink, (145, 155), (145, 18), 16)
        pygame.draw.line(surface, ink, (15, 23), (145, 23), 20)
        pygame.draw.line(surface, accent, (16, 20), (144, 20), 11)
        for x in (15, 145):
            pygame.draw.line(surface, wood, (x, 130), (x + (20 if x == 15 else -20), 154), 8)
    else:
        pygame.draw.line(surface, ink, (80, 8), (80, 155), 18)
        pygame.draw.line(surface, accent, (80, 10), (80, 154), 11)
        pygame.draw.line(surface, ink, (4, 90), (156, 90), 13)
        pygame.draw.line(surface, wood, (5, 87), (155, 87), 7)
        pygame.draw.line(surface, ink, (10, 130), (150, 130), 13)
        pygame.draw.line(surface, wood, (11, 127), (149, 127), 7)
        for y, width in ((36, 94), (70, 74), (104, 54), (138, 32)):
            pygame.draw.line(surface, ink, (80 - width // 2, y), (80 + width // 2, y), 11)
            pygame.draw.line(surface, wood, (80 - width // 2, y - 3), (80 + width // 2, y - 3), 5)
    return surface


def _obstacle_sprite(kind: str, solar: bool) -> pygame.Surface:
    surface = _silhouette_obstacle(kind, solar)
    _paper_texture(surface, (sum(ord(ch) for ch in kind) + (97 if solar else 11)), 30)
    return surface


def _obstacle_outline(source: pygame.Surface, warning: Color) -> pygame.Surface:
    """Contorno de contraste pré-calculado, sem extrair máscaras durante o voo."""
    outline = pygame.Surface(source.get_size(), pygame.SRCALPHA)
    points = pygame.mask.from_surface(source, 16).outline()
    if len(points) > 2:
        thickness = max(4, min(12, min(source.get_size()) // 18))
        pygame.draw.lines(outline, HC_INK, True, points, thickness)
        pygame.draw.lines(outline, warning, True, points, max(2, thickness // 2))
    return outline


class PaperItems:
    """Desenha entidades em papel 2D, projetadas pelas mesmas unidades do hitbox."""

    def __init__(self, cache_limit: int = 192) -> None:
        self.canonical: Dict[Hashable, pygame.Surface] = {}
        item_art = _atlas_cells("items_refined.png", 4, 2)
        for waste in WASTE_BY_KEY.values():
            base = _paper_token(waste.key, waste.color)
            if _valid_atlas(item_art[:7], 7) and len(item_art) == 8:
                index = {"papel": 0, "plastico": 1, "metal": 2, "vidro": 3}[waste.key]
                base = _compose_atlas_token(base, item_art[index], False)
            self.canonical[("waste", waste.key)] = base
        for offset, kind in enumerate(POWERUP_KINDS):
            base = _paper_token(kind, POWERUP_COLORS[kind])
            if _valid_atlas(item_art[:7], 7) and len(item_art) == 8:
                base = _compose_atlas_token(base, item_art[4 + offset], True)
            self.canonical[("powerup", kind)] = base
        obstacle_art = _obstacle_atlas_cells()
        for kind in ("low", "gate", "tower"):
            for solar in (False, True):
                base = _obstacle_sprite(kind, solar)
                if _valid_atlas(obstacle_art, 6):
                    index = (3 if solar else 0) + ("low", "gate", "tower").index(kind)
                    base = obstacle_art[index]
                self.canonical[("obstacle", kind, solar)] = base
        self._scaled: BoundedCache = BoundedCache(cache_limit, 12 * 1024 * 1024)
        self._shadows: BoundedCache = BoundedCache(64, 2 * 1024 * 1024)
        self.regional_skins = set()
        for kind in ("low", "gate", "tower"):
            for solar in (False, True):
                key = ("obstacle", kind, solar)
                warning = CORAL if solar else SUN
                self.canonical[("obstacle-outline", kind, solar)] = _obstacle_outline(self.canonical[key], warning)

    @staticmethod
    def regional_art_names(biome: str) -> tuple[str, ...]:
        if biome == "amazonia":
            return "AM_Balsa", "AM_PassarelaPalafita", "AM_GuindastePorto"
        if biome == "caatinga":
            return "CA_Carroca", "CA_PorticoIrrigacao", "CA_Aerogerador"
        return ()

    def set_region_scenery(self, biome: str, scenery: dict) -> None:
        """Add a local landmark detail inside unchanged obstacle silhouettes.

        The obstacle kind, physical dimensions, and collision contract remain
        owned by the game. This is a cached paper illustration detail only.
        """
        if biome in self.regional_skins:
            return
        names = dict(zip(("low", "gate", "tower"), self.regional_art_names(biome)))
        for kind, name in names.items():
            detail = scenery.get(name)
            if detail is None:
                continue
            for solar in (False, True):
                base = self.canonical[("obstacle", kind, solar)]
                composite = base.copy()
                # Keep the base category silhouette dominant; regional artwork
                # sits within the opening/face and cannot extend the hitbox.
                max_w = max(12, int(base.get_width() * (0.48 if kind == "gate" else 0.56)))
                max_h = max(12, int(base.get_height() * (0.52 if kind == "gate" else 0.48)))
                scale = min(max_w / detail.get_width(), max_h / detail.get_height())
                size = max(1, int(detail.get_width() * scale)), max(1, int(detail.get_height() * scale))
                icon = pygame.transform.smoothscale(detail, size).copy()
                icon.set_alpha(224)
                x = (base.get_width() - size[0]) // 2
                y = int(base.get_height() * (0.43 if kind == "gate" else 0.46)) - size[1] // 2
                composite.blit(icon, (x, max(0, min(base.get_height() - size[1], y))))
                regional_key = ("obstacle-regional", biome, kind, solar)
                self.canonical[regional_key] = composite
                warning = CORAL if solar else SUN
                self.canonical[("obstacle-regional-outline", biome, kind, solar)] = _obstacle_outline(
                    composite, warning
                )
        self.regional_skins.add(biome)

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

    def _draw_token(self, screen: pygame.Surface, entity: EntityView, cam: float, high_contrast: bool) -> None:
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

    def _draw_obstacle(
        self, screen: pygame.Surface, entity: EntityView, cam: float, high_contrast: bool, biome: str = ""
    ) -> None:
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
        base_key = ("obstacle", kind, bool(entity.solar))
        regional_key = ("obstacle-regional", biome, kind, bool(entity.solar))
        key = regional_key if regional_key in self.canonical else base_key
        if high_contrast:
            outline_key = (
                ("obstacle-regional-outline", biome, kind, bool(entity.solar))
                if key == regional_key
                else ("obstacle-outline", kind, bool(entity.solar))
            )
            screen.blit(self._scale(outline_key, (width, height)), rect.topleft)
        sprite = self._scale(key, (width, height))
        screen.blit(sprite, rect)

    def draw(
        self, screen: pygame.Surface, entity: EntityView, cam: float, high_contrast: bool = False, biome: str = ""
    ) -> None:
        """Desenha entidade no centro projetado, sem alterar seu tipo ou hitbox.

        Waste e power-ups usam o centro de sua hitbox (raios 30/28 do mundo);
        obstáculos usam largura e alturas definidas no ``ObstacleSpec``.
        """
        if entity.kind == "waste" or (entity.kind in POWERUP_KINDS and entity.spec is None):
            self._draw_token(screen, entity, cam, high_contrast)
        elif entity.spec is not None:
            self._draw_obstacle(screen, entity, cam, high_contrast, biome)
