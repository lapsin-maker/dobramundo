"""Pixel regression against PaintedGround.queue_line from commit 12dda71."""

import pygame

from dobramundo import config as C
from dobramundo.engine.assets import Assets
from dobramundo.engine.painted_route import PaintedGround


class _ReferenceGround(PaintedGround):
    """The pre-optimization queue_line implementation from 12dda71."""

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
        indices = tuple(int(value / mip_factor) % texture.get_height() for value in raw_vs)
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
                for row, value in enumerate(indices):
                    band.blit(texture, (0, row), (0, value, texture.get_width(), 1))
                pygame.transform.scale(band, (width, self.ROW_HEIGHT), line)
            buffer[1] = signature
        origin = cam * width / self.TILE_X - C.WIDTH / 2
        x, src = left, int(origin + left) % width
        while x < right:
            piece = min(width - src, right - x)
            jobs.append((line, (x, y), (src, 0, piece, self.ROW_HEIGHT)))
            x += piece
            src = 0


def _fully_prepared_ground(cls, atlas):
    ground = cls(atlas)
    for name in ground.textures:
        for _ in range(6):
            ground.prepare_vertical_mip(name)
    return ground


def test_ground_pixels_match_12dda71(display):
    atlas = Assets().sprite("watercolor", "terrain_tiles_v3")
    if atlas is None:
        atlas = Assets().sprite("watercolor", "terrain_tiles")
    assert atlas is not None
    optimized = _fully_prepared_ground(PaintedGround, atlas)
    reference = _fully_prepared_ground(_ReferenceGround, atlas)
    actual = pygame.Surface(display.get_size()).convert()
    expected = pygame.Surface(display.get_size()).convert()
    for biome in ("amazonia", "caatinga"):
        for distance in (0.0, 0.5, 123.4, 1300.0, 5240.0, 18000.0):
            for cam in (-420.0, -17.25, 0.0, 163.5, 510.0):
                actual.fill((8, 12, 16))
                expected.fill((8, 12, 16))
                fog = (226, 220, 191) if biome == "amazonia" else (240, 222, 185)
                optimized.paint(actual, biome, distance, cam, fog)
                reference.paint(expected, biome, distance, cam, fog)
                assert pygame.image.tobytes(actual, "RGB") == pygame.image.tobytes(expected, "RGB"), (
                    biome,
                    distance,
                    cam,
                )
