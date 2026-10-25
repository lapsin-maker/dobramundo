"""Sobre: proposta, ODS, créditos e referências (textos de apoio do GDD)."""

from __future__ import annotations

import pygame

from .. import config as C
from ..content import texts
from ..ui import theme as T
from .base import Scene

TABS = (("sobre", "O jogo"), ("ods", "ODS"), ("creditos", "Créditos"), ("referencias", "Referências"))
BODY = pygame.Rect(40, 160, C.WIDTH - 80, 390)


class AboutScene(Scene):
    def __init__(self, app, tab: str = "sobre") -> None:
        super().__init__(app)
        self.tab = tab
        self.page = 0

    def build(self) -> None:
        buttons = [
            self.button(
                (24 + i * 196, 86, 184, 54),
                label,
                (lambda k=key: self.set_tab(k)),
                selected=self.tab == key,
                size=T.SIZES["body"],
                key=f"tab_{key}",
            )
            for i, (key, label) in enumerate(TABS)
        ]
        if self.tab == "sobre":
            count = len(texts.ABOUT_SECTIONS)
            buttons.append(
                self.button(
                    (C.WIDTH - 360, 570, 160, 64), "< Anterior", lambda: self.turn(-1), enabled=self.page > 0, key="ant"
                )
            )
            buttons.append(
                self.button(
                    (C.WIDTH - 190, 570, 166, 64),
                    "Próxima >",
                    lambda: self.turn(1),
                    enabled=self.page < count - 1,
                    key="prox",
                )
            )
        buttons.append(self.button((24, 570, 300, 64), texts.UI["voltar"], lambda: self.goto("vila"), key="voltar"))
        self.menu.set_buttons(buttons)

    def set_tab(self, tab: str) -> None:
        self.tab, self.page = tab, 0
        self.build()

    def turn(self, step: int) -> None:
        self.page = max(0, min(len(texts.ABOUT_SECTIONS) - 1, self.page + step))
        self.build()

    def draw(self, screen: pygame.Surface) -> None:
        self.app.backdrop(screen, self.last_dt, "caatinga", 90.0)
        T.veil(screen, (10, 18, 40), 140)
        self.title(screen, texts.UI["sobre"], texts.TAGLINE)
        logo = self.app.assets.sprite("ui", "logo")
        if logo is not None:
            screen.blit(self.scaled(logo, (190, 96)), (C.WIDTH - 214, 70))
        card = BODY.inflate(24, 24)
        T.panel(screen, card, T.PAPER, T.NAVY, 246, 20, 3)
        text = self.text
        if self.tab == "sobre":
            title, paragraphs = texts.ABOUT_SECTIONS[self.page]
            text.blit(
                screen,
                f"{title}  ({self.page + 1}/{len(texts.ABOUT_SECTIONS)})",
                BODY.topleft,
                T.SIZES["label"],
                T.NAVY,
                True,
            )
            y = BODY.top + 42
            for paragraph in paragraphs:
                y = text.paragraph(screen, paragraph, pygame.Rect(BODY.left, y, BODY.width, 300), 19, T.INK, 1.25) + 8
        elif self.tab == "ods":
            text.blit(screen, "Objetivos de Desenvolvimento Sustentável", BODY.topleft, T.SIZES["label"], T.NAVY, True)
            for i, (number, name, why) in enumerate(texts.ODS):
                x = BODY.left + (i % 2) * (BODY.width // 2)
                y = BODY.top + 48 + (i // 2) * 100
                badge = pygame.Rect(x, y, 70, 70)
                pygame.draw.rect(screen, T.TEAL, badge, border_radius=14)
                text.blit(screen, str(number), badge.center, T.SIZES["title"], T.WHITE, True, "center")
                text.blit(screen, name, (x + 84, y + 4), T.SIZES["body"], T.INK, True)
                text.blit(screen, why, (x + 84, y + 36), T.SIZES["body"], T.MUTED)
            text.blit(screen, texts.ENERGY_FACT, (BODY.left, BODY.bottom - 22), T.SIZES["small"], T.NAVY, True)
        elif self.tab == "creditos":
            y = BODY.top
            for label, value in texts.CREDITS:
                text.blit(screen, label, (BODY.left, y), T.SIZES["body"], T.NAVY, True)
                y = (
                    text.paragraph(
                        screen,
                        value,
                        pygame.Rect(BODY.left + 190, y, BODY.width - 190, 80),
                        T.SIZES["body"],
                        T.INK,
                        1.2,
                    )
                    + 6
                )
        else:
            y = BODY.top
            for reference in texts.REFERENCES:
                y = (
                    text.paragraph(
                        screen, reference, pygame.Rect(BODY.left, y, BODY.width, 120), T.SIZES["body"], T.INK, 1.25
                    )
                    + 16
                )
        self.draw_menu(screen)
