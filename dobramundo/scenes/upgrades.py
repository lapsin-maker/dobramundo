"""Cuide da vila e aprimore o avião com prévia e confirmação de compra."""

from __future__ import annotations

import pygame

from .. import config as C
from ..content import texts
from ..content.items import WASTE_TYPES
from ..content.progress import MAX_PART_LEVEL, PLANE_PARTS, VILLAGE_UPGRADES, can_afford, plane_stats
from ..engine.village_art import village_prop
from ..ui import theme as T
from .base import Scene
from .village import draw_village

PAGE_SIZE = 4
CARD_RECTS = (
    pygame.Rect(25, 150, 480, 130),
    pygame.Rect(595, 150, 480, 130),
    pygame.Rect(25, 340, 480, 130),
    pygame.Rect(595, 340, 480, 130),
)


class UpgradesScene(Scene):
    def __init__(self, app, tab: str = "vila") -> None:
        super().__init__(app)
        self.tab = tab
        self.page = 0
        self.selected_key: str | None = None
        self.reveal_key: str | None = None

    def build(self) -> None:
        profile = self.app.profile
        if self.reveal_key is not None:
            self.menu.set_buttons(
                [
                    self.button(
                        (440, 560, 220, 66),
                        "Continuar",
                        self.end_reveal,
                        color=T.GREEN,
                        key="continuar",
                        size=T.SIZES["label"],
                    ),
                ],
                keep_focus=False,
            )
            return
        buttons = [
            self.button(
                (25, 18, 145, 58),
                "Vila",
                lambda: self.set_tab("vila"),
                selected=self.tab == "vila",
                key="tab_vila",
                size=T.SIZES["label"],
            ),
            self.button(
                (235, 18, 145, 58),
                "Avião",
                lambda: self.set_tab("aviao"),
                selected=self.tab == "aviao",
                key="tab_aviao",
                size=T.SIZES["label"],
            ),
            self.button((930, 18, 145, 58), texts.UI["voltar"], lambda: self.goto("vila"), key="voltar"),
        ]
        if self.tab == "vila":
            if self.selected_key is not None:
                buttons.extend(
                    [
                        self.button(
                            (250, 560, 260, 66),
                            "Construir",
                            self.confirm_purchase,
                            color=T.GREEN,
                            key="confirmar",
                            size=T.SIZES["label"],
                        ),
                        self.button(
                            (590, 560, 260, 66),
                            "Voltar à lista",
                            self.clear_selection,
                            key="cancelar",
                            size=T.SIZES["label"],
                        ),
                    ]
                )
            else:
                pages = (len(VILLAGE_UPGRADES) + PAGE_SIZE - 1) // PAGE_SIZE
                if self.page > 0:
                    buttons.append(
                        self.button((25, 560, 180, 66), "Anterior", lambda: self.change_page(-1), key="anterior")
                    )
                if self.page + 1 < pages:
                    buttons.append(
                        self.button((285, 560, 180, 66), "Mais obras", lambda: self.change_page(1), key="proxima")
                    )
                for i, upgrade in enumerate(VILLAGE_UPGRADES[self.page * PAGE_SIZE : (self.page + 1) * PAGE_SIZE]):
                    owned = upgrade.key in profile.vila
                    buttons.append(
                        self.button(
                            CARD_RECTS[i],
                            upgrade.name,
                            (lambda key=upgrade.key: self.select_upgrade(key)),
                            sublabel="",
                            selected=owned,
                            enabled=not owned,
                            key=upgrade.key,
                            size=T.SIZES["label"],
                            align="top",
                        )
                    )
        else:
            # Melhorias de voo preservam os três upgrades e níveis atuais.
            for i, part in enumerate(PLANE_PARTS):
                level = profile.pecas.get(part.key, 0)
                rect = pygame.Rect(130, 140 + i * 170, 840, 110)
                buttons.append(
                    self.button(
                        rect,
                        part.name,
                        (lambda p=part: self.buy_part(p)),
                        sublabel=f"Nível {level} / {MAX_PART_LEVEL}",
                        selected=level >= MAX_PART_LEVEL,
                        enabled=level < MAX_PART_LEVEL,
                        key=part.key,
                        size=T.SIZES["label"],
                        align="top",
                    )
                )
        self.menu.set_buttons(buttons)

    def set_tab(self, tab: str) -> None:
        self.tab = tab
        self.selected_key = None
        self.page = 0
        self.build()

    def change_page(self, delta: int) -> None:
        pages = (len(VILLAGE_UPGRADES) + PAGE_SIZE - 1) // PAGE_SIZE
        self.page = max(0, min(pages - 1, self.page + delta))
        self.build()

    def select_upgrade(self, key: str) -> None:
        if key in self.app.profile.vila:
            return
        self.selected_key = key
        self.build()

    def clear_selection(self) -> None:
        self.selected_key = None
        self.build()

    def end_reveal(self) -> None:
        self.reveal_key = None
        self.build()

    def say(self, text: str) -> None:
        self.toast.show(text)

    def pay(self, cost: dict) -> bool:
        wallet = self.app.profile.recursos
        if not can_afford(wallet, cost):
            self.say("Faltam recursos. Faça outro voo para coletar mais.")
            return False
        for key, amount in cost.items():
            wallet[key] -= amount
        self.app.audio.play("sfx_compra")
        return True

    def confirm_purchase(self) -> None:
        key = self.selected_key
        upgrade = next((item for item in VILLAGE_UPGRADES if item.key == key), None)
        if upgrade is None or key in self.app.profile.vila:
            self.clear_selection()
            return
        if not self.pay(upgrade.cost):
            return
        self.app.profile.vila.append(upgrade.key)
        self.app.profile.normalize()
        self.app.save()
        self.selected_key = None
        self.reveal_key = upgrade.key
        self.say(f"{upgrade.name} construída!")
        self.build()

    # Compatibilidade para chamadas de domínio já usadas por outros fluxos/testes.
    def buy_village(self, upgrade) -> None:
        if upgrade.key in self.app.profile.vila or not self.pay(upgrade.cost):
            return
        self.app.profile.vila.append(upgrade.key)
        self.app.profile.normalize()
        self.app.save()
        self.selected_key = None
        self.say(f"{upgrade.name} construída!")
        self.build()

    def buy_part(self, part) -> None:
        level = self.app.profile.pecas.get(part.key, 0)
        if level >= MAX_PART_LEVEL or not self.pay(part.level_costs[level]):
            if level >= MAX_PART_LEVEL:
                self.say("Essa peça já está no nível máximo.")
            return
        self.app.profile.pecas[part.key] = level + 1
        self.app.save()
        self.app.apply_options()  # a quilha muda a zona morta do controle corporal
        self.say(f"{part.name} instalada!")
        self.build()

    def _draw_cost_icons(self, screen: pygame.Surface, cost: dict, pos) -> None:
        x, y = pos
        wallet = self.app.profile.recursos
        for waste in WASTE_TYPES:
            amount = cost.get(waste.key)
            if not amount:
                continue
            icon = self.app.assets.sprite("waste_sprites", waste.sprite)
            rect = pygame.Rect(x, y, 34, 34)
            if icon is not None:
                screen.blit(self.scaled(icon, rect.size), rect)
            else:
                pygame.draw.circle(screen, waste.color, rect.center, 15)
                pygame.draw.circle(screen, T.INK, rect.center, 15, 2)
            self.text.blit(
                screen,
                f"{wallet.get(waste.key, 0)}/{amount}",
                (x + 40, y + 6),
                T.SIZES["body"],
                T.INK if wallet.get(waste.key, 0) >= amount else T.RED,
                True,
            )
            x += 132

    def _draw_village_list(self, screen: pygame.Surface) -> None:
        profile = self.app.profile
        start = self.page * PAGE_SIZE
        for i, upgrade in enumerate(VILLAGE_UPGRADES[start : start + PAGE_SIZE]):
            rect = CARD_RECTS[i]
            sprite = village_prop(upgrade.key)
            img = self.scaled(sprite, (130, 72), ("upgrade", upgrade.key))
            screen.blit(img, img.get_rect(midleft=(rect.left + 20, rect.centery + 6)))
            self.text.paragraph(
                screen,
                upgrade.description,
                pygame.Rect(rect.left + 170, rect.top + 38, rect.width - 190, 44),
                T.SIZES["small"],
                T.INK,
            )
            if upgrade.key not in profile.vila:
                self._draw_cost_icons(screen, upgrade.cost, (rect.left + 170, rect.top + 88))

    def _draw_selected(self, screen: pygame.Surface, upgrade) -> None:
        rect = pygame.Rect(180, 145, 740, 355)
        T.panel(screen, rect, T.PAPER, T.NAVY, 250, 22, 4)
        sprite = village_prop(upgrade.key)
        img = self.scaled(sprite, (250, 210), ("upgrade-preview", upgrade.key))
        screen.blit(img, img.get_rect(center=(rect.left + 160, rect.centery)))
        self.text.blit(
            screen, upgrade.name, (rect.left + 310, rect.top + 35), T.SIZES["title"], T.NAVY, True, "midleft"
        )
        self.text.paragraph(
            screen, upgrade.description, pygame.Rect(rect.left + 310, rect.top + 92, 380, 82), T.SIZES["body"], T.INK
        )
        self.text.blit(
            screen,
            "Materiais necessários",
            (rect.left + 310, rect.top + 194),
            T.SIZES["label"],
            T.NAVY,
            True,
            "midleft",
        )
        self._draw_cost_icons(screen, upgrade.cost, (rect.left + 310, rect.top + 245))

    def draw(self, screen: pygame.Surface) -> None:
        if self.reveal_key is not None:
            draw_village(self, screen, self.reveal_key)
            reveal_panel = pygame.Rect(16, 12, 570, 100)
            T.panel(screen, reveal_panel, T.PAPER, T.NAVY, 248, 18, 3)
            self.text.blit(screen, "A vila ganhou uma nova obra!", (32, 22), T.SIZES["title"], T.NAVY, True)
            self.text.blit(
                screen, "Veja o destaque no lugar onde foi construída.", (32, 67), T.SIZES["small"], T.INK, True
            )
            self.resource_bar(screen, right=C.WIDTH - 25, top=18)
            self.draw_menu(screen)
            return
        focused = self.menu.focused
        highlight = self.selected_key or (
            focused.key if focused is not None and focused.key in {u.key for u in VILLAGE_UPGRADES} else ""
        )
        draw_village(self, screen, highlight)
        T.veil(screen, (10, 18, 40), 45)
        title = "Cuidar da vila" if self.tab == "vila" else "Peças do avião"
        title_panel = pygame.Rect(410, 16, 470, 56)
        T.panel(screen, title_panel, T.PAPER, T.NAVY, 248, 16, 2)
        self.text.blit(screen, title, title_panel.center, T.SIZES["title"], T.NAVY, True, "center")
        self.resource_bar(screen, right=C.WIDTH - 25, top=82)
        self.draw_menu(screen)
        if self.tab == "vila":
            if self.selected_key:
                upgrade = next((u for u in VILLAGE_UPGRADES if u.key == self.selected_key), None)
                if upgrade is not None:
                    self._draw_selected(screen, upgrade)
            else:
                self._draw_village_list(screen)
                page_rect = pygame.Rect(520, 565, 110, 50)
                T.panel(screen, page_rect, T.PAPER, T.NAVY, 245, 12, 2)
                self.text.blit(
                    screen,
                    f"{self.page + 1} / {(len(VILLAGE_UPGRADES) + PAGE_SIZE - 1) // PAGE_SIZE}",
                    page_rect.center,
                    T.SIZES["small"],
                    T.NAVY,
                    True,
                    "center",
                )
        else:
            stats = plane_stats(self.app.profile.pecas)
            for part in PLANE_PARTS:
                button = next((b for b in self.menu.buttons if b.key == part.key), None)
                if button is None:
                    continue
                self.text.paragraph(
                    screen,
                    part.description,
                    pygame.Rect(button.rect.left + 300, button.rect.top + 30, 330, 54),
                    T.SIZES["body"],
                    T.INK,
                )
                level = self.app.profile.pecas.get(part.key, 0)
                if level < MAX_PART_LEVEL:
                    self._draw_cost_icons(
                        screen, part.level_costs[level], (button.rect.left + 650, button.rect.top + 55)
                    )
            info = f"Resposta x{stats.response:.2f}   Agilidade x{stats.max_speed:.2f}   Colisão x{stats.hitbox:.2f}"
            self.text.blit(screen, info, (40, 525), T.SIZES["body"], T.WHITE, True)
        self.toast.draw(screen, self.text, (C.WIDTH // 2, 630))
