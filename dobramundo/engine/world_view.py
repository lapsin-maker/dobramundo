"""Desenho de uma fase: céu, chão, pista (ou rio), cenário das margens, objetos e avião.

Ordem de pintura, do fundo para a frente: céu -> chão texturizado -> pista e
margens (trecho a trecho, do horizonte para o avião) -> objetos atrás do avião
-> avião -> objetos à frente -> textos. No alto contraste, tudo o que vem antes
dos objetos é dessaturado e escurecido, e objetos e avião ganham contorno espesso.
"""

from __future__ import annotations

from typing import Iterator, List, Optional, Tuple

import pygame

from .. import config as C
from ..content.biomes import Biome
from ..util import Color, clamp, lerp_color
from .accessible_view import screen_point, viewport
from .assets import Assets
from .cache import BoundedCache
from .contracts import EntityView, FlightView, WorldStateView
from .contracts import PlaneLook as PlaneLook
from .entity_layer import EntityLayer
from .ground import GroundRenderer
from .paper_items import PaperItems
from .plane_layer import PlaneLayer
from .plane_skin import PlaneSkin
from .sky import SkyRenderer
from .sprites import SpriteCache, fog_level, project
from .track_layer import TrackLayer
from .watercolor import WatercolorWorld

HC_DIM = (150, 150, 150)
ROTATION_CACHE_LIMIT = 400


