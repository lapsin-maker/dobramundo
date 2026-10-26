"""Mapa dos biomas: escolha da fase (Manaus/Amazônia e Petrolina/Caatinga) e do modo.

O contorno do Brasil e as manchas dos biomas são aproximações simplificadas
(longitude, latitude), suficientes para a criança localizar as cidades.
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

import pygame

from .. import config as C
from ..content import texts
from ..content.biomes import BIOME_MAP_COLORS, BIOME_ORDER, BIOMES, LOCKED_BIOMES
from ..ui import theme as T
from ..ui.widgets import star
from .base import Scene

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


def _part_icon(key: str, size: int = 36) -> pygame.Surface:
    """Peças de papel com silhuetas diferentes para cada requisito de voo."""
    icon = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    pygame.draw.circle(icon, T.PAPER, (center, center), center - 1)
    pygame.draw.circle(icon, T.TEAL, (center, center), center - 1, 2)
    if key == "estabilizador":
        shape = [
            (4, center - 3),
            (center - 3, 7),
            (center + 3, 7),
            (size - 4, center - 3),
            (center + 4, center + 5),
            (center - 4, center + 5),
        ]
        pygame.draw.polygon(icon, T.NAVY, shape)
        pygame.draw.line(icon, T.WHITE, (center, 9), (center, size - 9), 2)
    elif key == "leme":
        shape = [
            (center - 4, size - 6),
            (center - 4, center - 1),
            (center - 8, 8),
            (center + 8, 8),
            (center + 4, center - 1),
            (center + 4, size - 6),
        ]
        pygame.draw.polygon(icon, T.NAVY, shape)
        pygame.draw.polygon(icon, T.ORANGE, [(center + 4, 11), (size - 6, 7), (center + 4, 19)])
    else:  # quilha: a lâmina vertical no centro do avião
        shape = [
            (center, 5),
            (center + 7, center - 2),
            (center + 4, size - 6),
            (center, size - 11),
            (center - 4, size - 6),
            (center - 7, center - 2),
        ]
        pygame.draw.polygon(icon, T.NAVY, shape)
        pygame.draw.line(icon, T.WHITE, (center, 9), (center, size - 12), 2)
        pygame.draw.line(icon, T.ORANGE, (center - 9, center + 4), (center + 9, center + 4), 2)
    return icon


_map_cache: Optional[pygame.Surface] = None
_map_cache_texture: Optional[pygame.Surface] = None


def brazil_map(texture: Optional[pygame.Surface] = None) -> pygame.Surface:
    """Mapa geográfico com pigmento aquarelado recortado pelo contorno e cacheado."""
    global _map_cache, _map_cache_texture
    if _map_cache is not None and _map_cache_texture is texture:
        return _map_cache
    size = (C.WIDTH, C.HEIGHT)
    regions = pygame.Surface(size, pygame.SRCALPHA)
    outline = [to_screen(p) for p in BRAZIL]
    pygame.draw.polygon(regions, BIOME_MAP_COLORS["cerrado"], outline)
    for key, polygon in REGIONS.items():
        pygame.draw.polygon(regions, BIOME_MAP_COLORS[key], [to_screen(p) for p in polygon])
    mask = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.polygon(mask, (255, 255, 255, 255), outline)
    pigment = pygame.Surface(MAP_RECT.size)
    pigment.fill((255, 255, 255))
    if texture is not None:
        wash = pygame.transform.smoothscale(texture, MAP_RECT.size)
        wash.set_alpha(76)
        pigment.blit(wash, (0, 0))
    else:
        # Fallback sem asset: manchas sobrepostas em pequenas lavagens, com
        # semente fixa e sem tocar nos limites geográficos.
        rng = random.Random(1804)
        for _ in range(260):
            x = rng.randint(0, MAP_RECT.width)
            y = rng.randint(0, MAP_RECT.height)
            radius = rng.randint(5, 19)
            tint = rng.choice(((252, 239, 207), (225, 240, 238), (221, 230, 235), (252, 227, 198)))
            pygame.draw.circle(pigment, tint, (x, y), radius)
    # Multiplicar uma lavagem clara preserva os tons do bioma e o alpha da
    # máscara do país, em vez de substituir a geografia pela textura raster.
    regions.blit(pigment, MAP_RECT.topleft, special_flags=pygame.BLEND_RGB_MULT)
    regions.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    pygame.draw.polygon(regions, T.NAVY_DARK, outline, 3)
    _map_cache = regions
    _map_cache_texture = texture
    return regions


MODE_CARDS = (
    ("normal", "Normal", "Ritmo calmo", T.GREEN, 1),
    ("dificil", "Difícil", "Ritmo rápido", T.ORANGE, 3),
)
MODE_TOP = 92
CITY_RECTS = (pygame.Rect(635, 260, 440, 100), pygame.Rect(635, 420, 440, 100))


class MapScene(Scene):
    def _travel_card(self, name: str, size: Tuple[int, int]) -> Optional[pygame.Surface]:
        key = ("travel-card-cover", name, size)
        cached = self.watercolor_backgrounds.get(key)
        if cached is not None:
            return cached
        source = self.app.assets.sprite("watercolor", name)
        if source is None:
            return None
        scale = max(size[0] / source.get_width(), size[1] / source.get_height())
        scaled_size = (
            max(size[0], round(source.get_width() * scale)),
            max(size[1], round(source.get_height() * scale)),
        )
        resized = pygame.transform.smoothscale(source, scaled_size)
        left = (resized.get_width() - size[0]) // 2
        top = (resized.get_height() - size[1]) // 2
        card = pygame.Surface(size, pygame.SRCALPHA)
        card.blit(resized, (0, 0), pygame.Rect(left, top, *size))
        self.watercolor_backgrounds[key] = card
        return card

    def build(self) -> None:
        app = self.app
        profile = app.profile
        buttons = []
        for i, (mode, label, sub, color, _) in enumerate(MODE_CARDS):
            buttons.append(
                self.button(
                    (640 + i * 225, MODE_TOP, 165, 100),
                    label,
                    (lambda m=mode: self.set_mode(m)),
                    sublabel=sub if profile.modo != mode else "Escolhido",
                    selected=profile.modo == mode,
                    color=color,
                    size=T.SIZES["label"],
                    key=f"modo_{mode}",
                )
            )
        for i, key in enumerate(BIOME_ORDER):
            unlocked = profile.unlocked(key)
            buttons.append(
                self.button(
                    CITY_RECTS[i],
                    "",
                    (lambda k=key: self.start(k)),
                    enabled=unlocked,
                    key=key,
                    color=BIOME_MAP_COLORS[key],
                )
            )
        buttons.append(self.button((40, 560, 210, 66), texts.UI["voltar"], lambda: self.goto("vila"), key="voltar"))
        self.menu.set_buttons(buttons)

    def set_mode(self, mode: str) -> None:
        self.app.profile.modo = mode
        self.app.save()
        self.build()

    def start(self, key: str) -> None:
        flight = self.app.create_scene("voo", key)
        if not self.app.profile.tutorial_visto:
            tutorial = self.app.create_scene(
                "tutorial",
                next_scene=flight,
                return_to=self.app.create_scene("mapa"),
            )
            flight = tutorial
        body = self.app.input.body
        if body is not None and body.error is None and not body.calibrated:
            flight = self.app.create_scene("calibracao", return_to=flight)
        self.app.save()
        self.app.go(flight)

    def draw(self, screen: pygame.Surface) -> None:
        focused = self.menu.focused
        key = focused.key if focused is not None and focused.key in BIOMES else BIOME_ORDER[0]
        self._draw_geography(screen, key)
        self.title(screen, "Mapa dos biomas", "Escolha o destino e o ritmo do voo")
        self.text.blit(screen, "Ritmo", (642, 68), T.SIZES["small"], T.WHITE, True)
        self.menu.draw(screen, self.text, self.app.options.permanencia)
        self._draw_destinations(screen)
        self._draw_future_biomes(screen)
        self._draw_speed_cues(screen)
        self.menu.draw_pointer(screen, self.dwell_time, self.app.input.body_pointer() is not None)

    def _draw_geography(self, screen: pygame.Surface, key: str) -> None:
        self.app.backdrop(screen, self.last_dt, key, 5.0)
        T.veil(screen, (10, 18, 40), 110)
        T.panel(screen, MAP_RECT.inflate(20, 20), T.PAPER, T.NAVY, 240, 22, 3)
        pigment = self.app.assets.sprite("watercolor_prepared", "map_pigment_v17")
        if pigment is None:
            pigment = self.app.assets.sprite("watercolor", "map_pigment_v17")
        screen.blit(brazil_map(pigment), (0, 0))
        # A rota de aventura é uma pincelada sobre o mapa geográfico existente.
        city_a, city_b = [to_screen(BIOMES[key].map_point) for key in BIOME_ORDER]
        route = [
            city_a,
            (city_a[0] + 10, city_a[1] + 34),
            ((city_a[0] + city_b[0]) // 2, max(city_a[1], city_b[1]) + 72),
            (city_b[0] - 22, city_b[1] + 26),
            city_b,
        ]
        route_layer = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        pygame.draw.lines(route_layer, (255, 255, 248, 220), False, route, 13)
        pygame.draw.lines(route_layer, (238, 132, 69, 245), False, route, 5)
        screen.blit(route_layer, (0, 0))
        for k in BIOME_ORDER:
            biome = BIOMES[k]
            x, y = to_screen(biome.map_point)
            active = k == key
            radius = 13 if active else 9
            pygame.draw.circle(screen, T.WHITE, (x, y), radius + 4)
            pygame.draw.circle(screen, T.ORANGE if active else T.NAVY, (x, y), radius)
            self.text.blit(screen, biome.city, (x + 18, y - 14), T.SIZES["label"], T.NAVY_DARK, True)
            for i in range(3):
                star(screen, (x + 30 + i * 22, y + 26), 10, i < self.app.profile.estrelas.get(k, 0))

    def _draw_destinations(self, screen: pygame.Surface) -> None:
        for key_city in BIOME_ORDER:
            biome = BIOMES[key_city]
            button = next(b for b in self.menu.buttons if b.key == key_city)
            rect = button.rect
            sprite_name = "travel_amazonia" if key_city == "amazonia" else "travel_caatinga"
            art = self._travel_card(sprite_name, (156, 88))
            if art is not None:
                screen.blit(art, art.get_rect(midleft=(rect.left + 8, rect.centery)))
            else:
                fallback = "amazonia_2" if key_city == "amazonia" else "caatinga_2"
                art = self.app.assets.sprite("watercolor", fallback)
                if art is not None:
                    image = self.scaled(art, (156, 88), ("map-card", fallback))
                    screen.blit(image, image.get_rect(midleft=(rect.left + 8, rect.centery)))
                else:
                    pygame.draw.rect(
                        screen,
                        BIOME_MAP_COLORS[key_city],
                        pygame.Rect(rect.left + 12, rect.top + 14, 140, 72),
                        border_radius=14,
                    )
            label_color = T.NAVY_DARK
            self.text.blit(
                screen,
                biome.city,
                (rect.left + 178, rect.top + 9),
                T.SIZES["label"],
                label_color,
                True,
                "topleft",
            )
            self.text.blit(
                screen,
                biome.name,
                (rect.left + 178, rect.top + 43),
                max(T.SIZES["small"], 18),
                label_color,
                True,
                anchor="topleft",
            )
            for star_index in range(3):
                star(
                    screen,
                    (rect.right - 92 + star_index * 25, rect.top + 27),
                    10,
                    star_index < self.app.profile.estrelas.get(key_city, 0),
                )
            if not button.enabled:
                screen.blit(T.icon_surface("star", 27, T.RED), (rect.left + 179, rect.top + 67))
                self.text.blit(
                    screen,
                    "1 estrela antes",
                    (rect.left + 214, rect.top + 80),
                    T.SIZES["small"],
                    T.RED,
                    True,
                    "midleft",
                )
            elif biome.required_parts:
                screen.blit(T.icon_surface("star", 25, T.ORANGE), (rect.left + 179, rect.top + 68))
                self.text.blit(
                    screen,
                    "3ª",
                    (rect.left + 208, rect.top + 81),
                    max(T.SIZES["small"], 18),
                    T.NAVY,
                    True,
                    "midleft",
                )
                x = rect.left + 239
                for part_key, level in biome.required_parts.items():
                    icon = _part_icon(part_key, 30)
                    screen.blit(icon, (x, rect.top + 68))
                    self.text.blit(
                        screen,
                        str(level),
                        (x + 32, rect.top + 84),
                        max(T.SIZES["small"], 18),
                        T.NAVY,
                        True,
                        "midleft",
                    )
                    x += 64

    def _draw_future_biomes(self, screen: pygame.Surface) -> None:
        # Os biomas futuros ficam em duas colunas dentro de um painel legível.
        legend = pygame.Rect(635, 530, 440, 94)
        T.panel(screen, legend, T.PAPER, T.NAVY, 242, 14, 2)
        self.text.blit(screen, "Outros biomas", (650, 536), T.SIZES["small"], T.NAVY, True)
        for i, locked in enumerate(LOCKED_BIOMES):
            col, row = i % 2, i // 2
            cx = 654 + col * 210
            cy = 563 + row * 29
            pygame.draw.circle(screen, locked.color, (cx, cy + 8), 7)
            self.text.blit(screen, locked.name, (cx + 14, cy), T.SIZES["small"], T.INK, True)

    def _draw_speed_cues(self, screen: pygame.Surface) -> None:
        for mode, _, _, color, arrows in MODE_CARDS:
            button = next(b for b in self.menu.buttons if b.key == f"modo_{mode}")
            for k in range(arrows):  # setas de velocidade: 1 no Normal, 3 no Difícil
                x = button.rect.centerx - arrows * 11 + k * 22
                y = button.rect.bottom - 18
                pygame.draw.polygon(screen, color, [(x, y - 10), (x + 14, y), (x, y + 10)])
