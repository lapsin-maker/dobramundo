"""Opções: segmento de controle, calibração, superfície de exibição, som e alto contraste."""

from __future__ import annotations

from typing import Callable

import pygame

from .. import config as C
from ..content import texts
from ..input.api import SEGMENTS
from ..persistence import CONTROL_SEGMENTS, SURFACES
from ..ui import theme as T
from .base import Scene

SEGMENT_LABELS = {"teclado": "Teclado e mouse", **{k: s.label for k, s in SEGMENTS.items()}}
SURFACE_LABELS = {"monitor": "Monitor", "parede": "Parede", "mesa": "Mesa", "chao": "Chão (T-TEA)"}
SURFACE_HINT = {
    "monitor": "qualquer segmento",
    "parede": "tronco ou cabeça",
    "mesa": "uma das mãos",
    "chao": "pés, em pé sobre a projeção",
}
ROW_H = 48
GAP = 6
SECTION_H = 54
PAGE_ROW_H = 56
PAGE_GAP = 10
OPTION_PAGES = (
    ("controle", "Controle", "plane"),
    ("superficie", "Superfície", "map"),
    ("som", "Som", "sound"),
    ("acessibilidade", "Acessibilidade", "accessibility"),
)
# Superfície -> segmento sugerido (aplicado quando a câmera já está em uso).
SURFACE_SEGMENT = {"chao": "pes", "mesa": "mao_direita", "parede": "tronco_pe"}


class OptionsScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.section = "controle"

    def build(self) -> None:
        buttons = []
        self._build_controls(buttons)
        self._build_surface(buttons)
        self._build_audio(buttons)
        self._build_accessibility(buttons)
        self._build_footer(buttons)
        self._add_comfort_options(buttons)
        self._section_buttons = []
        tab_gap = 10
        tab_w = (C.WIDTH - 48 - tab_gap * 3) // 4
        for index, (key, label, icon_name) in enumerate(OPTION_PAGES):
            fitted_label, label_size = T.fit_text(
                self.text, label, tab_w - 64, size=T.SIZES["body"], minimum=T.SIZES["small"], bold=True
            )
            self._section_buttons.append(
                self.button(
                    (24 + index * (tab_w + tab_gap), 92, tab_w, SECTION_H),
                    fitted_label,
                    lambda section=key: self.select_section(section),
                    icon=T.icon_surface(icon_name, 34, T.TEAL if key == self.section else T.NAVY),
                    selected=key == self.section,
                    size=label_size,
                    key=f"section:{key}",
                )
            )
        controls, footer = self._partition_buttons(buttons)
        self._arrange_page(controls)
        visible_controls = [button for group in controls.values() for button in group]
        self.menu.set_buttons([*self._section_buttons, *visible_controls, *footer])

    def _add_comfort_options(self, buttons) -> None:
        o = self.app.options
        self._toggle(
            buttons,
            24,
            562,
            "movimento",
            "Movimento reduzido",
            o.reduzir_movimento,
            lambda: self.flip("reduzir_movimento"),
            510,
        )
        self._toggle(
            buttons,
            566,
            562,
            "auto_abertura",
            "Abertura automática",
            o.abertura_automatica,
            lambda: self.flip("abertura_automatica"),
            510,
        )

    @staticmethod
    def _unit_for_key(key: str) -> str:
        prefixes = (
            "seg",
            "sens",
            "perm_editor",
            "perm",
            "sup",
            "volume_geral",
            "volume_musica",
            "volume_efeitos",
            "escala_contraste",
        )
        for prefix in prefixes:
            if key.startswith(prefix):
                return prefix
        return key

    def _partition_buttons(self, buttons):
        page_for = {
            "seg": "controle",
            "calibrar": "controle",
            "posicao": "controle",
            "sens": "controle",
            "perm": "controle",
            "perm_editor": "controle",
            "sup": "superficie",
            "projecao": "superficie",
            "centralizar": "superficie",
            "foco": "superficie",
            "volume_geral": "som",
            "volume_musica": "som",
            "volume_efeitos": "som",
            "silencio": "som",
            "tela": "som",
            "contraste": "acessibilidade",
            "escala_contraste": "acessibilidade",
            "inverter": "acessibilidade",
            "inverter_lados": "acessibilidade",
            "efeitos": "acessibilidade",
            "movimento": "acessibilidade",
            "auto_abertura": "acessibilidade",
        }
        grouped = {name: {} for name, _, _ in OPTION_PAGES}
        footer = []
        for button in buttons:
            if button.key in {"voltar", "abertura", "treino", "dwell_treino", "preparar"}:
                footer.append(button)
                continue
            unit = self._unit_for_key(button.key)
            page = page_for.get(unit)
            if page is not None:
                grouped[page].setdefault(unit, []).append(button)
        return grouped[self.section], footer

    def _arrange_page(self, units) -> None:
        rows = {
            "controle": [
                (("seg", 2),),
                (("calibrar", 1), ("posicao", 1)),
                (("sens", 2),),
                (("perm", 1), ("perm_editor", 1)),
            ],
            "superficie": [(("sup", 2),), (("projecao", 1), ("centralizar", 1)), (("foco", 2),)],
            "som": [
                (("volume_geral", 2),),
                (("volume_musica", 2),),
                (("volume_efeitos", 2),),
                (("silencio", 1), ("tela", 1)),
            ],
            "acessibilidade": [
                (("contraste", 1), ("escala_contraste", 1)),
                (("inverter", 1), ("inverter_lados", 1)),
                (("efeitos", 2),),
                (("movimento", 1), ("auto_abertura", 1)),
            ],
        }[self.section]
        full_w = C.WIDTH - 48
        half_w = (full_w - GAP) // 2
        y = 165
        for row in rows:
            for unit_key, span in row:
                group = units.get(unit_key, [])
                if not group:
                    continue
                width = full_w if span == 2 else half_w
                x = 24 if span == 2 or len(row) == 1 else 24 + (0 if row.index((unit_key, span)) == 0 else half_w + GAP)
                if len(group) == 3:
                    arrow = min(48, max(38, width // 5))
                    group[0].rect = pygame.Rect(x, y, arrow, PAGE_ROW_H)
                    group[1].rect = pygame.Rect(x + arrow + 4, y, width - 2 * arrow - 8, PAGE_ROW_H)
                    group[2].rect = pygame.Rect(x + width - arrow, y, arrow, PAGE_ROW_H)
                else:
                    group[0].rect = pygame.Rect(x, y, width, PAGE_ROW_H)
            y += PAGE_ROW_H + PAGE_GAP

    def select_section(self, section: str) -> None:
        if section in {key for key, _, _ in OPTION_PAGES}:
            self.section = section
            self.build()

    def _stepper(
        self, buttons, x: int, y: int, key: str, label: str, value: str, minus: Callable, plus: Callable, w: int = 510
    ) -> None:
        arrow = min(48, max(38, w // 5))
        buttons.append(self.button((x, y, arrow, ROW_H), "<", minus, key=f"{key}-"))
        buttons.append(
            self.button(
                (x + arrow + 4, y, w - 2 * arrow - 8, ROW_H),
                value,
                plus,
                sublabel=label,
                size=T.SIZES["body"],
                key=f"{key}=",
            )
        )
        buttons.append(self.button((x + w - arrow, y, arrow, ROW_H), ">", plus, key=f"{key}+"))

    def _toggle(self, buttons, x: int, y: int, key: str, label: str, on: bool, action: Callable, w: int = 510) -> None:
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

    def _build_controls(self, buttons) -> None:
        o = self.app.options
        left, width = 24, 510
        half = (width - GAP) // 2
        profile = self.app.profile
        y = 128
        index = CONTROL_SEGMENTS.index(profile.controle)
        self._stepper(
            buttons,
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
        self._stepper(
            buttons,
            left,
            y,
            "sens",
            "Sensibilidade (alcance do movimento)",
            f"{o.sensibilidade:.1f}x",
            lambda: self.adjust("sensibilidade", -0.1, 0.5, 2.0),
            lambda: self.adjust("sensibilidade", 0.1, 0.5, 2.0),
        )
        y += ROW_H + GAP
        self._stepper(
            buttons,
            left,
            y,
            "perm",
            "Geral",
            f"{o.permanencia:.1f}s",
            lambda: self.adjust("permanencia", -0.25, 1.0, 3.5),
            lambda: self.adjust("permanencia", 0.25, 1.0, 3.5),
            half,
        )
        self._stepper(
            buttons,
            left + half + GAP,
            y,
            "perm_editor",
            "Personalização",
            f"{o.permanencia_editor:.1f}s",
            lambda: self.adjust("permanencia_editor", -0.25, 1.0, 5.0),
            lambda: self.adjust("permanencia_editor", 0.25, 1.0, 5.0),
            half,
        )
        y += ROW_H + GAP

    def _build_surface(self, buttons) -> None:
        o = self.app.options
        left, width = 24, 510
        half = (width - GAP) // 2
        y = 128 + 4 * (ROW_H + GAP)
        s_index = SURFACES.index(o.superficie)
        self._stepper(
            buttons,
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
        self._toggle(
            buttons,
            left + half + GAP,
            y,
            "centralizar",
            "Recentralizar",
            o.centralizar_sozinho,
            lambda: self.flip("centralizar_sozinho"),
            half,
        )
        y += ROW_H + GAP
        self._toggle(
            buttons,
            left,
            y,
            "foco",
            "Momento de foco (câmera lenta)",
            o.momento_foco,
            lambda: self.flip("momento_foco"),
        )

    def _build_audio(self, buttons) -> None:
        o = self.app.options
        right, width = 566, 510
        half = (width - GAP) // 2
        desktop = self.app.platform == "desktop"
        y = 128
        for key, label in (
            ("volume_geral", "Volume geral"),
            ("volume_musica", "Música"),
            ("volume_efeitos", "Efeitos"),
        ):
            value = vars(o)[key]
            self._stepper(
                buttons,
                right,
                y,
                key,
                label,
                f"{int(round(value * 100))}%",
                (lambda k=key: self.adjust(k, -0.1, 0.0, 1.0)),
                (lambda k=key: self.adjust(k, 0.1, 0.0, 1.0)),
            )
            y += ROW_H + GAP
        self._toggle(
            buttons, right, y, "silencio", texts.UI["silencio"], o.silencio, lambda: self.flip("silencio"), half
        )
        if desktop:
            self._toggle(buttons, right + half + GAP, y, "tela", "Tela cheia", o.tela_cheia, self.fullscreen, half)
        y += ROW_H + GAP

    def _build_accessibility(self, buttons) -> None:
        o = self.app.options
        right, width = 566, 510
        half = (width - GAP) // 2
        y = 128 + 4 * (ROW_H + GAP)
        self._toggle(
            buttons,
            right,
            y,
            "contraste",
            texts.UI["alto_contraste"],
            o.alto_contraste,
            lambda: self.flip("alto_contraste"),
            half,
        )
        self._stepper(
            buttons,
            right + half + GAP,
            y,
            "escala_contraste",
            "Escala de contraste",
            f"{o.escala_contraste:.1f}x",
            lambda: self.adjust("escala_contraste", -0.1, 1.0, 1.6),
            lambda: self.adjust("escala_contraste", 0.1, 1.0, 1.6),
            half,
        )
        y += ROW_H + GAP
        self._toggle(
            buttons,
            right,
            y,
            "inverter",
            "Trocar cima/baixo",
            o.inverter_vertical,
            lambda: self.flip("inverter_vertical"),
            half,
        )
        self._toggle(
            buttons,
            right + half + GAP,
            y,
            "inverter_lados",
            "Trocar lados",
            o.inverter_horizontal,
            lambda: self.flip("inverter_horizontal"),
            half,
        )
        y += ROW_H + GAP
        self._toggle(
            buttons,
            right,
            y,
            "efeitos",
            "Efeitos fortes (clarão, tremor)",
            o.efeitos_fortes,
            lambda: self.flip("efeitos_fortes"),
        )

    def _build_footer(self, buttons) -> None:
        footer = (
            (texts.UI["voltar"], lambda: self.goto("vila"), "voltar"),
            ("História", self.intro, "abertura"),
            ("Rever voo", self.replay_tutorial, "treino"),
            ("Mirar", self.replay_dwell, "dwell_treino"),
            ("Preparar", self.prepare, "preparar"),
        )
        footer_y = 536
        footer_width = (C.WIDTH - 48 - 4 * 10) // 5
        for index, (label, action, key) in enumerate(footer):
            buttons.append(
                self.button(
                    (24 + index * (footer_width + 10), footer_y, footer_width, 56),
                    label,
                    action,
                    key=key,
                    icon=T.icon_surface("stabilizer", 28, T.GREEN) if key == "preparar" else None,
                )
            )

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
        self.goto("calibracao", return_to=self.app.create_scene("opcoes"))

    def intro(self) -> None:
        self.goto("abertura")

    def replay_tutorial(self) -> None:
        return_to = self.app.create_scene("opcoes")
        self.goto("tutorial", next_scene=return_to, return_to=self.app.create_scene("opcoes"))

    def replay_dwell(self) -> None:
        return_to = self.app.create_scene("opcoes")
        self.goto("dwell_treino", next_scene=return_to, return_to=self.app.create_scene("opcoes"))

    def prepare(self) -> None:
        self.goto("preparar")

    def draw(self, screen: pygame.Surface) -> None:
        self.app.backdrop(screen, self.last_dt, None, 50.0)
        T.veil(screen, (10, 18, 40), 140)
        self.title(screen, texts.UI["opcoes"], "Ajustes para o supervisor e para a criança")
        self.draw_menu(screen)
        self.toast.draw(screen, self.text, (C.WIDTH // 2, 492), 560)
        body = self.app.input.body
        if body is not None and body.error:
            self.text.blit(
                screen, f"Câmera: {body.error}", (C.WIDTH - 24, 590), T.SIZES["small"], T.SUN, True, "topright"
            )