class WorldView(TrackLayer, EntityLayer, PlaneLayer):
    def __init__(self, assets: Assets, font: Optional[pygame.font.Font] = None) -> None:
        self.assets = assets
        self.cache = SpriteCache()
        self.sky = SkyRenderer(assets)
        self.ground = GroundRenderer(assets)
        self.skin = PlaneSkin(assets)
        self.watercolor = WatercolorWorld(assets)
        self.paper_items = PaperItems()
        self.scenery = {}
        self._scenery_loaded = False
        self._biome_scenery_names = set()
        self.waste = assets.folder("waste_sprites")
        self.powerups = assets.folder("powerup_sprites")
        self.fx = assets.folder("era_final_fx")
        self.shadows = BoundedCache(400, 8 * 1024 * 1024)
        self.rotations = BoundedCache(ROTATION_CACHE_LIMIT, 40 * 1024 * 1024)
        self.font = font or pygame.font.SysFont("segoeui,verdana,dejavusans", 20, bold=True)
        self.text_cache = BoundedCache(64, 4 * 1024 * 1024)
        self.biome: Optional[Biome] = None
        self.world: Optional[WorldStateView] = None
        self.cam = 0.0
        self.elapsed = 0.0
        self.mode = "normal"
        self.high_contrast = False
        self.contrast_scale = 1.3
        self.celebration = 0.0
        self.viewport = pygame.Rect(0, 0, C.WIDTH, C.HEIGHT)
        self.accessible_canvas = None
        self.gray_buffers = None
        self.player_rect = pygame.Rect(0, 0, 246, 180)
        self.reduce_motion = False
        self.show_hitboxes = False
        self.warm_queue: Optional[Iterator] = None

    # ------------------------------------------------------------ preparo
    def set_biome(self, biome: Biome) -> None:
        if self.biome is not biome:
            if self.biome is not None:
                self.release_biome_cache(self.biome.key)
            self.biome = biome
            self.sky.set_biome(biome)
            self._scenery_loaded = False
            self.scenery = {}
            self._biome_scenery_names = self.scenery_names(biome)
            self.warm_queue = self.warm_tasks()

    @staticmethod
    def scenery_names(biome: Biome) -> set:
        names = set()
        for specs in (
            biome.industrial_mid,
            biome.industrial_margin,
            biome.green_mid,
            biome.green_margin,
            biome.restored,
            biome.solar_mid,
            biome.solar_margin,
            [biome.landmark],
        ):
            names.update(name for name, _ in specs)
        for table in (biome.industrial_obstacles, biome.solar_obstacles):
            for specs in table.values():
                names.update(spec.sprite for spec in specs)
        return names

    def ensure_scenery(self) -> None:
        if not self._scenery_loaded and self.biome is not None:
            self.scenery = self.assets.scenery_for(self._biome_scenery_names)
            self._scenery_loaded = True

    def release_biome_cache(self, biome_key: str) -> None:
        """Solta superfícies temporárias do bioma após a cena deixar de usá-lo."""
        self.watercolor.release_biome(biome_key)
        self.watercolor.route.release_biome(biome_key)
        biome_names = set()
        if self.biome is not None and self.biome.key == biome_key:
            biome_names.update(self._biome_scenery_names)
            biome_names.update(decor.sprite for decor in self.biome.sky_decor)
            biome_names.add(self.biome.horizon_vehicle[0])
        if biome_names:
            self.assets.release_scenery(biome_names)
        if self.biome is not None and self.biome.key == biome_key:
            self.scenery = {}
            self._scenery_loaded = False
            self._biome_scenery_names = set()
            self.biome = None
            self.world = None
            self.warm_queue = None
            self.sky.release_biome_cache()
        self.cache = SpriteCache()
        self.shadows.clear()
        self.rotations.clear()
        self.text_cache.clear()

    def cache_stats(self) -> dict:
        """Unique surface-byte estimate for decoded assets and this renderer's owners."""
        seen = set()
        owners = {}

        def measure(name, *values):
            owners[name] = sum(BoundedCache.value_bytes(value, seen) for value in values)

        measure("assets", list(self.assets._loaded.values()), self.assets._scenery)
        measure("scene_sprites", self.scenery, self.waste, self.powerups, self.fx)
        measure("world_sprite_cache", self.cache.scaled, self.cache.mips, self.cache.outlines)
        measure(
            "world_transient", self.shadows, self.rotations, self.text_cache, self.gray_buffers, self.accessible_canvas
        )
        measure(
            "sky",
            self.sky.panorama_base,
            self.sky.panorama,
            self.sky.clouds,
            self.sky.skyline_cache,
            self.sky.skyline_state,
            self.sky.decor_sprites,
            self.sky.gradients,
            self.sky.decor_cache,
        )
        measure("ground", self.ground.textures, self.ground.groups, self.ground.fog_cache)
        route_ground = self.watercolor.route.ground
        measure(
            "watercolor",
            self.watercolor.backdrops,
            self.watercolor.composite,
            self.watercolor.route.banks,
            self.watercolor.route.cache.scaled,
            self.watercolor.route.cache.mips,
            self.watercolor.route.cache.outlines,
            route_ground.textures if route_ground else None,
            route_ground.source_rows if route_ground else None,
            route_ground.line_buffers if route_ground else None,
            self.watercolor.life.frames,
            self.watercolor.life.cache.scaled,
            self.watercolor.life.cache.mips,
            self.watercolor.life.cache.outlines,
        )
        pilots = self.skin.pilots
        pilot_art = pilots.painted
        planes = self.skin.painted_planes
        measure(
            "plane_skin",
            self.skin.patterns,
            self.skin.palettes,
            self.skin.uv_indices,
            self.skin.cache,
            self.skin.thumbs,
            planes._bases,
            planes._paper_masks,
            planes._patterns,
            planes._cache,
            pilots.cache,
            pilots.expression_cache,
            pilot_art.sprites,
            pilot_art.hair_sprites,
            pilot_art.mobility_sprites,
            pilot_art.palette,
            pilot_art.cache,
            pilot_art.hair_cache,
            pilot_art.mobility_cache,
        )
        measure("paper_items", self.paper_items.canonical, self.paper_items._scaled, self.paper_items._shadows)
        cache_items = {
            "scaled": len(self.cache.scaled),
            "mips": len(self.cache.mips),
            "outlines": len(self.cache.outlines),
            "rotations": len(self.rotations),
            "ground_groups": len(self.ground.groups),
            "asset_images": len(self.assets._loaded),
        }
        return {
            "unique_retained_surface_bytes": sum(owners.values()),
            "surface_bytes_by_owner": owners,
            "cache_items": cache_items,
            "estimate": (
                "pitch*height unique by Surface object; shared pygame subsurfaces can be conservatively overcounted"
            ),
        }

    def warm_tasks(self) -> Iterator:
        """Preparo incremental (mip dos sprites e silhuetas) para a partida não engasgar."""
        if self.biome and self.watercolor.load(self.biome.key) and self.watercolor.route.ready(self.biome.key):
            route = self.watercolor.route
            if route.ground is not None:
                yield from route.ground.warm_tasks()
            for index, sprite in enumerate(route.load(self.biome.key)):
                key = ("painted-bank", self.biome.key, index)
                yield lambda s=sprite, k=key: route.cache.warm(s, k, (False, True))
            return
        for name in ("back", "front", "green", "city"):
            yield lambda n=name: self.sky.skyline_base(n)
        yield from self.ground.warm_tasks()
        biome = self.biome
        if biome is None:
            return
        self.ensure_scenery()
        names = set()
        for specs in (
            biome.industrial_mid,
            biome.industrial_margin,
            biome.green_mid,
            biome.green_margin,
            biome.restored,
            biome.solar_mid,
            biome.solar_margin,
            [biome.landmark],
        ):
            names.update(n for n, _ in specs)
        for name in sorted(names):
            sprite = self.scenery.get(name)
            yield lambda s=sprite, n=name: self.cache.warm(s, ("scenery", n), (False, True))
        for table in (biome.industrial_obstacles, biome.solar_obstacles):
            for specs in table.values():
                for spec in specs:
                    yield lambda s=self.scenery.get(spec.sprite), n=spec.sprite: self.cache.warm(s, ("scenery", n))
        for name, sprite in list(self.waste.items()) + list(self.powerups.items()):
            yield lambda s=sprite, n=name: self.cache.warm(s, ("item", n))

    def step_warm_up(self, budget_ms: float) -> None:
        import time

        if self.warm_queue is None:
            return
        start = time.perf_counter()
        while (time.perf_counter() - start) * 1000.0 < budget_ms:
            task = next(self.warm_queue, None)
            if task is None:
                self.warm_queue = None
                return
            task()

    def update(self, dt: float) -> None:
        if not self.reduce_motion:
            self.elapsed += dt
            self.sky.update_decor(dt)

    # ------------------------------------------------------------ primitivas
    def blit_world(
        self,
        screen: pygame.Surface,
        sprite: pygame.Surface,
        key: tuple,
        x: float,
        y: float,
        z: float,
        height: float,
        flip: bool = False,
        cam: Optional[float] = None,
        outline: Optional[Color] = None,
    ) -> None:
        if z < C.NEAR_CLIP_Z:
            return  # colado na câmera: ficaria gigante (e caro)
        sx, sy, scale = project(x, y, z, self.cam if cam is None else cam)
        screen_h = max(2, int(height * scale))
        if screen_h > C.HEIGHT * 2:
            return
        if screen_h < 100:
            screen_h -= screen_h % 2  # pequenos/distantes: menos reescalas, diferença invisível
        else:
            screen_h -= screen_h % max(2, screen_h // 40)
        screen_w = max(2, int(screen_h * sprite.get_width() / max(1, sprite.get_height())))
        left, top = int(sx) - screen_w // 2, int(sy) - screen_h
        if left > C.WIDTH or left + screen_w < 0 or top > C.HEIGHT or top + screen_h < 0:
            return
        level = fog_level(z)
        if level >= C.FOG_LEVELS:
            return
        if outline is not None:  # alto contraste: contorno feito uma vez e reescalado como o sprite
            source = self.cache.outlined_source(sprite, key, outline)
            out_w = max(2, screen_w * source.get_width() // sprite.get_width())
            out_h = max(2, screen_h * source.get_height() // sprite.get_height())
            left, top = left - (out_w - screen_w) // 2, top - (out_h - screen_h) // 2
            screen.blit(self.cache.get(source, ("hc", key, outline), (out_w, out_h), flip), (left, top))
            return
        size = (screen_w, screen_h)
        scaled = self.cache.get(sprite, key, size, flip)
        if level > 0:
            scaled = self.cache.fogged(scaled, (key, size, flip), level)
        screen.blit(scaled, (left, top))

    def shadow(self, screen: pygame.Surface, x: float, z: float, width: float, alpha: int) -> None:
        alpha = int(alpha * (1.0 - fog_level(z) / C.FOG_LEVELS))
        if alpha <= 2:
            return
        sx, sy, scale = project(x, 0, z, self.cam)
        w = max(4, int(width * scale))
        h = max(2, int(w * 0.18))
        key = (w, h, alpha // 4)
        surf = self.shadows.get(key)
        if surf is None:
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            for layer in range(6):
                rect = surf.get_rect().inflate(-w * layer // 15, -h * layer // 15)
                pygame.draw.ellipse(surf, (28, 45, 52, round(alpha * (layer + 1) * 0.065)), rect)
            self.shadows[key] = surf
        screen.blit(surf, surf.get_rect(center=(int(sx), int(sy))))

    def text(self, text: str, color: Tuple[int, int, int]) -> pygame.Surface:
        key = (text, color)
        surf = self.text_cache.get(key)
        if surf is None:
            surf = self.font.render(text, True, color)
            self.text_cache[key] = surf
        return surf

    # ------------------------------------------------------------ quadro
    def background(self, screen: pygame.Surface, world: WorldStateView, cam: float) -> None:
        """Céu, chão, pista e margens (tudo o que fica atrás dos objetos)."""
        self.cam = cam
        self.set_biome(world.biome)
        self.world = world
        if self.watercolor.draw(screen, world, cam, self.reduce_motion):
            self.cache.fog_color = (231, 232, 217)
            if self.high_contrast:
                self.desaturate(screen)
            return
        a, b, t = world.visual_stage_pair()
        top = lerp_color(a.sky_top, b.sky_top, t)
        horizon = lerp_color(a.sky_horizon, b.sky_horizon, t)
        self.sky.update_atmosphere(world.visual, horizon, world.biome.polluted_haze)
        self.cache.fog_color = self.sky.fog_sprite_color
        solar = world.solar_share()
        self.sky.draw(screen, top, horizon, cam, world.distance, solar, self.elapsed, world.challenge_theme)
        pygame.draw.rect(screen, self.sky.fog_color, (0, C.HORIZON_Y, C.WIDTH, C.HEIGHT - C.HORIZON_Y))
        self.draw_track(screen, world, world.stage_flags())
        if self.high_contrast:
            self.desaturate(screen)

    def desaturate(self, screen: pygame.Surface) -> None:
        """Fundo em cinza escurecido, processado em um quarto da resolução.

        A leve suavização que sobra ajuda o avião e os objetos contornados a saltarem à vista.
        """
        w, h = screen.get_size()
        size = max(1, w // 4), max(1, h // 4)
        if self.gray_buffers is None or self.gray_buffers[0].get_size() != size:
            self.gray_buffers = (pygame.Surface(size).convert(), pygame.Surface(size).convert())
        small, gray = self.gray_buffers
        pygame.transform.scale(screen, size, small)
        pygame.transform.grayscale(small, gray)
        gray.fill(HC_DIM, special_flags=pygame.BLEND_RGB_MULT)
        pygame.transform.scale(gray, (w, h), screen)

    def draw_run(self, screen: pygame.Surface, run: FlightView, look: PlaneLook, celebration: float = 0.0) -> None:
        """Quadro completo de um voo (sem HUD)."""
        self.celebration = celebration
        if self.high_contrast and self.contrast_scale > 1.0:
            if self.accessible_canvas is None:
                self.accessible_canvas = pygame.Surface((C.WIDTH, C.HEIGHT)).convert()
            self._draw_run(self.accessible_canvas, run, look)
            self.viewport = viewport(self.contrast_scale, self.player_rect.center, self.player_rect.size)
            # A ampliação mantém contornos nítidos e evita filtrar o quadro inteiro
            # outra vez; o fundo já recebeu a suavização de alto contraste.
            pygame.transform.scale(self.accessible_canvas.subsurface(self.viewport), screen.get_size(), screen)
        else:
            self.viewport = pygame.Rect(0, 0, C.WIDTH, C.HEIGHT)
            self._draw_run(screen, run, look)

    def screen_point(self, point: tuple) -> tuple:
        """Converte âncoras de setas/pictogramas pelo mesmo enquadramento do voo."""
        return screen_point(point, self.viewport)

    def _draw_run(self, screen: pygame.Surface, run: FlightView, look: PlaneLook) -> None:
        world = run.world
        self.mode = run.mode
        self.background(screen, world, run.player.cam_x)
        entities: List[EntityView] = sorted(world.entities, key=lambda e: e.z, reverse=True)
        behind = [e for e in entities if e.z >= C.PLAYER_Z]
        ahead = [e for e in entities if e.z < C.PLAYER_Z]
        for entity in behind:
            self.draw_entity(screen, world, entity)
        self.draw_player(screen, run, look)
        for entity in ahead:
            self.draw_entity(screen, world, entity)
        for beam in [] if self.reduce_motion else run.beams:  # respingo opcional
            x, y, scale = project(beam.x, 90.0, max(C.NEAR_CLIP_Z, beam.z), self.cam)
            self.splash(screen, (x, y), beam.color, clamp(1.0 - beam.ttl / 0.55, 0.0, 1.0), scale)
        for text in run.floating:
            x, y, _ = project(text.x, text.y, C.PLAYER_Z, self.cam)
            surf = self.text(text.text, text.color)
            surf.set_alpha(int(255 * min(1.0, text.ttl / 0.25)))
            screen.blit(surf, surf.get_rect(center=(int(x), int(y))))
            surf.set_alpha(255)
