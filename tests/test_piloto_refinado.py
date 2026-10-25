"""QA focado no refinamento painterly do piloto e seu editor."""

from __future__ import annotations

import pygame

from dobramundo.content.pilot import DEFAULT_PILOT, UNSELECTED
from dobramundo.engine.painted_pilot import POSES, PaintedPilot
from dobramundo.engine.paper_pilot import SIZE, draw_pilot
from dobramundo.scenes.pilot import PAGE_BY_FIELD, PREVIEW, PilotScene


def test_renderer_pictorico_e_deterministico_nas_quatro_vistas():
    look = {**DEFAULT_PILOT, "pele": "pele4", "cabelo": "trancas", "cor_cabelo": "castanho"}
    for view in ("menu", "flight", "segura", "lanca"):
        first = draw_pilot(view, look)
        second = draw_pilot(view, look)
        assert first.get_size() == SIZE
        assert first.get_bounding_rect(min_alpha=1).width >= 135
        assert pygame.image.tobytes(first, "RGBA") == pygame.image.tobytes(second, "RGBA")


def test_rosto_opcoes_e_mobilidade_alteram_o_retrato():
    base = {**DEFAULT_PILOT, "pele": "pele4", "cabelo": "crespo", "olhos": "verdes"}
    neutral = draw_pilot("menu", base)
    glasses = draw_pilot("menu", {**base, "oculos": "redondo"})
    wheelchair = draw_pilot("menu", {**base, "cadeira": "sim"})
    walker = draw_pilot("menu", {**base, "andador": "sim"})
    assert len({pygame.image.tobytes(i, "RGBA") for i in (neutral, glasses, wheelchair, walker)}) == 4


def test_primeiro_acesso_permanece_sem_preselecionar_identidade():
    image = draw_pilot("menu", DEFAULT_PILOT)
    assert DEFAULT_PILOT["pele"] == DEFAULT_PILOT["cabelo"] == UNSELECTED
    assert image.get_bounding_rect(min_alpha=1).height > 200


def test_abas_tem_pictogramas_e_retrato_ampliado(app):
    scene = PilotScene(app, first_time=True)
    scene.build()
    buttons = {button.key: button for button in scene.menu.buttons}
    nav = [buttons[f"page:{field}"] for field in PAGE_BY_FIELD]
    assert all(button.icon is not None and button.icon.get_width() == 28 for button in nav)
    assert PREVIEW.width >= 300
    assert all(button.rect.right <= 1076 for button in nav)


class _FakeAssets:
    def __init__(self, sprites):
        self.sprites = sprites

    def folder(self, name, names=None):
        assert name == "watercolor"
        return {key: value for key, value in self.sprites.items() if names is None or key in names}


def test_loader_de_poses_watercolor_recoloreia_mas_preserva_pigmento():
    skin_key = (238, 198, 167)
    shirt_key = (145, 190, 205)
    source = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(source, (*skin_key, 255), (2, 2, 10, 26))
    pygame.draw.rect(source, (*shirt_key, 255), (20, 2, 10, 26))
    source.set_at((5, 5), (248, 207, 176, 255))  # pigment variation near the skin swatch
    painter = PaintedPilot(_FakeAssets({"front_standing": source}), skin_key=skin_key, shirt_key=shirt_key)
    look = {**DEFAULT_PILOT, "pele": "pele4", "roupa": "vermelha"}
    result = painter.compose("menu", look)
    assert result is not None and result is not source
    assert result.get_at((5, 5)) != source.get_at((5, 5))
    assert result.get_at((16, 16)).a == 0
    assert painter.compose("menu", look) is result  # tinted render cached by selected look


def test_pose_selection_uses_sitting_art_only_for_wheelchair():
    assert POSES["menu"] == ("front_standing", "front_seated")
    assert PaintedPilot.pose_key("flight", {"cadeira": "sim"}) == "back_seated"
    assert PaintedPilot.pose_key("flight", {"cadeira": "nao"}) == "back_standing"


def test_loader_watercolor_incompleto_retorna_none_para_fallback():
    painter = PaintedPilot(_FakeAssets({}))
    assert not painter.available
    assert painter.compose("menu", DEFAULT_PILOT) is None


