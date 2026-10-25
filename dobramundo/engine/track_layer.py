"""Pista e margens do renderizador de reserva; sem regras de partida."""

from __future__ import annotations

from typing import NamedTuple

import pygame

from .. import config as C
from ..content.biomes import Specs
from ..util import Color, clamp, haze_at, lerp_color, rgb, smoothstep
from .contracts import WorldStateView
from .sprites import project

RIVER_NEGRO = rgb("2a1a10")  # águas escuras do Rio Negro
RIVER_ENCOUNTER = rgb("b08452")
RIVER_CURB = rgb("e0c27a")  # orla do rio limpo
ROAD_CURB = rgb("c9a04a")  # meio-fio dourado do piso drenante
PURIFIED_ROAD = rgb("8bcf78")  # Solimões (barrento) ao lado do Rio Negro, no despertar


class TrackPalette(NamedTuple):
    even: Color
    odd: Color
    right_even: Color  # metade direita do rio (Solimões) no encontro das águas
    right_odd: Color
    purified: Color
    lane: Color
    ground: Color
    encounter: float  # 0..1: quanto do encontro das águas aparece
    wave_z: float  # até onde a pista já foi purificada


class TrackLayer:
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

    @staticmethod
    def theme_specs(world: WorldStateView, specs: Specs, stage: str) -> Specs:
        """Bias existing regional scenery by published theme; stages stay authoritative."""
        theme = world.challenge_theme
        if theme is None:
            return specs
        tags = set(theme.decorations)
        names = [name.lower() for name, _ in specs]
        selected = []
        if stage == "green" and "fruit_trees" in tags:
            orchard = ("mangueira", "videira", "juazeiro")
            selected = [item for item in specs if any(token in item[0].lower() for token in orchard)]
            # Add existing orchard trees from the final-era list only; no solar
            # equipment is introduced before the final stage.
            if world.biome.key == "caatinga":
                selected.extend(
                    item
                    for item in world.biome.solar_mid
                    if any(token in item[0].lower() for token in orchard) and item[0].lower() not in names
                )
        elif stage == "industrial" and "boat" in tags:
            tokens = ("porto", "balsa", "container")
            selected = [item for item in specs if any(token in item[0].lower() for token in tokens)]
        elif stage == "green" and "boat" in tags:
            selected = [item for item in specs if any(token in item[0].lower() for token in ("palafita", "flutuante"))]
        elif stage == "green" and "trees" in tags:
            tree_tokens = (
                "arvore",
                "samauma",
                "acaizeiro",
                "buriti",
                "seringueira",
                "juazeiro",
                "mandacaru",
                "carnauba",
                "umbuzeiro",
            )
            selected = [item for item in specs if any(token in item[0].lower() for token in tree_tokens)]
        elif stage == "solar":
            tokens = []
            if "solar" in tags:
                tokens.extend(("solar", "usina"))
            if "wind" in tags:
                tokens.extend(("eolica", "aerogerador"))
            if "boat" in tags:
                tokens.append("barco")
            if "trees" in tags:
                tokens.extend(
                    (
                        "samauma",
                        "acaizeiro",
                        "buriti",
                        "seringueira",
                        "juazeiro",
                        "mandacaru",
                        "carnauba",
                        "umbuzeiro",
                    )
                )
            if tokens:
                selected = [item for item in specs if any(token in item[0].lower() for token in tokens)]
        return list(specs) + selected if selected else specs

    def margins(self, screen: pygame.Surface, world: WorldStateView, seg: int, z: float) -> None:
        """Duas fileiras por lado em cada trecho: fundo (z) e borda (z + 50)."""
        self.ensure_scenery()
        biome = self.biome
        mid_cam = self.cam * C.MID_PARALLAX
        margin_cam = self.cam * C.MARGIN_PARALLAX
        border_z = z + 50.0
        green = world.segment_green(seg)
        solar = world.segment_solar(seg)
        keep = 1.0 - solar  # a peça do estágio anterior afunda enquanto a nova cresce
        industrial_mid = self.theme_specs(world, biome.industrial_mid, "industrial")
        industrial_margin = self.theme_specs(world, biome.industrial_margin, "industrial")
        green_mid = self.theme_specs(world, biome.green_mid, "green")
        green_margin = self.theme_specs(world, biome.green_margin, "green")
        solar_mid = self.theme_specs(world, biome.solar_mid, "solar")
        solar_margin = self.theme_specs(world, biome.solar_margin, "solar")
        for side in (-1, 1):
            # quarteirões: a cada 6 trechos, 2 ficam vazios (num lado de cada vez), para o
            # cenário ter blocos e respiros em vez de uma fila contínua de peças soltas
            if (seg + (3 if side > 0 else 0)) % 6 in (4, 5):
                continue
            if green < 1.0 and keep > 0.0:
                self.piece(screen, industrial_mid, seg, side, C.MID_ROW_X, z, mid_cam, (1.0 - green) * keep)
            if green > 0.0 and keep > 0.0:
                restored = seg % C.RESTORED_EVERY == C.RESTORED_REMAINDER
                specs = biome.restored if restored else green_mid
                index = seg // C.RESTORED_EVERY + (side > 0) if restored else seg
                self.piece(screen, specs, index, side, C.MID_ROW_X, z, mid_cam, green * keep)
            if solar > 0.0:
                marco = seg % C.LANDMARK_EVERY == 4 and (seg // C.LANDMARK_EVERY + (side > 0)) % 2 == 0
                specs = [biome.landmark] if marco else solar_mid
                self.piece(screen, specs, seg, side, C.MID_ROW_X, z, mid_cam, solar)
            if border_z > C.MARGIN_MAX_Z or (seg + (side > 0)) % 2 or (seg // 2) % 4 == 3:
                continue  # a borda alterna de lado a cada trecho, tem vãos e some ao longe
            if green < 1.0 and keep > 0.0:
                self.piece(
                    screen,
                    industrial_margin,
                    seg // 2,
                    side,
                    C.MARGIN_X,
                    border_z,
                    margin_cam,
                    (1.0 - green) * keep,
                )
            if green > 0.0 and keep > 0.0:
                self.piece(screen, green_margin, seg // 2 + 3, side, C.MARGIN_X, border_z, margin_cam, green * keep)
            if solar > 0.0:
                self.piece(
                    screen,
                    solar_margin,
                    seg // 2 + (3 if side > 0 else 0),
                    side,
                    C.MARGIN_X,
                    border_z,
                    margin_cam,
                    solar,
                )

    def track_palette(self, world: WorldStateView) -> TrackPalette:
        """Cores da pista no quadro (mistura dos estágios), calculadas uma vez."""
        a, b, t = world.visual_stage_pair()
        river = self.biome.river
        weight = self.encounter_weight(world) if river else 0.0
        if world.challenge_theme is not None and "river" in world.challenge_theme.decorations:
            weight = min(1.0, weight * 1.15)
        even = lerp_color(a.road_even, b.road_even, t)
        odd = lerp_color(a.road_odd, b.road_odd, t)
        return TrackPalette(
            even=even,
            odd=odd,
            right_even=lerp_color(even, RIVER_ENCOUNTER, weight),
            right_odd=lerp_color(odd, RIVER_ENCOUNTER, weight * 0.95),
            purified=lerp_color(even, PURIFIED_ROAD, 0.2),
            lane=lerp_color(a.lane_line, b.lane_line, t),
            ground=lerp_color(a.ground, b.ground, t),
            encounter=weight,
            wave_z=180.0 + (world.visual / 100.0) ** 1.15 * 2150.0,  # frente da pista purificada
        )

    def draw_track(self, screen: pygame.Surface, world: WorldStateView, flags) -> None:
        """Pista (ou rio) trecho a trecho, do horizonte para o avião, com as margens."""
        pal = self.track_palette(world)
        fog = self.sky.fog_color
        biome = self.biome
        cam = self.cam
        half = C.ROAD_WIDTH / 2
        stretches = []
        for i in range(len(world.segments) - 1, -1, -1):
            z = world.segments[i]
            seg = world.segment_base + i
            edges = (
                project(-half, 0, z, cam),
                project(half, 0, z, cam),
                project(-half, 0, z + C.SEGMENT_LENGTH, cam),
                project(half, 0, z + C.SEGMENT_LENGTH, cam),
            )
            haze = haze_at(z + 50.0)
            if not self.ground.textures:  # sem texturas: chão liso por trecho
                ground = C.GRASS_FALLBACK[seg % 2] if world.segment_green(seg) > 0.0 else pal.ground
                left1, right1, left2, right2 = edges
                pygame.draw.polygon(
                    screen,
                    lerp_color(ground, fog, haze),
                    [(0, left2[1]), (C.WIDTH, right2[1]), (C.WIDTH, right1[1]), (0, left1[1])],
                )
            stretches.append((i, seg, z, edges, haze))
        self.ground.draw(
            screen, world, flags, cam, fog, ("concrete", biome.green_ground, biome.solar_ground), biome.solar_road
        )
        solar_road = self.ground.has(biome.solar_road)
        solar_flags = flags[1]
        for i, seg, z, edges, haze in stretches:
            solar = bool(solar_flags) and solar_flags[i]
            self.draw_road(screen, pal, seg, z, edges, haze, solar and solar_road)
            if biome.river and solar:
                self.curbs(screen, edges, lerp_color(RIVER_CURB, fog, haze), 5)  # orla dourada do rio limpo
            self.draw_lanes(screen, pal, seg, z, haze)
            self.margins(screen, world, seg, z)

    def draw_road(
        self, screen: pygame.Surface, pal: TrackPalette, seg: int, z: float, edges, haze: float, paved: bool
    ) -> None:
        """Superfície de um trecho: piso drenante (só o meio-fio), rio com encontro das águas ou pista."""
        fog = self.sky.fog_color
        left1, right1, left2, right2 = edges
        if paved:  # a textura do piso já foi desenhada pelo chão
            self.curbs(screen, edges, lerp_color(ROAD_CURB, fog, haze), 6)
            return
        even = seg % 2 == 0
        river = self.biome.river
        purify = smoothstep((pal.wave_z - z) / C.ROAD_PURIFY_BAND) if not river else 0.0
        base = lerp_color(pal.even if even else pal.odd, pal.purified, purify)
        if river:  # encontro das águas: o Negro fica escuro à esquerda
            base = lerp_color(base, RIVER_NEGRO, pal.encounter * (0.9 if even else 1.0))
        color = lerp_color(base, fog, haze)
        if river and pal.encounter > 0.01:
            mid1, mid2 = project(0, 0, z, self.cam), project(0, 0, z + C.SEGMENT_LENGTH, self.cam)
            right = lerp_color(pal.right_even if even else pal.right_odd, fog, haze)
            pygame.draw.polygon(screen, color, [left1[:2], mid1[:2], mid2[:2], left2[:2]])
            pygame.draw.polygon(screen, right, [mid1[:2], right1[:2], right2[:2], mid2[:2]])
        else:
            pygame.draw.polygon(screen, color, [left1[:2], right1[:2], right2[:2], left2[:2]])

    def draw_lanes(self, screen: pygame.Surface, pal: TrackPalette, seg: int, z: float, haze: float) -> None:
        """Divisórias das faixas; no rio, reflexos curtos que andam (água corrente)."""
        lane = lerp_color(pal.lane, self.sky.fog_color, haze)
        if self.biome.river:
            if (seg + int(self.elapsed * 3)) % 3:
                return
            z0, z1, thickness = z + 20, z + 60, 3
        else:
            z0, z1, thickness = z, z + C.SEGMENT_LENGTH, 4
        for divider in (-0.5, 0.5):
            p1 = project(C.LANE_WIDTH * divider, 0, z0, self.cam)
            p2 = project(C.LANE_WIDTH * divider, 0, z1, self.cam)
            pygame.draw.line(screen, lane, p1[:2], p2[:2], max(1, int(thickness * p1[2])))

    @staticmethod
    def curbs(screen: pygame.Surface, edges, color, thickness: int) -> None:
        left1, right1, left2, right2 = edges
        width = max(1, int(thickness * left1[2]))
        pygame.draw.line(screen, color, left1[:2], left2[:2], width)
        pygame.draw.line(screen, color, right1[:2], right2[:2], width)

    @staticmethod
    def encounter_weight(world: WorldStateView) -> float:
        """Quanto do encontro das águas aparece: só no estágio do despertar (meio da fase)."""
        value = world.visual
        rise = clamp((value - C.ERA_SPAN * 0.8) / (C.ERA_SPAN * 0.4), 0.0, 1.0)
        fall = clamp((value - C.ERA_SPAN * 1.8) / (C.ERA_SPAN * 0.5), 0.0, 1.0)
        return rise * (1.0 - fall)
