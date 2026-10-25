"""Integração dos aviões ilustrados em aquarela e suas pinturas.

Os sprites vêm em atlas 2x2 RGBA. A cor e as estampas são limitadas ao papel
claro, preservando dobras coloridas, contorno e transparência da ilustração.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import pygame

from ..content.planes import PLANE_KEYS, color_value
from .assets import Assets
from .cache import BoundedCache

MAX_SOURCE_WIDTH = 640
FLIGHT_ATLASES = ("planes_flight_a_clean", "planes_flight_b", "planes_flight_c")
MENU_ATLASES = ("planes_menu_a", "planes_menu_b", "planes_menu_c")


class PaintedPlanes:
    """Carrega, recorta e pinta uma vez cada combinação usada pelo jogo."""

    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self._bases: Dict[Tuple[str, str], Optional[pygame.Surface]] = {}
        self._paper_masks: Dict[str, pygame.Surface] = {}
        self._patterns: Dict[str, Optional[pygame.Surface]] = {}
        self._cache = BoundedCache(96, 40 * 1024 * 1024)

    @staticmethod
    def _atlas_index(plane: str) -> Optional[int]:
        try:
            return PLANE_KEYS.index(plane)
        except ValueError:
            return None

    def _atlas(self, plane: str, view: str) -> Optional[pygame.Surface]:
        index = self._atlas_index(plane)
        if index is None:
            return None
        group, cell_index = divmod(index, 4)
        names = MENU_ATLASES if view == "menu" else FLIGHT_ATLASES
        atlas = self.assets.sprite("watercolor_prepared", names[group])
        if atlas is None:
            atlas = self.assets.sprite("watercolor", names[group])
        if atlas is None and view == "menu":
            atlas = self.assets.sprite("watercolor_prepared", FLIGHT_ATLASES[group])
            if atlas is None:
                atlas = self.assets.sprite("watercolor", FLIGHT_ATLASES[group])
        if atlas is None:
            return None
        cell_w, cell_h = atlas.get_width() // 2, atlas.get_height() // 2
        col, row = cell_index % 2, cell_index // 2
        x0, x1 = col * cell_w, (col + 1) * cell_w
        y0, y1 = row * cell_h, (row + 1) * cell_h
        cell = atlas.subsurface((x0, y0, x1 - x0, y1 - y0)).copy()
        components = pygame.mask.from_surface(cell, 20).connected_components(40)
        if not components:
            return None
        # Atlases podem ter minúsculos fragmentos de tinta fora da figura. Mantém
        # o maior bloco conectado (o avião) antes de calcular o alpha bounding box.
        plane_mask = max(components, key=lambda component: component.count())
        bounds = plane_mask.get_bounding_rects()[0]
        alpha_mask = plane_mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(255, 255, 255, 0))
        cell.blit(alpha_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        cell = cell.subsurface(bounds).copy()
        if cell.get_width() > MAX_SOURCE_WIDTH:
            height = max(1, round(cell.get_height() * MAX_SOURCE_WIDTH / cell.get_width()))
            cell = pygame.transform.smoothscale(cell, (MAX_SOURCE_WIDTH, height))
        return cell

    def base(self, plane: str, view: str) -> Optional[pygame.Surface]:
        key = (plane, view)
        if key not in self._bases:
            self._bases[key] = self._atlas(plane, view)
        return self._bases[key]

    @staticmethod
    def _paper_mask(base: pygame.Surface) -> pygame.Surface:
        """Máscara suave por pixel: claro e pouco saturado é papel cru."""
        raw = pygame.image.tobytes(base, "RGBA")
        mask = bytearray(len(raw))
        for i in range(0, len(raw), 4):
            r, g, b, a = raw[i], raw[i + 1], raw[i + 2], raw[i + 3]
            spread = max(r, g, b) - min(r, g, b)
            if a >= 20 and min(r, g, b) >= 138 and spread <= 90:
                mask[i : i + 4] = b"\xff\xff\xff\xff"
        return pygame.image.frombytes(bytes(mask), base.get_size(), "RGBA")

    @staticmethod
    def _mask_key(base: pygame.Surface) -> str:
        return f"{id(base)}:{base.get_width()}x{base.get_height()}"

    def _pattern(self, assets: Assets, name: str, size: Tuple[int, int]) -> Optional[pygame.Surface]:
        if name not in self._patterns:
            self._patterns[name] = assets.sprite("plane_patterns", name)
        pattern = self._patterns[name]
        if pattern is None:
            return None
        if pattern.get_size() != size:
            return pygame.transform.smoothscale(pattern, size)
        return pattern

    def painted(
        self, plane: str, view: str, color_key: str, pattern_key: str, patterns: Assets
    ) -> Optional[pygame.Surface]:
        base = self.base(plane, view)
        if base is None:
            return None
        if color_key in ("original", "") and pattern_key in ("liso", ""):
            return base
        cache_key = (plane, view, color_key, pattern_key)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        color = color_value(color_key)
        fill = self._pattern(patterns, pattern_key, base.get_size()) if pattern_key != "liso" else None
        if fill is None and color is None:
            return base
        layer = base.copy()
        if color is not None:
            layer.fill(color, special_flags=pygame.BLEND_RGB_MULT)
        if fill is not None:
            layer.blit(fill, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        mask_key = self._mask_key(base)
        mask = self._paper_masks.get(mask_key)
        if mask is None:
            mask = self._paper_masks[mask_key] = self._paper_mask(base)
        layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        out = base.copy()
        out.blit(layer, (0, 0))
        self._cache[cache_key] = out
        return out

    @staticmethod
    def mount_pilot(plane_surface: pygame.Surface, pilot_renderer, plane: str, view: str, look: dict) -> pygame.Surface:
        """Encaixe relativo ao avião ilustrado, independente dos anchors legados."""
        pilot_view = "flight" if view == "flight" else "menu"
        pilot_pose = "back_seated" if view == "flight" else "front_seated"
        pilot = pilot_renderer.compose(pilot_view, look, pose=pilot_pose)
        if pilot is None:
            return plane_surface
        if view == "flight":
            # Em voo, a dobra cobre quadril e pernas: só cabeça, ombros e tronco
            # superior ficam à vista, como alguém sentado dentro da fuselagem.
            visible_height = max(1, round(pilot.get_height() * 0.50))
            pilot = pilot.subsurface((0, 0, pilot.get_width(), visible_height)).copy()
        # O avião tem eixo longitudinal vertical; a cabeça fica perto do cockpit.
        share = (0.20 if plane == "bis14" else 0.24) if view == "flight" else 0.30
        target_h = max(12, round(plane_surface.get_height() * share))
        target_w = max(8, round(pilot.get_width() * target_h / max(1, pilot.get_height())))
        scaled = pygame.transform.smoothscale(pilot, (target_w, target_h))
        center_x = round(plane_surface.get_width() * 0.50)
        top_y = round(plane_surface.get_height() * (0.12 if view == "flight" else 0.20))
        # Não deixa transparência do sprite do piloto expandir o canvas.
        out = plane_surface.copy()
        out.blit(scaled, (center_x - target_w // 2, top_y))
        return out
