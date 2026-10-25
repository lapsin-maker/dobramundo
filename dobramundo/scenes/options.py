"""Opções: segmento de controle, calibração, superfície de exibição, som e alto contraste."""

from __future__ import annotations

from typing import Callable

import pygame

from .. import config as C
from ..content import texts
from ..input.pose import SEGMENTS
from ..persistence import CONTROL_SEGMENTS, SURFACES
from ..ui import theme as T
from . import make_scene
from .base import Scene

SEGMENT_LABELS = {"teclado": "Teclado e mouse", **{k: s.label for k, s in SEGMENTS.items()}}
SURFACE_LABELS = {"monitor": "Monitor", "parede": "Parede", "mesa": "Mesa", "chao": "Chão (T-TEA)"}
SURFACE_HINT = {
    "monitor": "qualquer segmento",
    "parede": "tronco ou cabeça",
    "mesa": "uma das mãos",
    "chao": "pés, em pé sobre a projeção",
}
ROW_H = 56
GAP = 10


class OptionsScene(Scene):
    def build(self) -> None:
        o = self.app.options
        profile = self.app.profile
        left, right = 24, 566
        width = 510
        buttons = []

        def stepper(x: int, y: int, key: str, label: str, value: str, minus: Callable, plus: Callable) -> None:
            buttons.append(self.button((x, y, 64, ROW_H), "<", minus, key=f"{key}-"))
            buttons.append(
                self.button(
                    (x + 72, y, width - 144, ROW_H), value, plus, sublabel=label, size=T.SIZES["body"], key=f"{key}="
                )
            )
            buttons.append(self.button((x + width - 64, y, 64, ROW_H), ">", plus, key=f"{key}+"))

        def toggle(x: int, y: int, key: str, label: str, on: bool, action: Callable) -> None:
            buttons.append(
                self.button(
                    (x, y, width, ROW_H),
                    f"{label}: {'sim' if on else 'não'}",
                    action,
                    selected=on,
                    size=T.SIZES["body"],
                    key=key,
                )
            )

        y = 128
        index = CONTROL_SEGMENTS.index(profile.controle)
        stepper(
            left,
            y,
            "seg",
            "Segmento de controle",
            SEGMENT_LABELS[profile.controle],
            lambda: self.set_segment(index - 1),
            lambda: self.set_segment(index + 1),
        )
        y += ROW_H + GAP
        buttons.append(
            self.button(
                (left, y, width, ROW_H),
                texts.UI["calibrar"],
                self.calibrate,
                enabled=profile.controle != "teclado",
                size=T.SIZES["body"],
                key="calibrar",
                sublabel="Posição neutra do segmento",
            )
        )
        y += ROW_H + GAP
        stepper(
            left,
            y,
            "sens",
            "Sensibilidade (alcance do movimento)",
            f"{o.sensibilidade:.1f}x",
            lambda: self.adjust("sensibilidade", -0.1, 0.5, 2.0),
            lambda: self.adjust("sensibilidade", 0.1, 0.5, 2.0),
        )
        y += ROW_H + GAP
        stepper(
            left,
            y,
            "perm",
            "Tempo de permanência nos botões",
            f"{o.permanencia:.1f} s",
            lambda: self.adjust("permanencia", -0.2, 0.6, 3.0),
            lambda: self.adjust("permanencia", 0.2, 0.6, 3.0),
        )
        y += ROW_H + GAP
        s_index = SURFACES.index(o.superficie)
        stepper(
            left,
            y,
            "sup",
            f"Superfície (sugestão: {SURFACE_HINT[o.superficie]})",
            SURFACE_LABELS[o.superficie],
            lambda: self.set_surface(s_index - 1),
            lambda: self.set_surface(s_index + 1),
        )
        y += ROW_H + GAP
        half = (width - GAP) // 2
        buttons.append(
            self.button(
                (left, y, half, ROW_H),
                f"Espelhar: {'sim' if o.espelhar else 'não'}",
                lambda: self.flip("espelhar"),
                selected=o.espelhar,
                size=T.SIZES["body"],
                key="esp",
            )
        )
        buttons.append(
            self.button(
                (left + half + GAP, y, half, ROW_H),
                f"Girar 180°: {'sim' if o.girar else 'não'}",
                lambda: self.flip("girar"),
                selected=o.girar,
                size=T.SIZES["body"],
                key="gir",
            )
        )
        y = 128
        for key, label in (
            ("volume_geral", "Volume geral"),
            ("volume_musica", "Música"),
            ("volume_efeitos", "Efeitos"),
        ):
            value = getattr(o, key)
            stepper(
                right,
                y,
                key,
                label,
                f"{int(round(value * 100))}%",
                (lambda k=key: self.adjust(k, -0.1, 0.0, 1.0)),
                (lambda k=key: self.adjust(k, 0.1, 0.0, 1.0)),
            )
            y += ROW_H + GAP
        toggle(right, y, "silencio", texts.UI["silencio"], o.silencio, lambda: self.flip("silencio"))
        y += ROW_H + GAP
        toggle(right, y, "contraste", texts.UI["alto_contraste"], o.alto_contraste, lambda: self.flip("alto_contraste"))
        y += ROW_H + GAP
        toggle(right, y, "tela", "Tela cheia (F11)", o.tela_cheia, self.fullscreen)
        buttons.append(self.button((24, 570, 300, 64), texts.UI["voltar"], lambda: self.goto("vila"), key="voltar"))
        buttons.append(self.button((340, 570, 300, 64), "Ver a abertura", self.intro, key="abertura"))
        self.menu.set_buttons(buttons)

    # ------------------------------------------------------------ ações
    def changed(self) -> None:
        self.app.apply_options()
        self.app.save()
        self.build()

    def set_segment(self, index: int) -> None:
        self.app.profile.controle = CONTROL_SEGMENTS[index % len(CONTROL_SEGMENTS)]
        self.changed()

    def set_surface(self, index: int) -> None:
        self.app.options.superficie = SURFACES[index % len(SURFACES)]
        self.changed()

    def adjust(self, name: str, step: float, low: float, high: float) -> None:
        o = self.app.options
        setattr(o, name, round(max(low, min(high, getattr(o, name) + step)), 2))
        self.changed()
        if name.startswith("volume"):
            self.app.audio.play("sfx_foco")

    def flip(self, name: str) -> None:
        o = self.app.options
        setattr(o, name, not getattr(o, name))
        self.changed()

    def fullscreen(self) -> None:
        self.app.options.tela_cheia = not self.app.options.tela_cheia
        self.app.toggle_fullscreen()
        self.changed()

    def calibrate(self) -> None:
        self.goto("calibracao", return_to=make_scene(self.app, "opcoes"))

    def intro(self) -> None:
        self.goto("abertura")

    def draw(self, screen: pygame.Surface) -> None:
        self.app.backdrop(screen, self.last_dt, None, 50.0)
        T.veil(screen, (10, 18, 40), 140)
        self.title(screen, texts.UI["opcoes"], "Ajustes para o supervisor e para a criança")
        self.text.blit(screen, "Controle e superfície", (24, 92), T.SIZES["label"], T.WHITE, True)
        self.text.blit(screen, "Som e visão", (566, 92), T.SIZES["label"], T.WHITE, True)
        self.draw_menu(screen)
        body = self.app.input.body
        if body is not None and body.error:
            self.text.blit(
                screen, f"Câmera: {body.error}", (C.WIDTH - 24, 590), T.SIZES["small"], T.SUN, True, "topright"
            )
