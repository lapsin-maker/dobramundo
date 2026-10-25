"""Identidade visual "papel e aquarela": paleta da logo, fontes embutidas, cartões
de papel com sombra e grão, e texto em cache."""

from __future__ import annotations

import math
import random
from functools import lru_cache
from typing import Dict, List, Tuple

import pygame

from ..engine.cache import BoundedCache
from ..log import log
from ..paths import find_asset_file
from ..util import Color, rgb

# Paleta tirada da logo: azul-marinho do letreiro, turquesa, amarelo e laranja da aquarela.
NAVY = rgb("1b3a8a")
NAVY_DARK = rgb("0f2257")
TEAL = rgb("1f9fb0")
SUN = rgb("f6c33b")
ORANGE = rgb("ee7a3a")
PAPER = rgb("f7f1e3")
PAPER_DARK = rgb("e8dcc0")
INK = rgb("1d2433")
MUTED = rgb("6b7280")
WHITE = (255, 255, 255)
GREEN = rgb("2e9e44")
RED = rgb("d64532")
LOCKED = rgb("a39d8f")

FONT_NAMES = "segoeui,verdana,dejavusans,arial"  # reserva, se as fontes embutidas faltarem
# Fontes embutidas (assets/fonts, licença OFL): Fredoka (títulos e botões, arredondada e
# amigável), Nunito (leitura) e Patrick Hand (legendas "escritas à mão" da abertura).
FONT_FILES = {"bold": "Fredoka.ttf", "regular": "Nunito.ttf", "hand": "PatrickHand.ttf"}
SIZES = {"small": 16, "body": 20, "label": 24, "title": 34, "hero": 46}
SHADOW = (31, 44, 80)  # sombra azulada dos cartões (tinta diluída)


def elide_text(value: str, font: pygame.font.Font, max_width: int) -> str:
    """Mantém texto inteiro se couber, ou corta em limite medido com reticências."""
    if max_width <= 0:
        return ""
    if font.size(value)[0] <= max_width:
        return value
    suffix = "…"
    if font.size(suffix)[0] > max_width:
        return ""
    low, high = 0, len(value)
    while low < high:
        middle = (low + high + 1) // 2
        if font.size(value[:middle].rstrip() + suffix)[0] <= max_width:
            low = middle
        else:
            high = middle - 1
    return value[:low].rstrip() + suffix


def fit_text(
    text: Text, value: str, max_width: int, size: int = 20, minimum: int = 16, bold: bool = False
) -> Tuple[str, int]:
    """Reduz até um piso legível e então abrevia; devolve (texto, tamanho)."""
    minimum = max(1, min(minimum, size))
    for candidate in range(size, minimum - 1, -1):
        font = text.font(candidate, bold)
        if font.size(value)[0] <= max_width:
            return value, candidate
    return elide_text(value, text.font(minimum, bold), max_width), minimum


