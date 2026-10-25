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
from .painted_route import PaintedRoute
from .regional_life import RegionalLife


class WatercolorWorld:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.route = PaintedRoute(assets)
        self.life = RegionalLife(assets)
        self.backdrops: dict[str, tuple] = {}
        self.composite_key = None
        self.composite = None

    def load(self, biome: str) -> tuple:
        if biome not in self.backdrops:
            names = tuple(f"{biome}_{stage}" for stage in range(3))
            prepared = self.assets.folder("watercolor_prepared", names)
            layers = [prepared.get(name) for name in names]
            if all(image is not None for image in layers):
                result = tuple(display_format(image) for image in layers)
            else:
                original = self.assets.folder("watercolor", names)
                layers = [original.get(name) for name in names]
                result = (
                    tuple(
                        display_format(pygame.transform.smoothscale(image, (C.WIDTH + 32, C.HEIGHT)))
                        for image in layers
                    )
                    if all(image is not None for image in layers)
                    else ()
                )
                self.assets.release_folder("watercolor", names)
            self.assets.release_folder("watercolor_prepared", names)
            self.backdrops[biome] = result
        return self.backdrops[biome]

    def release_biome(self, biome: str) -> None:
        self.backdrops.pop(biome, None)
        if self.composite_key is not None and self.composite_key[0] == biome:
            self.composite_key = None
            self.composite = None

    @staticmethod
    def stage_mix(visual: float) -> tuple[int, int, int]:
        """Limiar real preservado: indústria < 1/3, despertar até 2/3, solar."""
        if visual < C.ERA_SPAN:
            return 0, 0, 0
        if visual < 2 * C.ERA_SPAN:
            return 0, 1, round(smoothstep(clamp((visual - C.ERA_SPAN) / 16, 0, 1)) * 32)
        return 1, 2, round(smoothstep(clamp((visual - 2 * C.ERA_SPAN) / 12, 0, 1)) * 32)

    def backdrop(self, biome: str, visual: float, visible_height: int = C.HEIGHT) -> pygame.Surface | None:
        layers = self.load(biome)
        if not layers:
            return None
        a, b, step = self.stage_mix(visual)
        if a == b or step == 0:
            return layers[a]
        if step == 32:
            return layers[b]
        key = biome, a, b, step, visible_height
        if key != self.composite_key:
            # A aquarela nova chega primeiro ao horizonte. Faixas sobrepostas
            # de alfa evitam borda dura, ruído e mudanças abruptas na região do avião.
            result = layers[a].copy()
            progress = step / 32
            for y in range(0, visible_height, 26):
                spatial = y / C.HEIGHT
                alpha = clamp(progress * 1.5 - spatial * 0.5, 0, 1)
                opacity = round(alpha * 255)
                if opacity == 0:
                    continue
                strip = layers[b].subsurface((0, y, C.WIDTH + 32, min(26, visible_height - y)))
                strip.set_alpha(None if opacity == 255 else opacity)
                result.blit(strip, (0, y))
                strip.set_alpha(None)
            self.composite_key, self.composite = key, result
        return self.composite

    def draw(self, screen, world, cam: float, reduce_motion: bool = False) -> bool:
        height = C.HEIGHT
        if self.route.ready(world.biome.key) and self.route.ground.rows:
            height = self.route.ground.rows[0][0]
        painted = self.backdrop(world.biome.key, world.visual, height)
        if painted is None:
            return False
        drift = math.sin(world.distance / 1200) * 8
        shift = 0 if reduce_motion else int(clamp(cam * 0.045 + drift, -14, 14))
        screen.blit(painted, (-16 - shift, 0))
        # A pintura guarda apenas o horizonte distante. O percurso inteiro avança
        # em coordenadas de mundo, mesmo com efeitos decorativos reduzidos.
        fog = (226, 220, 191) if world.biome.key == "amazonia" else (240, 222, 185)
        if self.route.draw(screen, world, cam, reduce_motion, fog):
            self.life.draw(screen, world, cam, reduce_motion)
            return True
        # Sem o pacote móvel, o chamador usa todo o cenário procedural móvel.
        return False
