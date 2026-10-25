"""Calibração individual da postura neutra do segmento escolhido.

A criança fica parada na posição confortável por cerca de 2 s; o ponto mediano
vira o "centro" de onde os movimentos são medidos. O supervisor pode trocar o
segmento ou seguir com teclado e mouse.
"""

from __future__ import annotations

from typing import Optional

import pygame

from .. import config as C
from ..input.api import SEGMENTS
from ..ui import theme as T
from ..ui.widgets import ring, row
from .base import Scene


class CalibrationScene(Scene):
    def __init__(self, app, return_to: Optional[Scene] = None, guided: bool = False) -> None:
        super().__init__(app)
        self.return_to = return_to
        self.done_time = 0.0
        self.preview: Optional[pygame.Surface] = None
        self.preview_bytes: Optional[bytes] = None
        self.guided_index = -1
        self.guided_after_center = guided
        self.guided_samples = []
        self.guided_last_seq = -1
        self.guided_message = ""

    def enter(self) -> None:
        body = self.app.input.body
        if body is not None:
            body.recalibrate()
        super().enter()

    def build(self) -> None:
        rects = row(pygame.Rect(60, 560, C.WIDTH - 120, 70), 5)
        self.menu.set_buttons(
            [
                self.button(rects[0], "Reiniciar", self.restart, key="recomecar"),
                self.button(
                    rects[1], "Alcances", self.begin_guided, key="extremos", sublabel="Calibração guiada"
                ),
                self.button(rects[2], "Segmento", self.options, key="segmento", sublabel="Trocar"),
                self.button(rects[3], "Teclado", self.keyboard, key="teclado"),
                self.button(rects[4], "Continuar", self.finish, key="continuar"),
            ]
        )

    def restart(self) -> None:
        body = self.app.input.body
        if body is not None and body.error is not None:
            self.app.input.retry_camera()
        elif body is not None:
            body.recalibrate()
        self.done_time = 0.0
        self.guided_index = -1

    def begin_guided(self) -> None:
        body = self.app.input.body
        if body is None or not body.calibrated:
            self.guided_message = "Conclua primeiro a posição neutra."
            return
        self.guided_index = 0
        self.guided_samples = []
        self.guided_last_seq = body._seq
        self.guided_message = "Mova-se confortavelmente para a direita e confirme com Enter."

    def capture_guided(self) -> None:
        body = self.app.input.body
        directions = ("right", "left", "up", "down")
        labels = ("direita", "esquerda", "cima", "baixo")
        if body is None or self.guided_index < 0:
            return
        if not body.mapper.set_comfortable_extent(directions[self.guided_index], self.guided_samples[-18:]):
            self.guided_message = "Movimento curto: tente novamente ou volte ao centro."
            self.guided_samples = []
            return
        self.guided_index += 1
        self.guided_samples = []
        if self.guided_index >= len(directions):
            self.guided_index = -1
            self.guided_message = "Alcances confortáveis salvos."
        else:
            self.guided_message = f"Agora mova-se para {labels[self.guided_index]} e confirme com Enter."

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.guided_index >= 0 and event.type == pygame.KEYDOWN and event.key in (
            pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER
        ):
            self.capture_guided()
            return
        super().handle_event(event)

    def options(self) -> None:
        return_to, self.return_to = self.return_to, None
        if return_to is not None:
            # Ir às opções abandona este voo; creditá-lo agora evita perder o parcial.
            return_to.settle_on_close()
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
        if (
            self.guided_index >= 0
            and body.visible
            and body._seq != self.guided_last_seq
            and body._last_point is not None
        ):
            self.guided_last_seq = body._seq
            self.guided_samples.append(body._last_point)
        if body.calibrated:
            self.done_time += dt
            if self.guided_after_center:
                self.guided_after_center = False
                self.begin_guided()

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
        mapper = body.mapper
        size = body.frame_size or (0, 0)
        fps = f"{body.capture_fps:.0f}/{body.inference_fps:.0f} fps"
        age = "—" if body.reading_age == float("inf") else f"{body.reading_age * 1000:.0f}ms"
        rendered = "—" if body.capture_to_render_ms is None else f"{body.capture_to_render_ms:.0f}ms"
        diagnostic = (
            f"Webcam {size[0]}×{size[1]} · inicialização {body.camera_startup_ms:.0f}ms"
            f" · leitura/detector {fps} · inferência {body.inference_ms:.0f}ms"
            f" · idade {age} · último quadro {rendered}"
        )
        detail = (
            f"Pontos {body.valid_point_count}/{len(segment.landmarks) if segment else 0}"
            f" · confiança {body.confidence:.2f} · eixos {mapper.ax:+.2f}, {mapper.ay:+.2f}"
            f" · descartes {body.stale_dropped} · falhas de leitura {body.read_failures}"
            f" · erros {body.camera_errors}"
        )
        self.text.blit(
            screen, diagnostic, (card.centerx, card.bottom - 46), T.SIZES["small"], T.MUTED, anchor="midbottom"
        )
        self.text.blit(
            screen, detail, (card.centerx, card.bottom - 25), T.SIZES["small"], T.MUTED, anchor="midbottom"
        )
        if self.guided_message:
            self.text.blit(
                screen,
                self.guided_message,
                (card.centerx, card.bottom - 2),
                T.SIZES["small"],
                T.NAVY,
                anchor="midbottom",
            )

    def settle_on_close(self) -> None:
        if self.return_to is not None:
            self.return_to.settle_on_close()
