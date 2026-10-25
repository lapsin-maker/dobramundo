"""Personalização visual do piloto, em categorias e cartões pictóricos."""

from __future__ import annotations

import math
import random
from typing import List, Tuple

import pygame

from ..content import texts
from ..content.pilot import (
    ACCESSORIES,
    EYE_CHOICES,
    GLASSES,
    HAIR_CHOICES,
    HAIR_COLOR_CHOICES,
    HEARING_AID,
    SHIRT_COLORS,
    SKIN_CHOICES,
    UNSELECTED,
    Option,
    normalize_pilot,
    option_keys,
)
from ..engine import paper
from ..ui import theme as T
from ..ui.widgets import grid
from ..util import rgb
from .base import Scene

PAGES: Tuple[Tuple[str, str, List[Option]], ...] = (
    ("pele", "Pele", SKIN_CHOICES),
    ("cabelo", "Cabelo", HAIR_CHOICES),
    ("cor_cabelo", "Cor cabelo", HAIR_COLOR_CHOICES),
    ("olhos", "Olhos", EYE_CHOICES),
    ("roupa", "Roupa", SHIRT_COLORS),
    ("oculos", "Óculos", GLASSES),
    ("acessorio", "Acessório", ACCESSORIES),
    ("aparelho", "Audição", HEARING_AID),
    (
        "mobilidade",
        "Mobilidade",
        [
            Option("livre", "Sem dispositivo"),
            Option("cadeira", "Cadeira de rodas"),
            Option("andador", "Andador"),
        ],
    ),
)
PAGE_BY_FIELD = {field: (label, options) for field, label, options in PAGES}
MOBILITY_KEYS = ("livre", "cadeira", "andador")
NAV_LABELS = {"cor_cabelo": "Cor", "acessorio": "Enfeite", "mobilidade": "Apoio"}
GREETINGS = ("Oi! Esse é você?", "Que legal!", "Pronto para voar?", "Uau, ficou ótimo!")
PREVIEW = pygame.Rect(24, 146, 300, 390)
CHOICES = pygame.Rect(340, 146, 736, 390)


def mobility(look: dict) -> str:
    if look.get("cadeira") == "sim":
        return "cadeira"
    if look.get("andador") == "sim":
        return "andador"
    return "livre"


