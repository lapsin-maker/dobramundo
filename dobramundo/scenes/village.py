"""Vila-base: o ponto de decolagem e de volta, onde a progressão fica visível.

Um diorama de papel: morros ao fundo, um rio que atravessa a vila, caminhos
até um largo central onde o avião pousa, casas em três núcleos, árvores e
gente passeando. A vila começa cinzenta e poluída; cada melhoria comprada
aparece no seu lugar e, conforme a vila avança, o céu limpa, o rio fica azul,
o gramado verdeja e as casas industriais dão lugar à arquitetura solarpunk,
uma a uma.
"""

from __future__ import annotations

import math

import pygame

from .. import config as C
from ..content import texts
from ..content.biomes import BIOMES
from ..content.progress import VILLAGE_UPGRADES
from ..engine import paper
from ..persistence import MODE_LABELS
from ..ui import theme as T
from ..ui.widgets import row
from ..util import lerp_color, rgb
from .base import Scene

# Casas da vila (fundo): cada uma passa de industrial a solarpunk num ponto da evolução,
# em ordem, em vez de todas de uma vez. (sprite industrial, sprite solar, x, base y, altura)
HOUSES = [
    ("factory_wall_a", "EF_EscolaTaipa", 230, 318, 112),
    ("fabrica", "EF_ResidencialTerracos", 395, 312, 150),
    ("factory_wall_b", "EF_MercadoBambu", 760, 318, 110),
    ("pressure_tank", "EF_CentroComunitario", 905, 322, 128),
    ("chamine", "EF_ApartamentosExo", 1035, 312, 170),
]
# Onde cada melhoria aparece na vila: x, base y, altura (três núcleos e um largo central).
SLOTS = {
    "paineis": (610, 318, 96),
    "turbina": (980, 300, 220),
    "telhado_verde": (165, 436, 150),
    "horta": (300, 478, 66),
    "compostor": (420, 462, 70),
    "ponto_troca": (690, 468, 96),
    "cisterna": (830, 440, 96),
    "bicicletario": (930, 486, 58),
}
TREES = [
    (60, 350, 70, 1),
    (130, 330, 56, 2),
    (520, 300, 48, 3),
    (700, 312, 44, 4),
    (1070, 420, 80, 5),
    (990, 470, 50, 6),
]
PATH_LEFT = [(560, 405), (470, 430), (330, 452), (200, 500)]  # do largo para a esquerda, pela ponte
PATH_RIGHT = [(600, 405), (720, 440), (860, 470), (960, 520)]
PEOPLE = [(0.0, T.ORANGE), (0.37, T.TEAL), (0.7, rgb("8e5ad1"))]
SKY_POLLUTED = (rgb("4a5260"), rgb("a39b8c"))
SKY_CLEAN = (rgb("3fa5ea"), rgb("fff2b0"))
WATER_POLLUTED, WATER_CLEAN = rgb("4b5a52"), rgb("2bb3c4")
GROUND_POLLUTED, GROUND_CLEAN = rgb("8c8470"), rgb("7fc26a")
HILL_POLLUTED, HILL_CLEAN = rgb("6e7478"), rgb("5aa66a")
CANOPY_POLLUTED, CANOPY_CLEAN = rgb("8a8f7a"), rgb("4fae5e")
PATH_COLOR = rgb("d9b57a")
SQUARE = (580, 392)  # centro do largo onde o avião pousa
HILLS = ((-100, 700, 236, 90, 2, 0.35), (420, 1250, 240, 110, 3, 0.2), (-60, 1200, 262, 60, 4, 0.0))


def village_progress(profile) -> float:
    return len(profile.vila) / len(VILLAGE_UPGRADES)


def river_line() -> list:
    return paper.bezier((C.WIDTH + 40, 262), (760, 300), (520, 360), (-40, 470), 32)


