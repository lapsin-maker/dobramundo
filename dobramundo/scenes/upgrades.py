"""Melhorias: recursos viram melhorias da vila e peças reaproveitadas do avião."""

from __future__ import annotations

import pygame

from .. import config as C
from ..content import texts
from ..content.progress import MAX_PART_LEVEL, PLANE_PARTS, VILLAGE_UPGRADES, can_afford, plane_stats
from ..ui import theme as T
from ..ui.widgets import grid
from .base import Scene
from .village import draw_village


class UpgradesScene(Scene):
    def __init__(self, app, tab: str = "vila") -> None:
        super().__init__(app)
        self.tab = tab
        self.message = ""
        self.message_time = 0.0

    def build(self) -> None:
        from .village import VillageScene

        app = self.app
        profile = app.profile
        buttons = [
            self.button(
                (24, 86, 200, 54), "Vila", lambda: self.set_tab("vila"), selected=self.tab == "vila", key="tab_vila"
            ),
            self.button(
                (236, 86, 200, 54),
                "Avião",
                lambda: self.set_tab("aviao"),
                selected=self.tab == "aviao",
                key="tab_aviao",
            ),
            self.button(
                (C.WIDTH - 224, 570, 200, 64), texts.UI["voltar"], lambda: app.go(VillageScene(app)), key="voltar"
            ),
        ]
        if self.tab == "vila":
            cells = grid(pygame.Rect(24, 154, C.WIDTH - 48, 400), len(VILLAGE_UPGRADES), 4, 12)
            for upgrade, rect in zip(VILLAGE_UPGRADES, cells):
                owned = upgrade.key in profile.vila
                buttons.append(
                    self.button(
                        rect,
                        upgrade.name,
                        (lambda u=upgrade: self.buy_village(u)),
                        sublabel="Construído" if owned else "",
                        selected=owned,
                        enabled=not owned,
                        size=T.SIZES["body"],
                        key=upgrade.key,
                        align="top",
                    )
                )
        else:
            cells = grid(pygame.Rect(24, 154, C.WIDTH - 48, 400), len(PLANE_PARTS), 3, 14)
            for part, rect in zip(PLANE_PARTS, cells):
                level = profile.pecas.get(part.key, 0)
                done = level >= MAX_PART_LEVEL
                buttons.append(
                    self.button(
                        rect,
                        part.name,
                        (lambda p=part: self.buy_part(p)),
                        sublabel=f"Nível {level} de {MAX_PART_LEVEL}",
                        selected=done,
                        enabled=not done,
                        size=T.SIZES["label"],
                        key=part.key,
                        align="top",
                    )
                )
        self.menu.set_buttons(buttons)

    def set_tab(self, tab: str) -> None:
        self.tab = tab
        self.build()

    def say(self, text: str) -> None:
        self.message, self.message_time = text, 3.0

    def pay(self, cost: dict) -> bool:
        wallet = self.app.profile.recursos
        if not can_afford(wallet, cost):
            self.say("Faltam recursos: voe mais um pouco e colete resíduos!")
            return False
        for key, amount in cost.items():
            wallet[key] -= amount
        self.app.audio.play("sfx_compra")
        return True

    def buy_village(self, upgrade) -> None:
        if upgrade.key in self.app.profile.vila or not self.pay(upgrade.cost):
            return
        self.app.profile.vila.append(upgrade.key)
        self.app.profile.normalize()
        self.app.save()
        self.say(f"{upgrade.name} construído na vila!")
        self.build()

    def buy_part(self, part) -> None:
        level = self.app.profile.pecas.get(part.key, 0)
        if level >= MAX_PART_LEVEL or not self.pay(part.level_costs[level]):
            return
        self.app.profile.pecas[part.key] = level + 1
        self.app.save()
        self.app.apply_options()  # a quilha muda a zona morta do controle corporal
        self.say(f"{part.name} nível {level + 1} instalado!")
        self.build()

    def back(self) -> None:
        from .village import VillageScene

        self.app.go(VillageScene(self.app))

    def update(self, dt: float) -> None:
        super().update(dt)
        self.message_time = max(0.0, self.message_time - dt)

    def draw(self, screen: pygame.Surface) -> None:
        focused = self.menu.focused
        draw_village(self, screen, focused.key if focused is not None else "")
        T.veil(screen, (10, 18, 40), 70)
        self.title(screen, texts.UI["melhorias"], "Troque recursos por melhorias da vila e peças do avião")
        self.resource_bar(screen)
        self.draw_menu(screen)
        profile = self.app.profile
        scenery = self.app.assets.scenery
        if self.tab == "vila":
            for upgrade in VILLAGE_UPGRADES:
                button = next((b for b in self.menu.buttons if b.key == upgrade.key), None)
                if button is None:
                    continue
                sprite = scenery.get(upgrade.sprite)
                if sprite is not None:
                    img = self.scaled(sprite, (button.rect.width - 30, button.rect.height - 110))
                    screen.blit(img, img.get_rect(midtop=(button.rect.centerx, button.rect.top + 58)))
                if upgrade.key not in profile.vila:
                    self.draw_cost(screen, upgrade.cost, (button.rect.left + 14, button.rect.bottom - 36))
        else:
            stats = plane_stats(profile.pecas)
            for part in PLANE_PARTS:
                button = next((b for b in self.menu.buttons if b.key == part.key), None)
                if button is None:
                    continue
                self.text.paragraph(
                    screen,
                    part.description,
                    pygame.Rect(button.rect.left + 18, button.rect.top + 72, button.rect.width - 36, 120),
                    T.SIZES["body"],
                    T.INK,
                )
                level = profile.pecas.get(part.key, 0)
                for i in range(MAX_PART_LEVEL):
                    pip = pygame.Rect(button.rect.left + 18 + i * 34, button.rect.top + 200, 26, 26)
                    pygame.draw.rect(screen, T.GREEN if i < level else T.PAPER_DARK, pip, border_radius=6)
                    pygame.draw.rect(screen, T.INK, pip, 2, border_radius=6)
                if level < MAX_PART_LEVEL:
                    self.text.blit(
                        screen,
                        "Próximo nível:",
                        (button.rect.left + 18, button.rect.bottom - 120),
                        T.SIZES["small"],
                        T.MUTED,
                        True,
                    )
                    self.draw_cost(screen, part.level_costs[level], (button.rect.left + 18, button.rect.bottom - 96))
            info = f"Resposta x{stats.response:.2f}   Agilidade x{stats.max_speed:.2f}   Colisão x{stats.hitbox:.2f}"
            self.text.blit(screen, info, (40, 588), T.SIZES["body"], T.WHITE, True)
        if self.message_time > 0:
            box = pygame.Rect(0, 0, 640, 54)
            box.center = (C.WIDTH // 2 - 100, 600)
            T.panel(screen, box, T.PAPER, T.ORANGE, 250, 14, 3)
            self.text.blit(screen, self.message, box.center, T.SIZES["body"], T.INK, True, "center")
