"""Props grandes de papel e aquarela para as obras da vila.

As superfícies são desenhadas uma vez por processo e reutilizadas nos menus e
na vila. Silhuetas simples e contornos fortes mantêm os objetos reconhecíveis
em projeção; pequenas manchas translúcidas dão sensação de tinta sem ruído fino.
"""

from __future__ import annotations

from functools import lru_cache

import pygame

INK = (20, 45, 94)
PAPER = (250, 243, 222)
WOOD = (166, 112, 68)
GREEN = (83, 157, 97)
TEAL = (55, 157, 169)
SUN = (246, 195, 59)
CORAL = (238, 122, 58)
BLUE = (62, 128, 191)


def _shape(surface, points, fill, width=5):
    pygame.draw.polygon(surface, INK, points, width=width + 2)
    pygame.draw.polygon(surface, fill, points)


def _leaf(surface, start, end, color, width=11):
    pygame.draw.line(surface, INK, start, end, width + 4)
    pygame.draw.line(surface, color, start, end, width)
    mid = ((start[0] + end[0]) // 2, (start[1] + end[1]) // 2)
    pygame.draw.ellipse(surface, color, pygame.Rect(mid[0] - width, mid[1] - width // 2, width * 2, width))
    pygame.draw.ellipse(surface, INK, pygame.Rect(mid[0] - width, mid[1] - width // 2, width * 2, width), 2)


def _draw_prop(surface, key):
    # Ground shadow and one broad wash, shared by every object.
    pygame.draw.ellipse(surface, (42, 57, 84, 42), (20, 132, 180, 20))
    pygame.draw.ellipse(surface, (255, 255, 255, 100), (38, 24, 92, 42))
    if key == "ponto_troca":
        pygame.draw.rect(surface, INK, (48, 45, 124, 89), border_radius=12)
        pygame.draw.rect(surface, PAPER, (52, 43, 116, 86), border_radius=12)
        _shape(surface, [(45, 48), (110, 18), (176, 48)], CORAL)
        pygame.draw.rect(surface, INK, (72, 80, 34, 49), border_radius=4)
        pygame.draw.rect(surface, TEAL, (76, 84, 26, 45), border_radius=3)
        for x, color in ((122, BLUE), (146, CORAL), (170, SUN)):
            pygame.draw.circle(surface, INK, (x, 99), 14)
            pygame.draw.circle(surface, color, (x, 96), 12)
            pygame.draw.arc(surface, PAPER, (x - 6, 90, 12, 12), 0.2, 4.9, 3)
    elif key == "horta":
        _shape(surface, [(30, 78), (188, 78), (172, 135), (47, 135)], WOOD)
        pygame.draw.polygon(surface, (81, 122, 72), [(40, 79), (180, 79), (171, 100), (48, 100)])
        for x, h, c in ((62, 38, GREEN), (100, 54, TEAL), (138, 42, GREEN), (166, 34, CORAL)):
            _leaf(surface, (x, 88), (x - 7, 88 - h), c, 12)
            _leaf(surface, (x, 88), (x + 12, 84 - h // 2), c, 10)
        pygame.draw.line(surface, PAPER, (55, 108), (163, 108), 3)
    elif key == "paineis":
        pygame.draw.circle(surface, SUN, (168, 34), 22)
        _shape(surface, [(34, 65), (147, 42), (168, 110), (56, 132)], BLUE)
        for i in range(1, 4):
            a = (34 + i * 28, 65 - i * 5)
            b = (56 + i * 28, 132 - i * 5)
            pygame.draw.line(surface, PAPER, a, b, 3)
        pygame.draw.line(surface, PAPER, (48, 87), (154, 66), 3)
        pygame.draw.line(surface, PAPER, (52, 108), (160, 87), 3)
        pygame.draw.line(surface, INK, (64, 126), (58, 145), 7)
        pygame.draw.line(surface, INK, (147, 109), (154, 140), 7)
        pygame.draw.line(surface, WOOD, (58, 145), (154, 140), 7)
    elif key == "compostor":
        pygame.draw.rect(surface, INK, (56, 48, 114, 88), border_radius=20)
        pygame.draw.rect(surface, (142, 100, 61), (60, 45, 106, 88), border_radius=18)
        pygame.draw.rect(surface, (103, 75, 56), (68, 54, 90, 26), border_radius=12)
        _shape(surface, [(48, 49), (112, 23), (176, 49)], GREEN)
        for x, y, c in ((86, 100, GREEN), (118, 94, SUN), (142, 108, TEAL)):
            pygame.draw.ellipse(surface, c, (x - 10, y - 7, 20, 14))
            pygame.draw.ellipse(surface, INK, (x - 10, y - 7, 20, 14), 2)
    elif key == "cisterna":
        pygame.draw.rect(surface, INK, (48, 38, 126, 99), border_radius=30)
        pygame.draw.rect(surface, TEAL, (52, 34, 118, 98), border_radius=28)
        pygame.draw.ellipse(surface, (106, 198, 201), (57, 37, 108, 26))
        pygame.draw.ellipse(surface, INK, (57, 37, 108, 26), 4)
        pygame.draw.rect(surface, PAPER, (81, 70, 62, 7), border_radius=4)
        pygame.draw.rect(surface, (255, 255, 255, 105), (61, 63, 15, 49), border_radius=8)
        pygame.draw.line(surface, INK, (111, 20), (111, 34), 7)
        pygame.draw.line(surface, BLUE, (111, 20), (178, 20), 7)
        pygame.draw.line(surface, INK, (178, 20), (178, 34), 7)
        pygame.draw.ellipse(surface, BLUE, (168, 37, 20, 25))
    elif key == "bicicletario":
        for x in (52, 163):
            pygame.draw.circle(surface, INK, (x, 105), 34, 7)
            pygame.draw.circle(surface, PAPER, (x, 105), 27, 4)
        pygame.draw.line(surface, CORAL, (52, 105), (94, 61), 7)
        pygame.draw.line(surface, TEAL, (94, 61), (111, 105), 7)
        pygame.draw.line(surface, BLUE, (111, 105), (52, 105), 7)
        pygame.draw.line(surface, GREEN, (111, 105), (145, 65), 7)
        pygame.draw.line(surface, CORAL, (145, 65), (163, 105), 7)
        pygame.draw.line(surface, INK, (137, 63), (156, 63), 6)
        pygame.draw.line(surface, INK, (85, 57), (105, 57), 6)
        pygame.draw.line(surface, INK, (94, 61), (89, 50), 6)
    elif key == "telhado_verde":
        _shape(surface, [(35, 71), (106, 26), (179, 71)], CORAL)
        pygame.draw.rect(surface, INK, (50, 69, 113, 67), border_radius=4)
        pygame.draw.rect(surface, PAPER, (55, 72, 103, 61), border_radius=4)
        pygame.draw.rect(surface, WOOD, (94, 91, 28, 42), border_radius=4)
        for x, h in ((67, 26), (92, 18), (138, 28)):
            _leaf(surface, (x, 72), (x - 5, 72 - h), GREEN, 10)
            _leaf(surface, (x, 72), (x + 12, 70 - h // 2), TEAL, 9)
        pygame.draw.rect(surface, GREEN, (58, 68, 96, 9), border_radius=4)
    elif key == "turbina":
        pygame.draw.circle(surface, SUN, (158, 36), 20)
        pygame.draw.line(surface, INK, (103, 68), (104, 141), 11)
        pygame.draw.line(surface, PAPER, (103, 68), (104, 141), 6)
        hub = (103, 67)
        pygame.draw.line(surface, INK, hub, (98, 20), 10)
        pygame.draw.line(surface, PAPER, hub, (98, 20), 5)
        pygame.draw.line(surface, INK, hub, (62, 84), 10)
        pygame.draw.line(surface, TEAL, hub, (62, 84), 5)
        pygame.draw.line(surface, INK, hub, (145, 78), 10)
        pygame.draw.line(surface, CORAL, hub, (145, 78), 5)
        pygame.draw.circle(surface, INK, hub, 12)
        pygame.draw.circle(surface, SUN, hub, 7)
        pygame.draw.line(surface, INK, (77, 143), (132, 143), 7)


@lru_cache(maxsize=16)
def village_prop(key: str) -> pygame.Surface:
    """Superfície RGBA canônica de uma melhoria, compartilhada e cacheada."""
    surface = pygame.Surface((220, 160), pygame.SRCALPHA)
    _draw_prop(surface, key)
    return surface


@lru_cache(maxsize=8)
def destination_icon(key: str) -> pygame.Surface:
    """Ícone grande, de forma distinta, para os quatro destinos principais."""
    surface = pygame.Surface((48, 48), pygame.SRCALPHA)
    if key == "voar":
        _shape(surface, [(4, 28), (43, 7), (30, 44), (22, 29)], PAPER, 3)
        pygame.draw.line(surface, TEAL, (22, 29), (43, 7), 4)
    elif key == "hangar":
        _shape(surface, [(4, 20), (24, 5), (44, 20)], CORAL, 3)
        pygame.draw.rect(surface, INK, (8, 20, 32, 25), border_radius=4)
        pygame.draw.rect(surface, PAPER, (12, 23, 24, 20), border_radius=8)
        pygame.draw.line(surface, TEAL, (14, 38), (34, 38), 3)
    elif key == "piloto":
        pygame.draw.circle(surface, INK, (24, 15), 12)
        pygame.draw.circle(surface, SUN, (24, 14), 9)
        pygame.draw.ellipse(surface, INK, (7, 27, 34, 20))
        pygame.draw.ellipse(surface, TEAL, (10, 29, 28, 16))
        pygame.draw.arc(surface, PAPER, (15, 7, 18, 16), 0.3, 2.5, 2)
    elif key == "cuidar":
        pygame.draw.line(surface, INK, (24, 43), (24, 18), 6)
        pygame.draw.line(surface, GREEN, (24, 43), (24, 18), 3)
        _leaf(surface, (24, 34), (11, 19), GREEN, 9)
        _leaf(surface, (24, 28), (38, 12), TEAL, 9)
        pygame.draw.ellipse(surface, SUN, (19, 5, 11, 8))
    return surface
