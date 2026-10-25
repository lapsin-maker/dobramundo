"""Piloto: tom de pele, cabelo, roupa, óculos e acessórios, sem marcação de gênero.

É a primeira tela da criança no jogo (antes da vila): ela monta o personagem e
aperta "Pronto!". Cadeira de rodas e aparelho auditivo aparecem como itens
comuns da lista. As cores aparecem como amostras, para a criança escolher
olhando, não lendo.
"""

from __future__ import annotations

import math
from typing import Optional

import pygame

from ..content import texts
from ..content.pilot import PILOT_FIELDS, find_option, option_keys
from ..engine import paper
from ..ui import theme as T
from ..util import rgb
from .base import Scene

ROW_TOP = 88
ROW_STEP = 56
CARD = pygame.Rect(24, 86, 500, 470)
GREETINGS = ("Oi! Esse é você?", "Que legal!", "Pronto para voar?", "Uau, ficou ótimo!")


class PilotScene(Scene):
    def __init__(self, app, first_time: bool = False, return_to: Optional[Scene] = None) -> None:
        super().__init__(app)
        self.first_time = first_time
        self.return_to = return_to
        self.changes = 0

    def build(self) -> None:
        app = self.app
        look = app.profile.piloto
        buttons = []
        for i, (field, label, options) in enumerate(PILOT_FIELDS):
            y = ROW_TOP + i * ROW_STEP
            option = find_option(options, look[field])
            buttons.append(self.button((548, y, 60, 48), "<", (lambda f=field: self.cycle(f, -1)), key=f"{field}_prev"))
            text = (
                option.label if option.label.lower().startswith(("sem ", label.lower())) else f"{label}: {option.label}"
            )
            buttons.append(
                self.button(
                    (616, y, 392, 48),
                    text,
                    (lambda f=field: self.cycle(f, 1)),
                    swatch=option.color,
                    size=T.SIZES["body"],
                    key=f"{field}_val",
                )
            )
            buttons.append(self.button((1016, y, 60, 48), ">", (lambda f=field: self.cycle(f, 1)), key=f"{field}_next"))
        buttons.append(self.button((548, 548, 240, 60), "Surpresa!", self.shuffle, key="surpresa", color=T.TEAL))
        buttons.append(
            self.button(
                (800, 548, 276, 60),
                "Pronto!" if self.first_time else texts.UI["voltar"],
                self.finish,
                key="pronto",
                color=T.ORANGE if self.first_time else T.NAVY,
            )
        )
        self.menu.set_buttons(buttons)

    def cycle(self, field: str, step: int) -> None:
        options = next(opts for f, _, opts in PILOT_FIELDS if f == field)
        keys = option_keys(options)
        look = self.app.profile.piloto
        look[field] = keys[(keys.index(look[field]) + step) % len(keys)]
        self.changes += 1
        self.app.audio.play("sfx_selecao", 0.6)
        self.app.save()
        self.build()

    def shuffle(self) -> None:
        """Monta um piloto ao acaso (bom para quem não quer escolher item a item)."""
        import random

        look = self.app.profile.piloto
        for field, _, options in PILOT_FIELDS:
            if field in ("aparelho", "cadeira"):
                continue  # itens assistivos não são sorteados
            look[field] = random.choice(option_keys(options))
        self.changes += 1
        self.app.audio.play("sfx_powerup", 0.6)
        self.app.save()
        self.build()

    def finish(self) -> None:
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
        profile = app.profile
        app.backdrop(screen, self.last_dt, None, 40.0)
        T.veil(screen, (10, 18, 40), 120)
        self.title(
            screen,
            texts.UI["piloto"],
            "Monte o seu piloto do seu jeito" if self.first_time else "Monte o piloto do seu jeito",
        )
        T.panel(screen, CARD, T.PAPER, T.NAVY, 245, 22, 3)
        # um "palco" de papel para o personagem
        stage = pygame.Rect(CARD.left + 40, CARD.top + 300, CARD.width - 80, 40)
        pygame.draw.ellipse(screen, paper.INK, stage.inflate(4, 4))
        pygame.draw.ellipse(screen, rgb("dfe9f5"), stage)
        skin = app.view.skin
        pilot = skin.pilots.compose("menu", profile.piloto)
        if pilot is not None:
            img = self.scaled(pilot, (260, 280), ("piloto", tuple(sorted(profile.piloto.items()))))
            bob = math.sin(self.time * 2.0) * 4
            screen.blit(img, img.get_rect(midbottom=(CARD.centerx, CARD.top + 318 + int(bob))))
        else:
            self.text.blit(
                screen, "Camadas do piloto não encontradas", CARD.center, T.SIZES["body"], T.MUTED, anchor="center"
            )
        greeting = GREETINGS[min(len(GREETINGS) - 1, self.changes // 3)]
        bubble = pygame.Rect(0, 0, self.text.font(T.SIZES["label"], hand=True).size(greeting)[0] + 40, 46)
        bubble.midtop = (CARD.centerx + 110, CARD.top + 24)
        T.panel(screen, bubble, (255, 255, 255), T.NAVY, 255, 16, 2)
        self.text.blit(screen, greeting, bubble.center, T.SIZES["label"], T.NAVY, anchor="center", hand=True)
        plane = skin.surface(
            profile.aviao,
            "menu",
            profile.plane_color(profile.aviao),
            profile.plane_pattern(profile.aviao),
            profile.piloto,
        )
        if plane is not None:
            key = skin.look_key(
                profile.aviao, profile.plane_color(profile.aviao), profile.plane_pattern(profile.aviao), profile.piloto
            )
            img = self.scaled(plane, (280, 150), ("piloto_aviao", key))
            screen.blit(img, img.get_rect(midbottom=(CARD.centerx, CARD.bottom - 10)))
        self.draw_menu(screen)
