"""Aparência do avião: sprite do modelo + pintura (cor ou padrão) + piloto.

Pintura: a camada "paint" de cada sprite é o papel em branco com luz e dobras;
ela é multiplicada pela cor (ou pelo padrão vestido pelo mapa UV, em que G =
linha e R = coluna da textura 256x256) e desenhada sobre o original.
Piloto: montado em camadas (engine/pilot.py) e encaixado no ponto de cada avião.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import pygame

from .. import config as C
from ..content.planes import PLANE_KEYS, color_value
from .assets import Assets
from .cache import BoundedCache
from .painted_planes import PaintedPlanes
from .pilot import PilotRenderer

FOLDERS = {
    "flight": ("plane_sprites", "plane_paint", "plane_uv"),
    "menu": ("plane_menu", "plane_menu_paint", "plane_menu_uv"),
}


class PlaneSkin:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.pilots = PilotRenderer(assets)
        self.painted_planes = PaintedPlanes(assets)
        self.patterns: Dict[str, pygame.Surface] = {}
        for key, surface in assets.folder("plane_patterns").items():
            size = (C.PATTERN_TEXTURE_SIZE, C.PATTERN_TEXTURE_SIZE)
            self.patterns[key] = surface if surface.get_size() == size else pygame.transform.smoothscale(surface, size)
        self.palettes = BoundedCache(C.PATTERN_CACHE_LIMIT)  # ~2,7 MB cada
        self.uv_indices = BoundedCache(8)
        self.cache = BoundedCache(48, 40 * 1024 * 1024)
        self.thumbs: BoundedCache = BoundedCache(32, 4 * 1024 * 1024)

    def base(self, plane: str, view: str) -> Optional[pygame.Surface]:
        watercolor = self.painted_planes.base(plane, view)
        if watercolor is not None:
            return watercolor
        return self.assets.folder(FOLDERS[view][0]).get(f"{plane}__none")

    # ---------------------------------------------------------------- padrões
    def palette(self, pattern: str) -> Optional[list]:
        """Textura do padrão como lista de 65536 pixels RGB (índice = linha * 256 + coluna)."""
        palette = self.palettes.get(pattern)
        if palette is None:
            texture = self.patterns.get(pattern)
            if texture is None:
                return None
            data = pygame.image.tobytes(texture, "RGB")
            palette = [data[i : i + 3] for i in range(0, len(data), 3)]
            self.palettes[pattern] = palette
        return palette

    def uv_index(self, plane: str, view: str, size: Tuple[int, int]) -> Optional[list]:
        key = (plane, view)
        index = self.uv_indices.get(key)
        if index is None:
            uv = self.assets.folder(FOLDERS[view][2]).get(f"{plane}__none")
            if uv is None or uv.get_size() != size:
                return None
            data = pygame.image.tobytes(uv, "RGB")
            index = [(g << 8) | r for r, g in zip(data[0::3], data[1::3])]
            self.uv_indices[key] = index
        return index

    def pattern_fill(self, plane: str, view: str, pattern: str, size: Tuple[int, int]) -> Optional[pygame.Surface]:
        palette = self.palette(pattern)
        index = self.uv_index(plane, view, size) if palette is not None else None
        if palette is None or index is None:
            return None
        return pygame.image.frombytes(b"".join(map(palette.__getitem__, index)), size, "RGB")

    def thumb(self, pattern: str, size: Tuple[int, int]) -> Optional[pygame.Surface]:
        key = (pattern, size)
        thumb = self.thumbs.get(key)
        if thumb is None and pattern in self.patterns:
            thumb = pygame.transform.smoothscale(self.patterns[pattern], size)
            self.thumbs[key] = thumb
        return thumb

    # --------------------------------------------------------------- avião
    def painted(self, plane: str, view: str, color_key: str, pattern: str) -> Optional[pygame.Surface]:
        watercolor = self.painted_planes.painted(plane, view, color_key, pattern, self.assets)
        if watercolor is not None:
            return watercolor
        base = self.base(plane, view)
        color = color_value(color_key)
        if base is None or (color is None and pattern == "liso"):
            return base
        paint = self.assets.folder(FOLDERS[view][1]).get(f"{plane}__none")
        if paint is None or paint.get_size() != base.get_size():
            return base
        fill = self.pattern_fill(plane, view, pattern, base.get_size()) if pattern != "liso" else None
        if fill is None and color is None:
            return base
        layer = paint.copy()
        if fill is not None:
            layer.blit(fill, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        else:
            layer.fill(color, special_flags=pygame.BLEND_RGB_MULT)
        painted = base.copy()
        painted.blit(layer, (0, 0))  # piloto e peças que não são de papel ficam como estavam
        return painted

    def surface(
        self, plane: str, view: str, color_key: str, pattern: str, pilot: Optional[dict]
    ) -> Optional[pygame.Surface]:
        """Avião pintado com o piloto montado por cima (None = sem sprite)."""
        pilot_key = tuple(sorted(pilot.items())) if pilot else None
        key = (plane, view, color_key, pattern, pilot_key)
        result = self.cache.get(key)
        if result is None:
            painted = self.painted(plane, view, color_key, pattern)
            if painted is None:
                return None
            result = painted
            if pilot:
                if self.painted_planes.base(plane, view) is not None:
                    result = self.painted_planes.mount_pilot(painted, self.pilots, plane, view, pilot)
                else:
                    result = self.pilots.mount(painted, plane, view, pilot)
            self.cache[key] = result
        return result

    def look_key(self, plane: str, color_key: str, pattern: str, pilot: Optional[dict]) -> str:
        """Identifica o visual (para os caches de reescala)."""
        pilot_key = "-".join(f"{v}" for _, v in sorted(pilot.items())) if pilot else "sem"
        return f"{plane}@{color_key}+{pattern}#{pilot_key}"

    def models(self) -> List[str]:
        watercolor = [key for key in PLANE_KEYS if self.painted_planes.base(key, "flight") is not None]
        if len(watercolor) == len(PLANE_KEYS):
            return watercolor
        return sorted(k.split("__")[0] for k in self.assets.folder("plane_sprites") if k.endswith("__none"))