def draw_ground(scene: Scene, screen: pygame.Surface, progress: float) -> None:
    """Céu, morros, gramado, rio, ponte, caminhos e largo (tudo o que fica sob as casas)."""
    app, t = scene.app, scene.time
    sky = app.view.sky
    top = lerp_color(SKY_POLLUTED[0], SKY_CLEAN[0], progress)
    horizon = lerp_color(SKY_POLLUTED[1], SKY_CLEAN[1], progress)
    span = C.POLLUTION_CLEAR_END - C.POLLUTION_CLEAR_START
    sky.update_atmosphere(C.POLLUTION_CLEAR_START + span * progress, horizon, SKY_POLLUTED[1])
    screen.blit(sky.gradient(top, horizon), (0, 0))
    sky.draw_sun(screen, 0.0, horizon)
    sky.draw_clouds(screen, 0.0, t * 18.0)
    hill_color = lerp_color(HILL_POLLUTED, HILL_CLEAN, progress)
    for i, (x0, x1, base, height, bumps, mix) in enumerate(HILLS):
        hill = lerp_color(hill_color, horizon, mix)
        paper.ink_polygon(screen, paper.hill_points(x0, x1, base, height, bumps, i + 1), hill)
    ground = lerp_color(GROUND_POLLUTED, GROUND_CLEAN, progress)
    pygame.draw.rect(screen, ground, (0, 262, C.WIDTH, C.HEIGHT - 262))
    pygame.draw.line(screen, paper.INK, (0, 262), (C.WIDTH, 262), 3)
    for y in range(290, C.HEIGHT, 70):  # faixas de aquarela no gramado
        pygame.draw.rect(screen, lerp_color(ground, (255, 255, 255), 0.06), (0, y, C.WIDTH, 35))
    line = river_line()
    widths = [34 + 110 * (i / len(line)) for i in range(len(line))]
    water = lerp_color(WATER_POLLUTED, WATER_CLEAN, progress)
    paper.ink_polygon(screen, paper.ribbon(line, widths), water)
    paper.wave_lines(screen, line, lerp_color(water, (255, 255, 255), 0.5), t, 14)
    for route in (PATH_LEFT, PATH_RIGHT):
        curve = paper.bezier(route[0], route[1], route[2], route[3], 20)
        edge = lerp_color(PATH_COLOR, paper.INK, 0.5)
        paper.ink_polygon(screen, paper.ribbon(curve, [26] * len(curve)), PATH_COLOR, edge, 2)
    bridge = pygame.Rect(0, 0, 70, 30)
    bridge.center = (372, 440)
    pygame.draw.rect(screen, paper.INK, bridge.inflate(4, 4), border_radius=6)
    pygame.draw.rect(screen, rgb("b07a4a"), bridge, border_radius=5)
    for k in range(5):
        x = bridge.left + 8 + k * 14
        pygame.draw.line(screen, paper.INK, (x, bridge.top), (x, bridge.bottom), 1)
    square = pygame.Rect(0, 0, 250, 70)
    square.center = SQUARE
    pygame.draw.ellipse(screen, paper.INK, square.inflate(4, 4))
    pygame.draw.ellipse(screen, lerp_color(PATH_COLOR, (255, 255, 255), 0.2), square)


def draw_village(scene: Scene, screen: pygame.Surface, highlight: str = "") -> None:
    """Diorama da vila do perfil (usado também na tela de melhorias)."""
    app, t = scene.app, scene.time
    progress = village_progress(app.profile)
    draw_ground(scene, screen, progress)
    scenery = app.assets.scenery
    owned = set(app.profile.vila)
    items = []  # (base y, tipo, dados): desenhados do fundo para a frente
    for i, (industrial, solar, x, base_y, height) in enumerate(HOUSES):
        name = solar if progress >= (i + 0.5) / len(HOUSES) else industrial
        items.append((base_y, "sprite", (name, x, base_y, height, None)))
    for upgrade in VILLAGE_UPGRADES:
        x, base_y, height = SLOTS.get(upgrade.key, upgrade.slot)
        if upgrade.key in owned:
            items.append((base_y, "sprite", (upgrade.sprite, x, base_y, height, upgrade.key)))
        elif upgrade.key == highlight:
            items.append((base_y, "ghost", (x, base_y, height)))
    for x, y, height, seed in TREES:
        items.append((y, "tree", (x, y, height, seed)))
    for k, (phase, shirt) in enumerate(PEOPLE):
        route = PATH_LEFT if k % 2 == 0 else PATH_RIGHT
        u = (phase + t * 0.035) % 2.0
        u = u if u <= 1.0 else 2.0 - u  # vai e volta pelo caminho
        curve = paper.bezier(route[0], route[1], route[2], route[3], 40)
        px, py = curve[int(u * 39)]
        items.append((py, "person", (px, py, 34 + 14 * (py - 400) / 120, shirt, t * 9 + k)))
    items.sort(key=lambda item: item[0])
    canopy = lerp_color(CANOPY_POLLUTED, CANOPY_CLEAN, progress)
    for _, kind, data in items:
        if kind == "sprite":
            name, x, base_y, height, key = data
            sprite = scenery.get(name)
            if sprite is None:
                continue
            img = scene.scaled(sprite, (height * 3, height))
            rect = img.get_rect(midbottom=(x, base_y))
            paper.shadow(screen, (x, base_y - 2), int(rect.width * 0.9), max(8, int(height * 0.16)), 55)
            screen.blit(img, rect)
            if key == highlight:
                pygame.draw.rect(screen, T.SUN, rect.inflate(10, 10), 4, border_radius=12)
        elif kind == "ghost":
            x, base_y, height = data
            ghost = pygame.Rect(0, 0, height, height)
            ghost.midbottom = (x, base_y)
            pygame.draw.rect(screen, T.SUN, ghost, 3, border_radius=12)
            scene.text.blit(screen, "?", ghost.center, T.SIZES["title"], T.SUN, True, "center")
        elif kind == "tree":
            x, y, height, seed = data
            paper.tree(screen, (x, y), height, canopy, rgb("8a5a3a"), seed)
        else:
            px, py, height, shirt, phase = data
            paper.person(screen, (px, py), height, shirt, rgb("e8b48a"), phase)
    paper.smoke(screen, (1035, 150), t, 1.0 - progress, 1)
    paper.sparkles(screen, pygame.Rect(0, 280, C.WIDTH, 220), t, progress, rgb("f6c33b"))


class VillageScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.confirm_exit = False  # ESC na vila pergunta se é para sair do jogo

    def build(self) -> None:
        if self.confirm_exit:
            rects = row(pygame.Rect(C.WIDTH // 2 - 330, 340, 660, 80), 2)
            self.menu.set_buttons(
                [
                    self.button(rects[0], "Continuar jogando", self.back, color=T.GREEN, key="continuar"),
                    self.button(rects[1], "Sair do jogo", self.quit, color=T.RED, key="sair"),
                ],
                keep_focus=False,
            )
            return

        rects = row(pygame.Rect(16, 560, C.WIDTH - 32, 76), 6, 10)
        self.menu.set_buttons(
            [
                self.button(
                    rects[0],
                    texts.UI["decolar"],
                    lambda: self.goto("mapa"),
                    color=T.ORANGE,
                    sublabel="Mapa dos biomas",
                    key="decolar",
                ),
                self.button(rects[1], texts.UI["melhorias"], lambda: self.goto("melhorias"), sublabel="Vila e avião"),
                self.button(rects[2], texts.UI["hangar"], lambda: self.goto("hangar"), sublabel="Avião e pintura"),
                self.button(rects[3], texts.UI["piloto"], lambda: self.goto("piloto"), sublabel="Personalizar"),
                self.button(rects[4], texts.UI["opcoes"], lambda: self.goto("opcoes"), sublabel="Controle e som"),
                self.button(rects[5], texts.UI["sobre"], lambda: self.goto("sobre"), sublabel="ODS e créditos"),
            ]
        )

    def back(self) -> None:
        """ESC abre (ou fecha) a pergunta de saída, em vez de trocar de tela."""
        self.confirm_exit = not self.confirm_exit
        self.build()

    def quit(self) -> None:
        self.app.save()
        self.app.running = False

    def draw(self, screen: pygame.Surface) -> None:
        draw_village(self, screen)
        app = self.app
        profile = app.profile
        skin = app.view.skin
        color, pattern = profile.plane_color(profile.aviao), profile.plane_pattern(profile.aviao)
        plane = skin.surface(profile.aviao, "menu", color, pattern, profile.piloto)
        if plane is not None:
            key = ("vila", skin.look_key(profile.aviao, color, pattern, profile.piloto))
            img = self.scaled(plane, (250, 170), key)
            bob = math.sin(self.time * 2.2) * 6
            paper.shadow(screen, (SQUARE[0], SQUARE[1] + 3), 190 - int(bob * 3), 34, 60)
            screen.blit(img, img.get_rect(center=(SQUARE[0], int(330 + bob))))
        progress = village_progress(profile)
        self.title(
            screen,
            "Vila-base",
            f"Vila {int(progress * 100)}% sustentável   •   {profile.total_stars()} de "
            f"{3 * len(BIOMES)} estrelas   •   Modo {MODE_LABELS[profile.modo]}",
        )
        self.resource_bar(screen)
        logo = app.assets.sprite("ui", "logo")
        if logo is not None:
            screen.blit(self.scaled(logo, (210, 117)), (C.WIDTH - 226, 60))
        tip = texts.TIPS[int(self.time // 7) % len(texts.TIPS)]
        tip_rect = pygame.Rect(16, 512, C.WIDTH - 32, 38)
        T.panel(screen, tip_rect, T.PAPER, T.TEAL, 230, 12, 2)
        self.text.blit(screen, tip, tip_rect.center, T.SIZES["body"], T.INK, anchor="center")
        if app.save_failed:
            warn = pygame.Rect(16, 466, C.WIDTH - 32, 38)
            T.panel(screen, warn, T.PAPER, T.RED, 240, 12, 3)
            self.text.blit(
                screen,
                "Não foi possível salvar o progresso nesta pasta (veja dobramundo.log).",
                warn.center,
                T.SIZES["body"],
                T.RED,
                True,
                "center",
            )
        if self.confirm_exit:
            T.veil(screen, (10, 18, 40), 170)
            card = pygame.Rect(C.WIDTH // 2 - 360, 200, 720, 250)
            T.panel(screen, card, T.PAPER, T.NAVY, 250, 22, 4)
            self.text.blit(
                screen, "Sair do Dobramundo?", (card.centerx, card.top + 36), T.SIZES["title"], T.NAVY, True, "midtop"
            )
            self.text.blit(
                screen,
                "O progresso já está salvo.",
                (card.centerx, card.top + 88),
                T.SIZES["body"],
                T.MUTED,
                anchor="midtop",
            )
        self.draw_menu(screen)
