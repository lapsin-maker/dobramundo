"""Vila-base: o ponto de decolagem e de volta, onde a progressão fica visível.

Um diorama de papel: morros ao fundo, um rio que atravessa a vila, caminhos
até um largo central onde o avião pousa, casas em três núcleos, árvores e
gente passeando. A vila começa industrial, colorida e poluída; cada melhoria comprada
aparece no seu lugar e, conforme a vila avança, o céu limpa, o rio fica azul,
o gramado verdeja e as casas industriais dão lugar à arquitetura solarpunk,
uma a uma.
"""

from __future__ import annotations

import math

import pygame

from .. import config as C
from ..content.biomes import BIOMES
from ..content.pilot import DEFAULT_PILOT, normalize_pilot
from ..content.progress import VILLAGE_UPGRADES
from ..engine import paper
from ..engine.village_art import destination_icon, village_prop, village_resident
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
    # Meia-lua em dois agrupamentos habitados; deixa o corredor do avião livre.
    "paineis": (680, 500, 90),
    "turbina": (1040, 430, 90),
    "telhado_verde": (100, 430, 90),
    "horta": (450, 520, 72),
    "compostor": (330, 500, 72),
    "ponto_troca": (210, 470, 85),
    "cisterna": (800, 500, 90),
    "bicicletario": (920, 470, 68),
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
VILLAGE_NEIGHBOR_POSITIONS = ((280, 516), (835, 516), (960, 516))
HILLS = ((-100, 700, 236, 90, 2, 0.35), (420, 1250, 240, 110, 3, 0.2), (-60, 1200, 262, 60, 4, 0.0))


def village_progress(profile) -> float:
    return len(profile.vila) / len(VILLAGE_UPGRADES)


VILLAGE_REQUESTS = {
    "ponto_troca": "Podemos separar os materiais?",
    "horta": "Vamos plantar nosso lanche!",
    "paineis": "Queremos luz do sol em casa!",
    "compostor": "A terra pode ganhar adubo?",
    "cisterna": "Guarde água para os dias secos.",
    "bicicletario": "Vamos pedalar pela vila!",
    "telhado_verde": "Uma sombra de folhas ajudaria.",
    "turbina": "O vento pode acender a vila!",
}


def ensure_village_requests(profile) -> bool:
    """Mantém pedidos simples no perfil sem alterar a economia do jogo."""
    raw = profile.pedidos_vila
    valid_keys = {upgrade.key for upgrade in VILLAGE_UPGRADES}
    requests = {key: value for key, value in raw.items() if key in valid_keys}
    owned = set(profile.vila)
    changed = requests != raw
    for upgrade in VILLAGE_UPGRADES:
        wanted = "concluida" if upgrade.key in owned else "solicitada"
        if requests.get(upgrade.key) not in ("solicitada", "concluida"):
            requests[upgrade.key] = wanted
            changed = True
        elif upgrade.key in owned and requests[upgrade.key] != "concluida":
            requests[upgrade.key] = "concluida"
            changed = True
    if requests != raw:
        profile.pedidos_vila = requests
        changed = True
    return changed


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


