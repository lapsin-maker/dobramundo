"""Céu em camadas de paralaxe: degradê, panorama poluído, nuvens, silhuetas do
horizonte e decoração móvel (dirigível, balões, barco ou bonde, pássaros).

Do fundo para a frente, cada camada anda uma fração diferente do deslocamento
da câmera (o avião é o referencial): céu < nuvens < silhuetas < cenário.
"""

from __future__ import annotations

import math
import random
import time
from typing import Dict, List, Optional, Tuple

import pygame

from .. import config as C
from ..content.biomes import Biome
from ..util import Color, clamp, lerp_color, rgb
from .assets import Assets, display_format
from .cache import BoundedCache

# Silhuetas industriais do horizonte (assets/skyline_sprites): fileira de trás e da frente.
SKYLINE_BACK = [
    ("distant_factory", 70),
    ("background_silo", 96),
    ("power_pylon", 110),
    ("industrial_chimney", 84),
    ("distant_factory", 60),
    ("industrial_tower_a", 92),
    ("cargo_elevator", 52),
    ("background_silo", 80),
    ("power_pylon", 100),
    ("fixed_crane", 88),
    ("distant_factory", 66),
    ("pressure_tank", 58),
]
SKYLINE_FRONT = [
    ("industrial_tower_a", 128),
    ("distant_factory", 92),
    ("industrial_chimney", 140),
    ("fixed_crane", 120),
    ("power_pylon", 150),
    ("pressure_tank", 74),
    ("background_silo", 132),
    ("distant_factory", 84),
    ("cargo_elevator", 70),
]
CLOUD_LAYOUT = [  # x, y, largura, deriva, paralaxe, opacidade
    (60, 18, 420, 0.010, 0.55, 0.95),
    (520, 70, 300, 0.016, 0.80, 0.85),
    (900, 30, 460, 0.008, 0.45, 0.95),
    (1300, 110, 260, 0.020, 1.00, 0.75),
    (1620, 52, 380, 0.012, 0.65, 0.90),
    (260, 128, 220, 0.024, 1.15, 0.70),
    (1120, 150, 240, 0.022, 1.10, 0.65),
]


SUN_POS = (730, 96)  # no céu, à direita do centro (fora do painel de vidas); anda um pouco com a câmera
SUN_RADIUS = 40
CLOUD_INK = (28, 52, 110)


def paper_cloud(width: int, seed: int) -> pygame.Surface:
    """Nuvem de papel recortado: montes arredondados, base reta, sombra azulada e traço de tinta."""
    rng = random.Random(seed)
    height = int(width * 0.46)
    surface = pygame.Surface((width + 8, height + 8), pygame.SRCALPHA)
    base_y = height - 4
    bumps = []
    x = width * 0.12
    while x < width * 0.9:
        r = rng.uniform(0.14, 0.24) * width
        bumps.append((x, base_y - r * rng.uniform(0.55, 0.95), r))
        x += r * rng.uniform(0.9, 1.3)
    bumps.append((width * 0.5, base_y - width * 0.12, width * 0.22))
    for color, grow in (((*CLOUD_INK, 170), 3), ((248, 251, 255, 255), 0)):
        for cx, cy, r in bumps:
            pygame.draw.circle(surface, color, (int(cx) + 4, int(cy) + 4), int(r) + grow)
        pygame.draw.rect(
            surface,
            color,
            (int(bumps[0][0]) + 4 - grow, base_y - 6, int(bumps[-1][0] - bumps[0][0]) + 2 * grow, 10 + grow),
        )
    # sombra azulada na metade de baixo (papel dobrado) e base reta
    shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for cx, cy, r in bumps:
        pygame.draw.circle(shade, (176, 204, 236, 255), (int(cx) + 4, int(cy) + 4 + int(r * 0.45)), int(r))
    mask = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    mask.blit(surface, (0, 0))
    mask.fill((255, 255, 255, 255), special_flags=pygame.BLEND_RGB_MAX)
    shade.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surface.blit(shade, (0, 0))
    pygame.draw.rect(surface, (0, 0, 0, 0), (0, base_y + 6, width + 8, height + 8 - base_y - 6))
    pygame.draw.line(
        surface, (*CLOUD_INK, 170), (int(bumps[0][0]) + 2, base_y + 5), (int(bumps[-1][0]) + 6, base_y + 5), 3
    )
    return surface


