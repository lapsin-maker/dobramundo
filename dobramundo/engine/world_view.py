"""Desenho de uma fase: céu, chão, pista (ou rio), cenário das margens, objetos e avião.

Ordem de pintura, do fundo para a frente: céu -> chão texturizado -> pista e
margens (trecho a trecho, do horizonte para o avião) -> objetos atrás do avião
-> avião -> objetos à frente -> textos. No alto contraste, tudo o que vem antes
dos objetos é dessaturado e escurecido, e objetos e avião ganham contorno espesso.
"""

from __future__ import annotations

import time
from typing import Callable, List, Optional, Tuple

import pygame

from .. import config as C
from ..content.biomes import Biome
from ..util import Color, clamp, lerp_color
from .accessible_view import screen_point, viewport
from .assets import Assets
from .cache import DEFAULT_CACHE_BUDGET, BoundedCache
from .contracts import EntityView, FlightView, RenderContext, WorldStateView
from .contracts import PlaneLook as PlaneLook
from .entity_layer import EntityLayer
from .ground import GroundRenderer, compute_ground_rows
from .paper_items import PaperItems
from .plane_layer import PlaneLayer
from .plane_skin import PlaneSkin
from .sky import CLOUD_LAYOUT, SKYLINE_BACK, SKYLINE_FRONT, SkyRenderer
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
        self.waste = {}
        self.powerups = {}
        self.fx = {}
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
        self.warm_queue: List[Tuple[str, Callable[[], None]]] = []
        self._warmup_index = 0
        self.warmup_last_task_ms = 0.0
        self.warmup_max_task_ms = 0.0
        self.warmup_overruns = 0
        self.warmup_timings = []
        self._queued_looks = set()

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
            self._warmup_index = 0
            self.warmup_timings.clear()
            self._queued_looks.clear()

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
        for layout in (biome.industrial_skyline, biome.green_skyline, biome.solar_skyline):
            names.update(name for name, _height in layout)
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
            self.warm_queue = []
            self._warmup_index = 0
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
            route_ground.vertical_mips if route_ground else None,
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
            "aggregate_cache_bytes": DEFAULT_CACHE_BUDGET.retained_bytes(),
            "aggregate_cache_limit_bytes": DEFAULT_CACHE_BUDGET.byte_limit,
            "aggregate_cache_metrics": DEFAULT_CACHE_BUDGET.metrics(),
            "estimate": (
                "global cache budget deduplicates backing surfaces; owner estimates may count subsurfaces repeatedly"
            ),
        }

    @property
    def warmup_pending(self) -> bool:
        return self._warmup_index < len(self.warm_queue)

    @property
    def warmup_progress(self) -> float:
        total = len(self.warm_queue)
        return 1.0 if total == 0 else self._warmup_index / total

    @property
    def warmup_status(self) -> str:
        if not self.warmup_pending:
            return "Pronto"
        return self.warm_queue[self._warmup_index][0]

    def warm_tasks(self) -> List[Tuple[str, Callable[[], None]]]:
        """Build a side-effect-free queue of one-asset/preparation work units."""
        biome = self.biome
        if biome is None:
            return []
        tasks = []

        def add(label, function):
            tasks.append((label, function))

        route = self.watercolor.route
        prepared_backdrops = all(
            self.assets.has("watercolor_prepared", f"{biome.key}_{stage}")
            or self.assets.has("watercolor", f"{biome.key}_{stage}")
            for stage in range(3)
        )
        ground_atlas = self.assets.has("watercolor", "terrain_tiles_v3") or self.assets.has(
            "watercolor", "terrain_tiles"
        )
        painted_available = prepared_backdrops and ground_atlas and self.assets.has("watercolor", "banks_" + biome.key)

        if painted_available:
            # The active watercolor path does not render procedural sky, skyline,
            # or fallback scenery; do not decode/warm those unused assets.
            for stage in range(3):
                add("Preparando paisagem", lambda s=stage: self.watercolor.prepare_backdrop(biome.key, s))
            add("Preparando textura do percurso", route.prepare_ground)
            for index in range(12):
                add("Preparando margens", lambda i=index: route.prepare_bank(biome.key, i))
            active_textures = ("green", "negro", "solimoes") if biome.river else ("soil",)
            for name in active_textures:
                for _level in range(6):
                    add(
                        "Suavizando textura do chão",
                        lambda n=name: self._prepare_ground_mip(n),
                    )
            row_count = len(compute_ground_rows()[::3])
            for name in active_textures:
                for start in range(0, row_count, 16):
                    add(
                        "Alocando faixas do chão",
                        lambda n=name, begin=start: self._prepare_ground_line_buffers(n, begin, begin + 16),
                    )
            add("Preparando fauna", self.watercolor.life.prepare)
            regional_names = self.paper_items.regional_art_names(biome.key)
            for name in regional_names:
                add("Carregando elementos regionais", lambda n=name: self.scenery.update(self.assets.scenery_for((n,))))
            add("Preparando obstáculos regionais", lambda: self.paper_items.set_region_scenery(biome.key, self.scenery))
            return tasks

        # Legacy rendering fallback: queue only the selected biome's resources.
        add("Preparando céu", lambda: self.sky.prepare_atmosphere_asset("sky_panorama"))
        add("Preparando nuvens", lambda: self.sky.prepare_atmosphere_asset("smog_cloud"))
        for index in range(len(CLOUD_LAYOUT)):
            add("Preparando nuvens", lambda i=index: self.sky.prepare_cloud(i))
        add("Preparando cores do céu", self.sky.prepare_tinted_panorama)

        skyline_names = {name for name, _height in SKYLINE_BACK + SKYLINE_FRONT}
        for layout in (biome.industrial_skyline, biome.green_skyline, biome.solar_skyline):
            skyline_names.update(name for name, _height in layout)
        names = set(self._biome_scenery_names)
        names.update(decor.sprite for decor in biome.sky_decor)
        names.add(biome.horizon_vehicle[0])
        names.update(skyline_names)
        for name in sorted(names):
            add("Carregando cenário", lambda n=name: self.scenery.update(self.assets.scenery_for((n,))))
        add("Finalizando cenário", self._mark_scenery_loaded)
        decor_names = {decor.sprite for decor in biome.sky_decor}
        decor_names.add(biome.horizon_vehicle[0])
        for name in sorted(decor_names):
            add("Carregando decoração", lambda n=name: self.sky.prepare_decor(n))
        for name in sorted(skyline_names):
            add("Carregando horizonte", lambda n=name: self.sky.prepare_skyline_sprite(n))
        for name in ("back", "front", "green", "city"):
            add("Compondo horizonte", lambda n=name: self.sky.skyline_base(n))

        folders = (
            ("waste_sprites", self.waste),
            ("powerup_sprites", self.powerups),
            ("era_final_fx", self.fx),
        )
        for folder, target in folders:
            for name in self.assets.names(folder):
                add("Carregando itens", lambda f=folder, n=name, store=target: self._load_sprite_into(f, n, store))
        for name in sorted(names):
            add(
                "Preparando imagens de cenário",
                lambda n=name: self.cache.warm(self.scenery.get(n), ("scenery", n), (False, True)),
            )
        for task in self.ground.warm_tasks():
            add("Preparando faixas do chão", task)
        return tasks

    def prepare_look(self, look: PlaneLook) -> None:
        """Queue only the selected flight look, keeping cold composition out of draw.

        Atlas extraction, paint/pattern composition, pilot composition and final
        mount are separate measured work units where the existing APIs allow it.
        This deliberately does not warm the other selectable planes.
        """
        key = self.skin.look_key(look.plane, look.color, look.pattern, look.pilot)
        if key in self._queued_looks and self.warmup_pending:
            return
        if not self.warmup_pending:
            # The global budget may have evicted this look since the last flight.
            # Queue cached lookups again; deduplicate only the work still pending.
            self._queued_looks.clear()
            self.warm_queue.clear()
            self._warmup_index = 0
            self.warmup_timings.clear()
        self._queued_looks.add(key)
        self.warm_queue.extend(
            [
                ("Preparando avião", lambda: self.skin.base(look.plane, "flight")),
                (
                    "Aplicando pintura",
                    lambda: self.skin.painted(look.plane, "flight", look.color, look.pattern),
                ),
            ]
        )
        if look.pilot:
            self.warm_queue.append(
                (
                    "Preparando piloto",
                    lambda: self.skin.pilots.compose("flight", look.pilot, pose="back_seated"),
                )
            )
        self.warm_queue.append(
            (
                "Montando visual do voo",
                lambda: self.skin.surface(look.plane, "flight", look.color, look.pattern, look.pilot),
            )
        )

    def _load_sprite_into(self, folder: str, name: str, target: dict) -> None:
        sprite = self.assets.sprite(folder, name)
        if sprite is not None:
            target[name] = sprite

    def prepare_first_frame(self, run: FlightView, look: PlaneLook) -> None:
        """Warm view-dependent scales before the flight becomes interactive.

        The scratch frame never replaces the preparation screen and advances no
        rules. Its indivisible cost is reported as its own preparation task.
        """

        def prepare() -> None:
            preview = pygame.Surface((C.WIDTH, C.HEIGHT)).convert()
            self.draw_run(preview, run, look)

        self.warm_queue.append(("Preparando primeira vista", prepare))

    def _prepare_ground_mip(self, name: str) -> None:
        ground = self.watercolor.route.ground
        if ground is not None:
            ground.prepare_vertical_mip(name)

    def _prepare_ground_line_buffers(self, name: str, start: int, stop: int) -> None:
        ground = self.watercolor.route.ground
        if ground is not None:
            ground.prepare_line_buffers(name, ground.rows[start:stop])

    def _mark_scenery_loaded(self) -> None:
        self._scenery_loaded = True

    def step_warm_up(self, budget_ms: float) -> None:
        if not self.warmup_pending or budget_ms <= 0:
            return
        start = time.perf_counter()
        budget_s = budget_ms / 1000.0
        # Always execute at least one bounded unit for positive budgets. An
        # indivisible image transform may overrun; record it rather than hiding it.
        while self.warmup_pending:
            label, task = self.warm_queue[self._warmup_index]
            task_start = time.perf_counter()
            task()
            elapsed_ms = (time.perf_counter() - task_start) * 1000.0
            self.warmup_last_task_ms = elapsed_ms
            self.warmup_max_task_ms = max(self.warmup_max_task_ms, elapsed_ms)
            self.warmup_overruns += int(elapsed_ms > budget_ms)
            self.warmup_timings.append((label, elapsed_ms))
            # Completed tasks must not retain a previous run/appearance through
            # their closures. Keep the label/slot for progress until the next queue.
            self.warm_queue[self._warmup_index] = (label, self._prepared_task)
            self._warmup_index += 1
            if time.perf_counter() - start >= budget_s:
                break

    @staticmethod
    def _prepared_task() -> None:
        pass

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
        context = RenderContext(
            world=world,
            camera_x=cam,
            elapsed=self.elapsed,
            high_contrast=self.high_contrast,
            reduce_motion=self.reduce_motion,
            contrast_scale=self.contrast_scale,
        )
        self.compose_background(screen, context)

    def compose_background(self, screen: pygame.Surface, context: RenderContext) -> None:
        """Compose background layers from a typed, immutable frame snapshot."""
        world = context.world
        cam = context.camera_x
        self.cam = cam
        self.set_biome(world.biome)
        self.world = world
        if self.watercolor.draw(screen, world, cam, context.reduce_motion):
            self.cache.fog_color = (231, 232, 217)
            if context.high_contrast:
                self.desaturate(screen)
            return
        a, b, t = world.visual_stage_pair()
        top = lerp_color(a.sky_top, b.sky_top, t)
        horizon = lerp_color(a.sky_horizon, b.sky_horizon, t)
        self.sky.update_atmosphere(world.visual, horizon, world.biome.polluted_haze)
        self.cache.fog_color = self.sky.fog_sprite_color
        solar = world.solar_share()
        self.sky.draw(screen, top, horizon, cam, world.distance, solar, context.elapsed, world.challenge_theme)
        pygame.draw.rect(screen, self.sky.fog_color, (0, C.HORIZON_Y, C.WIDTH, C.HEIGHT - C.HORIZON_Y))
        self.draw_track(screen, world, world.stage_flags())
        if context.high_contrast:
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
        pygame.transform.smoothscale(gray, (w, h), screen)

    def draw_run(self, screen: pygame.Surface, run: FlightView, look: PlaneLook, celebration: float = 0.0) -> None:
        """Quadro completo de um voo (sem HUD)."""
        self.celebration = celebration
        if self.high_contrast and self.contrast_scale > 1.0:
            if self.accessible_canvas is None:
                self.accessible_canvas = pygame.Surface((C.WIDTH, C.HEIGHT)).convert()
            self._draw_run(self.accessible_canvas, run, look)
            self.viewport = viewport(self.contrast_scale, self.player_rect.center, self.player_rect.size)
            self.draw_edge_threats(self.accessible_canvas, run.world, self.viewport)
            # A ampliação mantém contornos nítidos e evita filtrar o quadro inteiro
            # outra vez; o fundo já recebeu a suavização de alto contraste.
            pygame.transform.scale(self.accessible_canvas.subsurface(self.viewport), screen.get_size(), screen)
        else:
            self.viewport = pygame.Rect(0, 0, C.WIDTH, C.HEIGHT)
            self._draw_run(screen, run, look)

    def screen_point(self, point: tuple) -> tuple:
        """Converte âncoras de setas/pictogramas pelo mesmo enquadramento do voo."""
        return screen_point(point, self.viewport)

    def draw_edge_threats(self, screen, world: WorldStateView, view_rect: pygame.Rect) -> int:
        """Mark clipped upcoming hitboxes at the crop edge in magnified view.

        Indicators are derived from the real obstacle bounds, drawn inside the
        same source viewport, and never change entity position or collision.
        """
        if view_rect.size == (C.WIDTH, C.HEIGHT):
            return 0
        margin = 15
        inner = view_rect.inflate(-2 * margin, -2 * margin)
        if inner.width <= 0 or inner.height <= 0:
            return 0
        marked = 0
        for entity in world.entities:
            if entity.kind not in ("low", "gate", "tower") or entity.hit or entity.passed or entity.dodged:
                continue
            if entity.z <= C.PLAYER_Z or entity.z > C.PLAYER_Z + 1300 or fog_level(entity.z) >= C.FOG_LEVELS:
                continue
            bounds = self.hitbox_rect(entity.hitbox())
            if view_rect.contains(bounds):
                continue
            cx, cy = bounds.center
            if bounds.left < view_rect.left:
                point = (inner.left, int(clamp(cy, inner.top, inner.bottom)))
            elif bounds.right > view_rect.right:
                point = (inner.right, int(clamp(cy, inner.top, inner.bottom)))
            elif bounds.top < view_rect.top:
                point = (int(clamp(cx, inner.left, inner.right)), inner.top)
            else:
                point = (int(clamp(cx, inner.left, inner.right)), inner.bottom)
            self._draw_edge_threat_marker(screen, point, entity.kind)
            marked += 1
        return marked

    @staticmethod
    def _draw_edge_threat_marker(screen, point: tuple, kind: str) -> None:
        x, y = point
        color = {"low": (214, 87, 43), "gate": (109, 69, 178), "tower": (22, 123, 132)}.get(kind, (214, 87, 43))
        diamond = [(x, y - 13), (x + 13, y), (x, y + 13), (x - 13, y)]
        pygame.draw.polygon(screen, (8, 20, 44), diamond)
        pygame.draw.polygon(screen, (255, 255, 255), [(x, y - 10), (x + 10, y), (x, y + 10), (x - 10, y)])
        pygame.draw.polygon(screen, color, [(x, y - 7), (x + 7, y), (x, y + 7), (x - 7, y)])
        if kind == "low":
            for offset in (-3, 0, 3):
                pygame.draw.line(screen, (255, 255, 255), (x - 3, y + offset), (x + 3, y + offset), 1)
        elif kind == "gate":
            pygame.draw.lines(
                screen,
                (255, 255, 255),
                False,
                [(x - 3, y + 3), (x - 3, y - 2), (x + 3, y - 2), (x + 3, y + 3)],
                1,
            )
        else:
            pygame.draw.line(screen, (255, 255, 255), (x, y - 4), (x, y + 4), 2)
            pygame.draw.line(screen, (255, 255, 255), (x - 3, y), (x + 3, y), 1)

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
