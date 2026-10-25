"""Piloto em camadas, montado sobre o avião.

assets/pilot_layers/<vista>__<camada>.png, geradas por tools/build_assets.py:
    skin, shirt          tons de cinza; recebem a cor escolhida (multiplicação)
    base                 calça, tênis, olhos (cor fixa)
    hair_<estilo>        cinza; recebe a cor do cabelo
    glasses_<estilo>, acc_<estilo>, hearing, chair     cor fixa
Cada camada opcional guarda só os pixels visíveis na cena completa, então a
ordem de desenho (base -> opcionais) já resolve o que fica na frente.
anchors.json: por vista e avião, a caixa [x0, y0, x1, y1] (em pixels do sprite
"__none") onde o piloto senta; y0 negativo = o piloto passa do topo do sprite.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import pygame

from ..content.pilot import ACCESSORIES, GLASSES, HAIR_COLORS, SHIRT_COLORS, SKIN_TONES, find_option, normalize_pilot
from .assets import Assets

FOLDER = "pilot_layers"


def tinted(layer: pygame.Surface, color) -> pygame.Surface:
    out = layer.copy()
    out.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return out


class PilotRenderer:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.anchors = assets.json(FOLDER, "anchors.json") or {}
        self.cache: Dict[tuple, pygame.Surface] = {}

    @property
    def available(self) -> bool:
        return bool(self.assets.folder(FOLDER)) and bool(self.anchors)

    def layer(self, view: str, name: str) -> Optional[pygame.Surface]:
        return self.assets.folder(FOLDER).get(f"{view}__{name}")

    def compose(self, view: str, look: dict) -> Optional[pygame.Surface]:
        """Piloto completo da vista, com as cores escolhidas (em cache por aparência)."""
        look = normalize_pilot(look)
        key = (view, tuple(sorted(look.items())))
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        skin = self.layer(view, "skin")
        if skin is None:
            return None
        canvas = pygame.Surface(skin.get_size(), pygame.SRCALPHA)
        wheelchair = look["cadeira"] == "sim"
        parts = []
        if wheelchair:
            parts.append((self.layer(view, "chair_back"), None))
        parts += [
            (skin, find_option(SKIN_TONES, look["pele"]).color),
            (self.layer(view, "base"), None),
            (self.layer(view, "shirt"), find_option(SHIRT_COLORS, look["roupa"]).color),
        ]
        if look["cabelo"] != "raspado":
            parts.append(
                (self.layer(view, f"hair_{look['cabelo']}"), find_option(HAIR_COLORS, look["cor_cabelo"]).color)
            )
        if look["aparelho"] == "sim":
            parts.append((self.layer(view, "hearing"), None))
        if find_option(GLASSES, look["oculos"]).key != "nenhum":
            parts.append((self.layer(view, f"glasses_{look['oculos']}"), None))
        if find_option(ACCESSORIES, look["acessorio"]).key != "nenhum":
            parts.append((self.layer(view, f"acc_{look['acessorio']}"), None))
        if wheelchair:
            parts.append((self.layer(view, "chair"), None))
        for surface, color in parts:
            if surface is None:
                continue
            canvas.blit(tinted(surface, color) if color is not None else surface, (0, 0))
        if len(self.cache) > 32:
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = canvas
        return canvas

    def anchor(self, plane: str, view: str) -> Optional[Tuple[int, int, int, int]]:
        box = self.anchors.get(view, {}).get(plane)
        return tuple(box) if box and len(box) == 4 else None  # type: ignore[return-value]

    def mount(self, plane_surface: pygame.Surface, plane: str, view: str, look: dict) -> pygame.Surface:
        """Avião + piloto. Sem camadas geradas, devolve o avião como está."""
        pilot = self.compose(view, look)
        box = self.anchor(plane, view)
        if pilot is None or box is None:
            return plane_surface
        x0, y0, x1, y1 = box
        target_h = max(4, y1 - y0)
        scale = target_h / pilot.get_height()
        size = (max(2, int(pilot.get_width() * scale)), target_h)
        pilot_scaled = pygame.transform.smoothscale(pilot, size)
        cx = (x0 + x1) // 2
        left = cx - size[0] // 2
        top = y0
        pad_top = max(0, -top)
        pad_left = max(0, -left)
        pad_right = max(0, left + size[0] - plane_surface.get_width())
        out = pygame.Surface(
            (plane_surface.get_width() + pad_left + pad_right, plane_surface.get_height() + pad_top), pygame.SRCALPHA
        )
        out.blit(plane_surface, (pad_left, pad_top))
        out.blit(pilot_scaled, (left + pad_left, top + pad_top))
        return out
