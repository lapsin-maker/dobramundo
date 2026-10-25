"""Projeção e chão (executável): orientação da imagem e calibração dos 4 cantos.

Para jogar com os pés sobre a imagem projetada no chão, a webcam precisa saber
onde a projeção está. A tela mostra quatro alvos numerados; a câmera tira uma
foto; o supervisor clica no centro de cada alvo nessa foto, na ordem 1, 2, 3, 4.
Daí em diante, onde a criança pisa na projeção vira a posição do avião e do
cursor. A calibração vale com a superfície "Chão" e o segmento "Pés".
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

from .. import config as C
from ..content import texts
from ..engine.orientation import ROTATIONS, standing, unrotate_point
from ..input.api import TARGETS, FloorMap
from ..ui import theme as T
from ..ui.widgets import row
from .base import Scene

SHOW_TARGETS_S = 2.5  # tempo com os alvos na projeção antes da foto
STILL_WAIT_S = 3.0  # espera máxima pela foto da câmera
PHOTO_RECT = pygame.Rect(150, 96, 800, 450)  # onde a foto da câmera aparece para os cliques


class ProjectionScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.state = "menu"  # menu | alvos | foto
        self.timer = 0.0
        self.photo: Optional[pygame.Surface] = None
        self.photo_size: Tuple[int, int] = (1, 1)
        self.clicks: List[Tuple[float, float]] = []
        self.message = ""

    # ------------------------------------------------------------ menu
    def build(self) -> None:
        o = self.app.options
        if self.state == "alvos":
            self.menu.set_buttons([])  # nada sobre os alvos; ESC cancela
            return
        if self.state != "menu":
            buttons = [self.button((24, 570, 300, 64), "Cancelar", self.cancel, key="cancelar")]
            if self.state == "foto":
                buttons.append(self.button((340, 570, 360, 64), "Tirar outra foto", self.calibrate, key="foto"))
            self.menu.set_buttons(buttons, keep_focus=False)
            return
        rects = row(pygame.Rect(40, 330, C.WIDTH - 80, 76), 3)
        rects2 = row(pygame.Rect(40, 420, C.WIDTH - 80, 76), 3)
        self.menu.set_buttons(
            [
                self.button(rects[0], f"Girar: {o.rotacao}°", self.rotate, key="girar", sublabel="Sentido horário"),
                self.button(
                    rects[1],
                    f"Espelhar: {'sim' if o.espelhar else 'não'}",
                    self.mirror,
                    selected=o.espelhar,
                    key="espelhar",
                    sublabel="Projeção por trás",
                ),
                self.button(
                    rects[2],
                    f"Cursor à frente: {int(round(o.alvo_frente * 100))}%",
                    self.lead,
                    key="frente",
                    sublabel="Distância dos dedos (0 a 35%)",
                ),
                self.button(rects2[0], "Calibrar os 4 cantos", self.calibrate, key="calibrar", enabled=self.camera_ok),
                self.button(rects2[1], "Apagar calibração", self.forget, key="apagar", enabled=bool(o.chao_pontos)),
                self.button(rects2[2], texts.UI["voltar"], lambda: self.goto("opcoes"), key="voltar"),
            ]
        )

    @property
    def camera_ok(self) -> bool:
        source = self.app.input.source
        return source is not None and source.error is None and hasattr(source, "request_still")

    def changed(self) -> None:
        self.app.apply_options()
        self.app.save()
        self.build()

    def rotate(self) -> None:
        o = self.app.options
        before = o.rotacao
        o.rotacao = ROTATIONS[(ROTATIONS.index(o.rotacao) + 1) % len(ROTATIONS)]
        if o.chao_pontos and standing(before) != standing(o.rotacao):
            # em pé ou deitada, a imagem ocupa outra área: os alvos calibrados não servem mais
            o.chao_pontos = []
            self.toast.show("A imagem mudou de formato: calibre os 4 cantos de novo")
        self.changed()

    def mirror(self) -> None:
        self.app.options.espelhar = not self.app.options.espelhar
        self.changed()

    def lead(self) -> None:
        o = self.app.options
        o.alvo_frente = 0.0 if o.alvo_frente >= 0.35 - 1e-6 else round(min(0.35, o.alvo_frente + 0.05), 2)
        self.changed()

    def forget(self) -> None:
        self.app.options.chao_pontos = []
        self.toast.show("Calibração apagada: os pés voltam a usar a posição relativa")
        self.changed()

    # ------------------------------------------------------- calibração
    def calibrate(self) -> None:
        """Mostra os alvos na projeção; depois de um instante, a câmera tira a foto."""
        self.state, self.timer, self.clicks, self.photo = "alvos", 0.0, [], None
        self.build()

    def cancel(self) -> None:
        self.state = "menu"
        self.build()

    def back(self) -> None:
        if self.state != "menu":
            self.cancel()
        else:
            self.goto("opcoes")

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.state != "alvos":
            return
        source = self.app.input.source
        before = self.timer
        self.timer += dt
        if before < SHOW_TARGETS_S <= self.timer and source is not None:
            source.request_still()
        still = source.still() if source is not None and self.timer >= SHOW_TARGETS_S else None
        if still is not None:
            data, size = still
            self.photo = pygame.image.frombytes(data, size, "RGB")
            self.photo_size = size
            self.state = "foto"
            self.build()
        elif self.timer > SHOW_TARGETS_S + STILL_WAIT_S:
            self.toast.show("A câmera não enviou a foto. Tente de novo.")
            self.cancel()

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.state == "foto" and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if PHOTO_RECT.collidepoint(event.pos):
                self.click(event.pos)
                return
        super().handle_event(event)

    def click(self, pos) -> None:
        rect = self.photo_rect()
        self.clicks.append(((pos[0] - rect.left) / rect.width, (pos[1] - rect.top) / rect.height))
        self.app.audio.play("sfx_selecao")
        if len(self.clicks) < 4:
            return
        if FloorMap.maybe(self.clicks) is None:
            self.toast.show("Os cliques não formam um quadrilátero: clique de novo, na ordem 1, 2, 3, 4")
            self.clicks = []
            return
        o = self.app.options
        o.chao_pontos = [[round(x, 4), round(y, 4)] for x, y in self.clicks]
        if o.superficie != "chao" or self.app.profile.controle != "pes":
            o.superficie, self.app.profile.controle = "chao", "pes"
            self.toast.show("Chão calibrado: superfície Chão e segmento Pés ativados")
        else:
            self.toast.show("Chão calibrado: pise sobre a projeção para conferir")
        self.state = "menu"
        self.changed()

    def photo_rect(self) -> pygame.Rect:
        w, h = self.photo_size
        scale = min(PHOTO_RECT.width / w, PHOTO_RECT.height / h)
        rect = pygame.Rect(0, 0, int(w * scale), int(h * scale))
        rect.center = PHOTO_RECT.center
        return rect

    # ------------------------------------------------------------ desenho
    def draw(self, screen: pygame.Surface) -> None:
        if self.state == "alvos":
            self.draw_targets(screen)
        elif self.state == "foto":
            self.draw_photo(screen)
        else:
            self.draw_options(screen)
        self.draw_menu(screen)
        self.toast.draw(screen, self.text, (C.WIDTH // 2, 300), 760)

    def draw_options(self, screen: pygame.Surface) -> None:
        self.app.backdrop(screen, self.last_dt, None, 50.0)
        T.veil(screen, (10, 18, 40), 150)
        self.title(screen, "Projeção e chão", "Orientação da imagem e calibração dos pés sobre a projeção")
        o = self.app.options
        if o.chao_pontos:
            status = "Chão calibrado." + (
                "" if o.superficie == "chao" and self.app.profile.controle == "pes" else " Vale com Chão e Pés."
            )
        else:
            status = "Sem calibração: com os pés, o avião segue o movimento a partir da posição neutra."
        lines = (
            status,
            "Calibrar: deixe a webcam vendo toda a projeção no chão e clique nos alvos 1, 2, 3 e 4 na foto.",
            "Mover a câmera ou o projetor, ou girar 90°/270°, pede uma calibração nova.",
            "A câmera estima a posição do pé; confira pisando sobre os alvos.",
        )
        for i, line in enumerate(lines):
            color = T.SUN if i == 0 else T.WHITE
            self.text.blit(screen, line, (40, 120 + i * 40), T.SIZES["body"], color, i == 0)
        if not self.camera_ok:
            self.text.blit(
                screen,
                "Ligue a câmera em Opções (um segmento do corpo) para calibrar.",
                (40, 290),
                T.SIZES["body"],
                T.SUN,
                True,
            )

    def draw_targets(self, screen: pygame.Surface) -> None:
        """Quatro alvos grandes a 15% das bordas da imagem projetada, e a borda da área de jogo."""
        o = self.app.options
        screen.fill((0, 0, 0))
        pygame.draw.rect(screen, (60, 220, 120), screen.get_rect(), 6)
        for i, (u, v) in enumerate(TARGETS):
            x, y = unrotate_point(u, v, o.rotacao, o.espelhar)
            center = (int(x * C.WIDTH), int(y * C.HEIGHT))
            pygame.draw.circle(screen, T.WHITE, center, 50)
            pygame.draw.circle(screen, (230, 40, 40), center, 40)
            pygame.draw.circle(screen, T.WHITE, center, 26)
            self.text.blit(screen, str(i + 1), center, T.SIZES["title"], (200, 30, 30), True, "center")
        left = max(0, int(SHOW_TARGETS_S - self.timer) + 1)
        self.text.blit(
            screen,
            f"Deixe a câmera ver os quatro alvos. Foto em {left}...",
            (C.WIDTH // 2, C.HEIGHT // 2),
            T.SIZES["label"],
            T.WHITE,
            True,
            "center",
        )

    def draw_photo(self, screen: pygame.Surface) -> None:
        screen.fill((16, 24, 44))
        rect = self.photo_rect()
        if self.photo is not None:
            screen.blit(pygame.transform.smoothscale(self.photo, rect.size), rect)
        for i, (x, y) in enumerate(self.clicks):
            point = (int(rect.left + x * rect.width), int(rect.top + y * rect.height))
            pygame.draw.circle(screen, T.SUN, point, 10, 3)
            self.text.blit(screen, str(i + 1), (point[0] + 14, point[1] - 14), T.SIZES["body"], T.SUN, True)
        step = len(self.clicks) + 1
        self.text.blit(
            screen,
            f"Clique no centro do alvo {step} (1 superior esquerdo, 2 superior direito, 3 inferior direito,"
            " 4 inferior esquerdo)",
            (C.WIDTH // 2, 40),
            T.SIZES["body"],
            T.WHITE,
            True,
            "center",
        )
