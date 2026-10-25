"""Abertura (GDD, seção 2): na metrópole poluída, uma criança dobra um jornal em
avião e o lança; a cada voo, a cidade se transforma.

A folha de jornal é desenhada como polígonos que se interpolam entre poses-chave
da dobradura (folha -> casinha -> ponta fina -> avião), preenchidos pela textura
de jornal; depois o avião de verdade (sprite) decola rumo ao horizonte.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import pygame

from .. import config as C
from ..content import texts
from ..ui import theme as T
from ..util import clamp, lerp, smoothstep
from .base import Scene

Poly = List[Tuple[float, float]]
# Poses-chave da dobradura (unidades da folha: x -1..1, y -0.7..0.7). Cada pose tem os
# mesmos polígonos com o mesmo número de vértices, para a interpolação funcionar.
FOLDS: List[Dict[str, Poly]] = [
    {
        "body": [(-1, -0.7), (0, -0.7), (1, -0.7), (1, 0.7), (0, 0.7), (-1, 0.7)],
        "flap_l": [(-1, -0.7), (-1, -0.7), (-1, -0.7)],
        "flap_r": [(1, -0.7), (1, -0.7), (1, -0.7)],
    },
    {
        "body": [(-1, 0), (0, -0.7), (1, 0), (1, 0.7), (0, 0.7), (-1, 0.7)],
        "flap_l": [(-1, 0), (0, -0.7), (0, 0)],
        "flap_r": [(1, 0), (0, -0.7), (0, 0)],
    },
    {
        "body": [(-0.5, 0.25), (0, -0.75), (0.5, 0.25), (0.5, 0.7), (0, 0.7), (-0.5, 0.7)],
        "flap_l": [(-0.5, 0.25), (0, -0.75), (0, 0.3)],
        "flap_r": [(0.5, 0.25), (0, -0.75), (0, 0.3)],
    },
    {
        "body": [(-1.05, 0.55), (0, -0.85), (1.05, 0.55), (0.16, 0.42), (0, 0.75), (-0.16, 0.42)],
        "flap_l": [(-1.05, 0.55), (0, -0.85), (-0.16, 0.42)],
        "flap_r": [(1.05, 0.55), (0, -0.85), (0.16, 0.42)],
    },
]
TIMELINE = (3.0, 6.0, 10.0, 13.0, 16.0)  # fim de cada legenda (s)
FOLD_START, FOLD_END = 4.0, 9.6
LAUNCH_START, LAUNCH_END = 10.0, 13.0
SHEET_SCALE = 150
CHILD_IN = 1.5  # a criança aparece com a 2ª legenda ("encontra um jornal")
CHILD_FEET = (330, 548)
PAPER_CENTER = (600, 320)  # a folha fica à frente das mãos da criança


def fold_pose(t: float) -> Dict[str, Poly]:
    """Pose da dobradura em t (0..1 ao longo das poses-chave)."""
    t = clamp(t, 0.0, 1.0) * (len(FOLDS) - 1)
    i = min(len(FOLDS) - 2, int(t))
    f = smoothstep(t - i)
    a, b = FOLDS[i], FOLDS[i + 1]
    return {name: [(lerp(pa[0], pb[0], f), lerp(pa[1], pb[1], f)) for pa, pb in zip(a[name], b[name])] for name in a}


class IntroScene(Scene):
    music = "musica_amazonia_1"

    def __init__(self, app, next_scene=None) -> None:
        super().__init__(app)
        self.next_scene = next_scene
        self.paper = app.assets.sprite("plane_patterns", "jornal")
        self.textures: Dict[Tuple[int, int], pygame.Surface] = {}
        self.layer: Optional[pygame.Surface] = None
        self.mask: Optional[pygame.Surface] = None

    def build(self) -> None:
        self.menu.set_buttons([self.button((C.WIDTH - 190, 20, 170, 56), "Pular", self.finish, key="pular")])

    def finish(self) -> None:
        self.app.profile.abertura_vista = True
        self.app.save()
        if self.next_scene is not None:
            self.app.go(self.next_scene)
        else:
            self.goto("vila")

    def back(self) -> None:
        self.finish()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) and event.dict.get("key") not in (
            pygame.K_LEFT,
            pygame.K_RIGHT,
            pygame.K_UP,
            pygame.K_DOWN,
        ):
            self.finish()
            return
        super().handle_event(event)

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.time >= TIMELINE[-1]:
            self.finish()

    # ------------------------------------------------------------ desenho
    def paper_texture(self, size: Tuple[int, int]) -> Optional[pygame.Surface]:
        """Textura de jornal na escala pedida (em cache: a folha cresce só no começo)."""
        if self.paper is None:
            return None
        texture = self.textures.get(size)
        if texture is None:
            texture = pygame.transform.smoothscale(self.paper, size)
            self.textures[size] = texture
        return texture

    def draw_paper(self, screen: pygame.Surface, center: Tuple[int, int], pose: Dict[str, Poly], scale: float) -> None:
        cx, cy = center
        scale = int(scale) // 4 * 4  # tamanhos em degraus: a textura em cache é reaproveitada
        size = (int(scale * 2.6), int(scale * 2.2))
        if self.layer is None or self.layer.get_size() != size:
            self.layer = pygame.Surface(size, pygame.SRCALPHA)
            self.mask = pygame.Surface(size, pygame.SRCALPHA)
        layer, mask = self.layer, self.mask
        layer.fill((0, 0, 0, 0))
        ox, oy = size[0] / 2, size[1] / 2
        shades = {"body": 255, "flap_l": 215, "flap_r": 200}
        texture = self.paper_texture(size)
        for name in ("body", "flap_l", "flap_r"):
            points = [(ox + x * scale, oy + y * scale) for x, y in pose[name]]
            if len({(round(x), round(y)) for x, y in points}) < 3:
                continue
            mask.fill((0, 0, 0, 0))
            pygame.draw.polygon(mask, (shades[name],) * 3 + (255,), points)
            if texture is not None:
                mask.blit(texture, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            layer.blit(mask, (0, 0))
            pygame.draw.polygon(layer, (60, 60, 60), points, 2)
        screen.blit(layer, (cx - ox, cy - oy))

    def draw_child(self, screen: pygame.Surface, t: float) -> None:
        """A criança da abertura, com a aparência escolhida para o piloto."""
        if t < CHILD_IN or t > LAUNCH_START + 1.6:
            return
        look = self.app.profile.piloto
        if look.get("cadeira") == "sim":
            view = "menu"  # na cadeira de rodas, a criança aparece sentada nela
        else:
            view = "segura" if t < LAUNCH_START else "lanca"
        child = self.app.view.skin.pilots.compose(view, look)
        if child is None:
            return
        key = ("abertura", view, tuple(sorted(look.items())))
        image = self.scaled(child, (260, 320), key)
        fade = clamp((t - CHILD_IN) / 0.6, 0.0, 1.0) * clamp((LAUNCH_START + 1.6 - t) / 0.5, 0.0, 1.0)
        image.set_alpha(int(255 * fade))
        screen.blit(image, image.get_rect(midbottom=CHILD_FEET))
        image.set_alpha(255)

    def draw(self, screen: pygame.Surface) -> None:
        t = self.time
        restoration = 5.0 if t < LAUNCH_END else lerp(5.0, 95.0, (t - LAUNCH_END) / 2.6)
        self.app.backdrop(screen, self.last_dt, "amazonia", restoration)
        T.veil(screen, (20, 14, 10), int(90 * (1.0 - clamp((t - LAUNCH_END) / 3.0, 0.0, 1.0))) // 10 * 10)
        self.draw_child(screen, t)
        if 3.0 <= t < LAUNCH_START + 0.4:
            appear = clamp((t - 3.0) / 0.8, 0.0, 1.0)
            pose = fold_pose((t - FOLD_START) / (FOLD_END - FOLD_START))
            self.draw_paper(screen, PAPER_CENTER, pose, SHEET_SCALE * (0.6 + 0.4 * appear))
        if LAUNCH_START <= t < TIMELINE[-1]:
            # o avião lançado vai sem piloto: a criança ficou no chão e o viu partir
            plane = self.app.view.skin.surface("dart", "flight", "original", "jornal", None)
            if plane is not None:
                u = smoothstep((t - LAUNCH_START) / (LAUNCH_END - LAUNCH_START))
                width = int(lerp(300, 40, u)) // 4 * 4
                img = self.scaled(plane, (width, width), ("abertura_aviao", width))
                x = lerp(PAPER_CENTER[0], C.WIDTH // 2 + 180, u)
                y = lerp(PAPER_CENTER[1], C.HORIZON_Y - 30, u) - math.sin(u * math.pi) * 70
                screen.blit(img, img.get_rect(center=(int(x), int(y))))
        index = next((i for i, end in enumerate(TIMELINE) if t < end), len(TIMELINE) - 1)
        caption = texts.INTRO_CAPTIONS[min(index, len(texts.INTRO_CAPTIONS) - 1)]
        box = pygame.Rect(0, 0, 820, 64)
        box.center = (C.WIDTH // 2, C.HEIGHT - 70)
        T.panel(screen, box, T.PAPER, T.NAVY, 235, 18, 3)
        self.text.blit(screen, caption, box.center, T.SIZES["label"], T.INK, True, "center")
        if t >= TIMELINE[-2]:
            logo = self.app.assets.sprite("ui", "logo")
            if logo is not None:
                alpha = clamp((t - TIMELINE[-2]) / 1.0, 0.0, 1.0)
                img = self.scaled(logo, (520, 300))
                img.set_alpha(int(255 * alpha))
                screen.blit(img, img.get_rect(center=(C.WIDTH // 2, 250)))
                img.set_alpha(255)
        self.draw_menu(screen)
