"""Piloto de papel em 2D, desenhado com formas Pygame e sem arquivos externos."""

from __future__ import annotations

import math

import pygame

from ..content.pilot import (
    EYE_COLORS,
    HAIR_COLORS,
    SHIRT_COLORS,
    SKIN_CHOICES,
    UNSELECTED,
    find_option,
    normalize_pilot,
)

INK = (18, 48, 104)
PAPER = (250, 245, 228)
SIZE = (190, 240)


def _outlined_ellipse(surface: pygame.Surface, rect, fill, width: int = 3) -> None:
    pygame.draw.ellipse(surface, INK, rect.inflate(width * 2, width * 2))
    pygame.draw.ellipse(surface, fill, rect)


def _outlined_round(surface: pygame.Surface, rect, fill, radius: int = 18, width: int = 3) -> None:
    pygame.draw.rect(surface, INK, rect.inflate(width * 2, width * 2), border_radius=radius + width)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)


def _line(surface: pygame.Surface, color, start, end, width: int) -> None:
    pygame.draw.line(surface, INK, start, end, width + 5)
    pygame.draw.line(surface, color, start, end, width)


def _device(surface: pygame.Surface, look: dict) -> None:
    """Cadeira ou andador, sempre atrás do corpo e com a mesma tinta do piloto."""
    if look["cadeira"] == "sim":
        for x in (52, 138):
            pygame.draw.circle(surface, INK, (x, 188), 31, 5)
            pygame.draw.circle(surface, (229, 237, 228), (x, 188), 25, 4)
            pygame.draw.circle(surface, (95, 142, 163), (x, 188), 4)
            for a in range(0, 360, 60):
                end = (x + int(22 * math.cos(math.radians(a))), 188 + int(22 * math.sin(math.radians(a))))
                pygame.draw.line(surface, (95, 142, 163), (x, 188), end, 2)
        _line(surface, (72, 133, 155), (53, 145), (135, 145), 5)
        _line(surface, (72, 133, 155), (59, 145), (79, 213), 5)
        _line(surface, (72, 133, 155), (132, 145), (132, 207), 5)
        _outlined_round(surface, pygame.Rect(66, 139, 57, 44), (242, 181, 98), 12, 3)
    elif look["andador"] == "sim":
        # Arco aberto para não encobrir o rosto nem o torso.
        _line(surface, (76, 137, 157), (43, 131), (43, 206), 5)
        _line(surface, (76, 137, 157), (147, 131), (147, 206), 5)
        _line(surface, (76, 137, 157), (43, 134), (147, 134), 5)
        _line(surface, (76, 137, 157), (43, 202), (147, 202), 5)
        for x in (43, 147):
            pygame.draw.circle(surface, INK, (x, 210), 8)
            pygame.draw.circle(surface, (242, 181, 98), (x, 210), 5)
        _outlined_round(surface, pygame.Rect(33, 124, 20, 9), (246, 203, 119), 5, 2)
        _outlined_round(surface, pygame.Rect(137, 124, 20, 9), (246, 203, 119), 5, 2)


def _hair_back(surface: pygame.Surface, style: str, color) -> None:
    if style in (UNSELECTED, "raspado"):
        return
    if style == "hijab":
        # Lenço amplo por trás do rosto, sem cobrir pele ou olhos.
        pygame.draw.ellipse(surface, INK, (39, 14, 112, 126))
        pygame.draw.ellipse(surface, color, (43, 18, 104, 118))
    elif style in ("longo", "trancas"):
        # Cabelos compridos ficam atrás do rosto; tranças laterais permanecem visíveis.
        pygame.draw.ellipse(surface, INK, (39, 13, 112, 136))
        pygame.draw.ellipse(surface, color, (43, 17, 104, 128))
        if style == "trancas":
            for x in (46, 144):
                for y in range(67, 130, 12):
                    pygame.draw.circle(surface, INK, (x, y), 7)
                    pygame.draw.circle(surface, color, (x, y), 5)