def _icon(field: str, option: Option, size: int = 44) -> pygame.Surface:
    """Miniatura desenhada com as mesmas formas de papel do retrato."""
    icon = pygame.Surface((size, size), pygame.SRCALPHA)
    ink = (18, 48, 104)
    center = (size // 2, size // 2)
    key = option.key
    if field == "pele":
        pygame.draw.circle(icon, ink, center, 18)
        pygame.draw.circle(icon, option.color or (247, 229, 198), center, 15)
        pygame.draw.ellipse(icon, (255, 249, 228), (12, 9, 11, 7))
    elif field in ("cor_cabelo", "roupa"):
        color = option.color or (198, 210, 213)
        if field == "cor_cabelo":
            pygame.draw.ellipse(icon, ink, (6, 7, 32, 27))
            pygame.draw.ellipse(icon, color, (9, 10, 26, 21))
        else:
            pygame.draw.polygon(
                icon, ink, [(13, 13), (19, 8), (25, 13), (34, 16), (30, 24), (28, 39), (16, 39), (14, 24), (10, 21)]
            )
            pygame.draw.polygon(
                icon, color, [(14, 14), (19, 11), (24, 14), (31, 17), (28, 23), (26, 36), (18, 36), (16, 23), (12, 20)]
            )
    elif field == "olhos":
        pygame.draw.ellipse(icon, (255, 255, 249), (3, 11, 17, 20))
        pygame.draw.ellipse(icon, (255, 255, 249), (24, 11, 17, 20))
        pygame.draw.circle(icon, option.color or (106, 62, 40), (12, 22), 6)
        pygame.draw.circle(icon, option.color or (106, 62, 40), (32, 22), 6)
        pygame.draw.circle(icon, ink, (12, 22), 2)
        pygame.draw.circle(icon, ink, (32, 22), 2)
    elif field == "cabelo":
        color = (90, 58, 42)
        if key == UNSELECTED or key == "raspado":
            pygame.draw.ellipse(icon, ink, (8, 8, 28, 29))
            pygame.draw.ellipse(icon, (247, 229, 198), (11, 11, 22, 23))
        elif key == "hijab":
            pygame.draw.ellipse(icon, ink, (5, 4, 34, 38))
            pygame.draw.ellipse(icon, (94, 155, 167), (8, 7, 28, 32))
            pygame.draw.ellipse(icon, (247, 229, 198), (13, 12, 18, 25))
        else:
            pygame.draw.ellipse(icon, ink, (6, 4, 32, 27))
            pygame.draw.ellipse(icon, color, (9, 7, 26, 21))
            if key in ("crespo", "cacheado", "puffs"):
                for x in (10, 18, 26, 34):
                    pygame.draw.circle(icon, color, (x, 9 + (x % 3) * 2), 5)
    elif field == "oculos":
        if key == "nenhum":
            pygame.draw.arc(icon, ink, (9, 13, 12, 13), 0, 3.14, 2)
            pygame.draw.arc(icon, ink, (24, 13, 12, 13), 0, 3.14, 2)
        else:
            pygame.draw.rect(icon, ink, (4, 12, 16, 18), 3, border_radius=6 if key == "redondo" else 3)
            pygame.draw.rect(icon, ink, (24, 12, 16, 18), 3, border_radius=6 if key == "redondo" else 3)
            pygame.draw.line(icon, ink, (20, 20), (24, 20), 3)
    elif field == "acessorio":
        if key == "nenhum":
            pygame.draw.circle(icon, (250, 221, 141), center, 14, 3)
        elif key in ("bone", "capacete"):
            pygame.draw.arc(icon, ink, (5, 5, 34, 30), 3.14, 6.28, 5)
            pygame.draw.line(icon, (241, 181, 77), (7, 19), (37, 19), 4)
        elif key == "abafador":
            pygame.draw.arc(icon, ink, (7, 3, 30, 38), 3.3, 6.1, 4)
            pygame.draw.rect(icon, (93, 157, 166), (5, 17, 7, 13), border_radius=3)
            pygame.draw.rect(icon, (93, 157, 166), (32, 17, 7, 13), border_radius=3)
        elif key in ("flor", "tiara", "coroa"):
            pygame.draw.polygon(icon, ink, [(7, 29), (10, 14), (18, 22), (22, 8), (26, 22), (34, 14), (37, 29)])
            pygame.draw.polygon(
                icon, (246, 198, 79), [(11, 27), (13, 18), (19, 25), (22, 13), (26, 25), (32, 18), (34, 27)]
            )
    elif field == "aparelho":
        pygame.draw.ellipse(icon, (247, 229, 198), (10, 4, 25, 36))
        pygame.draw.arc(icon, ink, (21, 11, 17, 22), 4.3, 1.7, 3)
        if key == "sim":
            pygame.draw.circle(icon, (43, 147, 157), (34, 24), 5)
        else:
            pygame.draw.line(icon, ink, (30, 19), (37, 27), 3)
    elif field == "mobilidade":
        if key == "cadeira":
            pygame.draw.circle(icon, ink, (13, 28), 10, 3)
            pygame.draw.circle(icon, ink, (34, 28), 10, 3)
            pygame.draw.line(icon, (74, 133, 155), (14, 13), (32, 13), 4)
            pygame.draw.line(icon, (74, 133, 155), (14, 13), (19, 26), 4)
            pygame.draw.line(icon, (74, 133, 155), (32, 13), (32, 26), 4)
        elif key == "andador":
            pygame.draw.line(icon, (74, 133, 155), (9, 8), (9, 35), 4)
            pygame.draw.line(icon, (74, 133, 155), (35, 8), (35, 35), 4)
            pygame.draw.line(icon, (74, 133, 155), (9, 9), (35, 9), 4)
            pygame.draw.circle(icon, ink, (9, 36), 4)
            pygame.draw.circle(icon, ink, (35, 36), 4)
        else:
            pygame.draw.circle(icon, (244, 200, 87), center, 14)
            pygame.draw.circle(icon, ink, center, 14, 2)
    return icon


class PilotScene(Scene):
    editor_dwell = True
    """Editor de personagem organizado em páginas amplas e com miniaturas visuais."""

    def __init__(self, app, first_time: bool = False, return_to=None) -> None:
        super().__init__(app)
        self.first_time = first_time
        self.return_to = return_to
        self.changes = 0
        self.page = "pele"

    def build(self) -> None:
        look = normalize_pilot(self.app.profile.piloto)
        self.app.profile.piloto.update(look)
        buttons = []
        nav_x, nav_y, nav_w, nav_h, gap = 24, 82, 112, 50, 5
        for index, (field, label, _options) in enumerate(PAGES):
            rect = (nav_x + index * (nav_w + gap), nav_y, nav_w, nav_h)
            buttons.append(
                self.button(
                    rect,
                    NAV_LABELS.get(field, label),
                    lambda f=field: self.select_page(f),
                    color=T.TEAL if field == self.page else T.NAVY,
                    selected=field == self.page,
                    size=T.SIZES["small"],
                    icon=_icon(field, _options[0], size=28),
                    key=f"page:{field}",
                )
            )

        _label, options = PAGE_BY_FIELD[self.page]
        selected = mobility(look) if self.page == "mobilidade" else look[self.page]
        rects = grid(CHOICES, len(options), 3, gap=8, row_height=68)
        for option, rect in zip(options, rects):
            option_value = option.key
            buttons.append(
                self.button(
                    rect,
                    option.label,
                    lambda f=self.page, v=option_value: self.choose(f, v),
                    icon=_icon(self.page, option),
                    selected=selected == option_value,
                    size=T.SIZES["small"],
                    key=f"option:{self.page}:{option_value}",
                )
            )
        buttons.append(
            self.button(
                (24, 558, 260, 62), "Surpresa!", self.shuffle, key="surpresa", color=T.TEAL, size=T.SIZES["label"]
            )
        )
        buttons.append(
            self.button(
                (816, 558, 260, 62),
                "Pronto!" if self.first_time else texts.UI["voltar"],
                self.finish,
                key="pronto",
                color=T.ORANGE if self.first_time else T.NAVY,
                size=T.SIZES["label"],
            )
        )
        self.menu.set_buttons(buttons)

    def select_page(self, field: str) -> None:
        if field not in PAGE_BY_FIELD:
            return
        self.page = field
        self.build()

    def choose(self, field: str, value: str) -> None:
        look = self.app.profile.piloto
        if field == "mobilidade":
            look["cadeira"] = "sim" if value == "cadeira" else "nao"
            look["andador"] = "sim" if value == "andador" else "nao"
        elif field in ("cadeira", "andador"):
            look[field] = value
            if value == "sim":
                look["andador" if field == "cadeira" else "cadeira"] = "nao"
        elif field == "pele" and value == UNSELECTED:
            look[field] = UNSELECTED
        elif field == "cabelo" and value == UNSELECTED:
            look[field] = UNSELECTED
        else:
            look[field] = value
        self.app.profile.piloto.update(normalize_pilot(look))
        self.changes += 1
        self.app.audio.play("sfx_selecao", 0.6)
        self.app.save()
        self.build()

    def cycle(self, field: str, step: int) -> None:
        """Compatibilidade com o fluxo/teste anterior de escolha sequencial."""
        if field == "mobilidade":
            keys = list(MOBILITY_KEYS)
            look = normalize_pilot(self.app.profile.piloto)
            current = mobility(look)
            self.choose(field, keys[(keys.index(current) + step) % len(keys)])
            return
        if field in ("cadeira", "andador"):
            self.choose(field, "sim" if self.app.profile.piloto.get(field) != "sim" else "nao")
            return
        options = PAGE_BY_FIELD.get(field, ("", []))[1]
        keys = option_keys(options)
        current = self.app.profile.piloto.get(field, keys[0])
        if current not in keys:
            current = keys[0]
        self.choose(field, keys[(keys.index(current) + step) % len(keys)])

    def shuffle(self) -> None:
        """Surpresa visual: mantém os dispositivos e recursos assistivos escolhidos."""
        look = self.app.profile.piloto
        preserve = {key: look.get(key) for key in ("aparelho", "cadeira", "andador", "oculos")}
        if look.get("acessorio") == "abafador":
            preserve["acessorio"] = "abafador"
        for field, _label, options in PAGES:
            if field in ("aparelho", "mobilidade"):
                continue
            look[field] = random.choice(option_keys(options))
        look.update({key: value for key, value in preserve.items() if value is not None})
        self.app.profile.piloto.update(normalize_pilot(look))
        self.changes += 1
        self.app.audio.play("sfx_powerup", 0.6)
        self.app.save()
        self.build()

    def finish(self) -> None:
        self.app.profile.piloto.update(normalize_pilot(self.app.profile.piloto))
        self.app.profile.piloto_montado = True
        self.app.save()
        if self.return_to is not None:
            self.app.go(self.return_to)
        else:
            self.goto("vila")

    def back(self) -> None:
        self.finish()

    def draw(self, screen: pygame.Surface) -> None:
        app = self.app
        app.backdrop(screen, self.last_dt, None, 40.0)
        T.veil(screen, (10, 18, 40), 112)
        subtitle = (
            "Fique sobre uma escolha para selecionar" if self.first_time else "Fique sobre uma escolha para mudar"
        )
        self.title(screen, texts.UI["piloto"], subtitle)

        T.panel(screen, PREVIEW, T.PAPER, T.NAVY, 245, 22, 3)
        stage = pygame.Rect(PREVIEW.left + 28, PREVIEW.bottom - 59, PREVIEW.width - 56, 28)
        pygame.draw.ellipse(screen, paper.INK, stage.inflate(5, 4))
        pygame.draw.ellipse(screen, rgb("dfe9f5"), stage)
        pilot = app.view.skin.pilots.compose("menu", app.profile.piloto)
        if pilot is not None:
            look_key = tuple(sorted(app.profile.piloto.items()))
            max_w, max_h = 250, 316
            factor = min(max_w / pilot.get_width(), max_h / pilot.get_height())
            size = (round(pilot.get_width() * factor), round(pilot.get_height() * factor))
            img = self.scaled(pilot, size, ("paper_pilot_preview", look_key, size))
            bob = int(math.sin(self.time * 2.0) * 2)
            screen.blit(img, img.get_rect(midbottom=(PREVIEW.centerx, stage.top + 3 + bob)))

        T.panel(screen, CHOICES, (250, 246, 233), T.NAVY, 225, 20, 2)
        self.draw_menu(screen)
