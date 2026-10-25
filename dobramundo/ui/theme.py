"""Identidade visual dos menus (paleta da logo em aquarela) e texto em cache."""

from __future__ import annotations

from typing import Dict, List, Tuple

import pygame

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

FONT_NAMES = "segoeui,verdana,dejavusans,arial"
SIZES = {"small": 16, "body": 20, "label": 24, "title": 34, "hero": 46}


class Text:
    """Fontes por tamanho e superfícies de texto em cache (o HUD não re-renderiza a cada quadro)."""

    def __init__(self) -> None:
        self.fonts: Dict[Tuple[int, bool], pygame.font.Font] = {}
        self.cache: Dict[tuple, pygame.Surface] = {}

    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        font = self.fonts.get(key)
        if font is None:
            font = pygame.font.SysFont(FONT_NAMES, size, bold=bold)
            self.fonts[key] = font
        return font

    def render(self, text: str, size: int = SIZES["body"], color: Color = INK, bold: bool = False) -> pygame.Surface:
        key = (text, size, color, bold)
        surf = self.cache.get(key)
        if surf is None:
            if len(self.cache) > 600:
                for old in list(self.cache)[:200]:
                    del self.cache[old]
            surf = self.font(size, bold).render(text, True, color)
            self.cache[key] = surf
        return surf

    def wrap(self, text: str, width: int, size: int = SIZES["body"], bold: bool = False) -> List[str]:
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
    ) -> pygame.Rect:
        surf = self.render(text, size, color, bold)
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


def panel(
    screen: pygame.Surface,
    rect: pygame.Rect,
    fill: Color = PAPER,
    border: Color = NAVY,
    alpha: int = 245,
    radius: int = 18,
    width: int = 3,
) -> None:
    """Cartão de papel com borda (superfície em cache por tamanho e cor)."""
    key = (rect.size, fill, border, alpha, radius, width)
    surf = _panels.get(key)
    if surf is None:
        if len(_panels) > 200:
            _panels.clear()
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*fill, alpha), surf.get_rect(), border_radius=radius)
        if width:
            pygame.draw.rect(surf, border, surf.get_rect(), width, border_radius=radius)
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