def draw_house(screen: pygame.Surface, x: int, base_y: int, height: int, index: int, progress: float) -> None:
    """Casa em massas de papel; usada apenas no fundo procedural de fallback."""
    solar = progress >= (index + 0.5) / len(HOUSES)
    width = int(height * 1.05)
    body = pygame.Rect(x - width // 2, base_y - int(height * 0.68), width, int(height * 0.68))
    paper.shadow(screen, (x, base_y - 2), width + 28, max(9, height // 8), 45)
    body_color = rgb("f5e6c6") if solar else rgb("aeb4b5")
    roof_color = rgb("dd8460") if solar else rgb("7b7c78")
    pygame.draw.rect(screen, paper.INK, body.inflate(6, 6), border_radius=8)
    pygame.draw.rect(screen, body_color, body, border_radius=7)
    roof = [(body.left - 12, body.top + 8), (x, body.top - height // 3), (body.right + 12, body.top + 8)]
    paper.ink_polygon(screen, roof, roof_color, paper.INK, max(3, height // 34))
    window_w, window_h = max(15, width // 5), max(20, height // 4)
    for wx in (body.left + width // 5, body.right - width // 5 - window_w):
        pane = pygame.Rect(wx, body.top + height // 4, window_w, window_h)
        pygame.draw.rect(screen, paper.INK, pane.inflate(4, 4), border_radius=4)
        pygame.draw.rect(screen, rgb("a8d7d8") if solar else rgb("c1c4bd"), pane, border_radius=3)
    door = pygame.Rect(x - width // 10, base_y - height // 3, width // 5, height // 3)
    pygame.draw.rect(screen, paper.INK, door.inflate(3, 3), border_radius=4)
    pygame.draw.rect(screen, rgb("9b6945"), door, border_radius=3)
    if solar:
        panel = [
            (x - width // 3, body.top + 10),
            (x, body.top - height // 8),
            (x + width // 3, body.top + 10),
            (x, body.top + height // 18),
        ]
        paper.ink_polygon(screen, panel, rgb("79aebc"), paper.INK, 2)
        pygame.draw.line(screen, rgb("f5e6c6"), (x, body.top - height // 7), (x, body.top + height // 18), 2)


def _watercolor_background(scene: Scene, progress: float) -> tuple[tuple[pygame.Surface, int], ...] | None:
    """Mistura os fundos pintados da vila em três estágios de transformação."""
    cache = scene.watercolor_backgrounds
    if not cache:
        for name in (
            "village_industrial_v3",
            "village_transition_v3",
            "village_start_v2",
            "village_start",
            "village_intermediate",
            "village_final",
            "village_clean",
        ):
            source = scene.app.assets.sprite("watercolor", name)
            cache[name] = scene.scaled(source, (C.WIDTH, C.HEIGHT), ("watercolor", name)) if source else None
    start = cache.get("village_industrial_v3") or cache.get("village_start_v2") or cache.get("village_start")
    intermediate = cache.get("village_transition_v3") or cache["village_intermediate"] or cache["village_clean"]
    final = cache["village_final"] or cache["village_clean"] or intermediate
    if start is None and intermediate is None and final is None:
        return None
    start = start or intermediate or final
    intermediate = intermediate or start
    final = final or intermediate
    # Se o fornecedor ainda não tiver entregue os três arquivos, repete o mais
    # próximo disponível sem quebrar a vila; cada fundo continua no mesmo recorte.
    for surface in {start, intermediate, final}:
        surface.set_alpha(255)
    stage = max(0.0, min(2.0, progress * 2))
    if stage <= 1:
        base, overlay, local = start, intermediate, stage
    else:
        base, overlay, local = intermediate, final, stage - 1
    blend = local * local * (3.0 - 2.0 * local)
    if base is overlay:
        base.set_alpha(255)
        scene.watercolor_mix = None
        return ((base, 255),)
    overlay.set_alpha(round(255 * blend))
    scene.watercolor_mix = overlay
    return ((base, 255), (overlay, round(255 * blend)))


def draw_village(scene: Scene, screen: pygame.Surface, highlight: str = "") -> None:
    """Diorama ilustrado e obras localizadas (também usado na tela de cuidado)."""
    app, t = scene.app, scene.time
    progress = village_progress(app.profile)
    ensure_village_requests(app.profile)
    background_layers = _watercolor_background(scene, progress)
    illustrated = background_layers is not None
    if background_layers is None:
        draw_ground(scene, screen, progress)
    else:
        for layer, alpha in background_layers:
            layer.set_alpha(alpha)
            screen.blit(layer, (0, 0))
    prop_atlas = app.assets.sprite("watercolor", "village_props")
    scenery = app.assets.scenery
    owned = set(app.profile.vila)
    items = []  # (base y, tipo, dados): desenhados do fundo para a frente
    if not illustrated:
        # Fundo procedural legado: preserva a evolução gradual das cinco casas.
        for i, (industrial, solar, x, base_y, height) in enumerate(HOUSES):
            name = solar if progress >= (i + 0.5) / len(HOUSES) else industrial
            items.append((base_y, "house", (name, x, base_y, height, i)))
    for upgrade in VILLAGE_UPGRADES:
        x, base_y, height = SLOTS.get(upgrade.key, upgrade.slot)
        if upgrade.key in owned:
            items.append((base_y, "sprite", (upgrade.sprite, x, base_y, height, upgrade.key)))
        elif upgrade.key == highlight:
            items.append((base_y, "ghost", (upgrade.key, x, base_y, height)))
    if not illustrated:
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
            if key is not None:
                sprite = village_prop(key, prop_atlas)
                prop_height = max(112, int(height * 1.55))
                prop_width = min(int(prop_height * 1.5), max(120, 2 * min(x, C.WIDTH - x) - 8))
                img = scene.scaled(sprite, (prop_width, prop_height), ("village_prop", key, prop_width, prop_height))
            else:
                sprite = scenery.get(name)
                if sprite is None:
                    continue
                img = scene.scaled(sprite, (height * 3, height))
            rect = img.get_rect(midbottom=(x, base_y))
            if key is None or prop_atlas is None:
                paper.shadow(screen, (x, base_y - 2), int(rect.width * 0.9), max(8, int(height * 0.16)), 55)
            screen.blit(img, rect)
            if key == highlight:
                pygame.draw.rect(screen, T.SUN, rect.inflate(10, 10), 4, border_radius=12)
        elif kind == "ghost":
            key, x, base_y, height = data
            if prop_atlas is not None:
                sprite = village_prop(key, prop_atlas)
                prop_height = max(112, int(height * 1.55))
                prop_width = min(int(prop_height * 1.5), max(120, 2 * min(x, C.WIDTH - x) - 8))
                img = scene.scaled(sprite, (prop_width, prop_height), ("village_prop_preview", key)).copy()
                img.set_alpha(175)
                rect = img.get_rect(midbottom=(x, base_y))
                paper.shadow(screen, (x, base_y - 2), int(rect.width * 0.9), max(8, int(height * 0.16)), 42)
                screen.blit(img, rect)
                pygame.draw.rect(screen, T.SUN, rect.inflate(12, 12), 4, border_radius=12)
            else:
                ghost = pygame.Rect(0, 0, height, height)
                ghost.midbottom = (x, base_y)
                pygame.draw.rect(screen, T.SUN, ghost, 3, border_radius=12)
                scene.text.blit(screen, "?", ghost.center, T.SIZES["title"], T.SUN, True, "center")
        elif kind == "house":
            _name, x, base_y, height, index = data
            draw_house(screen, x, base_y, height, index, progress)
        elif kind == "tree":
            x, y, height, seed = data
            paper.tree(screen, (x, y), height, canopy, rgb("8a5a3a"), seed)
        else:
            px, py, height, shirt, phase = data
            paper.person(screen, (px, py), height, shirt, rgb("e8b48a"), phase)
    _draw_village_neighbors(scene, screen, prop_atlas, highlight)
    if not illustrated:
        paper.smoke(screen, (1035, 150), t, 1.0 - progress, 1)
        paper.sparkles(screen, pygame.Rect(0, 280, C.WIDTH, 220), t, progress, rgb("f6c33b"))


def _draw_village_neighbors(scene: Scene, screen: pygame.Surface, prop_atlas, highlight: str) -> None:
    """Moradores apresentam pedidos persistentes por pictogramas no cenário."""
    app, profile = scene.app, scene.app.profile
    requests = profile.pedidos_vila
    states = [(u, requests.get(u.key, "solicitada")) for u in VILLAGE_UPGRADES]
    visible = [(u, state) for u, state in states if state == "solicitada"][:3]
    if len(visible) < 3:
        visible.extend([(u, state) for u, state in states if state == "concluida"][: 3 - len(visible)])
    atlas = app.assets.sprite("watercolor", "villagers_sprint3")
    looks = (
        {**DEFAULT_PILOT, "pele": "pele2", "cabelo": "cacheado", "cor_cabelo": "castanho", "roupa": "verde"},
        {**DEFAULT_PILOT, "pele": "pele5", "cabelo": "crespo", "cor_cabelo": "preto", "roupa": "amarela"},
        {**DEFAULT_PILOT, "pele": "pele3", "cabelo": "trancas", "cor_cabelo": "ruivo", "roupa": "azul"},
    )
    for index, (upgrade, state) in enumerate(visible):
        person_x, person_y = VILLAGE_NEIGHBOR_POSITIONS[index]
        pose = "pedido" if state == "solicitada" else "feliz"
        npc = village_resident(atlas, index % 2, pose)
        if npc is not None:
            image = _fit_resident(scene, npc, (68, 90), ("villager-sprint3", index % 2, pose))
        else:
            expression = "curious" if state == "solicitada" else "happy"
            source = app.view.skin.pilots.compose("menu", normalize_pilot(looks[index]), expression=expression)
            if source is None:
                continue
            image = _fit_resident(scene, source, (68, 90), ("villager-fallback", index, expression))
        bob = 0 if app.options.reduzir_movimento else round(2 * math.sin(scene.time * 3.2 + index * 1.8))
        screen.blit(image, image.get_rect(midbottom=(person_x, person_y + bob)))
        bubble = pygame.Rect(person_x - 24, person_y - 132 + bob, 48, 42)
        pygame.draw.ellipse(screen, paper.INK, bubble.inflate(4, 4))
        pygame.draw.ellipse(screen, (250, 243, 222), bubble)
        pygame.draw.polygon(
            screen,
            (250, 243, 222),
            ((person_x - 2, bubble.bottom - 2), (person_x + 4, bubble.bottom + 7), (person_x + 7, bubble.bottom - 3)),
        )
        icon = scene.scaled(village_prop(upgrade.key, prop_atlas), (34, 32), ("village-request-icon", upgrade.key))
        screen.blit(icon, icon.get_rect(center=bubble.center))
        if state == "concluida":
            mark = (bubble.right - 3, bubble.top + 2)
            pygame.draw.circle(screen, (66, 160, 95), mark, 8)
            pygame.draw.lines(
                screen,
                (255, 255, 245),
                False,
                [(mark[0] - 4, mark[1]), (mark[0] - 1, mark[1] + 3), (mark[0] + 4, mark[1] - 4)],
                2,
            )
        elif upgrade.key == highlight:
            pygame.draw.ellipse(screen, (246, 195, 59), bubble.inflate(8, 8), 3)


def _fit_resident(scene: Scene, source: pygame.Surface, bounds, key) -> pygame.Surface:
    """Preserva a proporção do atlas: cabeças e corpos não são achatados."""
    width, height = bounds
    factor = min(width / max(1, source.get_width()), height / max(1, source.get_height()))
    size = max(1, round(source.get_width() * factor)), max(1, round(source.get_height() * factor))
    return scene.scaled(source, size, ("villager-fit", key, size))


class VillageScene(Scene):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.confirm_exit = False  # ESC na vila pergunta se é para sair do jogo

    def enter(self) -> None:
        changed = ensure_village_requests(self.app.profile)
        super().enter()
        if changed:
            self.app.save()

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

        # Alvos grandes, separados para que as zonas de retenção do dwell não se
        # sobreponham. Opções e créditos ficam atrás do destino secundário.
        pilot_look = self.app.profile.piloto
        pilot_face = self.app.view.skin.pilots.compose("menu", pilot_look, expression="curious")
        pilot_icon = destination_icon("piloto")
        if pilot_face is not None:
            head = pygame.Rect(
                round(pilot_face.get_width() * 0.12),
                0,
                max(1, round(pilot_face.get_width() * 0.76)),
                max(1, round(pilot_face.get_height() * 0.29)),
            )
            pilot_icon = pygame.transform.smoothscale(pilot_face.subsurface(head).copy(), (48, 48))
        self.menu.set_buttons(
            [
                self.button(
                    (25, 548, 210, 86),
                    "VOAR",
                    lambda: self.goto("mapa"),
                    icon=destination_icon("voar"),
                    color=T.ORANGE,
                    key="voar",
                    size=T.SIZES["label"],
                ),
                self.button(
                    (295, 548, 210, 86),
                    "HANGAR",
                    lambda: self.goto("hangar"),
                    icon=destination_icon("hangar"),
                    key="hangar",
                    size=T.SIZES["label"],
                ),
                self.button(
                    (565, 548, 210, 86),
                    "PILOTO",
                    lambda: self.goto("piloto"),
                    icon=pilot_icon,
                    key="piloto",
                    size=T.SIZES["label"],
                ),
                self.button(
                    (835, 548, 210, 86),
                    "CUIDAR",
                    lambda: self.goto("melhorias"),
                    icon=destination_icon("cuidar"),
                    color=T.GREEN,
                    key="cuidar",
                    size=T.SIZES["label"],
                ),
                self.button((730, 12, 130, 48), "Opções", lambda: self.goto("opcoes"), key="opcoes"),
                self.button((922, 12, 130, 48), "Sobre", lambda: self.goto("sobre"), key="sobre"),
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
            backgrounds = self.watercolor_backgrounds
            painted = any(backgrounds.get(name) is not None for name in ("village_start_v2", "village_start"))
            plane_size = (225, 150) if painted else (250, 170)
            img = self.scaled(plane, plane_size, key)
            bob = math.sin(self.time * 2.2) * 6
            paper.shadow(screen, (SQUARE[0], SQUARE[1] + 3), int(img.get_width() * 0.88) - int(bob * 3), 34, 60)
            screen.blit(img, img.get_rect(center=(SQUARE[0], int((340 if painted else 330) + bob))))
        progress = village_progress(profile)
        # Cabeçalho sólido: título e progresso não se perdem sobre os detalhes do fundo.
        header = pygame.Rect(16, 12, 410, 110)
        T.panel(screen, header, T.PAPER, T.NAVY, 248, 18, 3)
        self.text.blit(screen, "Sua vila", (32, 20), T.SIZES["title"], T.NAVY, True)
        self.text.blit(
            screen,
            f"{profile.total_stars()} / {3 * len(BIOMES)} estrelas · {MODE_LABELS[profile.modo]}",
            (32, 64),
            T.SIZES["small"],
            T.NAVY,
            True,
        )
        self.text.blit(screen, f"{int(progress * 100)}% sustentável", (235, 55), T.SIZES["small"], T.INK, True)
        bar = pygame.Rect(235, 82, 180, 16)
        pygame.draw.rect(screen, T.PAPER, bar, border_radius=8)
        pygame.draw.rect(screen, T.TEAL, (bar.left, bar.top, int(bar.width * progress), bar.height), border_radius=8)
        self.resource_bar(screen, right=710, top=16)
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
