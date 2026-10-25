"""Vila-base: o ponto de decolagem e de volta, onde a progressão fica visível.

A vila começa industrial e poluída; cada melhoria comprada aparece no seu lugar
e, conforme a vila avança, o céu limpa e os prédios de fundo dão lugar à
arquitetura solarpunk.
"""

from __future__ import annotations

import math

import pygame

from .. import config as C
from ..content import texts
from ..content.progress import VILLAGE_UPGRADES
from ..ui import theme as T
from ..ui.widgets import row
from ..util import lerp_color, rgb
from .base import Scene

POLLUTED_BACK = [
    ("fabrica", 150, 340),
    ("chamine", 260, 300),
    ("factory_wall_a", 140, 560),
    ("industrial_chimney", 250, 720),
    ("factory_wall_b", 150, 860),
    ("pressure_tank", 150, 1010),
]
SOLAR_BACK = [
    ("EF_ResidencialTerracos", 220, 330),
    ("EF_EscolaTaipa", 130, 560),
    ("EF_CentroComunitario", 170, 720),
    ("EF_MercadoBambu", 140, 880),
    ("EF_ApartamentosExo", 230, 1030),
]
SKY_POLLUTED = (rgb("3b2a22"), rgb("8a5a36"))
SKY_CLEAN = (rgb("4fb3f0"), rgb("fff2b0"))


def village_progress(profile) -> float:
    return len(profile.vila) / len(VILLAGE_UPGRADES)


def draw_village(scene: Scene, screen: pygame.Surface, highlight: str = "") -> None:
    """Desenha a vila do perfil (usada também na tela de melhorias)."""
    app = scene.app
    progress = village_progress(app.profile)
    top = lerp_color(SKY_POLLUTED[0], SKY_CLEAN[0], progress)
    horizon = lerp_color(SKY_POLLUTED[1], SKY_CLEAN[1], progress)
    screen.blit(app.view.sky.gradient(top, horizon), (0, 0))
    pygame.draw.rect(screen, horizon, (0, C.HORIZON_Y, C.WIDTH, C.HEIGHT))
    sun = lerp_color(rgb("d9a066"), rgb("fff59d"), progress)
    pygame.draw.circle(screen, sun, (880, 120), 46)
    ground_top = lerp_color(rgb("5b4a3c"), rgb("7cc16a"), progress)
    ground_low = lerp_color(rgb("3d3129"), rgb("4f9a48"), progress)
    for y in range(400, C.HEIGHT, 6):
        t = (y - 400) / (C.HEIGHT - 400)
        pygame.draw.rect(screen, lerp_color(ground_top, ground_low, t), (0, y, C.WIDTH, 6))
    scenery = app.assets.scenery
    back = SOLAR_BACK if progress >= 0.5 else POLLUTED_BACK
    for name, height, x in back:
        sprite = scenery.get(name)
        if sprite is not None:
            img = scene.scaled(sprite, (height * 3, height))
            screen.blit(img, img.get_rect(midbottom=(x, 418)))
    if progress < 0.5:  # fumaça das chaminés
        for i in range(5):
            r = 26 + i * 9 + int(4 * math.sin(scene.time * 1.5 + i))
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (70, 60, 55, 120 - i * 18), (r, r), r)
            screen.blit(surf, (260 - r + i * 22, 110 - i * 34 - r))
    owned = set(app.profile.vila)
    for upgrade in sorted(VILLAGE_UPGRADES, key=lambda u: u.slot[1]):
        x, base_y, height = upgrade.slot
        sprite = scenery.get(upgrade.sprite)
        if upgrade.key in owned and sprite is not None:
            img = scene.scaled(sprite, (height * 3, height))
            rect = img.get_rect(midbottom=(x, base_y))
            screen.blit(img, rect)
            if upgrade.key == highlight:
                pygame.draw.rect(screen, T.SUN, rect.inflate(10, 10), 4, border_radius=12)
        elif upgrade.key == highlight:
            ghost = pygame.Rect(0, 0, height, height)
            ghost.midbottom = (x, base_y)
            pygame.draw.rect(screen, T.SUN, ghost, 3, border_radius=12)
            scene.text.blit(screen, "?", ghost.center, T.SIZES["title"], T.SUN, True, "center")


class VillageScene(Scene):
    def build(self) -> None:
        from .about import AboutScene
        from .hangar import HangarScene
        from .map import MapScene
        from .options import OptionsScene
        from .pilot import PilotScene
        from .upgrades import UpgradesScene

        app = self.app
        rects = row(pygame.Rect(16, 560, C.WIDTH - 32, 76), 6, 10)
        self.menu.set_buttons(
            [
                self.button(
                    rects[0],
                    texts.UI["decolar"],
                    lambda: app.go(MapScene(app)),
                    color=T.ORANGE,
                    sublabel="Mapa dos biomas",
                    key="decolar",
                ),
                self.button(
                    rects[1], texts.UI["melhorias"], lambda: app.go(UpgradesScene(app)), sublabel="Vila e avião"
                ),
                self.button(rects[2], texts.UI["hangar"], lambda: app.go(HangarScene(app)), sublabel="Avião e pintura"),
                self.button(rects[3], texts.UI["piloto"], lambda: app.go(PilotScene(app)), sublabel="Personalizar"),
                self.button(rects[4], texts.UI["opcoes"], lambda: app.go(OptionsScene(app)), sublabel="Controle e som"),
                self.button(rects[5], texts.UI["sobre"], lambda: app.go(AboutScene(app)), sublabel="ODS e créditos"),
            ]
        )

    def back(self) -> None:
        from .options import OptionsScene

        self.app.go(OptionsScene(self.app))

    def draw(self, screen: pygame.Surface) -> None:
        draw_village(self, screen)
        app = self.app
        plane = app.view.skin.surface(
            app.profile.aviao,
            "menu",
            app.profile.plane_color(app.profile.aviao),
            app.profile.plane_pattern(app.profile.aviao),
            app.profile.piloto,
        )
        if plane is not None:
            img = self.scaled(
                plane,
                (250, 170),
                (
                    "vila",
                    app.view.skin.look_key(
                        app.profile.aviao,
                        app.profile.plane_color(app.profile.aviao),
                        app.profile.plane_pattern(app.profile.aviao),
                        app.profile.piloto,
                    ),
                ),
            )
            bob = math.sin(self.time * 2.2) * 8
            screen.blit(img, img.get_rect(center=(560, int(300 + bob))))
        progress = village_progress(app.profile)
        self.title(
            screen,
            "Vila-base",
            f"Vila {int(progress * 100)}% sustentável   •   {app.profile.total_stars()} de 6 estrelas",
        )
        self.resource_bar(screen)
        logo = app.assets.sprite("ui", "logo")
        if logo is not None:
            screen.blit(self.scaled(logo, (200, 100)), (C.WIDTH - 220, 62))
        tip = texts.TIPS[int(self.time // 7) % len(texts.TIPS)]
        tip_rect = pygame.Rect(16, 512, C.WIDTH - 32, 38)
        T.panel(screen, tip_rect, T.PAPER, T.TEAL, 230, 12, 2)
        self.text.blit(screen, tip, tip_rect.center, T.SIZES["body"], T.INK, anchor="center")
        self.draw_menu(screen)
