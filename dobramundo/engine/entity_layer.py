"""Objetos coletáveis e obstáculos, com contrato de leitura do motor."""

from __future__ import annotations

import math

import pygame

from .. import config as C
from ..content.items import POWERUP_COLORS, WASTE_BY_KEY, ObstacleSpec
from ..util import Color, rgb
from .contracts import EntityView, WorldStateView
from .sprites import fog_level, project

HC_OBSTACLE = rgb("ff3d00")


class EntityLayer:
    def halo(self, screen: pygame.Surface, world: WorldStateView, entity: EntityView, size: float) -> None:
        """Halo pulsante atrás do que se pode PEGAR, em todos os estágios e modos.

        O GDD pede distinguir resíduos de obstáculos: o halo marca o que se coleta e os
        chevrons no chão (alert) marcam o que colide.
        """
        halo = self.fx.get("halo_coletavel")
        if halo is None:
            return
        pulse = (0.94, 1.0, 1.06)[int(self.elapsed * 4.0 + entity.z * 0.01) % 3]
        h = size * C.FINAL_HALO_SCALE * pulse
        self.blit_world(screen, halo, ("fx", "halo"), entity.x, entity.y - h / 2, entity.z + 1.0, h)

    def alert(self, screen: pygame.Surface, entity: EntityView, spec: ObstacleSpec) -> None:
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

    def draw_entity(self, screen: pygame.Surface, world: WorldStateView, entity: EntityView) -> None:
        if self.watercolor.has_backdrop(world.biome.key):
            self.paper_items.draw(screen, entity, self.cam, self.high_contrast, world.biome.key)
            if self.show_hitboxes:
                pygame.draw.rect(screen, rgb("ff1744"), self.hitbox_rect(entity.hitbox()), 2)
            return
        if entity.kind == "waste":
            self.draw_waste_entity(screen, world, entity)
        elif entity.spec is None:  # power-up
            self.draw_powerup_entity(screen, world, entity)
        else:
            self.draw_obstacle_entity(screen, entity)
        if self.show_hitboxes:
            rect = self.hitbox_rect(entity.hitbox())
            pygame.draw.rect(screen, rgb("00e676") if entity.kind == "waste" else rgb("ff1744"), rect, 2)

    def draw_waste_entity(self, screen: pygame.Surface, world: WorldStateView, entity: EntityView) -> None:
        self.halo(screen, world, entity, 46.0)
        self.shadow(screen, entity.x, entity.z, 50, 70)
        sprite = self.waste.get(entity.sprite)
        color = WASTE_BY_KEY[entity.sprite].color if entity.sprite in WASTE_BY_KEY else rgb("ffb300")
        bob = math.sin(self.elapsed * 3.0 + entity.z * 0.02) * 3
        if sprite is None:
            self.fallback_ball(screen, entity, color, 22)
            return
        self.blit_world(
            screen,
            sprite,
            ("item", entity.sprite),
            entity.x,
            entity.y - 23 + bob,
            entity.z,
            46,
            outline=color if self.high_contrast else None,
        )

    def draw_powerup_entity(self, screen: pygame.Surface, world: WorldStateView, entity: EntityView) -> None:
        self.halo(screen, world, entity, 56.0)
        self.shadow(screen, entity.x, entity.z, 46, 60)
        sprite = self.powerups.get(entity.kind)
        color = POWERUP_COLORS.get(entity.kind, (255, 255, 255))
        bob = math.sin(self.elapsed * 3.2 + entity.z * 0.015) * 4
        if sprite is None:
            self.fallback_ball(screen, entity, color, 20)
            return
        self.blit_world(
            screen,
            sprite,
            ("item", entity.kind),
            entity.x,
            entity.y - 26 + bob,
            entity.z,
            56,
            outline=color if self.high_contrast else None,
        )

    def draw_obstacle_entity(self, screen: pygame.Surface, entity: EntityView) -> None:
        spec = entity.spec
        if spec is None:
            return
        self.alert(screen, entity, spec)
        self.ensure_scenery()
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
                outline=HC_OBSTACLE if self.high_contrast else None,
            )
            return
        rect = self.hitbox_rect(entity.hitbox())
        color = {"low": rgb("5d4037"), "gate": rgb("311b92"), "tower": rgb("3e2723")}[entity.kind]
        pygame.draw.rect(screen, color, rect, 5 if entity.kind == "gate" else 0)

    def fallback_ball(self, screen: pygame.Surface, entity: EntityView, color: Color, radius: float) -> None:
        x, y, scale = project(entity.x, entity.y, entity.z, self.cam)
        r = max(3, int(radius * max(0.08, scale)))
        pygame.draw.circle(screen, color, (int(x), int(y)), r)
        pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), r, max(1, r // 6))

    def hitbox_rect(self, box) -> pygame.Rect:
        z = max(20.0, (box.z_min + box.z_max) / 2)
        x0, y0, _ = project(box.x_min, min(box.y_max, 330.0), z, self.cam)
        x1, y1, _ = project(box.x_max, box.y_min, z, self.cam)
        return pygame.Rect(int(x0), int(y0), max(1, int(x1 - x0)), max(1, int(y1 - y0)))