def blit_tiled(screen: pygame.Surface, surface: pygame.Surface, offset: float, y: int) -> None:
    """Desenha uma faixa que se repete na horizontal, deslocada por offset."""
    tile = surface.get_width()
    x = -(offset % tile)
    while x < C.WIDTH:
        screen.blit(surface, (int(x), y))
        x += tile


class SkyRenderer:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        # Heavy image decode/preparation is scheduled by WorldView's sliced
        # warm-up queue instead of happening in App construction/set_biome.
        self.panorama_base = None
        self.panorama = self.panorama_base
        self._smog_source = None
        self._smog_loaded = False
        self.clouds = []
        self.skyline_sprites = {}
        self.gradients = BoundedCache(24, 20 * 1024 * 1024)
        self.decor_cache = BoundedCache(64, 20 * 1024 * 1024)
        self.biome: Optional[Biome] = None
        self.pollution = 1.0
        self.fog_color: Color = (92, 54, 26)
        self.fog_sprite_color: Color = (92, 54, 26)
        self.decor_x: List[float] = []
        self.vehicle_x = 0.0
        self.birds_x = 300.0
        self.skyline_cache: Dict[str, Optional[pygame.Surface]] = {}
        self.skyline_state: Dict[str, dict] = {}
        self.decor_sprites: Dict[str, pygame.Surface] = {}

    def set_biome(self, biome: Biome) -> None:
        if self.biome is biome:
            return
        self.biome = biome
        self.panorama = self.panorama_base
        self.decor_sprites = {}
        self.skyline_cache = {}
        self.skyline_state = {}
        self.decor_cache = BoundedCache(64, 20 * 1024 * 1024)
        count = max(1, len(biome.sky_decor))
        self.decor_x = [i * C.DECOR_CYCLE / count + 120 * i for i in range(len(biome.sky_decor))]

    def prepare_atmosphere_asset(self, name: str) -> None:
        image = self.assets.sprite("atmosphere", name)
        if name == "sky_panorama":
            self.panorama_base = self.prepare_panorama(image)
            self.panorama = self.panorama_base
        elif name == "smog_cloud":
            self._smog_source = image
            self._smog_loaded = True

    def prepare_cloud(self, index: int) -> None:
        if len(self.clouds) > index:
            return
        if not self._smog_loaded:
            return
        if self._smog_source is None:
            self.clouds = []
            return
        x, y, width, drift, parallax, opacity = CLOUD_LAYOUT[index]
        smoke = pygame.transform.smoothscale(self._smog_source, (width, int(width * 0.42)))
        smoke.fill((38, 30, 24, 0), special_flags=pygame.BLEND_RGBA_ADD)
        clean = display_format(paper_cloud(int(width * 0.8), index), alpha=True)
        self.clouds.append(
            {
                "x": float(x),
                "y": y,
                "w": width,
                "drift": drift,
                "parallax": parallax,
                "opacity": opacity,
                "smoke": smoke,
                "clean": clean,
                "baked": BoundedCache(24, 2 * 1024 * 1024),
            }
        )

    def prepare_tinted_panorama(self) -> None:
        if self.biome is not None:
            self.panorama = self.tint_panorama(self.biome)

    def prepare_decor(self, name: str) -> None:
        self.decor_sprites.update(self.assets.scenery_for((name,)))

    def prepare_skyline_sprite(self, name: str) -> None:
        sprite = self.assets.sprite("skyline_sprites", name)
        if sprite is not None:
            self.skyline_sprites[name] = sprite

    def release_biome_cache(self) -> None:
        """Solta faixas e variações específicas de uma fase já encerrada."""
        self.biome = None
        self.panorama = self.panorama_base
        self.skyline_cache.clear()
        self.skyline_state.clear()
        self.decor_cache.clear()
        self.decor_sprites = {}
        self.decor_x = []

    # ------------------------------------------------------------ preparo
    def tint_panorama(self, biome: Biome) -> Optional[pygame.Surface]:
        """O panorama de fumaça do kit é alaranjado; aqui ele vira cinza e recebe a cor do bioma
        (névoa úmida em Manaus, poeira ocre em Petrolina), para cada fase poluída ter a sua cara."""
        base = self.panorama_base
        if base is None:
            return None
        grey = pygame.transform.grayscale(base)
        tinted = grey.copy()
        top, horizon = biome.stages[0].sky_top, biome.stages[0].sky_horizon
        tone = lerp_color(top, horizon, 0.55)
        tinted.fill(tone, special_flags=pygame.BLEND_RGB_MULT)
        tinted.fill((60, 60, 60), special_flags=pygame.BLEND_RGB_ADD)  # não deixa o céu virar breu
        # a faixa junto do horizonte puxa a cor do horizonte (névoa baixa)
        band = pygame.Surface((tinted.get_width(), 70), pygame.SRCALPHA)
        for y in range(70):
            band.fill((*horizon, int(120 * y / 69)), (0, y, tinted.get_width(), 1))
        tinted.blit(band, (0, tinted.get_height() - 70))
        return display_format(tinted)

    @staticmethod
    def prepare_panorama(panorama: Optional[pygame.Surface]) -> Optional[pygame.Surface]:
        """Recorta o céu do panorama do kit até a linha do horizonte e ajusta à tela."""
        if panorama is None:
            return None
        w, h = panorama.get_size()
        horizon_row = int(h * 0.725)  # faixa alaranjada do horizonte no panorama
        scaled_w, scaled_h = int(w * C.SKY_PANORAMA_SCALE), int(h * C.SKY_PANORAMA_SCALE)
        big = pygame.transform.smoothscale(panorama, (scaled_w, scaled_h))
        top = max(0, int(horizon_row * C.SKY_PANORAMA_SCALE) - C.HORIZON_Y)
        sky = pygame.Surface((scaled_w, C.HORIZON_Y))
        sky.blit(big, (0, -top))
        return display_format(sky)

    @staticmethod
    def prepare_clouds(smog: Optional[pygame.Surface]) -> List[dict]:
        """Nuvens em posições fixas: fumaça (estágio poluído) e nuvem de papel recortado (céu limpo)."""
        if smog is None:
            return []
        clouds = []
        for i, (x, y, w, drift, parallax, opacity) in enumerate(CLOUD_LAYOUT):
            smoke = pygame.transform.smoothscale(smog, (w, int(w * 0.42)))
            smoke.fill((38, 30, 24, 0), special_flags=pygame.BLEND_RGBA_ADD)  # aparece sobre o céu escuro
            clean = display_format(paper_cloud(int(w * 0.8), i), alpha=True)
            clouds.append(
                {
                    "x": float(x),
                    "y": y,
                    "w": w,
                    "drift": drift,
                    "parallax": parallax,
                    "opacity": opacity,
                    "smoke": smoke,
                    "clean": clean,
                    "baked": BoundedCache(24, 2 * 1024 * 1024),
                }
            )
        return clouds

    # --------------------------------------------------------- atmosfera
    def update_atmosphere(self, visual: float, horizon: Color, haze: Color) -> None:
        """Poluição do céu e cor da neblina conforme a transformação visual."""
        self.pollution = clamp(
            1.0 - (visual - C.POLLUTION_CLEAR_START) / (C.POLLUTION_CLEAR_END - C.POLLUTION_CLEAR_START), 0.0, 1.0
        )
        fog = lerp_color(horizon, haze, self.pollution * 0.8)
        self.fog_color = fog
        # Versão arredondada para os sprites: só refaz a neblina deles quando a cor muda de faixa.
        self.fog_sprite_color = (fog[0] // 12 * 12 + 6, fog[1] // 12 * 12 + 6, fog[2] // 12 * 12 + 6)

    def gradient(self, top: Color, horizon: Color) -> pygame.Surface:
        key = (tuple(c // 4 for c in top), tuple(c // 4 for c in horizon))
        surface = self.gradients.get(key)
        if surface is None:
            column = pygame.Surface((1, C.HORIZON_Y))
            for y in range(C.HORIZON_Y):
                column.set_at((0, y), lerp_color(top, horizon, y / max(1, C.HORIZON_Y - 1)))
            surface = pygame.transform.scale(column, (C.WIDTH, C.HORIZON_Y))
            self.gradients[key] = surface
        return surface

    # ---------------------------------------------------------- desenho
    def draw(
        self,
        screen: pygame.Surface,
        top: Color,
        horizon: Color,
        cam_x: float,
        distance: float,
        solar_share: float,
        elapsed: float,
        challenge_theme=None,
    ) -> None:
        screen.blit(self.gradient(top, horizon), (0, 0))
        self.draw_sun(screen, cam_x, horizon)
        self.draw_panorama(screen, cam_x, distance)
        self.draw_clouds(screen, cam_x, distance)
        self.draw_skyline(screen, horizon, cam_x, distance, solar_share)
        self.draw_sky_decor(screen, cam_x, solar_share, elapsed)
        self.draw_horizon_vehicle(screen, cam_x, solar_share, challenge_theme)

    def draw_sun(self, screen: pygame.Surface, cam_x: float, horizon: Color) -> None:
        """Sol de papel: pálido atrás da fumaça, amarelo e com halo quando o céu limpa."""
        clear = 1.0 - self.pollution
        x = int(SUN_POS[0] - cam_x * 0.04)
        y = SUN_POS[1]
        key = (int(clear * 10), tuple(c // 8 for c in horizon))
        sun = self.decor_cache.get(("sol", key))
        if sun is None:
            size = SUN_RADIUS * 4
            sun = pygame.Surface((size, size), pygame.SRCALPHA)
            center = (size // 2, size // 2)
            core = lerp_color(lerp_color(horizon, (255, 255, 255), 0.45), rgb("ffe36b"), clear)
            halo = lerp_color(horizon, rgb("fff3b0"), clear)
            for k in range(4, 0, -1):  # halo em degraus (aquarela aguada)
                alpha = int((28 if clear > 0.3 else 14) * clear + 6)
                pygame.draw.circle(sun, (*halo, alpha), center, SUN_RADIUS + k * 12)
            pygame.draw.circle(sun, (*CLOUD_INK, int(60 + 90 * clear)), center, SUN_RADIUS + 2)
            pygame.draw.circle(sun, (*core, int(150 + 105 * clear)), center, SUN_RADIUS)
            sun = display_format(sun, alpha=True)
            self.decor_cache[("sol", key)] = sun
        screen.blit(sun, sun.get_rect(center=(x, y)))

    def draw_panorama(self, screen: pygame.Surface, cam_x: float, distance: float) -> None:
        if self.panorama is None or self.pollution <= 0.01:
            return
        self.panorama.set_alpha(int(235 * self.pollution))
        blit_tiled(screen, self.panorama, cam_x * C.SKY_SHIFT_PX + distance * C.SKY_DRIFT_PX + 260, 0)

    def draw_clouds(self, screen: pygame.Surface, cam_x: float, distance: float) -> None:
        for cloud in self.clouds:
            shift = distance * cloud["drift"] + cam_x * C.CLOUD_SHIFT_PX * cloud["parallax"]
            x = (cloud["x"] - shift) % C.CLOUD_TILE - cloud["w"]
            if x > C.WIDTH:
                continue
            for variant, strength in (("smoke", 0.85 * self.pollution), ("clean", 0.6 * (1.0 - self.pollution))):
                surface = self.cloud_surface(cloud, variant, strength * cloud["opacity"])
                if surface is not None:
                    screen.blit(surface, (int(x), cloud["y"]))

    @staticmethod
    def cloud_surface(cloud: dict, variant: str, strength: float) -> Optional[pygame.Surface]:
        """Nuvem com a transparência já aplicada (12 níveis preparados uma vez)."""
        level = int(clamp(strength, 0.0, 1.0) * 12 + 0.5)
        if level <= 0:
            return None
        surface = cloud["baked"].get((variant, level))
        if surface is None:
            surface = display_format(cloud[variant].copy(), alpha=True)
            if level < 12:
                surface.fill((255, 255, 255, int(255 * level / 12)), special_flags=pygame.BLEND_RGBA_MULT)
            cloud["baked"][(variant, level)] = surface
        return surface

    # ----------------------------------------------------------- silhuetas
    @staticmethod
    def build_skyline(layout: List[Tuple[str, int]], sprites: dict) -> Optional[pygame.Surface]:
        """Faixa contínua de silhuetas (repete a cada FAR_TILE px, emenda invisível)."""
        items = [(sprites[name], h) for name, h in layout if name in sprites]
        if not items:
            return None
        strip = pygame.Surface((C.FAR_TILE, C.SKYLINE_HEIGHT), pygame.SRCALPHA)
        x, i = 0.0, 0
        while x < C.FAR_TILE:
            sprite, h = items[i % len(items)]
            w = max(2, int(sprite.get_width() * h / sprite.get_height()))
            scaled = pygame.transform.smoothscale(sprite, (w, h))
            for dx in (0, -C.FAR_TILE):
                strip.blit(scaled, (int(x) + dx, C.SKYLINE_HEIGHT - h))
            x += w * 0.78 + 14 + (i * 37) % 45
            i += 1
        return strip

    def skyline_base(self, name: str) -> Optional[pygame.Surface]:
        if name not in self.skyline_cache:
            biome = self.biome
            layout: List[Tuple[str, int]]
            if name == "green" and biome is not None:
                layout = biome.green_skyline
            elif name == "city" and biome is not None:
                layout = biome.solar_skyline
            elif name == "back":
                layout: List[Tuple[str, int]] = []
                regional = list(biome.industrial_skyline) if biome is not None else []
                for i, item in enumerate(SKYLINE_BACK):
                    layout.append(item)
                    if regional and i % 3 == 1:
                        layout.append(regional[(i // 3) % len(regional)])
            else:
                layout = SKYLINE_FRONT
            names = {sprite for sprite, _ in layout}
            for sprite_name in names:
                if sprite_name not in self.skyline_sprites:
                    sprite = self.assets.sprite("skyline_sprites", sprite_name)
                    if sprite is not None:
                        self.skyline_sprites[sprite_name] = sprite
            scene_sprites = self.assets.scenery_for(names) if name != "front" else {}
            strip = self.build_skyline(layout, {**self.skyline_sprites, **scene_sprites})
            self.skyline_cache[name] = strip
        return self.skyline_cache[name]

    def skyline_target(self, solar_share: float) -> tuple:
        """Estado desejado: indústria -> flora -> cidade solarpunk, e cor da neblina."""
        industrial = clamp(self.pollution * 1.4, 0.0, 1.0)
        return int(industrial * 10 + 0.5), tuple(c // 16 for c in self.fog_color), int(solar_share * 10 + 0.5)

    def skyline_job(self, name: str, target: tuple) -> dict:
        """Prepara uma fileira nova em pedaços (o trabalho se espalha por alguns quadros)."""
        level, _, city_level = target
        parts = []
        industrial = self.skyline_base(name)
        if industrial is not None and level > 0:
            parts.append((industrial, C.SKYLINE_HAZE[name], level / 10))
        green = self.skyline_base("green") if name == "front" else None
        if green is not None and level < 10:
            parts.append((green, C.SKYLINE_HAZE["green"], 1.0 - level / 10))
        city = self.skyline_base("city") if name == "back" and city_level > 0 else None
        if city is not None:
            parts.append((city, C.SKYLINE_HAZE["back"] * 0.8, city_level / 10))
        surface = pygame.Surface((C.FAR_TILE, C.SKYLINE_HEIGHT), pygame.SRCALPHA) if parts else None
        fog = self.fog_color

        def steps():
            for x in range(0, C.FAR_TILE, C.SKYLINE_CHUNK):
                rect = pygame.Rect(x, 0, min(C.SKYLINE_CHUNK, C.FAR_TILE - x), C.SKYLINE_HEIGHT)
                dest = surface.subsurface(rect)
                for i, (base, haze, alpha) in enumerate(parts):
                    piece = dest if i == 0 else pygame.Surface(rect.size, pygame.SRCALPHA)
                    piece.blit(base.subsurface(rect), (0, 0), special_flags=pygame.BLEND_RGBA_MAX)
                    keep = int(255 * (1.0 - haze))
                    piece.fill((keep, keep, keep, int(255 * alpha)), special_flags=pygame.BLEND_RGBA_MULT)
                    piece.fill(
                        (int(fog[0] * haze), int(fog[1] * haze), int(fog[2] * haze), 0),
                        special_flags=pygame.BLEND_RGBA_ADD,
                    )
                    if piece is not dest:
                        dest.blit(piece, (0, 0))
                yield

        return {"target": target, "surface": surface, "steps": steps() if parts else iter(())}

    def update_skyline(self, solar_share: float, budget_ms: float = C.SKYLINE_BUDGET_MS) -> None:
        target = self.skyline_target(solar_share)
        start = time.perf_counter()
        for name in ("back", "front"):
            state = self.skyline_state.setdefault(name, {"surface": None, "target": None, "job": None})
            if state["job"] is None and state["target"] != target:
                state["job"] = self.skyline_job(name, target)
            job = state["job"]
            if job is None:
                continue
            first_time = state["target"] is None  # primeira vez: monta tudo já
            fading = (
                state.get("previous") is not None
                and time.perf_counter() - state.get("fade_start", 0.0) < C.SKYLINE_FADE_S
            )
            if fading and not first_time:
                continue  # termina a transição atual antes da próxima
            while first_time or (time.perf_counter() - start) * 1000.0 < budget_ms:
                if next(job["steps"], StopIteration) is StopIteration:
                    if not first_time and state["surface"] is not None:
                        state["previous"], state["fade_start"] = state["surface"], time.perf_counter()
                    state["surface"], state["target"], state["job"] = job["surface"], job["target"], None
                    break

    def draw_skyline(
        self, screen: pygame.Surface, horizon: Color, cam_x: float, distance: float, solar_share: float
    ) -> None:
        self.update_skyline(solar_share)
        drift = distance * C.FAR_DRIFT_PX
        shift = cam_x * C.FAR_SHIFT_PX
        drew = False
        top = C.HORIZON_Y - C.SKYLINE_HEIGHT + 2
        for name, ratio, extra in (("back", C.FAR_BACK_RATIO, 700), ("front", 1.0, 0)):
            state = self.skyline_state.get(name, {})
            layer, previous = state.get("surface"), state.get("previous")
            if layer is None and previous is None:
                continue
            drew = True
            offset = (shift + drift) * ratio + extra
            fade = 1.0
            if previous is not None:
                fade = (time.perf_counter() - state.get("fade_start", 0.0)) / C.SKYLINE_FADE_S
                if fade >= 1.0:
                    state["previous"] = None
                    fade = 1.0
                elif layer is None:  # fileira esvaziou: a antiga some aos poucos
                    previous.set_alpha(int(255 * (1.0 - fade)))
                    blit_tiled(screen, previous, offset, top)
                    previous.set_alpha(255)
                else:
                    blit_tiled(screen, previous, offset, top)
            if layer is not None:
                layer.set_alpha(int(255 * clamp(fade, 0.0, 1.0)))
                blit_tiled(screen, layer, offset, top)
                layer.set_alpha(255)
        if not drew and self.skyline_base("back") is None and self.skyline_base("front") is None:
            self.draw_far_fallback(screen, horizon, cam_x, distance)

    @staticmethod
    def draw_far_fallback(screen: pygame.Surface, base: Color, cam_x: float, distance: float) -> None:
        """Silhueta de reserva (sem sprites): soma de senoides."""
        offset = (-cam_x * C.FAR_SHIFT_PX - distance * C.FAR_DRIFT_PX) % C.FAR_TILE
        color = lerp_color(base, (0, 0, 0), 0.35)
        n = len(C.FAR_PROFILE)
        left, right = -C.FAR_STEP * 2, C.WIDTH + C.FAR_STEP * 3
        points = [
            (sx, C.HORIZON_Y - C.FAR_PROFILE[int(((sx - offset) % C.FAR_TILE) // C.FAR_STEP) % n])
            for sx in range(left, right, C.FAR_STEP)
        ]
        points += [(right, C.HORIZON_Y), (left, C.HORIZON_Y)]
        pygame.draw.polygon(screen, color, points)

    # ------------------------------------------------------ decoração móvel
    def update_decor(self, dt: float) -> None:
        """Dirigível, balões, barco/bonde e pássaros andam sozinhos (não colidem)."""
        if self.biome is None:
            return
        for i, decor in enumerate(self.biome.sky_decor):
            self.decor_x[i] = (self.decor_x[i] + decor.speed * dt) % C.DECOR_CYCLE
        self.vehicle_x = (self.vehicle_x - self.biome.horizon_vehicle[2] * dt) % C.DECOR_CYCLE
        self.birds_x = (self.birds_x + 32.0 * dt) % C.DECOR_CYCLE

    def decor_sprite(self, name: str, height: int, alpha: int, haze: float = 0.0) -> Optional[pygame.Surface]:
        sprite = self.decor_sprites.get(name)
        if sprite is None or height < 2:
            return None
        fog = tuple(c // 16 * 16 for c in self.fog_color)
        key = (name, height, alpha // 32, int(haze * 10), fog if haze else None)
        cached = self.decor_cache.get(key)
        if cached is None:
            w = max(2, int(sprite.get_width() * height / sprite.get_height()))
            cached = pygame.transform.smoothscale(sprite, (w, height))
            if haze:
                keep = int(255 * (1.0 - haze))
                cached.fill((keep, keep, keep, 255), special_flags=pygame.BLEND_RGBA_MULT)
                cached.fill(
                    (int(fog[0] * haze), int(fog[1] * haze), int(fog[2] * haze), 0), special_flags=pygame.BLEND_RGBA_ADD
                )
            if alpha < 255:
                cached.fill((255, 255, 255, alpha // 32 * 32 + 31), special_flags=pygame.BLEND_RGBA_MULT)
            self.decor_cache[key] = cached
        return cached

    def draw_sky_decor(self, screen: pygame.Surface, cam_x: float, amount: float, elapsed: float) -> None:
        if amount <= 0.0 or self.biome is None:
            return
        alpha = int(255 * amount)
        for i, decor in enumerate(self.biome.sky_decor):
            surf = self.decor_sprite(decor.sprite, decor.height, alpha, haze=0.15)
            if surf is not None:
                screen.blit(surf, (int((self.decor_x[i] - cam_x * decor.parallax) % C.DECOR_CYCLE - 350), decor.top))
        bx = (self.birds_x - cam_x * 0.2) % C.DECOR_CYCLE - 350
        color = lerp_color(rgb("37474f"), self.fog_color, 0.25)
        for k in range(C.BIRDS):
            px = bx + k * 17 - (k % 2) * 6
            py = 150 + abs(k - C.BIRDS // 2) * 6 + math.sin(elapsed * 1.3 + k) * 2
            flap = math.sin(elapsed * 9.0 + k * 1.7) * 3.0
            pygame.draw.lines(screen, color, False, [(px - 5, py - 2 - flap), (px, py), (px + 5, py - 2 - flap)], 2)

    def draw_horizon_vehicle(self, screen: pygame.Surface, cam_x: float, amount: float, challenge_theme=None) -> None:
        """Na linha do horizonte, à frente das silhuetas: barco (Manaus) ou bonde (Petrolina)."""
        if amount <= 0.0 or self.biome is None:
            return
        name, height, _, parallax = self.biome.horizon_vehicle
        if challenge_theme is not None:
            tags = challenge_theme.decorations
            if name.startswith("AM_") and "boat" in tags:
                amount = min(1.0, amount * 1.15)
            elif name == "EF_BondeVLT" and "tram" in tags:
                amount = min(1.0, amount * 1.15)
        surf = self.decor_sprite(name, height, int(255 * amount), haze=0.35)
        if surf is None:
            return
        for k in range(2):
            x = (self.vehicle_x + k * C.DECOR_CYCLE / 2 - cam_x * parallax) % C.DECOR_CYCLE - 350
            screen.blit(surf, (int(x), C.HORIZON_Y - height + 3))