class Text:
    """Fontes por tamanho e superfícies de texto em cache (o HUD não re-renderiza a cada quadro)."""

    def __init__(self) -> None:
        self.fonts: Dict[Tuple[int, bool, bool], pygame.font.Font] = {}
        self.cache = BoundedCache(600, 16 * 1024 * 1024)  # superfícies de texto prontas
        self.wrapped = BoundedCache(200)  # quebras de linha por (texto, largura, tamanho)

    def font(self, size: int, bold: bool = False, hand: bool = False) -> pygame.font.Font:
        key = (size, bold, hand)
        font = self.fonts.get(key)
        if font is None:
            font = self.load_font("hand" if hand else ("bold" if bold else "regular"), size, bold)
            self.fonts[key] = font
        return font

    @staticmethod
    def load_font(kind: str, size: int, bold: bool) -> pygame.font.Font:
        path = find_asset_file("fonts", FONT_FILES[kind])
        if path is not None:
            try:
                font = pygame.font.Font(str(path), size)
                if bold and kind != "hand":
                    font.set_bold(True)  # as fontes variáveis abrem no peso regular
                return font
            except (OSError, pygame.error) as exc:
                log.warning("fonte não carregou: %s (%s)", path, exc)
        return pygame.font.SysFont(FONT_NAMES, size, bold=bold)

    def render(
        self, text: str, size: int = SIZES["body"], color: Color = INK, bold: bool = False, hand: bool = False
    ) -> pygame.Surface:
        key = (text, size, color, bold, hand)
        surf = self.cache.get(key)
        if surf is None:
            surf = self.font(size, bold, hand).render(text, True, color)
            self.cache[key] = surf
        return surf

    def wrap(self, text: str, width: int, size: int = SIZES["body"], bold: bool = False) -> List[str]:
        """Linhas que cabem em width (em cache: as telas redesenham o mesmo texto a cada quadro)."""
        key = (text, width, size, bold)
        lines = self.wrapped.get(key)
        if lines is None:
            lines = self.wrapped.put(key, self._wrap(text, width, size, bold))
        return lines

    def _wrap(self, text: str, width: int, size: int, bold: bool) -> List[str]:
        font = self.font(size, bold)
        lines: List[str] = []
        for paragraph in text.split("\n"):
            current = ""
            for word in paragraph.split():
                trial = f"{current} {word}".strip()
                if font.size(trial)[0] <= width or not current:
                    current = trial
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    def blit(
        self,
        screen: pygame.Surface,
        text: str,
        pos: Tuple[int, int],
        size: int = SIZES["body"],
        color: Color = INK,
        bold: bool = False,
        anchor: str = "topleft",
        hand: bool = False,
    ) -> pygame.Rect:
        surf = self.render(text, size, color, bold, hand)
        rect = surf.get_rect(**{anchor: pos})
        screen.blit(surf, rect)
        return rect

    def paragraph(
        self,
        screen: pygame.Surface,
        text: str,
        rect: pygame.Rect,
        size: int = SIZES["body"],
        color: Color = INK,
        spacing: float = 1.3,
        bold: bool = False,
    ) -> int:
        """Texto quebrado em linhas dentro de rect; devolve o y logo abaixo do texto."""
        y = rect.top
        step = int(self.font(size, bold).get_linesize() * spacing)
        for line in self.wrap(text, rect.width, size, bold):
            if line:
                screen.blit(self.render(line, size, color, bold), (rect.left, y))
            y += step
        return y


_panels: Dict[tuple, pygame.Surface] = {}


SHADOW_OFFSET = 5


@lru_cache(maxsize=1)
def paper_grain() -> pygame.Surface:
    """Grão de papel (ruído claro, multiplicado sobre os cartões), feito uma vez."""
    rng = random.Random(7)
    size = 256
    grain = pygame.Surface((size, size))
    grain.fill((255, 255, 255))
    px = pygame.PixelArray(grain)
    for y in range(size):
        for x in range(size):
            v = 255 - rng.randrange(0, 14)
            px[x, y] = (v, v, v)
    del px
    return grain


