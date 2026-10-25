"""Piloto: tom de pele, cabelo, roupa, óculos e acessórios, sem marcação de gênero.

Cadeira de rodas e aparelho auditivo aparecem como itens comuns da lista.
"""

from __future__ import annotations

import math

import pygame

from ..content import texts
from ..content.pilot import PILOT_FIELDS, find_option, option_keys
from ..ui import theme as T
from .base import Scene

ROW_TOP = 88
ROW_STEP = 58


class PilotScene(Scene):
    def build(self) -> None:
        app = self.app
        look = app.profile.piloto
        buttons = []
        for i, (field, label, options) in enumerate(PILOT_FIELDS):
            y = ROW_TOP + i * ROW_STEP
            option = find_option(options, look[field])
            buttons.append(self.button((560, y, 64, 50), "<", (lambda f=field: self.cycle(f, -1)), key=f"{field}_prev"))
            buttons.append(
                self.button(
                    (632, y, 368, 50),
                    option.label
                    if option.label.lower().startswith(("sem ", label.lower()))
                    else f"{label}: {option.label}",
                    (lambda f=field: self.cycle(f, 1)),
                    swatch=option.color,
                    size=T.SIZES["body"],
                    key=f"{field}_val",
                )
            )
            buttons.append(self.button((1008, y, 64, 50), ">", (lambda f=field: self.cycle(f, 1)), key=f"{field}_next"))
        buttons.append(self.button((24, 570, 300, 64), texts.UI["voltar"], lambda: self.goto("vila"), key="voltar"))
        self.menu.set_buttons(buttons)

    def cycle(self, field: str, step: int) -> None:
        options = next(opts for f, _, opts in PILOT_FIELDS if f == field)
        keys = option_keys(options)
        look = self.app.profile.piloto
        look[field] = keys[(keys.index(look[field]) + step) % len(keys)]
        self.app.save()
        self.build()

    def draw(self, screen: pygame.Surface) -> None:
        app = self.app
        profile = app.profile
        app.backdrop(screen, self.last_dt, None, 40.0)
        T.veil(screen, (10, 18, 40), 120)
        self.title(screen, texts.UI["piloto"], "Monte o piloto do seu jeito")
        card = pygame.Rect(24, 86, 516, 470)
        T.panel(screen, card, T.PAPER, T.NAVY, 245, 22, 3)
        skin = app.view.skin
        pilot = skin.pilots.compose("menu", profile.piloto)
        if pilot is not None:
            img = self.scaled(pilot, (240, 250), ("piloto", tuple(sorted(profile.piloto.items()))))
            bob = math.sin(self.time * 2.0) * 4
            screen.blit(img, img.get_rect(midbottom=(card.centerx, card.top + 290 + bob)))
        else:
            self.text.blit(
                screen, "Camadas do piloto não encontradas", card.center, T.SIZES["body"], T.MUTED, anchor="center"
            )
        plane = skin.surface(
            profile.aviao,
            "menu",
            profile.plane_color(profile.aviao),
            profile.plane_pattern(profile.aviao),
            profile.piloto,
        )
        if plane is not None:
            img = self.scaled(
                plane,
                (300, 160),
                (
                    "piloto_aviao",
                    skin.look_key(
                        profile.aviao,
                        profile.plane_color(profile.aviao),
                        profile.plane_pattern(profile.aviao),
                        profile.piloto,
                    ),
                ),
            )
            screen.blit(img, img.get_rect(midbottom=(card.centerx, card.bottom - 14)))
        self.draw_menu(screen)
