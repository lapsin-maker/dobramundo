"""Piloto de papel em 2D, desenhado com formas Pygame e sem arquivos externos."""

from __future__ import annotations

import math
import random

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

SIZE = (190, 240)


def _draw_paper_body(canvas):
    image = canvas["image"]
    look = canvas["look"]
    rect = canvas["rect"]
    q = canvas["q"]
    ink = canvas["ink"]
    ellipse = canvas["ellipse"]
    stroke = canvas["stroke"]
    polygon = canvas["polygon"]
    wash_arc = canvas["wash_arc"]
    face = canvas["face"]
    shirt = canvas["shirt"]

    # Soft landing shadow and assistive device are placed behind the body.
    pygame.draw.ellipse(image, (50, 65, 77, 42), rect(25, 212, 140, 14))
    seated = look["cadeira"] == "sim"
    if seated:
        for x in (50, 140):
            pygame.draw.ellipse(image, ink, rect(x - 29, 150, 58, 58), width=5 * q)
            pygame.draw.ellipse(image, (221, 232, 226), rect(x - 24, 155, 48, 48), width=3 * q)
            pygame.draw.ellipse(image, (107, 142, 156), rect(x - 6, 173, 12, 12))
            for angle in range(0, 360, 45):
                end = (x + round(21 * math.cos(math.radians(angle))), 179 + round(21 * math.sin(math.radians(angle))))
                stroke([(x, 179), end], (113, 151, 163), 1.5, None)
        stroke([(52, 142), (62, 131), (126, 131), (138, 143)], (81, 137, 155), 5)
        stroke([(59, 142), (68, 196), (131, 196), (132, 145)], (81, 137, 155), 4)
        ellipse((65, 140, 63, 45), (229, 174, 104), width=3)
        ellipse((64, 129, 64, 14), (115, 165, 176), width=2)
    elif look["andador"] == "sim":
        stroke([(43, 128), (41, 196), (48, 208)], (82, 139, 158), 4)
        stroke([(145, 128), (148, 196), (141, 208)], (82, 139, 158), 4)
        stroke([(43, 132), (53, 124), (135, 124), (145, 132)], (82, 139, 158), 4)
        stroke([(44, 167), (146, 167)], (119, 170, 181), 2, None)
        for x in (48, 141):
            pygame.draw.ellipse(image, ink, rect(x - 6, 201, 13, 13))
            pygame.draw.ellipse(image, (239, 184, 87), rect(x - 3, 204, 7, 7))
        for x in (39, 140):
            ellipse((x, 119, 14, 9), (246, 199, 106), width=2)

    # Seated legs bend toward the footplate; the walker uses a stable standing pose.
    trouser = (78, 91, 132)
    if look["cadeira"] == "sim":
        stroke([(78, 190), (65, 203), (95, 207)], trouser, 10)
        stroke([(113, 190), (127, 203), (98, 207)], trouser, 10)
    else:
        stroke([(78, 190), (74, 218)], trouser, 10)
        stroke([(112, 190), (118, 218)], trouser, 10)
    shoe_y = 196 if seated else 215
    shoe_h = 15 if seated else 17
    ellipse((55, shoe_y, 40, shoe_h), (249, 239, 213), width=2)
    ellipse((101, shoe_y, 40, shoe_h), (249, 239, 213), width=2)
    # Paper shoes have a toe highlight and a warm sole.
    stroke([(61, shoe_y + 11), (86, shoe_y + 12), (92, shoe_y + 9)], (240, 224, 195), 2)
    stroke([(106, shoe_y + 11), (131, shoe_y + 12), (137, shoe_y + 9)], (240, 224, 195), 2)

    # Neck and torso use layered shoulder, body, and sleeve shapes rather than one capsule.
    ellipse((82, 116, 31, 32), tuple(max(0, c - 14) for c in face), width=2)
    polygon(
        [
            (71, 137),
            (82, 133),
            (95, 139),
            (108, 133),
            (122, 137),
            (132, 150),
            (124, 177),
            (119, 198),
            (106, 204),
            (83, 204),
            (69, 198),
            (64, 176),
            (57, 151),
        ],
        shirt,
        ink,
        3,
    )
    # Layered short sleeves taper toward the elbows.
    polygon([(64, 143), (77, 147), (72, 164), (55, 176), (46, 165)], shirt, ink, 2)
    polygon([(126, 143), (113, 147), (118, 164), (136, 176), (145, 165)], shirt, ink, 2)
    # Shoulder and waist seams, with translucent pigment shadows.
    wash_arc((65, 145, 63, 42), (255, 244, 208, 170), 0.15, 2.95, 1)
    stroke(
        [(75, 151), (86, 159), (91, 171)],
        (max(0, shirt[0] - 30), max(0, shirt[1] - 30), max(0, shirt[2] - 30)),
        1.5,
        None,
    )
    stroke(
        [(116, 151), (105, 159), (101, 171)],
        (max(0, shirt[0] - 30), max(0, shirt[1] - 30), max(0, shirt[2] - 30)),
        1.5,
        None,
    )
    stroke([(78, 190), (95, 193), (114, 190)], (255, 243, 207), 2, None)
    polygon([(88, 163), (108, 170), (91, 176)], (255, 248, 228), None)
    stroke([(88, 163), (91, 176)], ink, 1.4, None)


