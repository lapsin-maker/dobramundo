"""Atalhos claros de preparação para conforto e acessibilidade."""

from __future__ import annotations

import pygame

from .. import config as C
from ..ui import theme as T
from .base import Scene


class PreparationScene(Scene):
    """Presets persistentes, calibragem e rotas rápidas para a supervisão."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self.page = "main"

    def build(self) -> None:
        if self.page == "meu_voo":
            self._build_my_flight()
            return
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
            selected = (key == "calmo" and o.reduzir_movimento and not o.efeitos_fortes) or (
                key == "visivel" and o.alto_contraste and o.escala_contraste >= 1.3
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
                    "Meu voo",
                    self.open_my_flight,
                    key="meu_voo",
                    icon=T.icon_surface("plane", 34, T.NAVY),
                ),
                self.button(
                    (744, 500, 152, 58),
                    "Mirar",
                    self.practice_selection,
                    key="mirar",
                    icon=T.icon_surface("next", 34, T.NAVY),
                ),
                self.button((929, 500, 137, 58), "Opções", self.back, key="opcoes"),
            ]
        )
        self.menu.set_buttons(buttons)

    def _build_my_flight(self) -> None:
        o = self.app.options
        durations = C.SESSION_LIMITS_S
        duration_index = durations.index(o.limite_voo_s) if o.limite_voo_s in durations else 0
        duration = durations[duration_index]
        duration_label = "Sem limite" if not duration else f"{duration // 60} minutos"
        seeds = (0,) + C.COMMUNITY_CHALLENGE_SEEDS
        seed_index = seeds.index(o.semente_desafio) if o.semente_desafio in seeds else -1
        seed = o.semente_desafio if seed_index < 0 else seeds[seed_index]
        challenge_label = (
            "Voo aleatório"
            if seed == 0
            else f"Desafio comunitário {seed_index} · semente {seed}"
            if seed_index >= 0
            else f"Semente personalizada · {seed}"
        )
        buttons = [
            self.button(
                (34, 160, 332, 230),
                duration_label,
                lambda: self.set_option("limite_voo_s", durations[(duration_index + 1) % len(durations)]),
                sublabel="Mire para escolher",
                size=T.SIZES["title"],
                key="duracao_voo",
                icon=T.icon_surface("clock", 58, T.TEAL),
            ),
            self.button(
                (384, 160, 332, 230),
                "Explorar" if o.modo_exploracao else "Com vidas",
                lambda: self.set_option("modo_exploracao", not o.modo_exploracao),
                sublabel="Sem eliminação · batidas contam" if o.modo_exploracao else "Vidas normais · 3 corações",
                size=T.SIZES["title"],
                key="exploracao",
                selected=o.modo_exploracao,
                icon=T.icon_surface("village", 58, T.GREEN if o.modo_exploracao else T.NAVY),
            ),
            self.button(
                (734, 160, 332, 230),
                "Com apoio" if o.assistencia_previsivel else "Sem apoio",
                lambda: self.set_option("assistencia_previsivel", not o.assistencia_previsivel),
                sublabel="5 vidas · proteção de 2 s" if o.assistencia_previsivel else "3 vidas · proteção de 1,25 s",
                size=T.SIZES["body"],
                key="assistencia",
                selected=o.assistencia_previsivel,
                icon=T.icon_surface("shield", 58, T.TEAL if o.assistencia_previsivel else T.NAVY),
            ),
            self.button(
                (34, 418, 700, 132),
                challenge_label,
                lambda: self.set_option("semente_desafio", seeds[(seed_index + 1) % len(seeds)]),
                sublabel="Próximo desafio · a região vem do mapa",
                size=T.SIZES["title"],
                key="desafio_comunitario",
                icon=T.icon_surface("portal", 50, T.ORANGE),
            ),
            self.button((750, 418, 316, 132), "Voltar", self.open_main, key="voltar"),
        ]
        self.menu.set_buttons(buttons)

    def set_option(self, name: str, value) -> None:
        if name == "limite_voo_s":
            self.app.options.limite_voo_s = int(value)
        elif name == "modo_exploracao":
            self.app.options.modo_exploracao = bool(value)
        elif name == "assistencia_previsivel":
            self.app.options.assistencia_previsivel = bool(value)
        elif name == "semente_desafio":
            self.app.options.semente_desafio = int(value)
        else:
            raise ValueError(f"opção de voo desconhecida: {name}")
        self._save_preset("Preferências do voo salvas")

    def open_my_flight(self) -> None:
        self.page = "meu_voo"
        self.build()

    def open_main(self) -> None:
        self.page = "main"
        self.build()

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
        self.goto("calibracao", return_to=self.app.create_scene("preparar"), guided=True)

    def practice_selection(self) -> None:
        self.goto(
            "dwell_treino",
            next_scene=self.app.create_scene("preparar"),
            return_to=self.app.create_scene("preparar"),
        )

    def draw(self, screen: pygame.Surface) -> None:
        self.app.backdrop(screen, self.last_dt, None, 20.0)
        T.veil(screen, (10, 18, 40), 150)
        if self.page == "meu_voo":
            self.title(screen, "Meu voo", "Escolhas previsíveis para esta aventura")
        else:
            self.title(screen, "Preparar", "Atalhos para ajustar a experiência")
        self.draw_menu(screen)
        if self.page == "main":
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
