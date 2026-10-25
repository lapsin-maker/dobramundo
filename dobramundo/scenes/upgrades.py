"""Cuide da vila e aprimore o avião com prévia e confirmação de compra."""

from __future__ import annotations

import math

import pygame

from .. import config as C
from ..content import texts
from ..content.items import WASTE_TYPES
from ..content.pilot import DEFAULT_PILOT, normalize_pilot
from ..content.progress import MAX_PART_LEVEL, PLANE_PARTS, VILLAGE_UPGRADES, can_afford, plane_stats
from ..engine.village_art import village_prop
from ..ui import theme as T
from .base import Scene
from .village import SLOTS, draw_village

PAGE_SIZE = 4
CARD_RECTS = (
    pygame.Rect(25, 150, 480, 130),
    pygame.Rect(595, 150, 480, 130),
    pygame.Rect(25, 340, 480, 130),
    pygame.Rect(595, 340, 480, 130),
)


class UpgradesScene(Scene):
    REVEAL_BEFORE_SECONDS = 0.45
    REVEAL_MATERIALS_SECONDS = 0.85
    REVEAL_BUILD_SECONDS = 1.05

    def __init__(self, app, tab: str = "vila", initial_key: str | None = None) -> None:
        super().__init__(app)
        self.tab = tab
        self.page = 0
        valid_keys = {item.key for item in VILLAGE_UPGRADES}
        self.selected_key = initial_key if initial_key in valid_keys else None
        self.reveal_key: str | None = None
        self.reveal_before: pygame.Surface | None = None
        self.reveal_after: pygame.Surface | None = None
        self.reveal_static_before: pygame.Surface | None = None
        self.reveal_static_after: pygame.Surface | None = None
        self.reveal_cost: dict = {}
        self.reveal_elapsed = 0.0

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
        if self.selected_key is not None:
            for index, button in enumerate(self.menu.buttons):
                if button.key == "confirmar":
                    self.menu.focus = index
                    break

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
        self.reveal_before = None
        self.reveal_after = None
        self.reveal_static_before = None
        self.reveal_static_after = None
        self.reveal_cost = {}
        self.reveal_elapsed = 0.0
        self.build()

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.reveal_key is not None and not self.app.options.reduzir_movimento:
            self.reveal_elapsed = min(
                self.REVEAL_BEFORE_SECONDS + self.REVEAL_MATERIALS_SECONDS + self.REVEAL_BUILD_SECONDS,
                self.reveal_elapsed + dt,
            )

    def _capture_village(self, key: str = "") -> pygame.Surface:
        surface = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        draw_village(self, surface, key)
        return surface

    def _start_reveal(self, upgrade, before: pygame.Surface) -> None:
        self.reveal_key = upgrade.key
        self.reveal_before = before
        self.reveal_cost = dict(upgrade.cost)
        self.reveal_elapsed = (
            self.REVEAL_BEFORE_SECONDS + self.REVEAL_MATERIALS_SECONDS + self.REVEAL_BUILD_SECONDS
            if self.app.options.reduzir_movimento
            else 0.0
        )
        self.reveal_after = self._capture_village(upgrade.key)
        x, base_y, height = SLOTS.get(upgrade.key, upgrade.slot)
        crop_width, crop_height = 360, 225
        center_y = base_y - height // 2
        crop_rect = pygame.Rect(0, 0, crop_width, crop_height)
        crop_rect.center = (x, center_y)
        crop_rect.clamp_ip(pygame.Rect(0, 0, C.WIDTH, C.HEIGHT))
        self.reveal_static_before = before.subsurface(crop_rect).copy()
        self.reveal_static_after = self.reveal_after.subsurface(crop_rect).copy()
        self.selected_key = None
        self.build()

    def _commit_village_purchase(self, upgrade) -> bool:
        if upgrade.key in self.app.profile.vila:
            self.clear_selection()
            return False
        if not can_afford(self.app.profile.recursos, upgrade.cost):
            self.pay(upgrade.cost)
            return False
        before = self._capture_village()
        if not self.pay(upgrade.cost):
            return False
        self.app.profile.vila.append(upgrade.key)
        self.app.profile.normalize()
        self.app.save()
        self._start_reveal(upgrade, before)
        return True

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
        self._commit_village_purchase(upgrade)

    # Compatibilidade para chamadas de domínio já usadas por outros fluxos/testes.
    def buy_village(self, upgrade) -> None:
        self._commit_village_purchase(upgrade)

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
        atlas = self.app.assets.sprite("watercolor", "village_props")
        for i, upgrade in enumerate(VILLAGE_UPGRADES[start : start + PAGE_SIZE]):
            rect = CARD_RECTS[i]
            sprite = village_prop(upgrade.key, atlas)
            img = self.scaled(sprite, (150, 96), ("upgrade", upgrade.key))
            screen.blit(img, img.get_rect(midleft=(rect.left + 8, rect.centery + 4)))
            if upgrade.key not in profile.vila:
                self._draw_cost_icons(screen, upgrade.cost, (rect.left + 170, rect.top + 88))

    def _draw_selected(self, screen: pygame.Surface, upgrade) -> None:
        slot_x = SLOTS.get(upgrade.key, upgrade.slot)[0]
        panel_left = 350 if slot_x < C.WIDTH // 2 else 20
        rect = pygame.Rect(panel_left, 108, 740, 300)
        T.panel(screen, rect, T.PAPER, T.NAVY, 250, 22, 4)
        sprite = village_prop(upgrade.key, self.app.assets.sprite("watercolor", "village_props"))
        img = self.scaled(sprite, (250, 210), ("upgrade-preview", upgrade.key))
        screen.blit(img, img.get_rect(center=(rect.left + 160, rect.centery)))
        self.text.blit(
            screen, upgrade.name, (rect.left + 310, rect.top + 20), T.SIZES["title"], T.NAVY, True, "midleft"
        )
        self.text.paragraph(
            screen, upgrade.description, pygame.Rect(rect.left + 310, rect.top + 68, 380, 65), T.SIZES["body"], T.INK
        )
        self.text.blit(
            screen,
            "Materiais necessários",
            (rect.left + 310, rect.top + 150),
            T.SIZES["label"],
            T.NAVY,
            True,
            "midleft",
        )
        self._draw_cost_icons(screen, upgrade.cost, (rect.left + 310, rect.top + 205))

    def _draw_flying_materials(self, screen: pygame.Surface, progress: float) -> None:
        upgrade = next((item for item in VILLAGE_UPGRADES if item.key == self.reveal_key), None)
        if upgrade is None:
            return
        x, base_y, height = SLOTS.get(upgrade.key, upgrade.slot)
        target = pygame.Vector2(x, base_y - height * 0.52)
        index_by_key = {waste.key: index for index, waste in enumerate(WASTE_TYPES)}
        for waste in WASTE_TYPES:
            if not self.reveal_cost.get(waste.key):
                continue
            index = index_by_key[waste.key]
            start = pygame.Vector2(748 + index * 86, 100)
            p1 = pygame.Vector2(start.x, 220)
            p2 = pygame.Vector2(target.x, 230)
            u = max(0.0, min(1.0, progress))
            one = start.lerp(p1, u)
            two = p1.lerp(p2, u)
            three = p2.lerp(target, u)
            left = one.lerp(two, u)
            right = two.lerp(three, u)
            point = left.lerp(right, u)
            icon = self.app.assets.sprite(
                "waste_sprites", next((item.sprite for item in WASTE_TYPES if item.key == waste.key), "")
            )
            if icon is not None:
                image = self.scaled(icon, (48, 48), ("village-material-flight", waste.key))
                screen.blit(image, image.get_rect(center=(round(point.x), round(point.y))))

    def _draw_community_reaction(self, screen: pygame.Surface, key: str, progress: float) -> None:
        x, base_y, height = SLOTS.get(key, next(item.slot for item in VILLAGE_UPGRADES if item.key == key))
        bob = 0 if self.app.options.reduzir_movimento else round(2 * math.sin(self.time * 7))
        looks = (
            {**DEFAULT_PILOT, "pele": "pele2", "cabelo": "cacheado", "cor_cabelo": "castanho", "roupa": "verde"},
            {
                **DEFAULT_PILOT,
                "pele": "pele5",
                "cabelo": "crespo",
                "cor_cabelo": "preto",
                "roupa": "amarela",
                "cadeira": "sim",
            },
            {
                **DEFAULT_PILOT,
                "pele": "pele3",
                "cabelo": "trancas",
                "cor_cabelo": "ruivo",
                "roupa": "azul",
                "aparelho": "sim",
            },
        )
        offsets = (-58, 58)
        for i, (look, dx) in enumerate(zip(looks, offsets)):
            if progress < (i + 1) / len(looks):
                continue
            neighbor_x = max(38, min(C.WIDTH - 38, x + dx))
            pilot = self.app.view.skin.pilots.compose("menu", normalize_pilot(look))
            if pilot is None:
                continue
            image = self.scaled(pilot, (62, 76), ("village-neighbor", i))
            ground_y = base_y - max(32, height * 0.43)
            screen.blit(image, image.get_rect(midbottom=(neighbor_x, ground_y + bob)))
            bubble = pygame.Rect(neighbor_x - 20, ground_y - 51 + bob, 40, 34)
            pygame.draw.ellipse(screen, T.PAPER, bubble)
            pygame.draw.ellipse(screen, T.NAVY, bubble, 2)
            pygame.draw.polygon(
                screen,
                T.PAPER,
                (
                    (bubble.left + 25, bubble.bottom - 2),
                    (bubble.left + 31, bubble.bottom + 6),
                    (bubble.left + 30, bubble.bottom - 3),
                ),
            )
            if i == 0:
                cx, cy = bubble.centerx, bubble.centery - 1
                pygame.draw.circle(screen, T.ORANGE, (cx - 5, cy - 3), 6)
                pygame.draw.circle(screen, T.ORANGE, (cx + 5, cy - 3), 6)
                pygame.draw.polygon(
                    screen,
                    T.ORANGE,
                    ((cx - 11, cy), (cx + 11, cy), (cx, cy + 12)),
                )
            else:
                pygame.draw.ellipse(screen, T.GREEN, (bubble.centerx - 6, bubble.centery - 10, 12, 20))
                pygame.draw.line(
                    screen,
                    T.NAVY,
                    (bubble.centerx, bubble.centery + 6),
                    (bubble.centerx, bubble.centery - 7),
                    2,
                )

    def draw(self, screen: pygame.Surface) -> None:
        if self.reveal_key is not None:
            before = self.reveal_before
            after = self.reveal_after
            if self.app.options.reduzir_movimento:
                screen.fill(T.PAPER)
                panel = pygame.Rect(74, 95, C.WIDTH - 148, 405)
                T.panel(screen, panel, T.PAPER, T.NAVY, 248, 20, 3)
                self.text.blit(
                    screen,
                    "Veja a mudança na vila",
                    (panel.centerx, panel.top + 16),
                    T.SIZES["title"],
                    T.NAVY,
                    True,
                    "midtop",
                )
                for image, x, label, color in (
                    (self.reveal_static_before, panel.left + 35, "ANTES", T.MUTED),
                    (self.reveal_static_after, panel.left + panel.width // 2 + 15, "AGORA", T.GREEN),
                ):
                    self.text.blit(screen, label, (x, panel.top + 63), T.SIZES["label"], color, True)
                    if image is not None:
                        thumb = self.scaled(image, (410, 260), ("reveal-static", label, self.reveal_key))
                        thumb_rect = thumb.get_rect(topleft=(x, panel.top + 100))
                        T.panel(screen, thumb_rect.inflate(10, 10), T.PAPER, T.NAVY, 245, 10, 2)
                        screen.blit(thumb, thumb_rect)
                self.resource_bar(screen, right=C.WIDTH - 25, top=18)
                self.draw_menu(screen)
                return
            before_end = self.REVEAL_BEFORE_SECONDS
            material_end = before_end + self.REVEAL_MATERIALS_SECONDS
            if before is not None:
                screen.blit(before, (0, 0))
            if self.reveal_elapsed < before_end:
                caption = "Sua vila antes da obra"
            elif self.reveal_elapsed < material_end:
                self._draw_flying_materials(
                    screen,
                    (self.reveal_elapsed - before_end) / self.REVEAL_MATERIALS_SECONDS,
                )
                caption = "Os materiais chegam"
            else:
                blend = max(0.0, min(1.0, (self.reveal_elapsed - material_end) / self.REVEAL_BUILD_SECONDS))
                eased = blend * blend * (3 - 2 * blend)
                if after is not None:
                    after.set_alpha(round(255 * eased))
                    screen.blit(after, (0, 0))
                    after.set_alpha(255)
                if blend > 0:
                    self._draw_community_reaction(screen, self.reveal_key, min(1.0, blend * 1.6))
                caption = "A vila ganhou uma nova obra!"
            reveal_panel = pygame.Rect(16, 12, 570, 82)
            T.panel(screen, reveal_panel, T.PAPER, T.NAVY, 248, 18, 3)
            self.text.blit(screen, caption, (32, 24), T.SIZES["title"], T.NAVY, True)
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
