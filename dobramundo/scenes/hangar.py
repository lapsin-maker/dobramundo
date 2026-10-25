"""Hangar pictórico: escolha por cartões grandes, com paleta e padrões paginados."""

from __future__ import annotations

import math

import pygame

from .. import config as C
from ..content import texts
from ..content.planes import (
    FREE_PATTERNS,
    PATTERN_PRICES,
    PLANE_COLORS,
    PLANE_MODELS,
    PLANE_PATTERNS,
    color_label,
    pattern_label,
)
from ..ui import theme as T
from ..ui.widgets import grid
from ..util import points_text
from .base import Scene

TABS = (("modelo", "Aviões"), ("cor", "Cores"), ("padrao", "Padrões"))
AREA = pygame.Rect(560, 150, 516, 400)
MODELS_PER_PAGE = 3
PATTERNS_PER_PAGE = 9


def _control_icon(kind: str, size: int = 36, color=(23, 82, 125)) -> pygame.Surface:
    image = pygame.Surface((size, size), pygame.SRCALPHA)
    center = size // 2
    pygame.draw.circle(image, (255, 255, 250), (center, center), size // 2 - 1)
    pygame.draw.circle(image, color, (center, center), size // 2 - 1, max(2, size // 14))
    width = max(3, size // 8)
    if kind == "up":
        points = [
            (center, size * 0.18),
            (size * 0.78, size * 0.48),
            (size * 0.61, size * 0.48),
            (size * 0.61, size * 0.78),
            (size * 0.39, size * 0.78),
            (size * 0.39, size * 0.48),
            (size * 0.22, size * 0.48),
        ]
        pygame.draw.polygon(image, color, points)
    else:
        pygame.draw.line(image, color, (size * 0.28, center), (size * 0.72, center), width)
        pygame.draw.polygon(
            image,
            color,
            [(size * 0.18, center), (size * 0.43, center - size * 0.2), (size * 0.43, center + size * 0.2)],
        )
        pygame.draw.polygon(
            image,
            color,
            [(size * 0.82, center), (size * 0.57, center - size * 0.2), (size * 0.57, center + size * 0.2)],
        )
    return image


class HangarScene(Scene):
    """Hangar de aparência; o tempo mais lento e a trava do menu evitam dupla escolha."""

    editor_dwell = True

    def __init__(self, app, tab: str = "modelo") -> None:
        super().__init__(app)
        self.tab = tab
        model_index = next((i for i, (key, _) in enumerate(PLANE_MODELS) if key == app.profile.aviao), 0)
        pattern_index = next(
            (i for i, (key, _) in enumerate(PLANE_PATTERNS) if key == app.profile.plane_pattern(app.profile.aviao)), 0
        )
        self.model_page = model_index // MODELS_PER_PAGE
        self.pattern_page = pattern_index // PATTERNS_PER_PAGE

    @property
    def plane(self) -> str:
        return self.app.profile.aviao

    def build(self) -> None:
        app = self.app
        profile = app.profile
        buttons = [
            self.button(
                (560 + i * 176, 86, 164, 52),
                label,
                (lambda k=key: self.set_tab(k)),
                selected=self.tab == key,
                key=f"tab_{key}",
                size=T.SIZES["body"],
                icon=T.icon_surface({"modelo": "paper", "cor": "palette", "padrao": "pattern"}[key], 30, T.NAVY),
            )
            for i, (key, label) in enumerate(TABS)
        ]
        if self.tab == "modelo":
            start = self.model_page * MODELS_PER_PAGE
            page_models = PLANE_MODELS[start : start + MODELS_PER_PAGE]
            cells = grid(AREA, len(page_models), 1, 10, row_height=118)
            for (key, _label), rect in zip(page_models, cells):
                buttons.append(
                    self.button(
                        rect,
                        "",
                        lambda k=key: self.choose_plane(k),
                        selected=key == self.plane,
                        key=f"aviao_{key}",
                    )
                )
            self._add_pager(buttons, self.model_page, math.ceil(len(PLANE_MODELS) / MODELS_PER_PAGE), "modelo")
        elif self.tab == "cor":
            cells = grid(AREA, len(PLANE_COLORS), 3, 8, row_height=72)
            current = profile.plane_color(self.plane)
            for (key, label, color), rect in zip(PLANE_COLORS, cells):
                buttons.append(
                    self.button(
                        rect,
                        label,
                        lambda k=key: self.choose_color(k),
                        size=T.SIZES["small"],
                        swatch=color or (245, 245, 240),
                        selected=key == current,
                        key=f"cor_{key}",
                    )
                )
        else:
            current = profile.plane_pattern(self.plane)
            start = self.pattern_page * PATTERNS_PER_PAGE
            page_patterns = PLANE_PATTERNS[start : start + PATTERNS_PER_PAGE]
            cells = grid(AREA, len(page_patterns), 3, 10, row_height=126)
            for (key, _label), rect in zip(page_patterns, cells):
                buttons.append(
                    self.button(
                        rect,
                        "",
                        lambda k=key: self.choose_pattern(k),
                        selected=key == current,
                        key=f"padrao_{key}",
                    )
                )
            self._add_pager(buttons, self.pattern_page, math.ceil(len(PLANE_PATTERNS) / PATTERNS_PER_PAGE), "padrao")
        buttons.append(self.button((24, 570, 300, 64), texts.UI["voltar"], lambda: self.goto("vila"), key="voltar"))
        self.menu.set_buttons(buttons)

    def _add_pager(self, buttons, page: int, total: int, tab: str) -> None:
        if page > 0:
            buttons.append(
                self.button((560, 560, 184, 58), "Anterior", lambda: self.change_page(tab, -1), key="pagina_ant")
            )
        if page + 1 < total:
            buttons.append(
                self.button((892, 560, 184, 58), "Próximos", lambda: self.change_page(tab, 1), key="pagina_prox")
            )

    def change_page(self, tab: str, step: int) -> None:
        if tab == "modelo":
            self.model_page = max(0, min(math.ceil(len(PLANE_MODELS) / MODELS_PER_PAGE) - 1, self.model_page + step))
        else:
            self.pattern_page = max(
                0, min(math.ceil(len(PLANE_PATTERNS) / PATTERNS_PER_PAGE) - 1, self.pattern_page + step)
            )
        self.build()

    def set_tab(self, tab: str) -> None:
        self.tab = tab
        self.build()

    def say(self, text: str) -> None:
        self.toast.show(text)

    def choose_plane(self, key: str) -> None:
        self.app.profile.aviao = key
        selected_index = next((i for i, (model, _) in enumerate(PLANE_MODELS) if model == key), 0)
        self.model_page = selected_index // MODELS_PER_PAGE
        pattern_index = next(
            (i for i, (pattern, _) in enumerate(PLANE_PATTERNS) if pattern == self.app.profile.plane_pattern(key)), 0
        )
        self.pattern_page = pattern_index // PATTERNS_PER_PAGE
        self.app.save()
        self.build()

    def choose_color(self, key: str) -> None:
        profile = self.app.profile
        profile.cores[self.plane] = key
        profile.padroes[self.plane] = "liso"
        self.pattern_page = 0
        self.app.save()
        self.build()

    def choose_pattern(self, key: str) -> None:
        profile = self.app.profile
        if key not in profile.owned_patterns and key not in FREE_PATTERNS:
            price = PATTERN_PRICES[key]
            if profile.pontos < price:
                self.say(f"Faltam {points_text(price - profile.pontos)} pontos para {pattern_label(key)}.")
                return
            # A trava de saída por alvo permanece ativa no rebuild; manter o gasto
            # aqui atômico garante que uma escolha por permanência não cobre duas vezes.
            profile.pontos -= price
            profile.padroes_comprados.append(key)
            profile.normalize()
            self.app.audio.play("sfx_compra")
            self.say(f"{pattern_label(key)} agora é seu!")
        profile.padroes[self.plane] = key
        pattern_index = next((i for i, (pattern, _) in enumerate(PLANE_PATTERNS) if pattern == key), 0)
        self.pattern_page = pattern_index // PATTERNS_PER_PAGE
        self.app.save()
        self.build()

    # ------------------------------------------------------------ desenho
    def draw(self, screen: pygame.Surface) -> None:
        app = self.app
        profile = app.profile
        T.watercolor_backdrop(screen, "sky")
        self.title(screen, "Hangar de papel")
        wallet_box = pygame.Rect(C.WIDTH - 254, 18, 226, 50)
        T.panel(screen, wallet_box, T.PAPER, T.TEAL, 245, 15, 2)
        screen.blit(T.icon_surface("star", 34, T.TEAL), (wallet_box.left + 10, wallet_box.top + 8))
        self.text.blit(
            screen,
            f"{points_text(profile.pontos)} pontos",
            (wallet_box.left + 54, wallet_box.centery),
            T.SIZES["body"],
            T.NAVY,
            True,
            "midleft",
        )
        card = pygame.Rect(24, 84, 516, 472)
        T.panel(screen, card, T.PAPER, T.NAVY, 250, 22, 2)
        skin = app.view.skin
        color, pattern = profile.plane_color(self.plane), profile.plane_pattern(self.plane)
        menu_view = skin.surface(self.plane, "menu", color, pattern, profile.piloto)
        if menu_view is not None:
            img = self.scaled(
                menu_view, (456, 250), ("hangar", skin.look_key(self.plane, color, pattern, profile.piloto))
            )
            bob = 0.0 if app.options.reduzir_movimento else math.sin(self.time * 2.0) * 4
            screen.blit(img, img.get_rect(center=(card.centerx, card.top + 156 + bob)))
        flight_view = skin.surface(self.plane, "flight", color, pattern, profile.piloto)
        if flight_view is not None:
            img = self.scaled(
                flight_view,
                (128, 84),
                ("hangar_voo", skin.look_key(self.plane, color, pattern, profile.piloto)),
            )
            preview_rect = img.get_rect(bottomright=(card.right - 16, card.bottom - 16))
            screen.blit(img, preview_rect)
            self.text.blit(
                screen,
                "vista de voo",
                (preview_rect.centerx, preview_rect.top - 14),
                T.SIZES["small"],
                T.MUTED,
                anchor="midbottom",
            )
        name = dict(PLANE_MODELS)[self.plane]
        self.text.blit(screen, name, (card.left + 22, card.top + 294), T.SIZES["title"], T.NAVY, True)
        self.text.blit(
            screen,
            "A forma muda; o controle é o mesmo.",
            (card.left + 24, card.top + 338),
            T.SIZES["small"],
            T.MUTED,
        )
        paint = pattern_label(pattern) if pattern != "liso" else color_label(color)
        self.text.blit(screen, paint, (card.left + 24, card.top + 366), T.SIZES["body"], T.INK)
        # Pictogramas ensinam o mesmo gesto em qualquer dobradura; não atribuem
        # estatísticas diferentes a modelos que compartilham a física do jogo.
        T.panel(screen, pygame.Rect(card.left + 18, card.bottom - 68, 264, 50), (255, 255, 250), T.TEAL, 235, 14, 2)
        screen.blit(_control_icon("up", 34, T.TEAL), (card.left + 28, card.bottom - 66))
        screen.blit(_control_icon("side", 34, T.ORANGE), (card.left + 134, card.bottom - 66))
        self.text.blit(screen, "subir", (card.left + 70, card.bottom - 48), T.SIZES["small"], T.INK, anchor="midleft")
        self.text.blit(
            screen, "desviar", (card.left + 176, card.bottom - 48), T.SIZES["small"], T.INK, anchor="midleft"
        )

        self.text.blit(
            screen,
            dict(TABS)[self.tab],
            (AREA.centerx, AREA.top - 10),
            T.SIZES["label"],
            T.NAVY,
            True,
            "midbottom",
        )
        self.menu.draw(screen, self.text, self.dwell_time)
        for button in self.menu.buttons:
            if button.key.startswith("aviao_"):
                key = button.key[6:]
                base = skin.surface(key, "menu", profile.plane_color(key), profile.plane_pattern(key), None)
                if base is not None:
                    image_rect = pygame.Rect(button.rect.left + 16, button.rect.top + 8, button.rect.width - 32, 78)
                    look_key = skin.look_key(key, profile.plane_color(key), profile.plane_pattern(key), None)
                    image = self.scaled(base, image_rect.size, ("thumb", look_key, image_rect.size))
                    screen.blit(image, image.get_rect(center=image_rect.center))
                self.text.blit(
                    screen,
                    dict(PLANE_MODELS)[key],
                    (button.rect.centerx, button.rect.bottom - 8),
                    T.SIZES["small"],
                    T.NAVY,
                    True,
                    "midbottom",
                )
            elif button.key.startswith("padrao_"):
                key = button.key[7:]
                image_rect = pygame.Rect(button.rect.left + 10, button.rect.top + 8, button.rect.width - 20, 82)
                thumb = skin.thumb(key, image_rect.size)
                if thumb is not None:
                    screen.blit(thumb, image_rect)
                else:
                    self.text.blit(screen, "Liso", image_rect.center, T.SIZES["small"], T.INK, True, "center")
                label = pattern_label(key)
                if self.text.font(T.SIZES["small"], True).size(label)[0] > button.rect.width - 12:
                    label = label[:17] + "…"
                self.text.blit(
                    screen,
                    label,
                    (button.rect.centerx, button.rect.bottom - 6),
                    T.SIZES["small"],
                    T.NAVY,
                    True,
                    "midbottom",
                )
                if key not in profile.owned_patterns and key not in FREE_PATTERNS:
                    price = PATTERN_PRICES[key]
                    badge = pygame.Rect(button.rect.right - 68, button.rect.top + 8, 58, 26)
                    T.panel(screen, badge, T.PAPER, T.TEAL, 238, 10, 1)
                    self.text.blit(screen, points_text(price), badge.center, T.SIZES["small"], T.NAVY, True, "center")
        if self.tab in ("modelo", "padrao"):
            page, total = (
                (self.model_page, math.ceil(len(PLANE_MODELS) / MODELS_PER_PAGE))
                if self.tab == "modelo"
                else (self.pattern_page, math.ceil(len(PLANE_PATTERNS) / PATTERNS_PER_PAGE))
            )
            self.text.blit(
                screen,
                f"{page + 1} / {total}",
                (818, 589),
                T.SIZES["body"],
                T.NAVY,
                True,
                "center",
            )
        self.toast.draw(screen, self.text, (C.WIDTH // 2 + 120, 600))
