"""Renderer 2D do piloto e encaixe no avião.

O personagem agora usa formas de papel procedurais; anchors.json continua vindo
de assets/pilot_layers e mantém a posição por modelo de avião. As PNGs legadas
seguem disponíveis para compatibilidade de conteúdo/build, mas não são necessárias
para renderizar o piloto novo.
"""

from __future__ import annotations

from typing import Optional, Tuple

import pygame

from ..content.pilot import normalize_pilot
from .assets import Assets
from .cache import BoundedCache
from .paper_pilot import draw_pilot

FOLDER = "pilot_layers"
INK = (29, 36, 51)
MIN_PILOT_SHARE = 0.27  # altura mínima do piloto em relação ao sprite do avião


def tinted(layer: pygame.Surface, color) -> pygame.Surface:
    out = layer.copy()
    out.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return out


def ink_outline(surface: pygame.Surface, color=INK, thickness: int = 2) -> pygame.Surface:
    """Traço de tinta em volta do piloto (mesma linguagem dos sprites "papel e aquarela")."""
    mask = pygame.mask.from_surface(surface, 40)
    line = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((surface.get_width() + 2 * thickness, surface.get_height() + 2 * thickness), pygame.SRCALPHA)
    for dx in range(-thickness, thickness + 1):
        for dy in range(-thickness, thickness + 1):
            if dx * dx + dy * dy <= thickness * thickness + 1:
                out.blit(line, (thickness + dx, thickness + dy))
    out.blit(surface, (thickness, thickness))
    return out


class PilotRenderer:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.anchors = assets.json(FOLDER, "anchors.json") or {}
        self.cache = BoundedCache(32)  # piloto montado por vista e aparência

    def layer(self, view: str, name: str) -> Optional[pygame.Surface]:
        return self.assets.folder(FOLDER).get(f"{view}__{name}")

    def compose(self, view: str, look: dict) -> Optional[pygame.Surface]:
        """Piloto 2D de papel, independente das antigas camadas low-poly."""
        look = normalize_pilot(look)
        key = (view, tuple(sorted(look.items())))
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        canvas = draw_pilot(view, look)
        self.cache[key] = canvas
        return canvas

    def anchor(self, plane: str, view: str) -> Optional[Tuple[int, int, int, int]]:
        box = self.anchors.get(view, {}).get(plane)
        return tuple(box) if box and len(box) == 4 else None  # type: ignore[return-value]

    def mount(self, plane_surface: pygame.Surface, plane: str, view: str, look: dict) -> pygame.Surface:
        """Avião + piloto. Sem camadas geradas, devolve o avião como está.

        O corpo do piloto (caixa "body" do anchors.json, sem cabelo nem cadeira) é
        escalado para a altura da caixa do avião e alinhado pelo centro da base.
        """
        pilot = self.compose(view, look)
        box = self.anchor(plane, view)
        body = self.anchors.get("body", {}).get(view)
        if pilot is None or box is None or not body:
            return plane_surface
        x0, y0, x1, y1 = box
        y0 = min(y0, y1 - int(plane_surface.get_height() * MIN_PILOT_SHARE))  # 14-Bis: boneco quase escondido
        bx0, by0, bx1, by1 = body
        scale = max(4, y1 - y0) / max(1, by1 - by0)
        size = (max(2, int(pilot.get_width() * scale)), max(2, int(pilot.get_height() * scale)))
        pilot_scaled = pygame.transform.smoothscale(pilot, size)
        left = int((x0 + x1) / 2 - (bx0 + bx1) / 2 * scale)
        top = int(y1 - by1 * scale)
        pad_top = max(0, -top)
        pad_left = max(0, -left)
        pad_right = max(0, left + size[0] - plane_surface.get_width())
        pad_bottom = max(0, top + size[1] - plane_surface.get_height())
        out = pygame.Surface(
            (plane_surface.get_width() + pad_left + pad_right, plane_surface.get_height() + pad_top + pad_bottom),
            pygame.SRCALPHA,
        )
        out.blit(plane_surface, (pad_left, pad_top))
        out.blit(pilot_scaled, (left + pad_left, top + pad_top))
        return out
