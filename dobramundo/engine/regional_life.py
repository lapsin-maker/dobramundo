"""Pequenos encontros ambientais, sem colisão e fora do corredor de reação."""

from __future__ import annotations

import math

from .. import config as C
from ..util import clamp, smoothstep
from .assets import display_format
from .sprites import SpriteCache, project


class RegionalLife:
    PERIOD = 3600.0

    def __init__(self, assets):
        self.frames = []
        self.cache = SpriteCache()
        self._world = None
        self._distance = 0.0
        self._quiet = 1.0
        atlas = assets.sprite("watercolor", "fauna_sprint3")
        if atlas is not None:
            w, h = atlas.get_size()
            for index in range(6):
                col, row = index % 3, index // 3
                cell = atlas.subsurface((col * w // 3, row * h // 2, w // 3, h // 2))
                bounds = cell.get_bounding_rect(min_alpha=40)
                self.frames.append(display_format(cell.subsurface(bounds).copy(), True) if bounds.w else None)

    @staticmethod
    def quiet_share(world):
        # A presença diminui gradualmente quando uma ação exige atenção;
        # nada é transformado em moeda, prêmio ou alvo de colisão.
        quiet = 1.0
        for entity in world.entities:
            if entity.kind not in ("low", "gate", "tower"):
                continue
            # Suave antes e depois do avião; remover um obstáculo já passado
            # não faz o animal reaparecer de um quadro para o outro.
            if entity.z >= C.PLAYER_Z:
                amount = smoothstep(clamp((entity.z - C.PLAYER_Z - 140) / 700, 0.0, 1.0))
            else:
                amount = smoothstep(clamp((C.PLAYER_Z - entity.z) / 70, 0.0, 1.0))
            quiet = min(quiet, amount)
        return quiet

    def encounter(self, world, reduced):
        target = self.quiet_share(world)
        if self._world is not world or world.distance < self._distance:
            self._world = world
            self._quiet = target
        else:
            # Se o obstáculo some por colisão, a fauna só volta lentamente.
            # Distância parada (pausa/redesenho) não avança essa transição.
            self._quiet = min(target, self._quiet + max(0, world.distance - self._distance) / 220)
        self._distance = world.distance
        sequence = math.floor(world.distance / self.PERIOD)
        z = sequence * self.PERIOD + 1850 - world.distance
        if not 260 < z < 1500 or world.visual < 25:
            return None
        river = world.biome.key == "amazonia"
        dolphin = river and sequence % 3 == 2
        pair = (2, 5) if dolphin else ((0, 1) if river else (3, 4))
        side = -1 if sequence % 2 else 1
        x, y = side * (330 if dolphin else 500), 12 if dolphin else 36
        phase = 0.0 if reduced else (world.distance / 125.0) % 1.0
        mix = 0.0 if reduced else (0.5 - 0.5 * math.cos(phase * math.tau))
        if dolphin and not reduced:
            y += 22 * math.sin(phase * math.pi)
        opacity = smoothstep(clamp((1500 - z) / 220, 0.0, 1.0))
        opacity *= smoothstep(clamp((z - 260) / 160, 0.0, 1.0))
        opacity *= smoothstep(clamp((world.visual - 25) / 10, 0.0, 1.0))
        return x, y, z, pair, mix, opacity * self._quiet, side

    def draw(self, screen, world, cam, reduced):
        if len(self.frames) != 6:
            return
        event = self.encounter(world, reduced)
        if event is None:
            return
        x, y, z, pair, mix, opacity, side = event
        if opacity < 0.01:
            return
        sx, sy, scale = project(x, y, z, cam)
        height = max(10, min(70, round(110 * scale)))
        for index, weight in ((pair[0], 1 - mix), (pair[1], mix)):
            sprite = self.frames[index]
            if sprite is None or weight < 0.01:
                continue
            width = max(8, round(height * sprite.get_width() / sprite.get_height()))
            # A segunda pose do boto olha para o lado oposto no atlas.
            flip = (side < 0) != (index == 5)
            image = self.cache.get(sprite, ("fauna", index), (width, height), flip)
            image.set_alpha(round(255 * opacity * weight))
            screen.blit(image, image.get_rect(midbottom=(round(sx), round(sy))))
            image.set_alpha(255)
