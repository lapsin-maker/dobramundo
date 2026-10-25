"""Cobertura dos estágios pintados e do ciclo visual de obra da vila."""

from __future__ import annotations

import pygame

from dobramundo.content.progress import VILLAGE_UPGRADES
from dobramundo.engine.village_art import VILLAGE_PROP_ORDER, village_prop
from dobramundo.scenes.result import ResultScene
from dobramundo.scenes.upgrades import UpgradesScene
from dobramundo.scenes.village import SLOTS, VillageScene, _watercolor_background, draw_village


def test_atlas_village_props_uses_declared_four_by_two_order():
    atlas = pygame.Surface((401, 203), pygame.SRCALPHA)
    atlas.fill((0, 0, 0, 0))
    for index, _key in enumerate(VILLAGE_PROP_ORDER):
        col, row = index % 4, index // 4
        left, right = col * atlas.get_width() // 4, (col + 1) * atlas.get_width() // 4
        top, bottom = row * atlas.get_height() // 2, (row + 1) * atlas.get_height() // 2
        rect = pygame.Rect(left, top, right - left, bottom - top)
        atlas.fill((index + 1, 0, 0, 255), rect)

    item = village_prop("cisterna", atlas)
    turbine = village_prop("turbina", atlas)

    assert item.get_size() == (100, 102)
    assert item.get_at((50, 50)) == pygame.Color(5, 0, 0, 255)
    assert turbine.get_size() == (101, 102)
    assert turbine.get_at((100, 101)) == pygame.Color(8, 0, 0, 255)


def test_background_blends_start_intermediate_and_final_stages(app):
    scene = VillageScene(app)
    scene.watercolor_backgrounds = {
        "village_start": pygame.Surface((8, 8)),
        "village_intermediate": pygame.Surface((8, 8)),
        "village_final": pygame.Surface((8, 8)),
        "village_clean": None,
    }

    early = _watercolor_background(scene, 0.25)
    late = _watercolor_background(scene, 0.75)

    assert early is not None and early[0][0] is scene.watercolor_backgrounds["village_start"]
    assert early[1][0] is scene.watercolor_backgrounds["village_intermediate"]
    assert early[1][1] in range(126, 130)
    assert late is not None and late[0][0] is scene.watercolor_backgrounds["village_intermediate"]
    assert late[1][0] is scene.watercolor_backgrounds["village_final"]
    assert late[1][1] in range(126, 130)


def test_purchase_animates_once_and_reduced_motion_shows_static_comparison(app):
    upgrade = VILLAGE_UPGRADES[0]
    app.profile.recursos.update({key: amount + 8 for key, amount in upgrade.cost.items()})
    before = dict(app.profile.recursos)
    app.options.reduzir_movimento = True
    scene = UpgradesScene(app)
    scene.build()
    scene.select_upgrade(upgrade.key)
    expected_before = scene._capture_village()

    scene.confirm_purchase()
    after = dict(app.profile.recursos)
    assert scene.reveal_key == upgrade.key
    assert scene.reveal_before is not None and scene.reveal_after is not None
    assert pygame.image.tobytes(scene.reveal_before, "RGBA") == pygame.image.tobytes(expected_before, "RGBA")
    assert all(after[key] == before[key] - amount for key, amount in upgrade.cost.items())
    scene.confirm_purchase()
    assert app.profile.recursos == after
    scene.draw(app.canvas)
    assert scene.menu.focused is not None and scene.menu.focused.key == "continuar"


def test_result_cta_opens_the_next_build_preview(app, run):
    upgrade = VILLAGE_UPGRADES[0]
    app.profile.recursos.update({key: amount + 1 for key, amount in upgrade.cost.items()})
    result = ResultScene(app, run)
    result.build()

    action = next(button for button in result.menu.buttons if button.key == "vila_proxima_obra")
    assert action.label == "Construir na vila"
    action.action()
    next_scene = app.next_scene
    next_scene.build()
    assert isinstance(next_scene, UpgradesScene)
    assert next_scene.selected_key == upgrade.key
    assert next_scene.menu.focused is not None and next_scene.menu.focused.key == "confirmar"


def test_proxima_obra_mostra_a_propria_previa_no_terreno(app):
    upgrade = VILLAGE_UPGRADES[1]
    scene = VillageScene(app)
    plain = pygame.Surface(app.canvas.get_size(), pygame.SRCALPHA)
    marked = pygame.Surface(app.canvas.get_size(), pygame.SRCALPHA)
    draw_village(scene, plain)
    draw_village(scene, marked, upgrade.key)
    x, base_y, height = SLOTS[upgrade.key]
    area = pygame.Rect(x - 120, base_y - height * 2 - 20, 240, height * 2 + 30)
    changed_pixels = sum(
        plain.get_at((px, py)) != marked.get_at((px, py))
        for px in range(area.left, area.right)
        for py in range(area.top, area.bottom)
    )
    assert changed_pixels > 5_000