def _hair_front(surface: pygame.Surface, style: str, color) -> None:
    if style in (UNSELECTED, "raspado", "hijab"):
        return
    # Cabelo curto e cachos formam uma silhueta sobre a testa, sem invadir os olhos.
    pygame.draw.ellipse(surface, INK, (46, 12, 98, 58))
    if style in ("cacheado", "crespo", "puffs"):
        count = 9 if style == "crespo" else 7
        for i in range(count):
            x = 51 + i * (88 // max(1, count - 1))
            y = 34 + int(math.sin(i * 2.1) * 9)
            pygame.draw.circle(surface, INK, (x, y), 14 if style == "crespo" else 12)
        pygame.draw.ellipse(surface, color, (51, 20, 88, 46))
        for i in range(count):
            x = 52 + i * (86 // max(1, count - 1))
            y = 33 + int(math.sin(i * 2.1) * 9)
            pygame.draw.circle(surface, color, (x, y), 10 if style == "crespo" else 9)
        if style == "puffs":
            for x in (49, 141):
                pygame.draw.circle(surface, INK, (x, 42), 17)
                pygame.draw.circle(surface, color, (x, 42), 13)
    elif style in ("coque", "chiquinhas"):
        for x in ((53, 137) if style == "chiquinhas" else (95,)):
            pygame.draw.circle(surface, INK, (x, 17), 17)
            pygame.draw.circle(surface, color, (x, 17), 13)
        pygame.draw.ellipse(surface, color, (52, 20, 86, 44))
    elif style == "moicano":
        pygame.draw.polygon(surface, INK, [(70, 58), (91, 5), (111, 58)])
        pygame.draw.polygon(surface, color, [(76, 53), (92, 15), (105, 53)])
        pygame.draw.ellipse(surface, color, (54, 31, 82, 34))
    else:
        pygame.draw.ellipse(surface, color, (51, 18, 88, 44))
        if style == "franja":
            pygame.draw.polygon(
                surface, INK, [(53, 44), (71, 39), (84, 57), (101, 39), (119, 57), (137, 39), (139, 57)]
            )


def _back_head(surface: pygame.Surface, style: str, skin, color) -> None:
    """Nuca vista de trás no voo; cabelo/dispositivo continuam legíveis."""
    pygame.draw.ellipse(surface, INK, (46, 25, 98, 110))
    pygame.draw.ellipse(surface, skin or (247, 229, 198), (50, 29, 90, 102))
    if style in (UNSELECTED, "raspado"):
        pygame.draw.arc(surface, (223, 206, 170), (61, 36, 67, 74), 0.4, 2.7, 2)
        return
    if style == "hijab":
        pygame.draw.ellipse(surface, INK, (39, 14, 112, 126))
        pygame.draw.ellipse(surface, color, (43, 18, 104, 118))
        pygame.draw.arc(surface, (238, 202, 124), (44, 21, 102, 111), 0.2, 2.9, 4)
        pygame.draw.line(surface, (232, 221, 195), (95, 105), (95, 137), 3)
        return
    if style in ("longo", "trancas"):
        pygame.draw.ellipse(surface, INK, (39, 13, 112, 136))
        pygame.draw.ellipse(surface, color, (43, 17, 104, 128))
        if style == "trancas":
            for x in (47, 143):
                for y in range(61, 130, 12):
                    pygame.draw.circle(surface, INK, (x, y), 8)
                    pygame.draw.circle(surface, color, (x, y), 5)
        pygame.draw.line(surface, (232, 221, 195), (95, 48), (95, 116), 2)
        return

    pygame.draw.ellipse(surface, INK, (46, 12, 98, 69))
    pygame.draw.ellipse(surface, color, (50, 16, 90, 61))
    if style in ("cacheado", "crespo", "puffs"):
        count = 9 if style == "crespo" else 7
        for i in range(count):
            x = 50 + i * (90 // max(1, count - 1))
            y = 35 + int(math.sin(i * 2.1) * 8)
            radius = 13 if style == "crespo" else 11
            pygame.draw.circle(surface, INK, (x, y), radius)
            pygame.draw.circle(surface, color, (x, y), radius - 3)
        if style == "puffs":
            for x in (48, 142):
                pygame.draw.circle(surface, INK, (x, 34), 17)
                pygame.draw.circle(surface, color, (x, 34), 13)
    elif style in ("coque", "chiquinhas"):
        buns = (53, 137) if style == "chiquinhas" else (95,)
        for x in buns:
            pygame.draw.circle(surface, INK, (x, 17), 17)
            pygame.draw.circle(surface, color, (x, 17), 13)
    elif style == "moicano":
        pygame.draw.polygon(surface, INK, [(71, 55), (95, 4), (119, 55)])
        pygame.draw.polygon(surface, color, [(77, 50), (95, 14), (113, 50)])
    elif style == "franja":
        pygame.draw.polygon(surface, color, [(54, 46), (71, 42), (85, 56), (101, 42), (118, 56), (136, 42), (137, 55)])
    # Pequena dobra central deixa a nuca com leitura de papel, sem desenhar face.
    pygame.draw.line(surface, (232, 221, 195), (95, 46), (95, 73), 2)


def draw_pilot(view: str, raw_look: dict) -> pygame.Surface:
    """Renderiza uma criança expressiva em quatro vistas de uso já existentes."""
    look = normalize_pilot(raw_look)
    surface = pygame.Surface(SIZE, pygame.SRCALPHA)

    # Mancha de sombra e dispositivo assistivo primeiro.
    pygame.draw.ellipse(surface, (23, 43, 72, 45), (25, 208, 140, 22))
    _device(surface, look)

    shirt = find_option(SHIRT_COLORS, look["roupa"]).color or (35, 160, 157)
    skin = find_option(SKIN_CHOICES, look["pele"]).color
    hair = (
        (233, 224, 203)
        if look["cor_cabelo"] == UNSELECTED
        else find_option(HAIR_COLORS, look["cor_cabelo"]).color or (91, 60, 39)
    )

    # Pernas, corpo e braços têm formas largas e contorno reforçado.
    _line(surface, (76, 89, 135), (78, 193), (74, 222), 12)
    _line(surface, (76, 89, 135), (112, 193), (118, 222), 12)
    _outlined_ellipse(surface, pygame.Rect(56, 214, 39, 18), (247, 235, 208), 3)
    _outlined_ellipse(surface, pygame.Rect(101, 214, 39, 18), (247, 235, 208), 3)
    _outlined_round(surface, pygame.Rect(58, 133, 75, 78), shirt, 25, 4)
    pygame.draw.polygon(surface, INK, [(65, 148), (40, 166), (49, 181), (72, 169)])
    pygame.draw.polygon(surface, shirt, [(67, 151), (46, 166), (52, 175), (73, 163)])
    pygame.draw.polygon(surface, INK, [(126, 148), (151, 165), (143, 180), (121, 167)])
    pygame.draw.polygon(surface, shirt, [(126, 152), (145, 166), (140, 175), (120, 163)])
    pygame.draw.line(surface, (255, 238, 178), (77, 149), (115, 149), 3)
    # Um pequeno avião de papel na camiseta ancora o tema sem texto.
    pygame.draw.polygon(surface, (255, 246, 220), [(88, 163), (108, 170), (91, 175)])
    pygame.draw.line(surface, INK, (88, 163), (91, 175), 2)

    if view == "flight":
        # No voo, a câmera vê a nuca da criança seguindo o avião para o horizonte.
        _back_head(surface, look["cabelo"], skin, hair)
        if look["aparelho"] == "sim":
            pygame.draw.circle(surface, INK, (137, 79), 7)
            pygame.draw.circle(surface, (45, 146, 157), (137, 79), 5)
            pygame.draw.circle(surface, (238, 207, 125), (137, 79), 2)
        if look["acessorio"] in ("bone", "capacete", "tiara", "coroa"):
            band = (246, 195, 59) if look["acessorio"] != "capacete" else (234, 165, 65)
            pygame.draw.arc(surface, INK, (43, 17, 104, 68), math.pi, 2 * math.pi, 7)
            pygame.draw.arc(surface, band, (48, 22, 94, 58), math.pi, 2 * math.pi, 5)
    else:
        _hair_back(surface, look["cabelo"], hair)
        # Cabeça creme neutra até a criança escolher um tom.
        pygame.draw.ellipse(surface, INK, (46, 25, 98, 110))
        pygame.draw.ellipse(surface, skin or (247, 229, 198), (50, 29, 90, 102))
        pygame.draw.ellipse(surface, (255, 244, 218), (57, 35, 28, 20))
        _hair_front(surface, look["cabelo"], hair)

        eye_color = (
            (58, 50, 44)
            if look["olhos"] == UNSELECTED
            else find_option(EYE_COLORS, look["olhos"]).color or (106, 62, 40)
        )
        eye_y = 72
        for x in (76, 114):
            _outlined_ellipse(surface, pygame.Rect(x - 10, eye_y - 8, 20, 18), (255, 255, 248), 2)
            pygame.draw.circle(surface, eye_color, (x, eye_y + 1), 5)
            pygame.draw.circle(surface, (31, 36, 48), (x, eye_y + 1), 2)
            pygame.draw.circle(surface, (255, 255, 255), (x - 1, eye_y - 1), 1)
        smile = [(82, 97), (87, 101), (95, 103), (103, 101), (108, 97)]
        pygame.draw.lines(surface, INK, False, smile, 5)
        pygame.draw.lines(surface, (161, 68, 66), False, smile, 3)
        pygame.draw.ellipse(surface, (235, 135, 123, 90), (58, 82, 19, 8))
        pygame.draw.ellipse(surface, (235, 135, 123, 90), (113, 82, 19, 8))

        # Óculos e acessórios são desenhados por cima, em traço legível.
        glasses = look["oculos"]
        if glasses != "nenhum":
            frame = (29, 49, 87) if glasses != "sol" else (47, 54, 74)
            for x in (76, 114):
                rect = pygame.Rect(x - 13, 61, 26, 23)
                pygame.draw.rect(surface, frame, rect, 3, border_radius=8 if glasses == "redondo" else 4)
            pygame.draw.line(surface, frame, (89, 72), (101, 72), 3)
        accessory = look["acessorio"]
        if accessory == "bone":
            _outlined_ellipse(surface, pygame.Rect(45, 24, 104, 30), (246, 195, 80), 3)
            pygame.draw.line(surface, INK, (55, 50), (144, 50), 4)
        elif accessory == "capacete":
            pygame.draw.arc(surface, INK, (44, 20, 102, 64), math.pi, 2 * math.pi, 7)
            pygame.draw.arc(surface, (234, 165, 65), (48, 24, 94, 57), math.pi, 2 * math.pi, 6)
        elif accessory in ("flor", "tiara", "coroa"):
            if accessory == "tiara":
                pygame.draw.arc(surface, INK, (48, 19, 94, 61), math.pi, 2 * math.pi, 3)
            elif accessory == "coroa":
                pygame.draw.polygon(
                    surface, INK, [(71, 35), (75, 20), (87, 31), (96, 17), (106, 31), (119, 20), (123, 35)]
                )
                pygame.draw.polygon(
                    surface, (250, 202, 73), [(75, 32), (78, 24), (88, 34), (96, 22), (105, 34), (117, 24), (119, 33)]
                )
            else:
                pygame.draw.circle(surface, INK, (137, 46), 11)
                pygame.draw.circle(surface, (241, 115, 139), (137, 46), 8)
                pygame.draw.circle(surface, (246, 205, 75), (137, 46), 3)

        if look["aparelho"] == "sim":
            pygame.draw.arc(surface, INK, (119, 57, 25, 35), 4.3, 1.7, 4)
            pygame.draw.circle(surface, (45, 146, 157), (137, 76), 6)
            pygame.draw.circle(surface, (238, 207, 125), (137, 76), 3)

    # Pose simples e estática; as telas existentes fornecem o movimento/voo.
    if view == "segura":
        _outlined_round(surface, pygame.Rect(75, 155, 42, 26), (250, 245, 228), 4, 2)
        pygame.draw.line(surface, (211, 164, 95), (81, 163), (110, 163), 2)
        pygame.draw.line(surface, (202, 213, 202), (81, 169), (106, 169), 2)
        _outlined_ellipse(surface, pygame.Rect(67, 160, 15, 15), skin or (247, 229, 198), 2)
        _outlined_ellipse(surface, pygame.Rect(110, 160, 15, 15), skin or (247, 229, 198), 2)
    elif view == "lanca":
        _line(surface, shirt, (140, 150), (163, 119), 11)
        _outlined_ellipse(surface, pygame.Rect(155, 111, 16, 16), skin or (247, 229, 198), 2)

    # Grão aquarelado leve, determinístico e aplicado só na composição cacheada.
    grain = pygame.Surface(SIZE, pygame.SRCALPHA)
    for i in range(96):
        x = 7 + (i * 47) % 176
        y = 7 + (i * 83) % 222
        if (i % 3) == 0:
            pygame.draw.circle(grain, (255, 255, 255, 16), (x, y), 1 + (i % 2))
    surface.blit(grain, (0, 0))
    return surface
