"""Cache de sprites reescalados, com neblina e com contorno (alto contraste).

Reduzir a partir de versões pré-reduzidas (mip) é muito mais barato do que
reduzir o PNG inteiro a cada novo tamanho; os resultados ficam num cache com
descarte gradual, que evita engasgos.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from .. import config as C
from ..util import Color, clamp, haze_at
from .cache import BoundedCache

Size = Tuple[int, int]
MIP_CACHE_LIMIT = 600  # ~120 sprites de cenário x 2 lados + aparências do avião
OUTLINE_CACHE_LIMIT = 200
SCALED_CACHE_BYTES = 28 * 1024 * 1024
MIP_CACHE_BYTES = 72 * 1024 * 1024
OUTLINE_CACHE_BYTES = 20 * 1024 * 1024


def project(x: float, y: float, z: float, cam: float) -> Tuple[float, float, float]:
    """Projeção em perspectiva: (x da tela, y da tela, escala)."""
    z = max(20.0, z)
    scale = C.FOV / z
    return C.WIDTH / 2 + (x - cam) * scale, C.HORIZON_Y + (C.CAMERA_HEIGHT - y) * scale, scale


def fog_level(z: float) -> int:
    return int(haze_at(z) * C.FOG_LEVELS + 0.5)


def outline_surface(sprite: pygame.Surface, color: Color, thickness: int) -> pygame.Surface:
    """Sprite com contorno espesso e cor intensificada (modo de alto contraste)."""
    w, h = sprite.get_size()
    pad = thickness
    out = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(sprite, 40)
    silhouette = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    dark = mask.to_surface(setcolor=(0, 0, 0, 255), unsetcolor=(0, 0, 0, 0))
    ring = [
        (dx, dy)
        for dx in range(-pad, pad + 1, max(1, pad // 4))
        for dy in range(-pad, pad + 1, max(1, pad // 4))
        if dx * dx + dy * dy <= pad * pad
    ]
    for dx, dy in ring:
        out.blit(dark, (pad + dx, pad + dy))
    inner = max(1, pad // 2)
    for dx, dy in ((-inner, 0), (inner, 0), (0, -inner), (0, inner)):
        out.blit(silhouette, (pad + dx, pad + dy))
    out.blit(sprite, (pad, pad))
    tint = mask.to_surface(setcolor=(*color, 90), unsetcolor=(0, 0, 0, 0))
    out.blit(tint, (pad, pad))  # cor intensa por cima do desenho original
    return out


class SpriteCache:
    def __init__(self) -> None:
        self.scaled = BoundedCache(C.SPRITE_CACHE_LIMIT, SCALED_CACHE_BYTES)
        self.mips = BoundedCache(MIP_CACHE_LIMIT, MIP_CACHE_BYTES)
        self.outlines = BoundedCache(OUTLINE_CACHE_LIMIT, OUTLINE_CACHE_BYTES)
        self.fog_color: Color = (92, 54, 26)

    def put(self, key: tuple, value: pygame.Surface) -> None:
        self.scaled[key] = value

    def mip_levels(self, sprite: pygame.Surface, key: tuple, flip: bool) -> List[pygame.Surface]:
        levels = self.mips.get((key, flip))
        if levels is None:
            base = pygame.transform.flip(sprite, True, False) if flip else sprite
            levels = [base]
            while min(levels[-1].get_size()) > 20:
                w, h = levels[-1].get_size()
                levels.append(pygame.transform.smoothscale(levels[-1], (max(1, int(w / 1.5)), max(1, int(h / 1.5)))))
            self.mips[(key, flip)] = levels
        return levels

    def get(self, sprite: pygame.Surface, key: tuple, size: Size, flip: bool = False) -> pygame.Surface:
        cache_key = (key, size, flip)
        scaled = self.scaled.get(cache_key)
        if scaled is None:
            levels = self.mip_levels(sprite, key, flip)
            source = levels[0]
            for level in reversed(levels):
                if level.get_width() >= size[0] and level.get_height() >= size[1]:
                    source = level
                    break
            if source.get_size() == size:
                scaled = source
            elif size[1] < 40:
                scaled = pygame.transform.scale(source, size)  # pequeno e distante: o mip já basta
            else:
                scaled = pygame.transform.smoothscale(source, size)
            self.put(cache_key, scaled)
        return scaled

    def fogged(self, scaled: pygame.Surface, cache_key: tuple, level: int) -> pygame.Surface:
        """Mistura o sprite à cor da neblina (nível 1..FOG_LEVELS-1)."""
        key = ("fog", cache_key, level, self.fog_color)
        tinted = self.scaled.get(key)
        if tinted is None:
            amount = level / C.FOG_LEVELS
            mix = min(0.9, amount * 0.95)
            keep = int(255 * (1.0 - mix))
            tinted = scaled.copy()
            alpha = 255 if amount < 0.75 else int(255 * clamp((1.0 - amount) / 0.25, 0.0, 1.0))
            tinted.fill((keep, keep, keep, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            r, g, b = self.fog_color
            tinted.fill((int(r * mix), int(g * mix), int(b * mix), 0), special_flags=pygame.BLEND_RGBA_ADD)
            self.put(key, tinted)
        return tinted

    def outlined_source(self, sprite: pygame.Surface, key: tuple, color: Color) -> pygame.Surface:
        """Versão de alto contraste do sprite inteiro, feita uma vez: depois é reescalada
        pelo cache normal (contornar cada novo tamanho custava ~25 ms por quadro)."""
        cache_key = (key, color)
        result = self.outlines.get(cache_key)
        if result is None:
            result = outline_surface(sprite, color, max(4, sprite.get_height() // 20))
            self.outlines[cache_key] = result
        return result

    def warm(self, sprite: Optional[pygame.Surface], key: tuple, flips=(False,)) -> None:
        if sprite is not None:
            for flip in flips:
                self.mip_levels(sprite, key, flip)