def test_atlas_quatro_vistas_corta_grade_2_por_2():
    atlas = pygame.Surface((16, 16), pygame.SRCALPHA)
    colors = ((200, 20, 20), (20, 200, 20), (20, 20, 200), (200, 200, 20))
    for i, color in enumerate(colors):
        pygame.draw.rect(atlas, color, ((i % 2) * 8, (i // 2) * 8, 8, 8))
    painter = PaintedPilot(_FakeAssets({"pilot_base": atlas}))
    assert painter.sprites["front_standing"].get_at((1, 1))[:3] == colors[0]
    assert painter.sprites["back_standing"].get_at((1, 1))[:3] == colors[1]
    assert painter.sprites["front_seated"].get_at((1, 1))[:3] == colors[2]
    assert painter.sprites["back_seated"].get_at((1, 1))[:3] == colors[3]


def test_atlas_cabelos_tem_doze_estilos_em_frente_e_costas():
    def hair_sheet(offset):
        sheet = pygame.Surface((48, 36), pygame.SRCALPHA)
        for index in range(12):
            color = (60 + index * 10, 35 + offset, 24, 255)
            pygame.draw.ellipse(sheet, color, ((index % 4) * 12 + 2, (index // 4) * 12 + 2, 8, 8))
        return sheet

    painter = PaintedPilot(_FakeAssets({"pilot_hair_front": hair_sheet(0), "pilot_hair_back": hair_sheet(12)}))
    assert len(painter.hair_sprites) == 24
    assert ("front", "crespo") in painter.hair_sprites
    assert ("back", "hijab") in painter.hair_sprites


def test_voo_pode_usar_pose_sentada_sem_mudar_dispositivo():
    source = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(source, (200, 120, 80, 255), (2, 2, 28, 28))
    from dobramundo.engine.pilot import PilotRenderer

    class AssetsWithPilot(_FakeAssets):
        @staticmethod
        def json(folder, filename):
            return {"body": {"flight": (0, 0, 32, 32)}}

    sprites = {
        "front_standing": source,
        "back_standing": source.copy(),
        "front_seated": source.copy(),
        "back_seated": source.copy(),
    }
    renderer = PilotRenderer(AssetsWithPilot(sprites))
    standing = renderer.compose("flight", DEFAULT_PILOT)
    seated = renderer.compose("flight", DEFAULT_PILOT, pose="back_seated")
    assert standing is not None and seated is not None
    assert standing is not seated


def test_segura_e_lanca_nao_compartilham_cache_de_vista():
    source = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.ellipse(source, (220, 168, 127, 255), (4, 2, 24, 28))
    sprites = {name: source.copy() for name in ("front_standing", "back_standing")}
    painter = PaintedPilot(_FakeAssets(sprites))
    held = painter.compose("segura", DEFAULT_PILOT)
    thrown = painter.compose("lanca", DEFAULT_PILOT)
    assert held is not None and thrown is not None
    assert pygame.image.tobytes(held, "RGBA") != pygame.image.tobytes(thrown, "RGBA")


def test_atlas_de_dispositivos_fornece_cadeira_e_andador_pintados():
    base = pygame.Surface((32, 32), pygame.SRCALPHA)
    pygame.draw.rect(base, (200, 120, 80, 255), (6, 2, 20, 29))
    devices = pygame.Surface((32, 32), pygame.SRCALPHA)
    for index, color in enumerate(((40, 100, 140), (60, 130, 150), (75, 145, 160), (85, 155, 170))):
        pygame.draw.rect(devices, (*color, 255), ((index % 2) * 16 + 2, (index // 2) * 16 + 2, 12, 12))
    sprites = {
        "front_standing": base,
        "back_standing": base.copy(),
        "front_seated": base.copy(),
        "back_seated": base.copy(),
        "pilot_mobility": devices,
    }
    painter = PaintedPilot(_FakeAssets(sprites))
    assert len(painter.mobility_sprites) == 4
    chair = painter.compose("menu", {**DEFAULT_PILOT, "cadeira": "sim"})
    walker = painter.compose("menu", {**DEFAULT_PILOT, "andador": "sim"})
    assert chair is not None and walker is not None
    assert chair.get_size() != walker.get_size()
