"""Mapa dos biomas: escolha da fase (Manaus/Amazônia e Petrolina/Caatinga) e do modo.

O contorno do Brasil e as manchas dos biomas são aproximações simplificadas
(longitude, latitude), suficientes para a criança localizar as cidades.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from .. import config as C
from ..content import texts
from ..content.biomes import BIOME_MAP_COLORS, BIOME_ORDER, BIOMES, LOCKED_BIOMES
from ..persistence import MODE_LABELS
from ..ui import theme as T
from .base import Scene
from .flight import draw_star, flight_or_calibration

LonLat = Tuple[float, float]
BRAZIL: List[LonLat] = [
    (-73.9, -7.4),
    (-72.6, -9.9),
    (-70.5, -11.0),
    (-69.4, -10.9),
    (-65.4, -9.8),
    (-65.3, -11.6),
    (-62.3, -13.0),
    (-60.1, -13.7),
    (-60.0, -16.3),
    (-58.3, -16.3),
    (-58.4, -17.9),
    (-57.6, -19.9),
    (-58.1, -20.2),
    (-57.9, -22.1),
    (-55.7, -22.3),
    (-54.6, -25.6),
    (-53.8, -27.1),
    (-55.6, -28.2),
    (-57.6, -30.2),
    (-56.0, -30.9),
    (-53.4, -33.7),
    (-52.1, -32.0),
    (-50.7, -30.4),
    (-48.6, -28.2),
    (-48.4, -25.8),
    (-46.9, -24.3),
    (-44.7, -23.3),
    (-42.0, -22.9),
    (-40.9, -21.9),
    (-39.7, -19.6),
    (-39.2, -17.7),
    (-38.9, -13.4),
    (-37.0, -11.0),
    (-35.1, -9.0),
    (-34.8, -7.1),
    (-35.3, -5.2),
    (-37.3, -4.7),
    (-39.9, -2.9),
    (-41.9, -2.8),
    (-44.3, -2.5),
    (-48.4, -1.2),
    (-50.0, 0.0),
    (-51.2, 4.1),
    (-51.6, 4.3),
    (-54.0, 2.3),
    (-56.0, 1.9),
    (-58.8, 1.3),
    (-60.0, 5.2),
    (-61.4, 4.3),
    (-63.4, 3.9),
    (-64.8, 4.1),
    (-64.0, 2.0),
    (-66.9, 1.2),
    (-69.4, 1.1),
    (-69.8, -0.3),
    (-69.9, -4.2),
    (-72.9, -5.2),
]
REGIONS = {
    "amazonia": [
        (-75, 6),
        (-75, -12),
        (-62, -13),
        (-60, -14.5),
        (-56, -13),
        (-52, -11.5),
        (-49.5, -9),
        (-48.5, -5.5),
        (-46, -3),
        (-44.5, -1),
        (-50, 6),
    ],
    "caatinga": [
        (-46, -3),
        (-41, -2.6),
        (-37, -4.5),
        (-35.8, -6.0),
        (-36.5, -9.5),
        (-38.5, -12.0),
        (-40.5, -15.5),
        (-43.8, -16.0),
        (-44.5, -13.0),
        (-45.5, -10.0),
        (-44.0, -6.5),
        (-46.0, -4.5),
    ],
    "mata_atlantica": [
        (-35, -6),
        (-34, -8),
        (-38, -13),
        (-39, -18),
        (-41, -22.5),
        (-44.7, -23.4),
        (-48.6, -28.4),
        (-50.5, -30),
        (-53, -29.5),
        (-55.5, -27.5),
        (-54.5, -24.5),
        (-52, -22.5),
        (-48.5, -21.5),
        (-45, -20),
        (-42, -17),
        (-40.5, -15.5),
        (-38.5, -12),
        (-36.5, -9.5),
        (-35.8, -6),
    ],
    "pampa": [(-57.7, -30.2), (-53.4, -33.9), (-51, -31), (-53, -29.5), (-55.5, -28.5)],
    "pantanal": [(-58.2, -16), (-55.5, -16.5), (-55.5, -20.5), (-57.9, -22), (-58.2, -19)],
}
MAP_RECT = pygame.Rect(40, 86, 560, 468)
LON_RANGE = (-74.5, -33.8)
LAT_RANGE = (5.6, -34.2)


def to_screen(point: LonLat, rect: pygame.Rect = MAP_RECT) -> Tuple[int, int]:
    lon, lat = point
    span_lon = LON_RANGE[1] - LON_RANGE[0]
    span_lat = LAT_RANGE[0] - LAT_RANGE[1]
    scale = min(rect.width / span_lon, rect.height / span_lat)
    x = rect.left + (lon - LON_RANGE[0]) * scale + (rect.width - span_lon * scale) / 2
    y = rect.top + (LAT_RANGE[0] - lat) * scale
    return int(x), int(y)


_map_cache: Optional[pygame.Surface] = None


def brazil_map() -> pygame.Surface:
    """Mapa pintado uma vez: Cerrado como fundo e os demais biomas recortados pelo contorno."""
    global _map_cache
    if _map_cache is not None:
        return _map_cache
    size = (C.WIDTH, C.HEIGHT)
    regions = pygame.Surface(size, pygame.SRCALPHA)
    outline = [to_screen(p) for p in BRAZIL]
    pygame.draw.polygon(regions, BIOME_MAP_COLORS["cerrado"], outline)
    for key, polygon in REGIONS.items():
        pygame.draw.polygon(regions, BIOME_MAP_COLORS[key], [to_screen(p) for p in polygon])
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), outline)
    regions.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.polygon(regions, T.NAVY_DARK, outline, 3)
    _map_cache = regions
    return regions


class MapScene(Scene):
    def build(self) -> None:
        from .village import VillageScene

        app = self.app
        profile = app.profile
        buttons = []
        y = 96
        for key in BIOME_ORDER:
            biome = BIOMES[key]
            unlocked = profile.unlocked(key)
            stars = profile.estrelas.get(key, 0)
            sub = f"{biome.name}   •   {stars}/3 estrelas" if unlocked else "Ganhe 1 estrela na fase anterior"
            buttons.append(
                self.button(
                    (640, y, 420, 92),
                    biome.city,
                    (lambda k=key: self.start(k)),
                    sublabel=sub,
                    enabled=unlocked,
                    key=key,
                    color=BIOME_MAP_COLORS[key],
                )
            )
            y += 108
        buttons.append(
            self.button(
                (640, 330, 420, 64),
                f"Modo: {MODE_LABELS[profile.modo]}",
                self.toggle_mode,
                sublabel="Normal: mais calmo   •   Difícil: combo",
                key="modo",
            )
        )
        buttons.append(self.button((640, 560, 420, 70), texts.UI["voltar"], lambda: app.go(VillageScene(app))))
        self.menu.set_buttons(buttons)

    def toggle_mode(self) -> None:
        profile = self.app.profile
        profile.modo = "dificil" if profile.modo == "normal" else "normal"
        self.app.save()
        self.build()

    def start(self, key: str) -> None:
        self.app.save()
        self.app.go(flight_or_calibration(self.app, key))

    def back(self) -> None:
        from .village import VillageScene

        self.app.go(VillageScene(self.app))

    def draw(self, screen: pygame.Surface) -> None:
        focused = self.menu.focused
        key = focused.key if focused is not None and focused.key in BIOMES else BIOME_ORDER[0]
        self.app.backdrop(screen, 1 / 60, key, 5.0)
        T.veil(screen, (10, 18, 40), 110)
        T.panel(screen, MAP_RECT.inflate(20, 20), T.PAPER, T.NAVY, 240, 22, 3)
        screen.blit(brazil_map(), (0, 0))
        for k in BIOME_ORDER:
            biome = BIOMES[k]
            x, y = to_screen(biome.map_point)
            active = k == key
            radius = 13 if active else 9
            pygame.draw.circle(screen, T.WHITE, (x, y), radius + 4)
            pygame.draw.circle(screen, T.ORANGE if active else T.NAVY, (x, y), radius)
            self.text.blit(screen, biome.city, (x + 18, y - 14), T.SIZES["label"], T.NAVY_DARK, True)
            for i in range(3):
                draw_star(screen, (x + 30 + i * 22, y + 26), 9, i < self.app.profile.estrelas.get(k, 0))
        self.title(screen, "Mapa dos biomas", "Escolha a cidade do próximo voo")
        legend_y = 410
        T.panel(screen, pygame.Rect(640, legend_y, 420, 136), T.PAPER, T.NAVY, 235, 16, 2)
        self.text.blit(screen, "Em breve:", (656, legend_y + 10), T.SIZES["body"], T.MUTED, True)
        for i, locked in enumerate(LOCKED_BIOMES):
            cx = 666 + (i % 2) * 200
            cy = legend_y + 52 + (i // 2) * 38
            pygame.draw.circle(screen, locked.color, (cx, cy), 10)
            self.text.blit(screen, locked.name, (cx + 18, cy - 12), T.SIZES["body"], T.INK)
        self.draw_menu(screen)
        for button in self.menu.buttons:
            if button.key in BIOMES and button.enabled:
                for i in range(3):
                    draw_star(
                        screen,
                        (button.rect.right - 80 + i * 26, button.rect.top + 22),
                        10,
                        i < self.app.profile.estrelas.get(button.key, 0),
                    )