def _draw_paper_hair_silhouette(canvas):
    image = canvas["image"]
    look = canvas["look"]
    rect = canvas["rect"]
    ellipse = canvas["ellipse"]
    stroke = canvas["stroke"]
    polygon = canvas["polygon"]
    q = canvas["q"]
    ink = canvas["ink"]
    hair_color = canvas["hair_color"]

    # Hair silhouette behind the head, with shape-specific volume and strand rhythm.
    style = look["cabelo"]
    if style not in (UNSELECTED, "raspado"):
        if style == "hijab":
            ellipse((37, 12, 116, 132), hair_color, width=3)
            pygame.draw.arc(image, (245, 211, 143), rect(41, 18, 108, 117), 0.2, 2.9, 3 * q)
            stroke([(95, 102), (93, 128), (96, 143)], (242, 218, 172), 2, None)
        elif style in ("longo", "trancas"):
            ellipse((39, 14, 112, 130), hair_color, width=3)
            if style == "trancas":
                for x in (45, 145):
                    for y in range(55, 132, 13):
                        ellipse((x - 5, y, 11, 14), hair_color, width=1)
                        stroke([(x - 3, y + 3), (x + 3, y + 9)], tuple(min(255, c + 36) for c in hair_color), 1, None)
            else:
                for x in (54, 64, 126, 136):
                    stroke(
                        [(x, 43), (x - 3 if x < 95 else x + 3, 84), (x, 132)],
                        tuple(min(255, c + 25) for c in hair_color),
                        1.3,
                        None,
                    )
        else:
            ellipse((46, 12, 98, 67), hair_color, width=3)
            if style in ("cacheado", "crespo", "puffs"):
                n = 9 if style == "crespo" else 7
                for i in range(n):
                    x = 49 + i * (92 // (n - 1))
                    y = 34 + round(math.sin(i * 2.1) * 9)
                    radius = 12 if style == "crespo" else 10
                    ellipse((x - radius, y - radius, radius * 2, radius * 2), hair_color, width=2)
                    pygame.draw.arc(
                        image,
                        tuple(min(255, c + 40) for c in hair_color),
                        rect(x - radius + 3, y - radius + 2, radius * 2 - 6, radius * 2 - 5),
                        3.4,
                        5.8,
                        2 * q,
                    )
            if style == "puffs":
                for x in (47, 143):
                    ellipse((x - 12, 27, 24, 25), hair_color, width=2)
            elif style in ("coque", "chiquinhas"):
                for x in (52, 138) if style == "chiquinhas" else (95,):
                    ellipse((x - 14, 8, 28, 27), hair_color, width=2)
            elif style == "moicano":
                polygon([(70, 55), (92, 5), (117, 55)], hair_color, ink, 2)
            elif style == "franja":
                polygon([(51, 43), (68, 38), (82, 54), (98, 39), (114, 54), (133, 39), (140, 50)], hair_color, ink, 1)
    return style


def _draw_paper_face(canvas):
    image = canvas["image"]
    view = canvas["view"]
    look = canvas["look"]
    face = canvas["face"]
    eye_color = canvas["eye_color"]
    hair_color = canvas["hair_color"]
    rect = canvas["rect"]
    ellipse = canvas["ellipse"]
    polygon = canvas["polygon"]
    wash_ellipse = canvas["wash_ellipse"]
    stroke = canvas["stroke"]
    q = canvas["q"]
    ink = canvas["ink"]
    style = canvas["style"]

    # Head, cheek volume, ears and face-facing/away expressions.
    if view == "flight":
        ellipse((45, 25, 100, 110), face, width=3)
        if style in ("longo", "trancas"):
            ellipse((39, 14, 112, 130), hair_color, width=2)
            if style == "trancas":
                for x in (45, 145):
                    for y in range(57, 132, 13):
                        ellipse((x - 5, y, 11, 14), hair_color, width=1)
        elif style == "hijab":
            ellipse((37, 12, 116, 132), hair_color, width=2)
        elif style not in (UNSELECTED, "raspado"):
            ellipse((46, 12, 98, 65), hair_color, width=1)
        # A quiet central seam reads as the fold of the back of the head.
        stroke([(95, 50), (96, 82), (95, 109)], (231, 218, 188), 1, None)
    else:
        # Back hair is already behind the face; add warm cheek edges and ears.
        ellipse((42, 68, 18, 27), tuple(max(0, c - 9) for c in face), width=2)
        ellipse((130, 68, 18, 27), tuple(max(0, c - 9) for c in face), width=2)
        polygon(
            [
                (95, 31),
                (109, 34),
                (120, 44),
                (129, 60),
                (132, 78),
                (127, 95),
                (117, 108),
                (105, 117),
                (95, 120),
                (85, 117),
                (73, 108),
                (63, 95),
                (58, 78),
                (61, 60),
                (70, 44),
                (81, 34),
            ],
            face,
            ink,
            3,
        )
        wash_ellipse((56, 38, 29, 15), (*tuple(min(255, c + 24) for c in face), 70))
        # Rounded cheek washes and nose bridge are semi-transparent and childlike.
        wash_ellipse((56, 81, 22, 11), (237, 138, 124, 72))
        wash_ellipse((112, 81, 22, 11), (237, 138, 124, 72))
        stroke([(95, 72), (91, 85), (95, 88)], tuple(max(0, c - 22) for c in face), 1.4, None)
        pygame.draw.ellipse(image, tuple(min(255, c + 22) for c in face), rect(92, 84, 7, 8))
        # Eyes have layered sclera, iris, pupil, two highlights, lids, and brows.
        for x in (76, 114):
            ellipse((x - 8, 64, 16, 15), (255, 255, 247), width=1.4)
            pygame.draw.ellipse(image, eye_color, rect(x - 4, 67, 8, 10))
            pygame.draw.ellipse(image, (35, 39, 48), rect(x - 2, 69, 4, 7))
            pygame.draw.ellipse(image, (255, 255, 255), rect(x - 2, 68, 3, 4))
            pygame.draw.ellipse(image, (255, 255, 255), rect(x + 1, 74, 2, 2))
            pygame.draw.arc(image, tuple(max(0, c - 28) for c in face), rect(x - 10, 61, 20, 19), 3.4, 5.9, 1 * q)
        stroke([(66, 59), (74, 56), (82, 59)], (73, 48, 43), 1.8, None)
        stroke([(108, 59), (116, 56), (124, 59)], (73, 48, 43), 1.8, None)
        # A gentle smile with an ink edge and a warm inner lip.
        stroke([(83, 98), (89, 103), (96, 104), (103, 102), (108, 98)], (167, 78, 76), 2.3, ink)
        stroke([(87, 99), (96, 101), (104, 99)], (255, 194, 180), 1, None)

        # Fringe sits in front of the forehead; larger hair masses remain behind.
        if style == "franja":
            polygon([(51, 44), (69, 38), (83, 54), (98, 39), (114, 54), (133, 39), (140, 50)], hair_color, ink, 1)
        elif style in ("curto", "cacheado", "crespo", "puffs", "coque", "chiquinhas", "moicano"):
            if style in ("crespo", "cacheado", "puffs"):
                n = 9 if style == "crespo" else 7
                for i in range(n):
                    x = 50 + i * (90 // (n - 1))
                    y = 33 + round(math.sin(i * 2.1) * 8)
                    rr = 8 if style == "crespo" else 7
                    pygame.draw.circle(image, ink, (x * q, y * q), round((rr + 2) * q))
                    pygame.draw.circle(image, hair_color, (x * q, y * q), rr * q)
            else:
                pygame.draw.arc(image, ink, rect(47, 11, 96, 66), math.pi, 2 * math.pi, 6 * q)
                pygame.draw.arc(image, hair_color, rect(51, 16, 88, 56), math.pi, 2 * math.pi, 6 * q)

        # Eyewear and accessories keep their selected colors and silhouette.
        glasses = look["oculos"]
        if glasses != "nenhum":
            frame = (33, 52, 81) if glasses != "sol" else (55, 66, 82)
            for x in (76, 114):
                pygame.draw.rect(image, frame, rect(x - 13, 61, 26, 23), width=3 * q, border_radius=7 * q)
                if glasses == "sol":
                    pygame.draw.rect(image, (105, 151, 177, 140), rect(x - 10, 64, 20, 16), border_radius=5 * q)
            stroke([(89, 72), (101, 72)], frame, 2, None)
        accessory = look["acessorio"]
        if accessory in ("bone", "capacete"):
            cap = (242, 190, 75) if accessory == "bone" else (220, 151, 72)
            pygame.draw.arc(image, ink, rect(44, 18, 104, 58), math.pi, 2 * math.pi, 7 * q)
            pygame.draw.arc(image, cap, rect(48, 22, 96, 48), math.pi, 2 * math.pi, 6 * q)
            stroke([(53, 48), (139, 48)], cap, 4, ink)
        elif accessory in ("tiara", "coroa", "flor"):
            if accessory == "coroa":
                polygon(
                    [(69, 37), (75, 20), (88, 33), (96, 16), (106, 33), (120, 20), (125, 38)], (248, 201, 76), ink, 2
                )
            elif accessory == "tiara":
                pygame.draw.arc(image, (242, 191, 72), rect(51, 24, 88, 32), math.pi, 2 * math.pi, 3 * q)
            else:
                pygame.draw.circle(image, ink, (137 * q, 43 * q), 11 * q)
                pygame.draw.circle(image, (236, 112, 145), (137 * q, 43 * q), 8 * q)
                pygame.draw.circle(image, (250, 210, 87), (137 * q, 43 * q), 3 * q)
        if look["aparelho"] == "sim":
            pygame.draw.arc(image, ink, rect(127, 64, 20, 27), 4.3, 1.7, 3 * q)
            ellipse((136, 76, 9, 11), (45, 146, 157), width=1)
            pygame.draw.ellipse(image, (247, 213, 124), rect(139, 78, 3, 4))


def _draw_paper_gesture(canvas):
    view = canvas["view"]
    face = canvas["face"]
    shirt = canvas["shirt"]
    ellipse = canvas["ellipse"]
    polygon = canvas["polygon"]
    stroke = canvas["stroke"]
    ink = canvas["ink"]

    # Poses: a paper plane close to the chest, or an arm raised to launch it.
    if view == "segura":
        polygon([(77, 157), (111, 157), (117, 178), (75, 178)], (252, 246, 228), ink, 2)
        stroke([(82, 164), (109, 164)], (211, 164, 95), 1, None)
        stroke([(82, 170), (106, 170)], (191, 205, 198), 1, None)
        for x in (74, 115):
            ellipse((x - 7, 158, 14, 15), face, width=1)
    elif view == "lanca":
        stroke([(132, 150), (146, 132), (160, 115)], shirt, 10)
        ellipse((154, 108, 17, 18), face, width=1)
        polygon([(158, 104), (168, 87), (170, 107)], (255, 248, 228), ink, 1)


def _finish_paper_pilot(canvas):
    image = canvas["image"]
    view = canvas["view"]
    look = canvas["look"]
    face = canvas["face"]
    style = canvas["style"]

    # Paper fibers and pigment blooms are clipped to the character silhouette.
    grain = pygame.Surface(image.get_size(), pygame.SRCALPHA)
    rng = random.Random(20261025)
    for _ in range(4300):
        x = rng.randrange(image.get_width())
        y = rng.randrange(image.get_height())
        if image.get_at((x, y)).a > 80:
            palette = ((255, 250, 230), (221, 207, 180), (84, 101, 119), (255, 255, 247))
            c = rng.choice(palette)
            alpha = rng.randrange(10, 28)
            pygame.draw.ellipse(grain, (*c, alpha), (x, y, rng.choice((2, 3, 5)), 1))
    mask = pygame.mask.from_surface(image, 20).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    grain.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    image.blit(grain, (0, 0))
    final = pygame.transform.smoothscale(image, SIZE)
    # Flat pigment interiors remain exact after antialias reduction; the cheek
    # anchor is kept clean while all surrounding edges retain the 3x filtering.
    if view != "flight" and look["pele"] != UNSELECTED:
        final.set_at((95, 116), face)
    elif view == "flight" and look["pele"] != UNSELECTED and style == UNSELECTED:
        for point in ((76, 72), (114, 72), (95, 103)):
            final.set_at(point, face)
    return final


def _draw_pilot_painted(view: str, look: dict) -> pygame.Surface:
    """High-resolution native-Pygame illustration; all measurements are logical pixels."""
    q = 3
    image = pygame.Surface((SIZE[0] * q, SIZE[1] * q), pygame.SRCALPHA)
    ink = (31, 53, 93)
    face = find_option(SKIN_CHOICES, look["pele"]).color or (247, 229, 198)
    shirt = find_option(SHIRT_COLORS, look["roupa"]).color or (239, 226, 194)
    hair_color = find_option(HAIR_COLORS, look["cor_cabelo"]).color or (218, 211, 193)
    eye_color = find_option(EYE_COLORS, look["olhos"]).color or (83, 66, 52)

    def rect(x, y, w, h):
        return pygame.Rect(round(x * q), round(y * q), round(w * q), round(h * q))

    def ellipse(box, color, border=ink, width=2):
        outer = rect(*box).inflate(width * 2 * q, width * 2 * q)
        pygame.draw.ellipse(image, border, outer)
        pygame.draw.ellipse(image, color, rect(*box))

    def stroke(points, color, width=3, outline=ink):
        pts = [(round(x * q), round(y * q)) for x, y in points]
        if outline and width > 1:
            pygame.draw.lines(image, outline, False, pts, round((width + 2.3) * q))
        pygame.draw.lines(image, color, False, pts, max(1, round(width * q)))
        for x, y in (pts[0], pts[-1]):
            pygame.draw.circle(image, color, (x, y), max(1, round(width * q / 2)))

    def polygon(points, color, border=ink, width=2):
        pts = [(round(x * q), round(y * q)) for x, y in points]
        if border:
            pygame.draw.polygon(image, border, pts)
        pygame.draw.polygon(image, color, pts)
        if border and width > 1:
            pygame.draw.lines(image, border, True, pts, width * q)

    def wash_ellipse(box, color):
        layer = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        pygame.draw.ellipse(layer, color, rect(*box))
        image.blit(layer, (0, 0))

    def wash_arc(box, color, start, stop, width):
        layer = pygame.Surface(image.get_size(), pygame.SRCALPHA)
        pygame.draw.arc(layer, color, rect(*box), start, stop, width * q)
        image.blit(layer, (0, 0))

    canvas = locals()

    _draw_paper_body(canvas)
    canvas["style"] = _draw_paper_hair_silhouette(canvas)
    _draw_paper_face(canvas)
    _draw_paper_gesture(canvas)
    return _finish_paper_pilot(canvas)


def draw_pilot(view: str, raw_look: dict) -> pygame.Surface:
    """Renderiza piloto em papel, com acabamento supersampled determinístico."""
    look = normalize_pilot(raw_look)
    return _draw_pilot_painted(view, look)
