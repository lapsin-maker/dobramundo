"""Atalhos claros de preparação para conforto e acessibilidade."""

from __future__ import annotations

import pygame

from .. import config as C
from ..ui import theme as T
from . import make_scene
from .base import Scene


class PreparationScene(Scene):
    """Presets persistentes, calibragem e rotas rápidas para a supervisão."""

    def build(self) -> None:
        o = self.app.options
        body = self.app.input.body
        can_calibrate = body is not None and body.error is None
        calibrate_label = "Calibrar" if can_calibrate else "Escolher controle"
        calibrate_detail = "Centro · extremos na sessão" if can_calibrate else "Configure em Opções"
        calibrate_action = self.calibrate if can_calibrate else self.open_options
        projection_enabled = self.app.platform == "desktop"
        cards = (
            (pygame.Rect(34, 166, 332, 282), "Calmo", "Movimento leve · som 35/40%", self.apply_calm, "calmo"),
            (pygame.Rect(384, 166, 332, 282), "Mais visível", "Contraste · zoom 1,3×", self.apply_visible, "visivel"),
            (pygame.Rect(734, 166, 332, 282), calibrate_label, calibrate_detail, calibrate_action, "calibrar"),
        )
        buttons = []
        for rect, label, detail, action, key in cards:
            selected = (
                (key == "calmo" and o.reduzir_movimento and not o.efeitos_fortes)
                or (key == "visivel" and o.alto_contraste and o.escala_contraste >= 1.3)
            )
            buttons.append(
                self.button(
                    rect,
                    label,
                    action,
                    sublabel=detail,
                    selected=selected,
                    size=T.SIZES["title"],
                    key=key,
                    align="top",
                )
            )
        buttons.extend(
            [
                self.button(
                    (34, 500, 322, 58),
                    "Projeção",
                    lambda: self.goto("projecao"),
                    key="projecao",
                    enabled=projection_enabled,
                ),
                self.button(
                    (389, 500, 322, 58),
                    "Seleção",
                    self.practice_selection,
                    key="selecao",
                    icon=T.icon_surface("next", 34, T.NAVY),
                ),
                self.button((744, 500, 322, 58), "Opções", self.back, key="opcoes"),
            ]
        )
        self.menu.set_buttons(buttons)

    def back(self) -> None:
        self.goto("opcoes")

    def open_options(self) -> None:
        self.goto("opcoes")

    def _save_preset(self, message: str) -> None:
        self.app.apply_options()
        self.app.save()
        self.build()
        self.toast.show(message)

    def apply_calm(self) -> None:
        o = self.app.options
        o.reduzir_movimento = True
        o.efeitos_fortes = False
        o.volume_geral = 0.35
        o.volume_musica = 0.35
        o.volume_efeitos = 0.4
        o.permanencia_editor = 3.5
        self._save_preset("Ajuste calmo salvo")

    def apply_visible(self) -> None:
        o = self.app.options
        o.alto_contraste = True
        o.escala_contraste = 1.3
        self._save_preset("Mais visível salvo")

    def calibrate(self) -> None:
        body = self.app.input.body
        if body is None or body.error is not None:
            self.open_options()
            return
        self.goto("calibracao", return_to=make_scene(self.app, "preparar"), guided=True)

    def practice_selection(self) -> None:
        self.goto(
            "dwell_treino",
            next_scene=make_scene(self.app, "preparar"),
            return_to=make_scene(self.app, "preparar"),
        )

    def draw(self, screen: pygame.Surface) -> None:
        self.app.backdrop(screen, self.last_dt, None, 20.0)
        T.veil(screen, (10, 18, 40), 150)
        self.title(screen, "Preparar", "Atalhos para ajustar a experiência")
        self.draw_menu(screen)
        self._draw_icons(screen)
        self.toast.draw(screen, self.text, (C.WIDTH // 2, 614), 520)

    def _draw_icons(self, screen: pygame.Surface) -> None:
        centers = ((200, 338), (550, 338), (900, 338))
        # Lua/folha: descanso. Olho: contraste. Mira: centro e extremos.
        cx, cy = centers[0]
        pygame.draw.circle(screen, T.GREEN, (cx, cy), 48, 8)
        pygame.draw.ellipse(screen, T.GREEN, pygame.Rect(cx - 25, cy - 20, 32, 20), 5)
        pygame.draw.ellipse(screen, T.GREEN, pygame.Rect(cx - 4, cy + 1, 32, 20), 5)
        pygame.draw.line(screen, T.GREEN, (cx - 4, cy + 4), (cx + 8, cy - 6), 5)

        cx, cy = centers[1]
        pygame.draw.ellipse(screen, T.NAVY, pygame.Rect(cx - 55, cy - 34, 110, 68), 7)
        pygame.draw.circle(screen, T.NAVY, (cx, cy), 20, 6)
        pygame.draw.circle(screen, T.ORANGE, (cx, cy), 8)
        pygame.draw.line(screen, T.NAVY, (cx - 70, cy), (cx - 57, cy), 5)
        pygame.draw.line(screen, T.NAVY, (cx + 57, cy), (cx + 70, cy), 5)

        cx, cy = centers[2]
        pygame.draw.circle(screen, T.ORANGE, (cx, cy), 46, 7)
        pygame.draw.circle(screen, T.NAVY, (cx, cy), 20, 6)
        pygame.draw.circle(screen, T.GREEN, (cx, cy), 6)
        for dx, dy in ((0, -62), (0, 62), (-62, 0), (62, 0)):
            pygame.draw.line(screen, T.NAVY, (cx + dx // 2, cy + dy // 2), (cx + dx, cy + dy), 6)
