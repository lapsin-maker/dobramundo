"""Hangar: escolha da dobradura (11 aviões) e da pintura (cores e padrões colecionáveis)."""

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

TABS = (("modelo", "Dobradura"), ("cor", "Cor"), ("padrao", "Padrão"))
AREA = pygame.Rect(560, 150, 516, 400)


class HangarScene(Scene):
    def __init__(self, app, tab: str = "modelo") -> None:
        super().__init__(app)
        self.tab = tab
        self.message = ""
        self.message_time = 0.0

    @property
    def plane(self) -> str:
        return self.app.profile.aviao

    def build(self) -> None:
        from .village import VillageScene

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
            )
            for i, (key, label) in enumerate(TABS)
        ]
        if self.tab == "modelo":
            cells = grid(AREA, len(PLANE_MODELS), 4, 10)
            for (key, _label), rect in zip(PLANE_MODELS, cells):
                buttons.append(
                    self.button(
                        rect, "", (lambda k=key: self.choose_plane(k)), selected=key == self.plane, key=f"aviao_{key}"
                    )
                )
        elif self.tab == "cor":
            cells = grid(AREA, len(PLANE_COLORS), 3, 10)
            current = profile.plane_color(self.plane)
            for (key, label, color), rect in zip(PLANE_COLORS, cells):
                buttons.append(
                    self.button(
                        rect,
                        label,
                        (lambda k=key: self.choose_color(k)),
                        size=T.SIZES["small"],
                        swatch=color or (245, 245, 240),
                        selected=key == current,
                        key=f"cor_{key}",
                    )
                )
        else:
            cells = grid(AREA, len(PLANE_PATTERNS), 6, 8)
            current = profile.plane_pattern(self.plane)
            for (key, _label), rect in zip(PLANE_PATTERNS, cells):
                buttons.append(
                    self.button(
                        rect, "", (lambda k=key: self.choose_pattern(k)), selected=key == current, key=f"padrao_{key}"
                    )
                )
        buttons.append(
            self.button((24, 570, 300, 64), texts.UI["voltar"], lambda: app.go(VillageScene(app)), key="voltar")
        )
        self.menu.set_buttons(buttons)

    def set_tab(self, tab: str) -> None:
        self.tab = tab
        self.build()

    def say(self, text: str) -> None:
        self.message, self.message_time = text, 3.0

    def choose_plane(self, key: str) -> None:
        self.app.profile.aviao = key
        self.app.save()
        self.build()

    def choose_color(self, key: str) -> None:
        profile = self.app.profile
        profile.cores[self.plane] = key
        profile.padroes[self.plane] = "liso"  # cor lisa: tira o padrão
        self.app.save()
        self.build()

    def choose_pattern(self, key: str) -> None:
        profile = self.app.profile
        if key not in profile.owned_patterns:
            price = PATTERN_PRICES[key]
            if profile.pontos < price:
                self.say(f"Faltam {points_text(price - profile.pontos)} pontos para {pattern_label(key)}.")
                return
            profile.pontos -= price
            profile.padroes_comprados.append(key)
            profile.normalize()
            self.app.audio.play("sfx_compra")
            self.say(f"{pattern_label(key)} agora é seu!")
        profile.padroes[self.plane] = key
        self.app.save()
        self.build()

    def back(self) -> None:
        from .village import VillageScene

        self.app.go(VillageScene(self.app))

    def update(self, dt: float) -> None:
        super().update(dt)
        self.message_time = max(0.0, self.message_time - dt)

    # ------------------------------------------------------------ desenho
    def draw(self, screen: pygame.Surface) -> None:
        app = self.app
        profile = app.profile
        app.backdrop(screen, 1 / 60, None, 40.0)
        T.veil(screen, (10, 18, 40), 120)
        self.title(screen, texts.UI["hangar"], "Escolha a dobradura e a pintura do seu avião de papel")
        wallet = f"Pontos para padrões: {points_text(profile.pontos)}"
        self.text.blit(screen, wallet, (C.WIDTH - 24, 24), T.SIZES["body"], T.NAVY, True, "topright")
        card = pygame.Rect(24, 86, 516, 470)
        T.panel(screen, card, T.PAPER, T.NAVY, 245, 22, 3)
        skin = app.view.skin
        color, pattern = profile.plane_color(self.plane), profile.plane_pattern(self.plane)
        menu_view = skin.surface(self.plane, "menu", color, pattern, profile.piloto)
        if menu_view is not None:
            img = self.scaled(
                menu_view, (460, 270), ("hangar", skin.look_key(self.plane, color, pattern, profile.piloto))
            )
            bob = math.sin(self.time * 2.0) * 6
            screen.blit(img, img.get_rect(center=(card.centerx, card.top + 170 + bob)))
        flight_view = skin.surface(self.plane, "flight", color, pattern, profile.piloto)
        if flight_view is not None:
            img = self.scaled(
                flight_view, (180, 110), ("hangar_voo", skin.look_key(self.plane, color, pattern, profile.piloto))
            )
            screen.blit(img, img.get_rect(bottomright=(card.right - 18, card.bottom - 18)))
            self.text.blit(
                screen, "em voo", (card.right - 108, card.bottom - 134), T.SIZES["small"], T.MUTED, anchor="midtop"
            )
        name = dict(PLANE_MODELS)[self.plane]
        self.text.blit(screen, name, (card.left + 24, card.top + 330), T.SIZES["title"], T.NAVY, True)
        paint = pattern_label(pattern) if pattern != "liso" else color_label(color)
        self.text.blit(screen, f"Pintura: {paint}", (card.left + 24, card.top + 378), T.SIZES["body"], T.INK)
        self.draw_menu(screen)
        for button in self.menu.buttons:
            if button.key.startswith("aviao_"):
                key = button.key[6:]
                base = skin.surface(key, "menu", profile.plane_color(key), profile.plane_pattern(key), None)
                if base is not None:
                    img = self.scaled(
                        base,
                        (button.rect.width - 16, button.rect.height - 16),
                        ("thumb", skin.look_key(key, profile.plane_color(key), profile.plane_pattern(key), None)),
                    )
                    screen.blit(img, img.get_rect(center=button.rect.center))
            elif button.key.startswith("padrao_"):
                key = button.key[7:]
                inner = button.rect.inflate(-14, -14)
                thumb = skin.thumb(key, inner.size)
                if thumb is not None:
                    screen.blit(thumb, inner)
                else:
                    self.text.blit(screen, "Liso", inner.center, T.SIZES["small"], T.INK, True, "center")
                if key not in profile.owned_patterns and key not in FREE_PATTERNS:
                    shade = pygame.Rect(inner)
                    T.panel(screen, shade, (20, 24, 36), (20, 24, 36), 150, 6, 0)
                    price = PATTERN_PRICES[key]
                    color_tag = T.SUN if profile.pontos >= price else T.WHITE
                    self.text.blit(
                        screen, points_text(price), shade.center, T.SIZES["small"], color_tag, True, "center"
                    )
        focused = self.menu.focused
        if focused is not None and focused.key.startswith("padrao_"):
            self.text.blit(
                screen,
                pattern_label(focused.key[7:]),
                (AREA.centerx, AREA.bottom + 4),
                T.SIZES["body"],
                T.WHITE,
                True,
                "midtop",
            )
        if self.message_time > 0:
            box = pygame.Rect(0, 0, 640, 54)
            box.center = (C.WIDTH // 2 + 120, 600)
            T.panel(screen, box, T.PAPER, T.ORANGE, 250, 14, 3)
            self.text.blit(screen, self.message, box.center, T.SIZES["body"], T.INK, True, "center")
