"""Percurso aquarelado com chão projetado e margens ancoradas no mundo.

O deslocamento usa a mesma distância e projeção dos objetos de jogo. O horizonte
é distante; água, solo e construções nunca ficam presos à tela. Texturas espelhadas
formam um período contínuo nas duas direções, sem saltar ao reiniciar o percurso.
"""

from __future__ import annotations

import math

import pygame

from .. import config as C
from .assets import Assets, display_format
from .ground import GroundRenderer, compute_ground_rows
from .sprites import SpriteCache, fog_level, project


class PaintedGround(GroundRenderer):
    TILE_X = 1050.0
    TILE_Z = 1300.0

    def __init__(self, atlas: pygame.Surface) -> None:
        self.textures = {}
        for index, name in enumerate(("negro", "solimoes", "soil", "green")):
            w, h = atlas.get_size()
            col, row = index % 2, index // 2
            rect = pygame.Rect(col * w // 2, row * h // 2,
                               (col + 1) * w // 2 - col * w // 2,
                               (row + 1) * h // 2 - row * h // 2)
            small = pygame.transform.smoothscale(atlas.subsurface(rect), (512, 512))
            # Espelhamento evita emendas de posição/cor no módulo da textura.
            tile = display_format(pygame.Surface((1024, 1024)))
            for x, y in ((0, 0), (512, 0), (0, 512), (512, 512)):
                tile.blit(pygame.transform.flip(small, bool(x), bool(y)), (x, y))
            self.textures[name] = tile
        # Faixas de dois pixels preservam perspectiva sem custar centenas de
        # transformações extras; objetos/piloto continuam em resolução integral.
        self.rows = compute_ground_rows()[::2]
        self.fog_cache = {}
        self.source_rows = {name: tuple(tile.subsurface((0, v, 1024, 1)) for v in range(1024))
                            for name, tile in self.textures.items()}
        self.line_buffers = {}

    def warm_tasks(self):
        # A textura já está preparada. Somente linhas de um pixel são reescaladas
        # durante o voo; não há dezenas de cópias gigantes por grupo de escala.
        return iter(())

    def queue_line(self, jobs, name, y, z, left, right, distance, cam):
        width = max(8, round(self.TILE_X * C.FOV / z))
        v = int((z + distance) / self.TILE_Z * 1024) % 1024
        key = name, y
        buffer = self.line_buffers.get(key)
        if buffer is None:
            buffer = [display_format(pygame.Surface((width, 2))), -1]
            self.line_buffers[key] = buffer
        line = buffer[0]
        if buffer[1] != v:
            pygame.transform.scale(self.source_rows[name][v], (width, 2), line)
            buffer[1] = v
        origin = cam * width / self.TILE_X - C.WIDTH / 2
        x, src = left, int(origin + left) % width
        while x < right:
            piece = min(width - src, right - x)
            jobs.append((line, (x, y), (src, 0, piece, 2)))
            x += piece
            src = 0

    def paint(self, screen, biome: str, distance: float, cam: float, fog) -> None:
        jobs = []
        river = biome == "amazonia"
        half = C.ROAD_WIDTH / 2
        for y, z, _ in self.rows:
            scale = C.FOV / z
            # Pequenas curvas da margem não alteram as faixas de colisão.
            bend = math.sin((distance + z) / 1100) * 45 + math.sin((distance + z) / 140) * 18
            left = max(0, min(C.WIDTH, round(C.WIDTH / 2 + (-half + bend - cam) * scale)))
            right = max(0, min(C.WIDTH, round(C.WIDTH / 2 + (half + bend - cam) * scale)))
            seam = bend + math.sin((distance + z) / 170) * 32 + math.sin((distance + z) / 53) * 10
            center = max(left, min(right, round(C.WIDTH / 2 + (seam - cam) * scale)))
            bank = "green" if river else "soil"
            ranges = [(bank, 0, left), (bank, right, C.WIDTH)]
            if river:
                ranges.extend([("negro", left, center), ("solimoes", center, right)])
            else:
                ranges.append(("soil", left, right))
            for name, x0, x1 in ranges:
                if x1 > x0:
                    self.queue_line(jobs, name, y, z, x0, x1, distance, cam)
        screen.blits(jobs, doreturn=False)
        overlay, y_far = self.fog_overlay(fog)
        screen.blit(overlay, (0, y_far))


class PaintedRoute:
    """Cenografia sem colisões; posições em unidades de mundo, não pixels."""

    SPACING = 220.0
    HEIGHTS = (170, 230, 235, 270, 170, 180, 230, 285, 190, 140, 180, 200)

    def __init__(self, assets: Assets) -> None:
        atlas = assets.sprite("watercolor", "terrain_tiles")
        valid = atlas is not None and min(atlas.get_size()) >= 2 and atlas.get_bounding_rect().w > 0
        self.ground = PaintedGround(atlas) if valid else None
        self.banks = {}
        self.cache = SpriteCache()
        self.assets = assets

    def load(self, biome: str) -> tuple:
        if biome not in self.banks:
            atlas = self.assets.sprite("watercolor", "banks_" + biome)
            sprites = []
            if atlas is not None and atlas.get_width() >= 4 and atlas.get_height() >= 3:
                w, h = atlas.get_size()
                for index in range(12):
                    col, row = index % 4, index // 4
                    rect = pygame.Rect(col * w // 4, row * h // 3,
                                       (col + 1) * w // 4 - col * w // 4,
                                       (row + 1) * h // 3 - row * h // 3)
                    cell = atlas.subsurface(rect)
                    bounds = cell.get_bounding_rect(min_alpha=30)
                    if bounds.w == 0 or bounds.h == 0:
                        sprites = []
                        break  # pacote parcial: o chamador usa o cenário procedural completo
                    sprites.append(display_format(cell.subsurface(bounds).copy(), True))
            self.banks[biome] = tuple(sprites)
        return self.banks[biome]

    def ready(self, biome: str) -> bool:
        return self.ground is not None and len(self.load(biome)) == 12

    @staticmethod
    def scenery_index(sequence: int, side: int, stage: int) -> int:
        slot = (sequence + (3 if side > 0 else 0)) % 8
        if slot in (1, 3, 6):
            return (2, 6, 7)[slot % 3]  # flora em todos os estágios
        if slot == 7:
            return 3  # marco/árvore local menos frequente
        return ((0, 1, 0, 2), (4, 5, 4, 6), (8, 9, 10, 11))[stage][slot % 4]

    def placements(self, distance: float, stage: int, reduced: bool = False, biome: str = "amazonia"):
        """A identidade de cada peça persiste enquanto ela atravessa a câmera."""
        first = math.floor(distance / self.SPACING) - 1
        result = []
        for sequence in range(first, first + 14):
            for side in (-1, 1):
                z = sequence * self.SPACING + (85 if side > 0 else 0) - distance
                if not C.NEAR_CLIP_Z - 95 <= z <= C.FOG_END:
                    continue
                # No modo reduzido menos peças; a navegação continua avançando.
                if reduced and (sequence + (side > 0)) % 2:
                    continue
                index = self.scenery_index(sequence, side, stage)
                if biome == "amazonia" and index == 3:
                    index = 3 if sequence % 48 == 7 and side < 0 else 7
                x = side * (530 + (sequence % 3) * 64)
                if z >= C.NEAR_CLIP_Z:
                    result.append((z, x, index, side))
                if not reduced and sequence % 2 == 0 and C.NEAR_CLIP_Z <= z + 95 <= C.FOG_END:
                    result.append((z + 95, side * 1030, 2 if sequence % 4 else 7, side))
        return sorted(result, reverse=True)

    def draw(self, screen, world, cam: float, reduced: bool, fog) -> bool:
        sprites = self.load(world.biome.key)
        if not self.ready(world.biome.key):
            return False
        self.ground.paint(screen, world.biome.key, world.distance, cam, fog)
        self.cache.fog_color = fog
        stage = min(2, int(world.visual / C.ERA_SPAN))
        for z, x, index, side in self.placements(world.distance, stage, reduced, world.biome.key):
            sx, sy, scale = project(x, 0, z, cam)
            sprite = sprites[index]
            height = max(4, round(self.HEIGHTS[index] * scale / 3) * 3)
            width = max(4, round(height * sprite.get_width() / sprite.get_height()))
            if sx + width / 2 < 0 or sx - width / 2 > C.WIDTH:
                continue
            key = ("painted-bank", world.biome.key, index)
            size = width, height
            image = self.cache.get(sprite, key, size, side > 0)
            level = fog_level(z)
            if level:
                image = self.cache.fogged(image, (key, size, side > 0), level)
            screen.blit(image, (round(sx - width / 2), round(sy - height)))
        return True
