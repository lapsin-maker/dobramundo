"""Chão texturizado fora da pista: concreto (estágio industrial), solo do bioma
(despertar) e prado (solarpunk), mais a pista de piso drenante do estágio final.

A câmera tem altura fixa, então cada linha da tela corresponde sempre à mesma
profundidade do chão; só a textura desliza sobre ela. Linhas de escala
parecida compartilham uma faixa de textura reduzida, e cada linha é montada com
2 a 4 pedaços dela num único screen.blits() por quadro.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import pygame

from .. import config as C
from ..util import Color, clamp, lerp_color
from .assets import Assets
from .sprites import project

Row = Tuple[int, float, int]  # y da tela, profundidade, grupo de escala


def compute_ground_rows() -> List[Row]:
    rows = []
    for y in range(C.HORIZON_Y + 1, C.HEIGHT):
        z = C.CAMERA_HEIGHT * C.FOV / (y + 0.5 - C.HORIZON_Y)
        if z > C.FOG_END:
            continue  # além disso o chão já está todo na neblina
        rows.append((y, z, int(round(math.log(C.FOV / z) / math.log(C.GROUND_ROW_GROUP)))))
    return rows


class GroundRenderer:
    def __init__(self, assets: Assets) -> None:
        self.textures = {
            name: s.convert() if pygame.display.get_surface() else s for name, s in assets.folder("ground").items()
        }
        self.rows = compute_ground_rows()
        self.groups: Dict[tuple, object] = {}
        self.fog_cache: Dict[Color, pygame.Surface] = {}

    def has(self, name: Optional[str]) -> bool:
        return name is not None and name in self.textures

    def group_strip(self, name: str, group: int) -> Tuple[pygame.Surface, int]:
        cached = self.groups.get((name, group))
        if cached is None:
            texture = self.textures[name]
            tile_w = max(4, int(round(C.GROUND_TILES.get(name, (240.0, 120.0))[0] * C.GROUND_ROW_GROUP**group)))
            tex_h = texture.get_height()
            tile = pygame.transform.smoothscale(texture, (tile_w, tex_h))
            copies = max(1, math.ceil(C.GROUND_STRIP_MIN / tile_w))
            strip = pygame.Surface((tile_w * copies, tex_h))
            if pygame.display.get_surface():
                strip = strip.convert()
            for x in range(0, strip.get_width(), tile_w):
                strip.blit(tile, (x, 0))
            cached = (strip, tile_w)
            self.groups[(name, group)] = cached
        return cached  # type: ignore[return-value]

    def row_info(self, name: str, group: int) -> Optional[tuple]:
        key = ("info", name, group)
        info = self.groups.get(key, False)
        if info is False:
            if name not in self.textures:
                info = None
            else:
                strip, tile_w = self.group_strip(name, group)
                tile_x, tile_z = C.GROUND_TILES.get(name, (240.0, 120.0))
                info = (strip, tile_w, strip.get_width(), tile_x, tile_z, self.textures[name].get_height())
            self.groups[key] = info
        return info  # type: ignore[return-value]

    def warm_tasks(self):
        groups = sorted({g for _, _, g in self.rows})
        for name in self.textures:
            for group in groups:
                yield lambda n=name, g=group: self.group_strip(n, g)

    def fog_overlay(self, fog: Color) -> Tuple[pygame.Surface, int]:
        y_far = int(C.HORIZON_Y + C.CAMERA_HEIGHT * C.FOV / C.FOG_END)
        y_near = int(C.HORIZON_Y + C.CAMERA_HEIGHT * C.FOV / C.FOG_START) + 1
        overlay = self.fog_cache.get(fog)
        if overlay is None:
            self.fog_cache.clear()
            column = pygame.Surface((1, y_near - y_far), pygame.SRCALPHA)
            for i in range(y_near - y_far):
                z = C.CAMERA_HEIGHT * C.FOV / (y_far + i + 0.5 - C.HORIZON_Y)
                haze = clamp((z - C.FOG_START) / (C.FOG_END - C.FOG_START), 0.0, 1.0)
                column.set_at((0, i), (*fog, int(255 * haze)))
            overlay = pygame.transform.scale(column, (C.WIDTH, y_near - y_far))
            self.fog_cache[fog] = overlay
        return overlay, y_far

    @staticmethod
    def _queue_row(
        jobs: list, info: tuple, y: int, z: float, left: int, right: int, distance: float, cam: float
    ) -> None:
        strip, tile_w, strip_w, tile_x, tile_z, tex_h = info
        origin = ((cam - (C.WIDTH / 2) * tile_x / tile_w) / tile_x) % 1.0 * tile_w
        v = int((z + distance) / tile_z % 1.0 * tex_h)
        x = left
        src = int(origin + left) % tile_w
        while x < right:
            piece = min(strip_w - src, right - x)
            jobs.append((strip, (x, y), (src, v, piece, 1)))
            x += piece
            src = 0

    def draw(
        self,
        screen: pygame.Surface,
        world,
        flags,
        cam: float,
        fog: Color,
        names: Tuple[str, str, str],
        road_texture: Optional[str],
    ) -> None:
        """names = (chão industrial, chão do despertar, chão solarpunk)."""
        if not self.textures:
            return
        green_flags, final_flags = flags
        industrial, green_name, solar_name = names
        solar_ok = self.has(solar_name)
        green_ok = self.has(green_name)
        road_ok = self.has(road_texture)
        segments = world.segments
        first = segments[0] if segments else 0.0
        count = len(segments)
        distance = world.distance
        jobs: list = []
        road_jobs: list = []
        for y, z, group in self.rows:
            i = int((z - first) // C.SEGMENT_LENGTH)
            in_track = 0 <= i < count
            is_final = bool(final_flags) and in_track and final_flags[i]
            if is_final and solar_ok:
                name = solar_name
            elif green_flags and in_track and green_flags[i] and green_ok:
                name = green_name
            else:
                name = industrial
            scale = C.FOV / z
            road_left = int(C.WIDTH / 2 + (-C.ROAD_WIDTH / 2 - cam) * scale)
            road_right = int(C.WIDTH / 2 + (C.ROAD_WIDTH / 2 - cam) * scale)
            if is_final and road_ok:
                info = self.row_info(road_texture, group)  # type: ignore[arg-type]
                if info is not None:
                    self._queue_row(
                        road_jobs, info, y, z, max(0, road_left), min(C.WIDTH, road_right + 1), distance, cam
                    )
            if road_left + 2 <= 0 and road_right - 2 >= C.WIDTH:
                continue  # a pista cobre a linha inteira
            info = self.row_info(name, group)
            if info is None:
                continue
            # Só as laterais: a pista (desenhada depois) cobre o meio da linha.
            self._queue_row(jobs, info, y, z, 0, min(road_left + 2, C.WIDTH), distance, cam)
            self._queue_row(jobs, info, y, z, max(road_right - 2, 0), C.WIDTH, distance, cam)
        screen.blits(jobs, doreturn=False)
        if road_jobs:
            screen.blits(road_jobs, doreturn=False)
        if industrial == "concrete" and "concrete" in self.textures:
            for near_z, far_z in self.concrete_spans(world, green_flags):
                self.draw_concrete_joints(screen, near_z, far_z, cam, fog)
        overlay, y_far = self.fog_overlay(fog)
        screen.blit(overlay, (0, y_far))

    @staticmethod
    def concrete_spans(world, green_flags) -> List[Tuple[float, float]]:
        """Faixas de profundidade ainda de concreto (para as juntas das placas)."""
        near = C.CAMERA_HEIGHT * C.FOV / (C.HEIGHT - C.HORIZON_Y)
        if not green_flags:
            return [(near, C.FOG_END)]
        spans: List[Tuple[float, float]] = []
        for i, z in enumerate(world.segments):
            if green_flags[i]:
                continue
            z0, z1 = max(z, near), min(z + C.SEGMENT_LENGTH, C.FOG_END)
            if z1 <= z0:
                continue
            if spans and abs(spans[-1][1] - z0) < 1e-6:
                spans[-1] = (spans[-1][0], z1)
            else:
                spans.append((z0, z1))
        return spans

    @staticmethod
    def draw_concrete_joints(screen: pygame.Surface, near_z: float, far_z: float, cam: float, fog: Color) -> None:
        """Juntas das placas paralelas à pista, em perspectiva exata."""
        marks = [C.FOG_START + (C.FOG_END - C.FOG_START) * k / 4 for k in range(5)]
        pieces = [near_z] + [m for m in marks if near_z < m < far_z] + [far_z]
        for x in C.CONCRETE_JOINTS_X:
            for side in (-1, 1):
                for z0, z1 in zip(pieces, pieces[1:]):
                    if z1 <= z0:
                        continue
                    haze = clamp((z0 - C.FOG_START) / (C.FOG_END - C.FOG_START), 0.0, 1.0)
                    p0 = project(side * x, 0, z0, cam)
                    p1 = project(side * x, 0, z1, cam)
                    pygame.draw.line(
                        screen,
                        lerp_color(C.CONCRETE_JOINT_COLOR, fog, haze),
                        (p0[0], p0[1]),
                        (p1[0], p1[1]),
                        max(1, int(2.2 * p0[2])),
                    )
