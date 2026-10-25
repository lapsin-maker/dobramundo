"""Percurso aquarelado com chão projetado e margens ancoradas no mundo.

O deslocamento usa a mesma distância e projeção dos objetos de jogo. O horizonte
é distante; água, solo e construções nunca ficam presos à tela. Texturas espelhadas
formam um período contínuo nas duas direções, sem saltar ao reiniciar o percurso.
"""

from __future__ import annotations

import math

import pygame

from .. import config as C
from ..util import clamp, smoothstep
from .assets import Assets, display_format
from .ground import GroundRenderer, compute_ground_rows
from .sprites import SpriteCache, fog_level, project


class PaintedGround(GroundRenderer):
    TILE_X = 1050.0
    TILE_Z = 1300.0
    # Three output rows are sampled separately into a small source band, then
    # scaled together. This avoids repeated nearest-expanded rows without
    # tripling screen blits or transform calls.
    ROW_HEIGHT = 3

    def __init__(self, atlas: pygame.Surface) -> None:
        self.textures = {}
        for index, name in enumerate(("negro", "solimoes", "soil", "green")):
            w, h = atlas.get_size()
            col, row = index % 2, index // 2
            rect = pygame.Rect(
                col * w // 2, row * h // 2, (col + 1) * w // 2 - col * w // 2, (row + 1) * h // 2 - row * h // 2
            )
            small = pygame.transform.smoothscale(atlas.subsurface(rect), (512, 512))
            # Espelhamento evita emendas de posição/cor no módulo da textura.
            tile = display_format(pygame.Surface((1024, 1024)))
            for x, y in ((0, 0), (512, 0), (0, 512), (512, 512)):
                tile.blit(pygame.transform.flip(small, bool(x), bool(y)), (x, y))
            self.textures[name] = tile
        self.rows = compute_ground_rows()[:: self.ROW_HEIGHT]
        self.fog_cache = {}
        self.vertical_mips = {name: [tile] for name, tile in self.textures.items()}
        self.line_buffers = {}

    def warm_tasks(self):
        # Each lower-resolution level is a separate bounded warm-up unit.
        for name in self.textures:
            for _level in range(6):
                yield lambda n=name: self.prepare_vertical_mip(n)

    def prepare_vertical_mip(self, name: str) -> None:
        levels = self.vertical_mips[name]
        source = levels[-1]
        if source.get_height() <= 16:
            return
        target_size = (source.get_width(), max(1, source.get_height() // 2))
        levels.append(pygame.transform.smoothscale(source, target_size))

    def prepare_line_buffers(self, name: str, rows) -> None:
        for y, _z, _group in rows:
            middle_y = y + self.ROW_HEIGHT // 2
            middle_z = C.CAMERA_HEIGHT * C.FOV / (middle_y + 0.5 - C.HORIZON_Y)
            width = max(8, round(self.TILE_X * C.FOV / middle_z))
            key = name, y
            if key not in self.line_buffers:
                band = display_format(pygame.Surface((1024, self.ROW_HEIGHT)))
                line = display_format(pygame.Surface((width, self.ROW_HEIGHT)))
                self.line_buffers[key] = [line, (), band]

    def queue_line(self, jobs, name, y, z, left, right, distance, cam):
        depths = tuple(C.CAMERA_HEIGHT * C.FOV / (row_y + 0.5 - C.HORIZON_Y) for row_y in range(y, y + self.ROW_HEIGHT))
        z = depths[self.ROW_HEIGHT // 2]
        width = max(8, round(self.TILE_X * C.FOV / z))
        raw_vs = tuple((row_z + distance) / self.TILE_Z * 1024 for row_z in depths)
        step = max(abs(raw_vs[0] - raw_vs[1]), abs(raw_vs[1] - raw_vs[2]))
        mip_level = 0
        while step / (2**mip_level) > 1.25 and mip_level < len(self.vertical_mips[name]) - 1:
            mip_level += 1
        texture = self.vertical_mips[name][mip_level]
        mip_factor = 2**mip_level
        indices = tuple(int(v / mip_factor) % texture.get_height() for v in raw_vs)
        signature = mip_level, indices
        key = name, y
        buffer = self.line_buffers.get(key)
        if buffer is None:
            self.prepare_line_buffers(name, ((y, z, 0),))
            buffer = self.line_buffers[key]
        line = buffer[0]
        band = buffer[2]
        if buffer[1] != signature:
            if indices[0] - indices[1] == 1 and indices[1] - indices[2] == 1:
                source_band = texture.subsurface((0, indices[2], texture.get_width(), self.ROW_HEIGHT))
                source_band = pygame.transform.flip(source_band, False, True)
                pygame.transform.scale(source_band, (width, self.ROW_HEIGHT), line)
            else:
                for row, v in enumerate(indices):
                    band.blit(texture, (0, row), (0, v, texture.get_width(), 1))
                pygame.transform.scale(band, (width, self.ROW_HEIGHT), line)
            buffer[1] = signature
        origin = cam * width / self.TILE_X - C.WIDTH / 2
        x, src = left, int(origin + left) % width
        while x < right:
            piece = min(width - src, right - x)
            jobs.append((line, (x, y), (src, 0, piece, self.ROW_HEIGHT)))
            x += piece
            src = 0

    def paint(self, screen, biome: str, distance: float, cam: float, fog) -> None:
        jobs = []
        river = biome == "amazonia"
        half = C.ROAD_WIDTH / 2
        for y, z, _ in self.rows:
            if not river:
                # Na Caatinga as três regiões usam o mesmo solo: uma única faixa
                # produz os mesmos pixels sem repetir recortes e trigonometria.
                self.queue_line(jobs, "soil", y, z, 0, C.WIDTH, distance, cam)
                continue
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
        self.ground = None
        self._ground_attempted = False
        self.banks = {}
        self.cache = SpriteCache()
        self.assets = assets
        self._bank_atlas = None
        self._bank_biome = None
        self._bank_failed = False

    def prepare_ground(self) -> None:
        """Decode and prepare the ground atlas as one explicit warm-up unit."""
        if self._ground_attempted:
            return
        self._ground_attempted = True
        atlas = self.assets.sprite("watercolor", "terrain_tiles_v3")
        if atlas is None:
            atlas = self.assets.sprite("watercolor", "terrain_tiles")
        valid = atlas is not None and min(atlas.get_size()) >= 2 and atlas.get_bounding_rect().w > 0
        self.ground = PaintedGround(atlas) if valid else None
        self.assets.release_folder("watercolor", ("terrain_tiles_v3", "terrain_tiles"))

    def prepare_bank(self, biome: str, index: int) -> None:
        """Extract one atlas cell; the 12 pieces are separate warm-up units."""
        if isinstance(self.banks.get(biome), tuple):
            return
        if self._bank_biome != biome:
            self._bank_biome = biome
            self._bank_atlas = self.assets.sprite("watercolor", "banks_" + biome)
            self._bank_failed = False
            self.banks[biome] = []
        atlas = self._bank_atlas
        if self._bank_failed or atlas is None or atlas.get_width() < 4 or atlas.get_height() < 3:
            self._bank_failed = True
            self.banks[biome] = ()
            self._finish_banks(biome)
            return
        w, h = atlas.get_size()
        col, row = index % 4, index // 4
        rect = pygame.Rect(
            col * w // 4, row * h // 3, (col + 1) * w // 4 - col * w // 4, (row + 1) * h // 3 - row * h // 3
        )
        cell = atlas.subsurface(rect)
        bounds = cell.get_bounding_rect(min_alpha=30)
        if bounds.w == 0 or bounds.h == 0:
            self._bank_failed = True
            self.banks[biome] = ()
            self._finish_banks(biome)
            return
        current = self.banks[biome]
        if isinstance(current, list):
            current.append(display_format(cell.subsurface(bounds).copy(), True))
            if len(current) == 12:
                self.banks[biome] = tuple(current)
                self._finish_banks(biome)

    def _finish_banks(self, biome: str) -> None:
        self._bank_atlas = None
        self.assets.release_folder("watercolor", ("banks_" + biome,))

    def load(self, biome: str) -> tuple:
        if biome not in self.banks:
            atlas = self.assets.sprite("watercolor", "banks_" + biome)
            sprites = []
            if atlas is not None and atlas.get_width() >= 4 and atlas.get_height() >= 3:
                w, h = atlas.get_size()
                for index in range(12):
                    col, row = index % 4, index // 4
                    rect = pygame.Rect(
                        col * w // 4, row * h // 3, (col + 1) * w // 4 - col * w // 4, (row + 1) * h // 3 - row * h // 3
                    )
                    cell = atlas.subsurface(rect)
                    bounds = cell.get_bounding_rect(min_alpha=30)
                    if bounds.w == 0 or bounds.h == 0:
                        sprites = []
                        break  # pacote parcial: o chamador usa o cenário procedural completo
                    sprites.append(display_format(cell.subsurface(bounds).copy(), True))
            self.banks[biome] = tuple(sprites)
            self.assets.release_folder("watercolor", ("banks_" + biome,))
        return self.banks[biome]

    def release_biome(self, biome: str) -> None:
        self.banks.pop(biome, None)
        if self._bank_biome == biome:
            self._bank_atlas = None
            self._bank_biome = None
            self._bank_failed = False
        self.cache = SpriteCache()

    def ready(self, biome: str) -> bool:
        return self.ground is not None and len(self.banks.get(biome, ())) == 12

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
                    # O Teatro é um marco único no horizonte: não reaparece como
                    # cópias de um prédio a cada volta do percurso.
                    index = 7
                x = side * (530 + (sequence % 3) * 64)
                if z >= C.NEAR_CLIP_Z:
                    result.append((z, x, index, side))
                if not reduced and sequence % 2 == 0 and C.NEAR_CLIP_Z <= z + 95 <= C.FOG_END:
                    result.append((z + 95, side * 1030, 2 if sequence % 4 else 7, side))
        return sorted(result, reverse=True)

    @staticmethod
    def stage_blend(visual: float, z: float) -> tuple:
        """Transformação contínua, chegando do horizonte à margem próxima."""
        delay = 4.0 * (1.0 - clamp(z / C.FOG_END, 0.0, 1.0))
        if visual < C.ERA_SPAN + delay:
            return 0, 0, 0.0
        if visual < 2 * C.ERA_SPAN + delay:
            mix = smoothstep(clamp((visual - C.ERA_SPAN - delay) / 16.0, 0.0, 1.0))
            return (1, 1, 0.0) if mix >= 1 else (0, 1, mix)
        mix = smoothstep(clamp((visual - 2 * C.ERA_SPAN - delay) / 12.0, 0.0, 1.0))
        return (2, 2, 0.0) if mix >= 1 else (1, 2, mix)

    def _bank(self, screen, sprites, biome, placement, cam, opacity=1.0):
        z, x, index, side = placement
        sx, sy, scale = project(x, 0, z, cam)
        sprite = sprites[index]
        height = max(4, round(self.HEIGHTS[index] * scale / 3) * 3)
        width = max(4, round(height * sprite.get_width() / sprite.get_height()))
        if sx + width / 2 < 0 or sx - width / 2 > C.WIDTH:
            return
        key = ("painted-bank", biome, index)
        size = width, height
        image = self.cache.get(sprite, key, size, side > 0)
        level = fog_level(z)
        if level:
            image = self.cache.fogged(image, (key, size, side > 0), level)
        # Peças próximas saem gradualmente, inclusive quando uma curva deixa
        # parte da silhueta visível junto ao plano de corte.
        near = smoothstep(clamp((z - C.NEAR_CLIP_Z) / 55, 0.0, 1.0))
        alpha = round(255 * opacity * near)
        if alpha:
            image.set_alpha(alpha)
            screen.blit(image, (round(sx - width / 2), round(sy - height)))
            image.set_alpha(255)

    def draw(self, screen, world, cam: float, reduced: bool, fog) -> bool:
        if not self.ready(world.biome.key):
            return False
        sprites = self.banks.get(world.biome.key, ())
        if not self.ready(world.biome.key):
            return False
        self.ground.paint(screen, world.biome.key, world.distance, cam, fog)
        self.cache.fog_color = fog
        # A posição de cada peça é estável em todos os estágios; só sua forma
        # se dissolve para a seguinte. Desenhar não avança relógios ou o mundo.
        stages = [self.placements(world.distance, stage, reduced, world.biome.key) for stage in range(3)]
        for slot, placement in enumerate(stages[0]):
            a, b, mix = self.stage_blend(world.visual, placement[0])
            old, new = stages[a][slot], stages[b][slot]
            if old[2] == new[2] or a == b:
                self._bank(screen, sprites, world.biome.key, old, cam)
            else:
                self._bank(screen, sprites, world.biome.key, old, cam, 1.0 - mix)
                self._bank(screen, sprites, world.biome.key, new, cam, mix)
        return True