def panel(
    screen: pygame.Surface,
    rect: pygame.Rect,
    fill: Color = PAPER,
    border: Color = NAVY,
    alpha: int = 245,
    radius: int = 18,
    width: int = 3,
    shadow: bool = True,
) -> None:
    """Cartão de papel: sombra suave, grão e borda de tinta (superfície em cache por tamanho e cor).

    A sombra fica fora do retângulo pedido (para baixo e para a direita), então o
    cartão continua ocupando exatamente ``rect``.
    """
    key = (rect.size, fill, border, alpha, radius, width, shadow)
    surf = _panels.get(key)
    if surf is None:
        if len(_panels) > 200:
            _panels.clear()
        pad = SHADOW_OFFSET if shadow else 0
        surf = pygame.Surface((rect.width + pad, rect.height + pad), pygame.SRCALPHA)
        body = pygame.Rect(0, 0, rect.width, rect.height)
        if shadow:
            pygame.draw.rect(surf, (*SHADOW, min(alpha, 70)), body.move(pad, pad), border_radius=radius)
        card = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(card, (*fill, alpha), card.get_rect(), border_radius=radius)
        if alpha > 160 and sum(fill) > 500:  # grão só nos cartões claros e opacos
            grain = pygame.Surface(rect.size, pygame.SRCALPHA)
            tile = paper_grain()
            for y in range(0, rect.height, tile.get_height()):
                for x in range(0, rect.width, tile.get_width()):
                    grain.blit(tile, (x, y))
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
            grain.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            card.blit(grain, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
        if width:
            pygame.draw.rect(card, border, card.get_rect(), width, border_radius=radius)
        surf.blit(card, (0, 0))
        _panels[key] = surf
    screen.blit(surf, rect)


_veils: Dict[tuple, pygame.Surface] = {}


_watercolor_backdrops: Dict[Tuple[Tuple[int, int], str], pygame.Surface] = {}


def watercolor_backdrop(screen: pygame.Surface, variant: str = "sky") -> None:
    """Papel com lavagens amplas, pré-computado uma vez por tamanho e variante."""
    size = screen.get_size()
    key = (size, variant)
    surface = _watercolor_backdrops.get(key)
    if surface is None:
        surface = pygame.Surface(size)
        surface.fill(PAPER)
        wash = pygame.Surface(size, pygame.SRCALPHA)
        if variant == "warm":
            colors = ((ORANGE, (0.04, 0.52, 0.32, 0.30)), (SUN, (0.48, 0.02, 0.30, 0.32)))
        elif variant == "river":
            colors = ((TEAL, (0.02, 0.48, 0.42, 0.24)), (NAVY, (0.63, 0.06, 0.36, 0.30)))
        else:
            colors = ((TEAL, (0.02, 0.48, 0.36, 0.24)), (SUN, (0.64, 0.05, 0.35, 0.28)))
        for color, (x, y, w, h) in colors:
            rect = pygame.Rect(int(size[0] * x), int(size[1] * y), int(size[0] * w), int(size[1] * h))
            for inset, alpha in ((0, 14), (14, 12), (30, 9)):
                pygame.draw.ellipse(wash, (*color, alpha), rect.inflate(-inset * 2, -inset * 2))
        surface.blit(wash, (0, 0))
        _watercolor_backdrops[key] = surface
    screen.blit(surface, (0, 0))


_icons: Dict[Tuple[str, int, Color], pygame.Surface] = {}


def icon_surface(kind: str, size: int = 56, color: Color = NAVY) -> pygame.Surface:
    """Ícone vetorial em papel, cacheado como Surface para uso em botões e cartões."""
    key = (kind, int(size), color)
    surface = _icons.get(key)
    if surface is not None:
        return surface
    size = max(20, int(size))
    surface = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    r = size * 0.42
    pygame.draw.circle(surface, (255, 255, 255, 240), (cx, cy), int(r))
    pygame.draw.circle(surface, color, (cx, cy), int(r), max(2, size // 24))
    s = size / 56.0

    def points(values):
        return [(int(cx + x * s), int(cy + y * s)) for x, y in values]

    ink = color
    if kind in {"paper", "collect"}:
        pygame.draw.polygon(surface, (255, 255, 255), points([(-15, -12), (15, -12), (15, 12), (-15, 12)]))
        pygame.draw.polygon(surface, ink, points([(-15, -12), (15, -12), (15, 12), (-15, 12)]), 3)
        pygame.draw.line(surface, TEAL, points([(-12, -4)])[0], points([(12, -4)])[0], 2)
        pygame.draw.line(surface, ORANGE, points([(-12, 3)])[0], points([(8, 3)])[0], 2)
    elif kind == "clock":
        pygame.draw.circle(surface, ink, (cx, cy), int(16 * s), max(2, int(3 * s)))
        pygame.draw.lines(surface, ink, False, points([(0, -10), (0, 0), (9, 5)]), max(2, int(3 * s)))
    elif kind == "back":
        pygame.draw.polygon(surface, ink, points([(17, -6), (-4, -6), (-4, -15), (-19, 0), (-4, 15), (-4, 6), (17, 6)]))
    elif kind == "plane":
        pygame.draw.polygon(surface, PAPER, points([(-19, 13), (17, -15), (8, 18), (-2, 7)]))
        pygame.draw.polygon(surface, ink, points([(-19, 13), (17, -15), (8, 18), (-2, 7)]), max(2, int(2 * s)))
        pygame.draw.line(surface, ORANGE, points([(-2, 7)])[0], points([(17, -15)])[0], max(2, int(3 * s)))
    elif kind == "map":
        route = points([(-15, 13), (-8, 0), (4, 6), (14, -13)])
        pygame.draw.lines(surface, ink, False, route, max(2, int(3 * s)))
        for point in (route[0], route[-1]):
            pygame.draw.circle(surface, ORANGE, point, max(3, int(5 * s)))
    elif kind in {"dodge", "desviar", "next"}:
        pygame.draw.polygon(surface, ink, points([(-17, -6), (4, -6), (4, -15), (19, 0), (4, 15), (4, 6), (-17, 6)]))
    elif kind in {"portal", "gate"}:
        pygame.draw.arc(
            surface,
            ink,
            pygame.Rect(cx - int(17 * s), cy - int(17 * s), int(34 * s), int(34 * s)),
            math.pi,
            2 * math.pi,
            max(3, int(5 * s)),
        )
        pygame.draw.line(surface, ink, points([(-17, 0)])[0], points([(-17, 15)])[0], max(3, int(5 * s)))
        pygame.draw.line(surface, ink, points([(17, 0)])[0], points([(17, 15)])[0], max(3, int(5 * s)))
        pygame.draw.line(surface, TEAL, points([(-17, 14)])[0], points([(17, 14)])[0], max(2, int(3 * s)))
    elif kind == "magnet":
        pygame.draw.lines(
            surface,
            ink,
            False,
            points([(-12, -15), (-12, 7), (-6, 15), (6, 15), (12, 7), (12, -15)]),
            max(5, int(8 * s)),
        )
        pygame.draw.line(surface, ORANGE, points([(-12, -15)])[0], points([(-12, -5)])[0], max(5, int(8 * s)))
        pygame.draw.line(surface, TEAL, points([(12, -15)])[0], points([(12, -5)])[0], max(5, int(8 * s)))
    elif kind in {"powerup", "shield", "repair"}:
        pygame.draw.polygon(surface, ink, points([(0, -18), (16, -11), (13, 7), (0, 18), (-13, 7), (-16, -11)]))
        pygame.draw.line(surface, (255, 255, 255), points([(0, -10)])[0], points([(0, 9)])[0], max(2, int(3 * s)))
        if kind == "repair":
            pygame.draw.line(surface, (255, 255, 255), points([(-8, 0)])[0], points([(8, 0)])[0], max(2, int(3 * s)))
    elif kind in {"stabilizer", "keel", "rudder", "part"}:
        pygame.draw.polygon(surface, ink, points([(-18, 9), (0, -13), (18, 9), (0, 4)]))
        pygame.draw.line(surface, (255, 255, 255), points([(0, -10)])[0], points([(0, 8)])[0], max(2, int(3 * s)))
        if kind == "rudder":
            pygame.draw.polygon(surface, ORANGE, points([(0, 5), (12, -14), (13, 8)]))
    elif kind in {"star", "reward"}:
        star_pts = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            radius = (17 if i % 2 == 0 else 8) * s
            star_pts.append((int(cx + math.cos(angle) * radius), int(cy + math.sin(angle) * radius)))
        pygame.draw.polygon(surface, SUN, star_pts)
        pygame.draw.polygon(surface, ink, star_pts, max(2, size // 28))
    elif kind == "palette":
        pygame.draw.ellipse(
            surface,
            ink,
            pygame.Rect(cx - int(17 * s), cy - int(15 * s), int(34 * s), int(30 * s)),
            max(2, int(3 * s)),
        )
        for ox, oy, shade in ((-8, -5, ORANGE), (3, -8, TEAL), (9, 3, SUN), (-4, 8, GREEN)):
            pygame.draw.circle(surface, shade, (cx + int(ox * s), cy + int(oy * s)), max(2, int(4 * s)))
    elif kind == "pattern":
        rect = pygame.Rect(cx - int(15 * s), cy - int(15 * s), int(30 * s), int(30 * s))
        pygame.draw.rect(surface, ink, rect, max(2, int(3 * s)), border_radius=max(2, int(5 * s)))
        for row in range(3):
            for col in range(3):
                if (row + col) % 2 == 0:
                    tile = pygame.Rect(
                        rect.left + int((4 + col * 9) * s),
                        rect.top + int((4 + row * 9) * s),
                        max(2, int(5 * s)),
                        max(2, int(5 * s)),
                    )
                    pygame.draw.rect(surface, TEAL if row == 1 else ORANGE, tile)
    elif kind in {"village", "home"}:
        pygame.draw.polygon(
            surface,
            ink,
            points([(-18, -2), (0, -17), (18, -2), (14, -2), (14, 15), (-14, 15), (-14, -2)]),
        )
        pygame.draw.rect(surface, PAPER, pygame.Rect(cx - int(4 * s), cy + int(2 * s), int(8 * s), int(13 * s)))
    else:
        pygame.draw.polygon(surface, ink, points([(-17, 0), (14, -12), (7, 0), (14, 12)]))
        pygame.draw.line(surface, PAPER, points([(-3, 0)])[0], points([(2, -1)])[0], max(2, int(2 * s)))
    _icons[key] = surface
    return surface


def veil(screen: pygame.Surface, color: Color = (10, 18, 40), alpha: int = 150) -> None:
    """Escurece a tela inteira (superfície criada uma vez por cor/alfa)."""
    key = (screen.get_size(), color, alpha)
    surf = _veils.get(key)
    if surf is None:
        surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        surf.fill((*color, alpha))
        _veils[key] = surf
    screen.blit(surf, (0, 0))
