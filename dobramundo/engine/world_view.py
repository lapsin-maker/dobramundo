"""Desenho de uma fase: céu, chão, pista (ou rio), cenário das margens, objetos e avião.

Ordem de pintura, do fundo para a frente: céu -> chão texturizado -> pista e
margens (trecho a trecho, do horizonte para o avião) -> objetos atrás do avião
-> avião -> objetos à frente -> textos. No alto contraste, tudo o que vem antes
dos objetos é dessaturado e escurecido, e objetos e avião ganham contorno espesso.
"""

from __future__ import annotations

import math
from typing import Iterator, List, Optional, Tuple

import pygame

from .. import config as C
from ..content.biomes import Biome, Specs
from ..content.items import POWERUP_COLORS, WASTE_BY_KEY, ObstacleSpec
from ..content.planes import MANEUVER_STYLES
from ..game.entities import Entity, entity_hitbox
from ..game.world import World
from ..util import Color, clamp, lerp_color, rgb
from .assets import Assets
from .ground import GroundRenderer
from .plane_skin import PlaneSkin
from .sky import SkyRenderer
from .sprites import SpriteCache, fog_level, project

RIVER_NEGRO = rgb("2a1a10")  # águas escuras do Rio Negro
RIVER_ENCOUNTER = rgb("b08452")  # Solimões (barrento) ao lado do Rio Negro, no despertar
HC_PLANE = rgb("ffeb3b")
HC_OBSTACLE = rgb("ff3d00")
HC_DIM = (150, 150, 150)  # escurecimento do fundo dessaturado


class PlaneLook:
    """O que o jogador escolheu para o avião (modelo, pintura, piloto)."""

    def __init__(
        self, plane: str, color: str = "original", pattern: str = "jornal", pilot: Optional[dict] = None
    ) -> None:
        self.plane = plane
        self.color = color
        self.pattern = pattern
        self.pilot = pilot


