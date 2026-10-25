"""Abertura (GDD, seção 2) como um livro ilustrado de quatro páginas.

1. A cidade colorida, com fumaça e poluição.
2. A criança (o piloto que ela montou) encontra um jornal esquecido na rua.
3. Ela dobra o papel, dobra a dobra, até virar um avião.
4. Ela o lança: o avião sobe deixando um rastro de aquarela e a cidade ganha cor.

As páginas viram com um deslizar de papel; as legendas são "escritas à mão". A
folha de jornal é desenhada como polígonos que se interpolam entre as poses da
dobradura, com a linha de dobra tracejada e uma seta mostrando o movimento.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import pygame

from .. import config as C
from ..content import texts
from ..content.story import (
    LAUNCH_CAPTION_S,
    LAUNCH_FADE_S,
    LAUNCH_GLIDE_S,
    LOGO_APPEAR_S,
    LOGO_FADE_S,
    PAGE_DURATIONS,
    PAGE_TURN_S,
)
from ..engine import paper
from ..ui import theme as T
from ..util import clamp, lerp, lerp_color, rgb, smoothstep
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
PAGES = PAGE_DURATIONS
TURN_S = PAGE_TURN_S
SHEET_SCALE = 190
CHILD_FEET = (300, 560)
HANDS = (335, 405)  # onde as mãos da criança seguram a folha (página 2)
TABLE = (600, 330)  # centro da folha na página da dobradura
TRAIL = (rgb("1b3a8a"), rgb("1f9fb0"), rgb("f6c33b"), rgb("ee7a3a"))  # cores da logo
FOLD_STEPS = ("Dobra ao meio...", "Dobra as pontas...", "Dobra as asas...", "Pronto: um avião!")


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
        self.trail: List[Tuple[float, float]] = []
        self._button_page = -1
        self._manual_page = 0
        self.story_backgrounds: Dict[str, Optional[pygame.Surface]] = {}

    def build(self) -> None:
        page = self.page()[0]
        last_page = page >= len(PAGES) - 1
        self.menu.set_buttons(
            [
                self.button(
                    (C.WIDTH - 338, 18, 158, 52),
                    "Concluir" if last_page else "Próxima",
                    self.advance_page,
                    key="proxima",
                    size=T.SIZES["body"],
                    icon=T.icon_surface("next", 28, T.NAVY),
                ),
                self.button((C.WIDTH - 170, 18, 146, 52), "Pular", self.finish, key="pular", size=T.SIZES["body"]),
            ]
        )
        self._button_page = page

    def finish(self) -> None:
        self.app.profile.abertura_vista = True
        self.app.save()
        if self.next_scene is not None:
            self.app.go(self.next_scene)
        else:
            self.goto("vila")

    def back(self) -> None:
        self.finish()

    def advance_page(self) -> None:
        if self._manual_page >= len(PAGES) - 1:
            self.finish()
            return
        self._manual_page += 1
        self.time = sum(PAGES[: self._manual_page]) + 0.001
        self.build()

    def previous_page(self) -> None:
        if self._manual_page > 0:
            self._manual_page -= 1
            self.time = sum(PAGES[: self._manual_page]) + 0.001
            self.build()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RIGHT, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.advance_page()
                return
            if event.key == pygame.K_LEFT:
                self.previous_page()
                return
            if event.key == pygame.K_ESCAPE:
                self.finish()
                return
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.menu.handle_event(event):
                self.app.audio.play("sfx_selecao")
            else:
                self.advance_page()
            return
        super().handle_event(event)

    def update(self, dt: float) -> None:
        super().update(dt)
        automatic = self.app.options.abertura_automatica
        if not automatic:
            turn_allowance = TURN_S if self._manual_page < len(PAGES) - 1 else 0.0
            max_time = sum(PAGES[: self._manual_page + 1]) - turn_allowance - 0.001
            self.time = min(self.time, max_time)
        elif self.time >= sum(PAGES) + 0.8:
            self.finish()
        if self.page()[0] != self._button_page:
            self.build()

    # ------------------------------------------------------------ páginas
    def page(self) -> Tuple[int, float, float]:
        """(página atual, segundos dentro dela, 0..1 da virada em andamento)."""
        t = self.time
        for index, length in enumerate(PAGES):
            if t < length:
                turning = clamp((length - t) / TURN_S, 0.0, 1.0) if index < len(PAGES) - 1 else 1.0
                return index, t, 1.0 - turning
            t -= length
        return len(PAGES) - 1, PAGES[-1] + t, 0.0

    # ------------------------------------------------------------ desenho
    def paper_texture(self, size: Tuple[int, int]) -> Optional[pygame.Surface]:
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
        shades = {"body": 255, "flap_l": 222, "flap_r": 206}
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
            pygame.draw.polygon(layer, paper.INK, points, 3)
        screen.blit(layer, (cx - ox, cy - oy))

    def draw_child(
        self,
        screen: pygame.Surface,
        view: str,
        feet,
        size=(300, 380),
        alpha: int = 255,
        expression: str = "curious",
    ) -> None:
        look = self.app.profile.piloto
        if look.get("cadeira") == "sim":
            view = "menu"  # na cadeira de rodas, a criança aparece sentada nela
        child = self.app.view.skin.pilots.compose(view, look, expression=expression)
        if child is None:
            return
        image = self.scaled(child, size, ("abertura", view, tuple(sorted(look.items())), size))
        paper.shadow(screen, (feet[0], feet[1] + 4), int(size[0] * 0.5), 26, 60)
        if alpha < 255:
            image.set_alpha(alpha)
        screen.blit(image, image.get_rect(midbottom=feet))
        image.set_alpha(255)

    def caption(self, screen: pygame.Surface, text: str, sub: str = "") -> None:
        width = self.text.font(T.SIZES["hero"], hand=True).size(text)[0] + 70
        box = pygame.Rect(0, 0, max(520, width), 112 if sub else 74)
        box.center = (C.WIDTH // 2, C.HEIGHT - (80 if sub else 72))
        T.panel(screen, box, T.PAPER, T.NAVY, 240, 18, 3)
        y = box.top + 14 if sub else box.centery
        self.text.blit(
            screen, text, (box.centerx, y), T.SIZES["hero"], T.NAVY, anchor="midtop" if sub else "center", hand=True
        )
        if sub:
            self.text.blit(screen, sub, (box.centerx, box.top + 74), T.SIZES["body"], T.MUTED, anchor="midtop")

    def draw_arrow(self, screen: pygame.Surface, start, end) -> None:
        """Seta curva da dobradura (mostra para onde o papel vai)."""
        (x0, y0), (x1, y1) = start, end
        mx, my = (x0 + x1) / 2, min(y0, y1) - 50
        curve = paper.bezier((x0, y0), (mx, my), (mx, my), (x1, y1), 16)
        pygame.draw.lines(screen, T.ORANGE, False, [(int(x), int(y)) for x, y in curve], 5)
        ax, ay = curve[-1]
        bx, by = curve[-3]
        angle = math.atan2(ay - by, ax - bx)
        tip = [(ax, ay)] + [(ax - 18 * math.cos(angle + d), ay - 18 * math.sin(angle + d)) for d in (0.5, -0.5)]
        pygame.draw.polygon(screen, T.ORANGE, [(int(x), int(y)) for x, y in tip])

    def draw(self, screen: pygame.Surface) -> None:
        page, t, turn = self.page()
        reduced_motion = self.app.options.reduzir_movimento
        elapsed_total = 0.0 if reduced_motion else self.time
        # Cada página pode ter um cenário próprio, sem personagem/texto embutidos.
        # Em pacotes antigos, mantém o fundo de voo como fallback.
        story_key = ("story_city", "story_newspaper", "story_fold", "story_launch")[page]
        if story_key not in self.story_backgrounds:
            source = self.app.assets.sprite("watercolor", story_key)
            self.story_backgrounds[story_key] = (
                self.scaled(source, (C.WIDTH, C.HEIGHT), ("story-background", story_key)) if source else None
            )
        story_background = self.story_backgrounds[story_key]
        # A página de lançamento recebe uma passagem de cor discreta mesmo se o
        # atlas de história estiver ausente e o fallback for usado.
        if page == 3:
            restoration = lerp(5.0, 95.0, smoothstep((t - 1.0) / 3.2))
        else:
            restoration = 5.0
        if story_background is not None:
            screen.blit(story_background, (0, 0))
        else:
            self.app.backdrop(screen, self.last_dt, "amazonia", restoration)
        if page < 3 and story_background is None:
            T.veil(screen, (20, 24, 40), 60)
        if page == 0:
            for k, x in enumerate((180, 420, 760, 980)):
                paper.smoke(screen, (x, 150 + (k % 2) * 30), elapsed_total, 0.9, k)
            self.caption(screen, texts.INTRO_CAPTIONS[0])
        elif page == 1:
            found_feet = (610, 560) if story_background is not None else CHILD_FEET
            self.draw_child(screen, "menu", found_feet, (280, 350), expression="curious")
            # O fundo novo já traz o jornal no chão, perto da mão da criança.
            if story_background is None:
                appear = smoothstep((t - 0.4) / 0.8)
                if appear > 0:
                    self.draw_paper(screen, HANDS, FOLDS[0], SHEET_SCALE * 0.5 * (0.4 + 0.6 * appear))
            bubble_t = clamp((t - 1.4) / 0.4, 0.0, 1.0)
            if bubble_t > 0:
                bubble = pygame.Rect(0, 0, int(96 * bubble_t), int(60 * bubble_t))
                bubble.midbottom = (found_feet[0] + 150, found_feet[1] - 360)
                T.panel(screen, bubble, (255, 255, 255), T.NAVY, 255, 18, 2)
                if bubble_t >= 1.0:
                    self.text.blit(screen, "?", bubble.center, T.SIZES["hero"], T.NAVY, anchor="center", hand=True)
            self.caption(screen, texts.INTRO_CAPTIONS[1])
        elif page == 2:
            if story_background is None:
                table = pygame.Rect(0, 0, 640, 420)
                table.center = TABLE
                T.panel(screen, table, rgb("f3ecd8"), T.NAVY, 235, 26, 3)
            u = 1.0 if reduced_motion else clamp((t - 0.5) / (PAGES[2] - 1.4), 0.0, 1.0)
            self.draw_paper(screen, TABLE, fold_pose(u), SHEET_SCALE)
            step = min(3, int(u * 3.2))
            pose = FOLDS[min(step, 2)]
            if not reduced_motion and step < 3 and (u * 3.2) % 1.0 < 0.55:  # seta no começo de cada dobra
                fx, fy = pose["flap_r"][0]
                tx, ty = FOLDS[step + 1]["flap_r"][0]
                self.draw_arrow(
                    screen,
                    (TABLE[0] + fx * SHEET_SCALE, TABLE[1] + fy * SHEET_SCALE),
                    (TABLE[0] + tx * SHEET_SCALE, TABLE[1] + ty * SHEET_SCALE),
                )
            if not reduced_motion and step < 3:  # linha de dobra tracejada
                for k in range(-9, 10, 2):
                    y = TABLE[1] + k * 12
                    pygame.draw.line(screen, T.MUTED, (TABLE[0], y), (TABLE[0], y + 8), 2)
            self.draw_child(screen, "menu", (150, 600), (220, 280), expression="focused")
            self.caption(screen, texts.INTRO_CAPTIONS[2], FOLD_STEPS[step])
        else:
            launch_alpha = 255 if reduced_motion else int(255 * clamp((PAGES[3] - t) / LAUNCH_FADE_S, 0.0, 1.0))
            self.draw_child(
                screen,
                # A animação do avião no céu é o gesto do lançamento; omite a
                # miniatura estática que o preview de ação põe na mão/cabeça.
                "menu",
                CHILD_FEET,
                alpha=launch_alpha,
                expression="happy",
            )
            u = 1.0 if reduced_motion else smoothstep(t / LAUNCH_GLIDE_S)
            x = lerp(440, C.WIDTH - 140, u)
            y = lerp(360, 120, u) - (0 if reduced_motion else math.sin(u * math.pi) * 90)
            if not self.trail or (abs(self.trail[-1][0] - x) > 6):
                self.trail.append((x, y))
            # rastro de aquarela com as cores da logo
            for i in range(1, len(self.trail)):
                color = TRAIL[min(3, int(4 * i / max(1, len(self.trail))))]
                width = max(3, int(22 - 16 * i / max(1, len(self.trail))))
                a, b = self.trail[i - 1], self.trail[i]
                pygame.draw.line(
                    screen,
                    lerp_color(color, (255, 255, 255), 0.15),
                    (int(a[0]), int(a[1])),
                    (int(b[0]), int(b[1])),
                    width,
                )
            plane = self.app.view.skin.surface("dart", "flight", "original", "liso", None)
            if plane is not None:
                width = int(lerp(260, 60, u)) // 4 * 4
                img = self.scaled(plane, (width, width), ("abertura_aviao", width))
                screen.blit(img, img.get_rect(center=(int(x), int(y))))
            if not reduced_motion:
                paper.sparkles(
                    screen, pygame.Rect(0, 80, C.WIDTH, 400), elapsed_total, clamp((t - 1.5) / 2.0, 0.0, 1.0), T.SUN
                )
            self.caption(screen, texts.INTRO_CAPTIONS[4] if t > LAUNCH_CAPTION_S else texts.INTRO_CAPTIONS[3])
            if t > LOGO_APPEAR_S:
                logo = self.app.assets.sprite("ui", "logo")
                if logo is not None:
                    alpha = clamp((t - LOGO_APPEAR_S) / LOGO_FADE_S, 0.0, 1.0)
                    img = self.scaled(logo, (520, 291))
                    img.set_alpha(int(255 * alpha))
                    screen.blit(img, img.get_rect(center=(C.WIDTH // 2, 250)))
                    img.set_alpha(255)
        if 0.0 < turn < 1.0:  # virada de página: uma folha de papel desliza da direita
            sheet = pygame.Rect(int(C.WIDTH * (1.0 - smoothstep(turn))), 0, C.WIDTH, C.HEIGHT)
            pygame.draw.rect(screen, T.PAPER, sheet)
            pygame.draw.line(screen, paper.INK, (sheet.left, 0), (sheet.left, C.HEIGHT), 4)
        self.draw_menu(screen)
