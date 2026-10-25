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
ROW_H = 52
GAP = 8
# Superfície -> segmento sugerido (aplicado quando a câmera já está em uso).
SURFACE_SEGMENT = {"chao": "pes", "mesa": "mao_direita", "parede": "tronco_pe"}


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

        def toggle(x: int, y: int, key: str, label: str, on: bool, action: Callable, w: int = width) -> None:
            buttons.append(
                self.button(
                    (x, y, w, ROW_H),
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
        half = (width - GAP) // 2
        buttons.append(
            self.button(
                (left, y, half, ROW_H),
                texts.UI["calibrar"],
                self.calibrate,
                enabled=profile.controle != "teclado",
                size=T.SIZES["body"],
                key="calibrar",
                sublabel="Posição neutra",
            )
        )
        buttons.append(
            self.button(
                (left + half + GAP, y, half, ROW_H),
                "Posição" if o.controle_posicao else "Velocidade",
                lambda: self.flip("controle_posicao"),
                selected=o.controle_posicao,
                size=T.SIZES["body"],
                key="posicao",
                sublabel="Controle do avião",
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
            lambda: self.adjust("permanencia", -0.25, 1.0, 3.5),
            lambda: self.adjust("permanencia", 0.25, 1.0, 3.5),
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
        desktop = self.app.platform == "desktop"  # no console, a projeção é do próprio console
        buttons.append(
            self.button(
                (left, y, half, ROW_H),
                "Projeção e chão",
                lambda: self.goto("projecao"),
                enabled=desktop,
                size=T.SIZES["body"],
                key="projecao",
                sublabel=f"Girar {o.rotacao}°" + (", espelhada" if o.espelhar else ""),
            )
        )
        toggle(
            left + half + GAP,
            y,
            "centralizar",
            "Centrar sozinho",
            o.centralizar_sozinho,
            lambda: self.flip("centralizar_sozinho"),
            half,
        )
        y += ROW_H + GAP
        toggle(left, y, "foco", "Momento de foco (câmera lenta)", o.momento_foco, lambda: self.flip("momento_foco"))
        y = 128
        for key, label in (
            ("volume_geral", "Volume geral"),
            ("volume_musica", "Música"),
            ("volume_efeitos", "Efeitos"),
        ):
            value = vars(o)[key]
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
        toggle(right, y, "silencio", texts.UI["silencio"], o.silencio, lambda: self.flip("silencio"), half)
        if desktop:
            toggle(right + half + GAP, y, "tela", "Tela cheia", o.tela_cheia, self.fullscreen, half)
        y += ROW_H + GAP
        toggle(right, y, "contraste", texts.UI["alto_contraste"], o.alto_contraste, lambda: self.flip("alto_contraste"))
        y += ROW_H + GAP
        toggle(
            right, y, "inverter", "Trocar cima/baixo", o.inverter_vertical, lambda: self.flip("inverter_vertical"), half
        )
        toggle(
            right + half + GAP,
            y,
            "inverter_lados",
            "Trocar lados",
            o.inverter_horizontal,
            lambda: self.flip("inverter_horizontal"),
            half,
        )
        y += ROW_H + GAP
        toggle(
            right,
            y,
            "efeitos",
            "Efeitos fortes (clarão, tremor)",
            o.efeitos_fortes,
            lambda: self.flip("efeitos_fortes"),
        )
        buttons.append(self.button((24, 570, 132, 64), texts.UI["voltar"], lambda: self.goto("vila"), key="voltar"))
        buttons.append(self.button((164, 570, 154, 64), "Ver história", self.intro, key="abertura"))
        buttons.append(self.button((326, 570, 164, 64), "Rever treino", self.replay_tutorial, key="treino"))
        toggle(
            498, 570, "movimento", "Movimento reduzido", o.reduzir_movimento,
            lambda: self.flip("reduzir_movimento"), 282,
        )
        toggle(
            788, 570, "auto_abertura", "Abertura automática", o.abertura_automatica,
            lambda: self.flip("abertura_automatica"), 288,
        )
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
        """Troca a superfície; com a câmera em uso, já aplica o segmento sugerido para ela."""
        surface = SURFACES[index % len(SURFACES)]
        self.app.options.superficie = surface
        suggested = SURFACE_SEGMENT.get(surface)
        profile = self.app.profile
        if suggested and profile.controle != "teclado" and profile.controle != suggested:
            profile.controle = suggested
            self.toast.show(f"Segmento ajustado para {SEGMENT_LABELS[suggested]} ({SURFACE_LABELS[surface]})")
        self.changed()

    def adjust(self, name: str, step: float, low: float, high: float) -> None:
        o = self.app.options
        setattr(o, name, round(max(low, min(high, vars(o)[name] + step)), 2))
        self.changed()
        if name.startswith("volume"):
            self.app.audio.play("sfx_foco")

    def flip(self, name: str) -> None:
        o = self.app.options
        setattr(o, name, not vars(o)[name])
        self.changed()

    def fullscreen(self) -> None:
        self.app.options.tela_cheia = not self.app.options.tela_cheia
        self.app.toggle_fullscreen()
        self.changed()

    def calibrate(self) -> None:
        self.goto("calibracao", return_to=make_scene(self.app, "opcoes"))

    def intro(self) -> None:
        self.goto("abertura")

    def replay_tutorial(self) -> None:
        return_to = make_scene(self.app, "opcoes")
        self.goto("tutorial", next_scene=return_to, return_to=make_scene(self.app, "opcoes"))

    def draw(self, screen: pygame.Surface) -> None:
        self.app.backdrop(screen, self.last_dt, None, 50.0)
        T.veil(screen, (10, 18, 40), 140)
        self.title(screen, texts.UI["opcoes"], "Ajustes para o supervisor e para a criança")
        self.text.blit(screen, "Controle e superfície", (24, 92), T.SIZES["label"], T.WHITE, True)
        self.text.blit(screen, "Som e visão", (566, 92), T.SIZES["label"], T.WHITE, True)
        self.draw_menu(screen)
        self.toast.draw(screen, self.text, (C.WIDTH // 2 + 160, 604), 560)
        body = self.app.input.body
        if body is not None and body.error:
            self.text.blit(
                screen, f"Câmera: {body.error}", (C.WIDTH - 24, 590), T.SIZES["small"], T.SUN, True, "topright"
            )
