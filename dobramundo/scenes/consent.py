"""Aviso ao supervisor na primeira execução: supervisão, privacidade (LGPD) e pausa."""

from __future__ import annotations

from datetime import datetime

import pygame

from .. import config as C
from ..content import texts
from ..ui import theme as T
from .base import Scene


class ConsentScene(Scene):
    def __init__(self, app, next_scene) -> None:
        super().__init__(app)
        self.next_scene = next_scene

    def build(self) -> None:
        self.menu.set_buttons(
            [
                self.button(
                    (C.WIDTH // 2 - 230, 548, 460, 76),
                    "Li e concordo",
                    self.accept,
                    sublabel="confirmação do supervisor",
                    color=T.GREEN,
                    key="aceito",
                ),
            ]
        )

    def accept(self) -> None:
        self.app.profile.consentimento = True
        self.app.profile.consentimento_em = datetime.now().isoformat(timespec="minutes")
        self.app.save()
        self.app.go(self.next_scene)

    def back(self) -> None:
        self.app.running = False

    def draw(self, screen: pygame.Surface) -> None:
        self.app.backdrop(screen, self.last_dt, None, 5.0)
        T.veil(screen, (10, 18, 40), 170)
        card = pygame.Rect(90, 30, C.WIDTH - 180, 500)
        T.panel(screen, card, T.PAPER, T.NAVY, 250, 24, 4)
        logo = self.app.assets.sprite("ui", "logo")
        top = card.top + 20
        if logo is not None:
            img = self.scaled(logo, (220, 110))
            screen.blit(img, img.get_rect(midtop=(card.centerx, top)))
            top += 116
        self.text.blit(screen, texts.CONSENT_TITLE, (card.centerx, top), T.SIZES["label"], T.NAVY, True, "midtop")
        y = top + 46
        for line in texts.CONSENT_LINES:
            pygame.draw.circle(screen, T.TEAL, (card.left + 70, y + 12), 5)
            self.text.blit(screen, line, (card.left + 86, y), T.SIZES["body"], T.INK)
            y += 34
        self.text.blit(
            screen, "ESC: sair do jogo", (card.centerx, card.bottom - 30), T.SIZES["small"], T.MUTED, anchor="midtop"
        )
        self.draw_menu(screen)
