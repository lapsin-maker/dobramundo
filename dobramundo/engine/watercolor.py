"""Paisagens pintadas em camadas, com movimento de chão e caches CPU limitados.

As ilustrações são cenografia: nunca definem colisões ou itens coletáveis.
Transformações são compostas só quando o passo visual muda; nenhum PNG é
decodificado, nem uma tela inteira redimensionada, dentro do laço de voo.
"""

from __future__ import annotations

import math

import pygame

from .. import config as C
from ..util import clamp, smoothstep
from .assets import Assets, display_format
from .sprites import project


class WatercolorWorld:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.backdrops: dict[str, tuple] = {}
        self.composite_key = None
        self.composite = None
        self.highlight = display_format(pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA), True)

    def load(self, biome: str) -> tuple:
        if biome not in self.backdrops:
            images = self.assets.folder("watercolor")
            layers = [images.get(f"{biome}_{stage}") for stage in range(3)]
            self.backdrops[biome] = (
                tuple(display_format(pygame.transform.smoothscale(image, (C.WIDTH + 32, C.HEIGHT)))
                      for image in layers) if all(image is not None for image in layers) else ()
            )
        return self.backdrops[biome]

    @staticmethod
    def stage_mix(visual: float) -> tuple[int, int, int]:
        """Limiar real preservado: indústria < 1/3, despertar até 2/3, solar."""
        if visual < C.ERA_SPAN:
            return 0, 0, 0
        if visual < 2 * C.ERA_SPAN:
            return 0, 1, round(smoothstep(clamp((visual - C.ERA_SPAN) / 16, 0, 1)) * 32)
        return 1, 2, round(smoothstep(clamp((visual - 2 * C.ERA_SPAN) / 12, 0, 1)) * 32)

    def backdrop(self, biome: str, visual: float) -> pygame.Surface | None:
        layers = self.load(biome)
        if not layers:
            return None
        a, b, step = self.stage_mix(visual)
        if a == b or step == 0:
            return layers[a]
        if step == 32:
            return layers[b]
        key = biome, a, b, step
        if key != self.composite_key:
            # A aquarela nova chega primeiro ao horizonte. Faixas sobrepostas
            # de alfa evitam borda dura, ruído e mudanças abruptas na região do avião.
            result = layers[a].copy()
            progress = step / 32
            for y in range(0, C.HEIGHT, 26):
                spatial = y / C.HEIGHT
                alpha = clamp(progress * 1.5 - spatial * 0.5, 0, 1)
                strip = layers[b].subsurface((0, y, C.WIDTH + 32, min(26, C.HEIGHT - y)))
                strip.set_alpha(round(alpha * 255))
                result.blit(strip, (0, y))
                strip.set_alpha(None)
            self.composite_key, self.composite = key, result
        return self.composite

    def draw(self, screen, world, cam: float, reduce_motion: bool = False) -> bool:
        painted = self.backdrop(world.biome.key, world.visual)
        if painted is None:
            return False
        shift = 0 if reduce_motion else int(clamp(cam * 0.045, -14, 14))
        screen.blit(painted, (-16 - shift, 0))
        if not reduce_motion:
            self.flow(screen, world, cam)
        return True

    def flow(self, screen, world, cam: float) -> None:
        """Marcas suaves do chão movem-se na mesma perspectiva e velocidade dos itens."""
        overlay = self.highlight
        overlay.fill((0, 0, 0, 0))
        river = world.biome.key == "amazonia"
        for index in range(44):
            z = 90 + (index * 73.0 - world.distance) % 2250
            x = math.sin(index * 2.399) * 520
            sx, sy, scale = project(x, 0, z, cam)
            if sy < C.HORIZON_Y + 35 or sy > C.HEIGHT + 15:
                continue
            extent = max(3, int((14 + index % 4 * 9) * scale))
            color = (255, 249, 223, 42) if river else (180, 133, 74, 30)
            width = max(1, min(3, int(scale * 1.2)))
            points = [(int(sx - extent), int(sy)), (int(sx), int(sy + 2 * scale)),
                      (int(sx + extent), int(sy))]
            pygame.draw.lines(overlay, color, False, points, width)
        screen.blit(overlay, (0, 0))
