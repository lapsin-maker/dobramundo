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
        self.life = RegionalLife(assets, defer=True)
        self.backdrops: dict[str, tuple] = {}
        self.composite_key = None
        self.composite = None

    def load(self, biome: str) -> tuple:
        if biome not in self.backdrops:
            for stage in range(3):
                self.prepare_backdrop(biome, stage)
        layers = self.backdrops[biome]
        return layers if len(layers) == 3 and all(layers) else ()

    def prepare_backdrop(self, biome: str, stage: int) -> None:
        """Load/prepare one stage image as an explicit, measurable task."""
        existing = self.backdrops.get(biome, ())
        if len(existing) == 3 and all(existing):
            return
        layers = list(existing) if existing else [None, None, None]
        if layers[stage] is None:
            name = f"{biome}_{stage}"
            image = self.assets.sprite("watercolor_prepared", name)
            if image is None:
                image = self.assets.sprite("watercolor", name)
                if image is not None:
                    image = display_format(pygame.transform.smoothscale(image, (C.WIDTH + 32, C.HEIGHT)))
            layers[stage] = image
            self.assets.release_folder("watercolor_prepared", (name,))
            self.assets.release_folder("watercolor", (name,))
        if all(image is not None for image in layers):
            self.backdrops[biome] = tuple(layers)
        else:
            # Keep partial state without presenting a false successful package.
            self.backdrops[biome] = tuple(layers)

    def has_backdrop(self, biome: str) -> bool:
        return len(self.backdrops.get(biome, ())) == 3 and all(self.backdrops[biome])

    def release_biome(self, biome: str) -> None:
        self.backdrops.pop(biome, None)
        if self.composite_key is not None and self.composite_key[0] == biome:
            self.composite_key = None
            self.composite = None

    @staticmethod
    def stage_mix(visual: float) -> tuple[int, int, int]:
        """Mistura cedo e sem salto, preservando o início industrial do voo.

        O primeiro 5% permanece inteiramente industrial. Depois, a passagem para
        o despertar ocupa o restante do primeiro terço; a passagem solarpunk
        ocupa o segundo terço. O valor devolvido é uma etapa de 0..32.
        """
        if visual < 5.0:
            return 0, 0, 0
        if visual < C.ERA_SPAN:
            progress = smoothstep(clamp((visual - 5.0) / (C.ERA_SPAN - 5.0), 0.0, 1.0))
            return 0, 1, round(progress * 32)
        if visual < 2 * C.ERA_SPAN:
            progress = smoothstep(clamp((visual - C.ERA_SPAN) / C.ERA_SPAN, 0.0, 1.0))
            return 1, 2, round(progress * 32)
        return 2, 2, 0

    def backdrop(
        self, biome: str, visual: float, visible_height: int = C.HEIGHT, load_if_missing: bool = True
    ) -> pygame.Surface | None:
        layers = self.load(biome) if load_if_missing else self.backdrops.get(biome, ())
        if len(layers) != 3 or not all(layers):
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
        # Rendering never starts asset decoding or atlas extraction. Until all
        # visual prerequisites are ready, the caller can show its light prep UI.
        if not self.has_backdrop(world.biome.key) or not self.route.ready(world.biome.key):
            return False
        height = C.HEIGHT
        if self.route.ground.rows:
            height = self.route.ground.rows[0][0]
        painted = self.backdrop(world.biome.key, world.visual, height, load_if_missing=False)
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
