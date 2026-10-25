"""Calibração individual da postura neutra do segmento escolhido.

A criança fica parada na posição confortável por cerca de 2 s; o ponto mediano
vira o "centro" de onde os movimentos são medidos. O supervisor pode trocar o
segmento ou seguir com teclado e mouse.
"""

from __future__ import annotations

from typing import Optional

import pygame

from .. import config as C
from ..input.pose import SEGMENTS
from ..ui import theme as T
from ..ui.widgets import ring, row
from .base import Scene

CONFIRM_S = 1.0  # depois de calibrar, mostra "pronto" um instante antes de seguir


class CalibrationScene(Scene):
    def __init__(self, app, return_to: Optional[Scene] = None) -> None:
        super().__init__(app)
        self.return_to = return_to
        self.done_time = 0.0
        self.preview: Optional[pygame.Surface] = None
        self.preview_bytes: Optional[bytes] = None

    def enter(self) -> None:
        body = self.app.input.body
        if body is not None:
            body.recalibrate()
        super().enter()

    def build(self) -> None:
        rects = row(pygame.Rect(140, 560, C.WIDTH - 280, 70), 3)
        self.menu.set_buttons(
            [
                self.button(rects[0], "Recomeçar", self.restart, key="recomecar"),
                self.button(rects[1], "Trocar segmento", self.options, key="segmento"),
                self.button(rects[2], "Usar teclado", self.keyboard, key="teclado"),
            ]
        )

    def restart(self) -> None:
        if self.app.input.body is not None:
            self.app.input.body.recalibrate()
        self.done_time = 0.0

    def options(self) -> None:
        self.goto("opcoes")

    def keyboard(self) -> None:
        self.app.profile.controle = "teclado"
        self.app.apply_options()
        self.app.save()
        self.finish()

    def finish(self) -> None:
        if self.return_to is not None:
            self.app.go(self.return_to)
        else:
            self.goto("vila")

    def back(self) -> None:
        self.finish()

    def update(self, dt: float) -> None:
        super().update(dt)
        body = self.app.input.body
        if body is None:
            self.finish()
            return
        if body.calibrated:
            self.done_time += dt
            if self.done_time >= CONFIRM_S:
                self.app.audio.play("sfx_selecao")
                self.finish()

    def draw(self, screen: pygame.Surface) -> None:
        self.app.backdrop(screen, self.last_dt, None, 20.0)
        T.veil(screen, (10, 18, 40), 160)
        body = self.app.input.body
        segment = SEGMENTS.get(self.app.profile.controle)
        self.title(screen, "Calibração", f"Segmento: {segment.label if segment else 'teclado'}")
        card = pygame.Rect(140, 90, C.WIDTH - 280, 450)
        T.panel(screen, card, T.PAPER, T.NAVY, 248, 24, 4)
        if body is None:
            self.draw_menu(screen)
            return
        if body.error:
            message, detail = "Câmera indisponível", f"{body.error}. Você pode jogar com o teclado."
        elif not body.receiving:
            message, detail = "Ligando a câmera...", "Isso leva alguns segundos."
        elif body.calibrated:
            message, detail = "Pronto!", "Agora é só se mover para pilotar."
        elif not body.visible:
            message, detail = "Não estou vendo o segmento", "Entre na área da câmera."
        else:
            message, detail = segment.hint if segment else "Fique parado", "Fique parado assim um instante..."
        size = (
            T.SIZES["title"]
            if self.text.font(T.SIZES["title"], True).size(message)[0] < card.width - 60
            else T.SIZES["label"]
        )
        self.text.blit(screen, message, (card.centerx, card.top + 24), size, T.NAVY, True, "midtop")
        self.text.blit(screen, detail, (card.centerx, card.top + 74), T.SIZES["label"], T.INK, anchor="midtop")
        center = (card.left + 250, card.top + 270)
        radius = 110
        pygame.draw.circle(screen, T.PAPER_DARK, center, radius, 18)
        progress = body.progress
        ring(screen, center, radius, 18, progress, T.GREEN if body.calibrated else T.ORANGE)
        self.text.blit(screen, f"{int(progress * 100)}%", center, T.SIZES["hero"], T.NAVY, True, "center")
        if body.preview is not None:
            if self.preview_bytes is not body.preview:
                self.preview = pygame.transform.smoothscale(
                    pygame.image.frombytes(body.preview, (160, 120), "RGB"), (320, 240)
                )
                self.preview_bytes = body.preview
            rect = self.preview.get_rect(center=(card.right - 230, card.top + 270))
            screen.blit(self.preview, rect)
            pygame.draw.rect(screen, T.GREEN if body.visible else T.RED, rect, 4)
            if body.landmarks and segment is not None:
                for i in segment.landmarks:
                    if i < len(body.landmarks) and body.landmarks[i][2] >= 0.5:
                        x, y, _ = body.landmarks[i]
                        pygame.draw.circle(
                            screen, T.SUN, (rect.left + int(x * rect.width), rect.top + int(y * rect.height)), 7
                        )
            self.text.blit(
                screen,
                "Imagem só na tela, nada é gravado",
                (rect.centerx, rect.bottom + 8),
                T.SIZES["small"],
                T.MUTED,
                anchor="midtop",
            )
        self.draw_menu(screen)