class WorldView:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.cache = SpriteCache()
        self.sky = SkyRenderer(assets)
        self.ground = GroundRenderer(assets)
        self.skin = PlaneSkin(assets)
        self.scenery = assets.scenery
        self.waste = assets.folder("waste_sprites")
        self.powerups = assets.folder("powerup_sprites")
        self.fx = assets.folder("era_final_fx")
        self.shadows: dict = {}
        self.rotations: dict = {}
        self.font = pygame.font.SysFont("segoeui,verdana,dejavusans", 20, bold=True)
        self.text_cache: dict = {}
        self.biome: Optional[Biome] = None
        self.world: Optional[World] = None
        self.cam = 0.0
        self.elapsed = 0.0
        self.mode = "normal"
        self.high_contrast = False
        self.show_hitboxes = False
        self.warm_queue: Optional[Iterator] = None

    # ------------------------------------------------------------ preparo
    def set_biome(self, biome: Biome) -> None:
        if self.biome is not biome:
            self.biome = biome
            self.sky.set_biome(biome)
            self.warm_queue = self.warm_tasks()

    def warm_tasks(self) -> Iterator:
        """Preparo incremental (mip dos sprites e silhuetas) para a partida não engasgar."""
        for name in ("back", "front", "green", "city"):
            yield lambda n=name: self.sky.skyline_base(n)
        yield from self.ground.warm_tasks()
        biome = self.biome
        if biome is None:
            return
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
        size = (screen_w, screen_h)
        scaled = self.cache.get(sprite, key, size, flip)
        if outline is not None:
            scaled = self.cache.outlined(scaled, (key, size, flip), outline)
            pad = (scaled.get_width() - screen_w) // 2
            left, top = left - pad, top - pad
        elif level > 0:
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
            if len(self.shadows) > 400:
                self.shadows.pop(next(iter(self.shadows)))
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (0, 0, 0, alpha // 4 * 4), surf.get_rect())
            self.shadows[key] = surf
        screen.blit(surf, surf.get_rect(center=(int(sx), int(sy))))

    def text(self, text: str, color: Tuple[int, int, int]) -> pygame.Surface:
        key = (text, color)
        surf = self.text_cache.get(key)
        if surf is None:
            if len(self.text_cache) > 64:
                self.text_cache.clear()
            surf = self.font.render(text, True, color)
            self.text_cache[key] = surf
        return surf

    # ------------------------------------------------------------- cenário
    def piece(
        self, screen: pygame.Surface, specs: Specs, seq: int, side: int, x: float, z: float, cam: float, grow: float
    ) -> None:
        """Peça das margens na ordem fixa da lista; grow < 1 = afundando ou crescendo."""
        if z < C.NEAR_CLIP_Z or grow < 0.04 or not specs:
            return
        offset = len(specs) // 2 if side > 0 else 0
        for step in range(len(specs)):
            name, height = specs[(seq + offset + step) % len(specs)]
            sprite = self.scenery.get(name)
            if sprite is not None:
                # Os sprites mostram o lado direito (vista 3/4): à direita da pista, espelhados.
                self.blit_world(screen, sprite, ("scenery", name), side * x, 0, z, height * grow, side > 0, cam)
                return

    def margins(self, screen: pygame.Surface, world: World, seg: int, z: float) -> None:
        """Duas fileiras por lado em cada trecho: fundo (z) e borda (z + 50)."""
        biome = self.biome
        mid_cam = self.cam * C.MID_PARALLAX
        margin_cam = self.cam * C.MARGIN_PARALLAX
        border_z = z + 50.0
        green = world.segment_green(seg)
        final = world.segment_final(seg)
        keep = 1.0 - final  # a peça do estágio anterior afunda enquanto a nova cresce
        for side in (-1, 1):
            if green < 1.0 and keep > 0.0:
                self.piece(screen, biome.industrial_mid, seg, side, C.MID_ROW_X, z, mid_cam, (1.0 - green) * keep)
            if green > 0.0 and keep > 0.0:
                restored = seg % C.RESTORED_EVERY == C.RESTORED_REMAINDER
                specs = biome.restored if restored else biome.green_mid
                index = seg // C.RESTORED_EVERY + (side > 0) if restored else seg
                self.piece(screen, specs, index, side, C.MID_ROW_X, z, mid_cam, green * keep)
            if final > 0.0:
                marco = seg % C.LANDMARK_EVERY == 4 and (seg // C.LANDMARK_EVERY + (side > 0)) % 2 == 0
                specs = [biome.landmark] if marco else biome.solar_mid
                self.piece(screen, specs, seg, side, C.MID_ROW_X, z, mid_cam, final)
            if border_z > C.MARGIN_MAX_Z or (seg + (side > 0)) % 2:
                continue  # a borda alterna de lado a cada trecho e some ao longe
            if green < 1.0 and keep > 0.0:
                self.piece(
                    screen,
                    biome.industrial_margin,
                    seg // 2,
                    side,
                    C.MARGIN_X,
                    border_z,
                    margin_cam,
                    (1.0 - green) * keep,
                )
            if green > 0.0 and keep > 0.0:
                self.piece(
                    screen, biome.green_margin, seg // 2 + 3, side, C.MARGIN_X, border_z, margin_cam, green * keep
                )
            if final > 0.0:
                self.piece(
                    screen,
                    biome.solar_margin,
                    seg // 2 + (3 if side > 0 else 0),
                    side,
                    C.MARGIN_X,
                    border_z,
                    margin_cam,
                    final,
                )

    def draw_track(self, screen: pygame.Surface, world: World, flags) -> None:
        a, b, t = world.visual_stage_pair()
        fog = self.sky.fog_color
        road_even = lerp_color(a.road_even, b.road_even, t)
        road_odd = lerp_color(a.road_odd, b.road_odd, t)
        lane_base = lerp_color(a.lane_line, b.lane_line, t)
        ground_base = lerp_color(a.ground, b.ground, t)
        biome = self.biome
        river = biome.river
        stage_weight = self.encounter_weight(world)
        right_even = lerp_color(road_even, RIVER_ENCOUNTER, stage_weight) if river else road_even
        right_odd = lerp_color(road_odd, RIVER_ENCOUNTER, stage_weight * 0.95) if river else road_odd
        purified = lerp_color(road_even, rgb("8bcf78"), 0.2)
        wave_z = 180.0 + (world.visual / 100.0) ** 1.15 * 2150.0  # frente da pista purificada
        textured = bool(self.ground.textures)
        solar_road = self.ground.has(biome.solar_road)
        final_flags = flags[1]
        cam = self.cam
        stretches = []
        for i in range(len(world.segments) - 1, -1, -1):
            z = world.segments[i]
            seg = world.segment_base + i
            next_z = z + C.SEGMENT_LENGTH
            left1 = project(-C.ROAD_WIDTH / 2, 0, z, cam)
            right1 = project(C.ROAD_WIDTH / 2, 0, z, cam)
            left2 = project(-C.ROAD_WIDTH / 2, 0, next_z, cam)
            right2 = project(C.ROAD_WIDTH / 2, 0, next_z, cam)
            haze = clamp((z + 50.0 - C.FOG_START) / (C.FOG_END - C.FOG_START), 0.0, 1.0)
            if not textured:
                ground = C.GRASS_FALLBACK[seg % 2] if world.segment_green(seg) > 0.0 else ground_base
                pygame.draw.polygon(
                    screen,
                    lerp_color(ground, fog, haze),
                    [(0, left2[1]), (C.WIDTH, right2[1]), (C.WIDTH, right1[1]), (0, left1[1])],
                )
            stretches.append((i, seg, z, next_z, left1, right1, left2, right2, haze))
        self.ground.draw(
            screen, world, flags, cam, fog, ("concrete", biome.green_ground, biome.solar_ground), biome.solar_road
        )
        for i, seg, z, next_z, left1, right1, left2, right2, haze in stretches:
            final = bool(final_flags) and final_flags[i]
            purify = clamp((wave_z - z) / C.ROAD_PURIFY_BAND, 0.0, 1.0)
            purify = purify * purify * (3 - 2 * purify)
            even = seg % 2 == 0
            base = lerp_color(road_even if even else road_odd, purified, purify * (not river))
            if river:  # encontro das águas: o Negro fica escuro à esquerda
                base = lerp_color(base, RIVER_NEGRO, stage_weight * (0.9 if even else 1.0))
            color = lerp_color(base, fog, haze)
            lane = lerp_color(lane_base, fog, haze)
            if final and solar_road:
                curb = lerp_color(rgb("c9a04a"), fog, haze)  # meio-fio dourado do piso drenante
                width = max(1, int(6 * left1[2]))
                pygame.draw.line(screen, curb, (left1[0], left1[1]), (left2[0], left2[1]), width)
                pygame.draw.line(screen, curb, (right1[0], right1[1]), (right2[0], right2[1]), width)
            elif river and stage_weight > 0.01:
                mid1 = project(0, 0, z, cam)
                mid2 = project(0, 0, next_z, cam)
                right = lerp_color(right_even if even else right_odd, fog, haze)
                pygame.draw.polygon(
                    screen, color, [(left1[0], left1[1]), (mid1[0], mid1[1]), (mid2[0], mid2[1]), (left2[0], left2[1])]
                )
                pygame.draw.polygon(
                    screen,
                    right,
                    [(mid1[0], mid1[1]), (right1[0], right1[1]), (right2[0], right2[1]), (mid2[0], mid2[1])],
                )
            else:
                pygame.draw.polygon(
                    screen,
                    color,
                    [(left1[0], left1[1]), (right1[0], right1[1]), (right2[0], right2[1]), (left2[0], left2[1])],
                )
            if river:
                if final:  # orla dourada do rio limpo
                    curb = lerp_color(rgb("e0c27a"), fog, haze)
                    width = max(1, int(5 * left1[2]))
                    pygame.draw.line(screen, curb, (left1[0], left1[1]), (left2[0], left2[1]), width)
                    pygame.draw.line(screen, curb, (right1[0], right1[1]), (right2[0], right2[1]), width)
                if (seg + int(self.elapsed * 3)) % 3 == 0:  # reflexos que andam: água corrente
                    for divider in (-0.5, 0.5):
                        p1 = project(C.LANE_WIDTH * divider, 0, z + 20, cam)
                        p2 = project(C.LANE_WIDTH * divider, 0, z + 60, cam)
                        pygame.draw.line(screen, lane, (p1[0], p1[1]), (p2[0], p2[1]), max(1, int(3 * p1[2])))
            else:
                for divider in (-0.5, 0.5):
                    p1 = project(C.LANE_WIDTH * divider, 0, z, cam)
                    p2 = project(C.LANE_WIDTH * divider, 0, next_z, cam)
                    pygame.draw.line(screen, lane, (p1[0], p1[1]), (p2[0], p2[1]), max(1, int(4 * p1[2])))
            self.margins(screen, world, seg, z)

    @staticmethod
    def encounter_weight(world: World) -> float:
        """Quanto do encontro das águas aparece: só no estágio do despertar (meio da fase)."""
        value = world.visual
        rise = clamp((value - C.ERA_SPAN * 0.8) / (C.ERA_SPAN * 0.4), 0.0, 1.0)
        fall = clamp((value - C.ERA_SPAN * 1.8) / (C.ERA_SPAN * 0.5), 0.0, 1.0)
        return rise * (1.0 - fall)

    # ----------------------------------------------------------- objetos
    def halo(self, screen: pygame.Surface, world: World, entity: Entity, size: float) -> None:
        """Estágio solarpunk, só no Difícil: halo pulsante atrás do que se pode PEGAR."""
        halo = self.fx.get("halo_coletavel")
        if self.mode != "dificil" or halo is None or not world.final_at(entity.z):
            return
        pulse = (0.94, 1.0, 1.06)[int(self.elapsed * 4.0 + entity.z * 0.01) % 3]
        h = size * C.FINAL_HALO_SCALE * pulse
        self.blit_world(screen, halo, ("fx", "halo"), entity.x, entity.y - h / 2, entity.z + 1.0, h)

    def alert(self, screen: pygame.Surface, entity: Entity, spec: ObstacleSpec) -> None:
        """Estágio solarpunk: chevrons âmbar no chão da faixa antes do que COLIDE."""
        alert = self.fx.get("alerta_chao")
        if alert is None:
            return
        near, far = entity.z - C.FINAL_ALERT_DEPTH[1], entity.z - C.FINAL_ALERT_DEPTH[0]
        if near < C.NEAR_CLIP_Z or fog_level(far) >= C.FOG_LEVELS:
            return
        half = min(spec.width, C.LANE_WIDTH) * 0.42
        x0, y_far, _ = project(entity.x - half, 0, far, self.cam)
        x1, _, _ = project(entity.x + half, 0, far, self.cam)
        x2, y_near, _ = project(entity.x - half, 0, near, self.cam)
        x3, _, _ = project(entity.x + half, 0, near, self.cam)
        w, h = int(max(x1 - x0, x3 - x2)), int(y_near - y_far)
        if w < 4 or h < 2 or w > C.WIDTH * 2:
            return
        step = max(2, int(w * 0.05))
        size = (w - w % step + step, max(2, h - h % max(2, int(h * 0.05)) + 2))
        scaled = self.cache.get(alert, ("fx", "alerta"), size)
        level = fog_level(far)
        if level > 0:
            scaled = self.cache.fogged(scaled, (("fx", "alerta"), size, False), level)
        screen.blit(scaled, (int((x2 + x3) / 2 - size[0] / 2), int(y_far)))

    def draw_entity(self, screen: pygame.Surface, world: World, entity: Entity) -> None:
        hc = self.high_contrast
        if entity.kind == "waste":
            self.halo(screen, world, entity, 46.0)
            self.shadow(screen, entity.x, entity.z, 50, 70)
            sprite = self.waste.get(entity.sprite)
            color = WASTE_BY_KEY[entity.sprite].color if entity.sprite in WASTE_BY_KEY else rgb("ffb300")
            bob = math.sin(self.elapsed * 3.0 + entity.z * 0.02) * 3
            if sprite is not None:
                self.blit_world(
                    screen,
                    sprite,
                    ("item", entity.sprite),
                    entity.x,
                    entity.y - 23 + bob,
                    entity.z,
                    46,
                    outline=color if hc else None,
                )
            else:
                self.fallback_ball(screen, entity, color, 22)
        elif entity.spec is None:  # power-up
            self.halo(screen, world, entity, 56.0)
            self.shadow(screen, entity.x, entity.z, 46, 60)
            sprite = self.powerups.get(entity.kind)
            color = POWERUP_COLORS.get(entity.kind, (255, 255, 255))
            bob = math.sin(self.elapsed * 3.2 + entity.z * 0.015) * 4
            if sprite is not None:
                self.blit_world(
                    screen,
                    sprite,
                    ("item", entity.kind),
                    entity.x,
                    entity.y - 26 + bob,
                    entity.z,
                    56,
                    outline=color if hc else None,
                )
            else:
                self.fallback_ball(screen, entity, color, 20)
        else:
            spec = entity.spec
            if entity.solar or hc:
                self.alert(screen, entity, spec)
            sprite = self.scenery.get(spec.sprite)
            if sprite is not None:
                self.blit_world(
                    screen,
                    sprite,
                    ("scenery", spec.sprite),
                    entity.x,
                    0,
                    entity.z,
                    spec.visual_height,
                    outline=HC_OBSTACLE if hc else None,
                )
            else:
                rect = self.hitbox_rect(entity_hitbox(entity))
                color = {"low": rgb("5d4037"), "gate": rgb("311b92"), "tower": rgb("3e2723")}[entity.kind]
                pygame.draw.rect(screen, color, rect, 5 if entity.kind == "gate" else 0)
        if self.show_hitboxes:
            rect = self.hitbox_rect(entity_hitbox(entity))
            pygame.draw.rect(screen, rgb("00e676") if entity.kind == "waste" else rgb("ff1744"), rect, 2)

    def fallback_ball(self, screen: pygame.Surface, entity: Entity, color: Color, radius: float) -> None:
        x, y, scale = project(entity.x, entity.y, entity.z, self.cam)
        r = max(3, int(radius * max(0.08, scale)))
        pygame.draw.circle(screen, color, (int(x), int(y)), r)
        pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), r, max(1, r // 6))

    def hitbox_rect(self, box) -> pygame.Rect:
        z = max(20.0, (box.z_min + box.z_max) / 2)
        x0, y0, _ = project(box.x_min, min(box.y_max, 330.0), z, self.cam)
        x1, y1, _ = project(box.x_max, box.y_min, z, self.cam)
        return pygame.Rect(int(x0), int(y0), max(1, int(x1 - x0)), max(1, int(y1 - y0)))

    # ----------------------------------------------------------------- avião
    def draw_player(self, screen: pygame.Surface, run, look: PlaneLook) -> None:
        player = run.player
        self.shadow(
            screen,
            player.x,
            C.PLAYER_Z,
            C.PLANE_WIDTH * (1.1 - player.y / 800),
            int(clamp(150 - player.y * 0.5, 40, 150)),
        )
        if run.invulnerable_timer > 0 and int(self.elapsed * 14) % 2:
            return  # pisca depois de uma colisão
        bob = math.sin(self.elapsed * 3.0) * 3.0
        sx, sy, scale = project(player.x, player.y + bob, C.PLAYER_Z, self.cam)
        width = max(8, int(C.PLANE_WIDTH * scale))
        sprite = self.skin.surface(look.plane, "flight", look.color, look.pattern, look.pilot)
        look_key = self.skin.look_key(look.plane, look.color, look.pattern, look.pilot)
        pose = player.maneuver_pose()
        if sprite is None:
            self.draw_paper_fallback(screen, int(sx), int(sy), width, player.roll + (pose[0] if pose else 0.0))
            return
        aspect = sprite.get_height() / max(1, sprite.get_width())
        height = max(4, int(width * aspect))
        max_h = int(120 * scale)  # piloto alto não cobre a tela
        if height > max_h:
            height = max_h
            width = max(8, int(height / aspect))
        if pose is not None:
            m_roll, m_pitch, m_dx, m_dy, m_dz = pose
            style = MANEUVER_STYLES[player.maneuver]
            sx += m_dx * style.sway * width
            sy = max(C.MANEUVER_TOP_MARGIN, sy - m_dy * style.lift * width)
            depth = 1.0 / max(0.4, 1.0 + style.depth * m_dz)
            vertical = math.cos(math.radians(m_pitch))
            thickness = round(max(C.MANEUVER_MIN_THICKNESS, abs(vertical)) * 25) / 25
            size = (max(8, int(width * depth)), max(3, int(height * depth * thickness)))
            img = self.cache.get(sprite, ("plane", look_key), size)
            if vertical < 0:  # de cabeça para baixo (topo do looping)
                img = pygame.transform.flip(img, False, True)
            image = pygame.transform.rotozoom(img, player.roll + m_roll, 1.0)
            width = size[0]
        else:
            base = self.cache.get(sprite, ("plane", look_key), (width, height))
            angle = round(player.roll / 2.0) * 2.0
            key = (look_key, width, height, angle)
            image = self.rotations.get(key)
            if image is None:
                if len(self.rotations) > 400:
                    self.rotations.clear()
                image = pygame.transform.rotozoom(base, angle, 1.0)
                self.rotations[key] = image
        if self.high_contrast:
            image = self.cache.outlined(image, ("plane_hc", look_key, image.get_size()), HC_PLANE)
        screen.blit(image, image.get_rect(center=(int(sx), int(sy))))
        if run.shield_timer > 0:
            pulse = 0.5 + 0.5 * math.sin(self.elapsed * 8.0)
            pygame.draw.ellipse(
                screen,
                lerp_color(rgb("40c4ff"), (255, 255, 255), pulse * 0.4),
                pygame.Rect(int(sx - width * 0.62), int(sy - width * 0.36), int(width * 1.24), int(width * 0.72)),
                max(2, int(3 * scale)),
            )
        if run.magnet_timer > 0:
            pygame.draw.circle(
                screen,
                POWERUP_COLORS["magnet"],
                (int(sx), int(sy)),
                int(width * (0.7 + 0.05 * math.sin(self.elapsed * 10))),
                1,
            )
        if self.show_hitboxes:
            pygame.draw.rect(screen, rgb("40c4ff"), self.hitbox_rect(player.hitbox()), 2)

    @staticmethod
    def draw_paper_fallback(screen: pygame.Surface, cx: int, cy: int, width: int, roll: float) -> None:
        """Avião de papel desenhado por código (se os sprites faltarem)."""
        h = width * 0.28
        angle = math.radians(roll)

        def rot(px: float, py: float) -> Tuple[int, int]:
            return (
                int(cx + px * math.cos(angle) - py * math.sin(angle)),
                int(cy + px * math.sin(angle) + py * math.cos(angle)),
            )

        left = [rot(0, -h * 0.35), rot(-width / 2, h * 0.25), rot(0, h * 0.1)]
        right = [rot(0, -h * 0.35), rot(width / 2, h * 0.25), rot(0, h * 0.1)]
        keel = [rot(0, -h * 0.35), rot(-width * 0.05, h * 0.6), rot(width * 0.05, h * 0.6)]
        pygame.draw.polygon(screen, (232, 232, 226), left)
        pygame.draw.polygon(screen, (250, 250, 246), right)
        pygame.draw.polygon(screen, (180, 186, 190), keel)
        pygame.draw.lines(screen, rgb("78909c"), True, left + right[1:], 1)

    # ------------------------------------------------------------ quadro
    def background(self, screen: pygame.Surface, world: World, cam: float) -> None:
        """Céu, chão, pista e margens (tudo o que fica atrás dos objetos)."""
        self.world = world
        self.cam = cam
        self.set_biome(world.biome)
        a, b, t = world.visual_stage_pair()
        top = lerp_color(a.sky_top, b.sky_top, t)
        horizon = lerp_color(a.sky_horizon, b.sky_horizon, t)
        self.sky.update_atmosphere(world.visual, horizon, world.biome.polluted_haze)
        self.cache.fog_color = self.sky.fog_sprite_color
        solar = world.final_share()
        self.sky.draw(screen, top, horizon, cam, world.distance, solar, self.elapsed)
        pygame.draw.rect(screen, self.sky.fog_color, (0, C.HORIZON_Y, C.WIDTH, C.HEIGHT - C.HORIZON_Y))
        self.draw_track(screen, world, world.stage_flags())
        if self.high_contrast:
            self.desaturate(screen)

    @staticmethod
    def desaturate(screen: pygame.Surface) -> None:
        gray = pygame.transform.grayscale(screen)
        gray.fill(HC_DIM, special_flags=pygame.BLEND_RGB_MULT)
        screen.blit(gray, (0, 0))

    def draw_run(self, screen: pygame.Surface, run, look: PlaneLook) -> None:
        """Quadro completo de um voo (sem HUD)."""
        world = run.world
        self.mode = run.mode
        self.background(screen, world, run.player.cam_x)
        entities: List[Entity] = sorted(world.entities, key=lambda e: e.z, reverse=True)
        behind = [e for e in entities if e.z >= C.PLAYER_Z]
        ahead = [e for e in entities if e.z < C.PLAYER_Z]
        for entity in behind:
            self.draw_entity(screen, world, entity)
        self.draw_player(screen, run, look)
        for entity in ahead:
            self.draw_entity(screen, world, entity)
        for beam in run.beams:
            x, y, scale = project(beam.x, 160.0, max(C.NEAR_CLIP_Z, beam.z), self.cam)
            _, y0, _ = project(beam.x, 0.0, max(C.NEAR_CLIP_Z, beam.z), self.cam)
            alpha = clamp(beam.ttl / 0.18, 0.0, 1.0)
            pygame.draw.line(
                screen,
                lerp_color(self.sky.fog_color, beam.color, alpha),
                (int(x), int(y)),
                (int(x), int(y0)),
                max(1, int(6 * scale * alpha)),
            )
        for text in run.floating:
            x, y, _ = project(text.x, text.y, C.PLAYER_Z, self.cam)
            surf = self.text(text.text, text.color)
            surf.set_alpha(int(255 * min(1.0, text.ttl / 0.25)))
            screen.blit(surf, surf.get_rect(center=(int(x), int(y))))
            surf.set_alpha(255)
