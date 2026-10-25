"""Identidade visual "papel e aquarela": paleta da logo, fontes embutidas, cartões
de papel com sombra e grão, e texto em cache."""

from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

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


class Text:
    """Fontes por tamanho e superfícies de texto em cache (o HUD não re-renderiza a cada quadro)."""

    def __init__(self) -> None:
        self.fonts: Dict[Tuple[int, bool], pygame.font.Font] = {}
        self.cache = BoundedCache(600)  # superfícies de texto prontas
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


_grain: Optional[pygame.Surface] = None
SHADOW_OFFSET = 5


def paper_grain() -> pygame.Surface:
    """Grão de papel (ruído claro, multiplicado sobre os cartões), feito uma vez."""
    global _grain
    if _grain is None:
        rng = random.Random(7)
        size = 256
        _grain = pygame.Surface((size, size))
        _grain.fill((255, 255, 255))
        px = pygame.PixelArray(_grain)
        for y in range(size):
            for x in range(size):
                v = 255 - rng.randrange(0, 14)
                px[x, y] = (v, v, v)
        del px
    return _grain


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


def veil(screen: pygame.Surface, color: Color = (10, 18, 40), alpha: int = 150) -> None:
    """Escurece a tela inteira (superfície criada uma vez por cor/alfa)."""
    key = (screen.get_size(), color, alpha)
    surf = _veils.get(key)
    if surf is None:
        surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        surf.fill((*color, alpha))
        _veils[key] = surf
    screen.blit(surf, (0, 0))
