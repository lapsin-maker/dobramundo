"""Regressão do fundo estático: o cenário inteiro deve avançar com o voo."""

import pygame
import pytest

from dobramundo.content.biomes import BIOMES
from dobramundo.engine.assets import Assets
from dobramundo.engine.watercolor import WatercolorWorld
from dobramundo.game.world import World


def prepare_mobile(painter, biome):
    for stage in range(3):
        painter.prepare_backdrop(biome, stage)
    painter.route.prepare_ground()
    for index in range(12):
        painter.route.prepare_bank(biome, index)
    painter.life.prepare()


@pytest.mark.parametrize("biome", ["amazonia", "caatinga"])
@pytest.mark.parametrize("reduced", [False, True])
def test_large_ground_area_moves_without_any_entities(display, biome, reduced):
    painter = WatercolorWorld(Assets())
    world = World(BIOMES[biome])
    prepare_mobile(painter, biome)
    world.entities.clear()
    painter.draw(display, world, 0, reduced)
    before = [display.get_at((x, y)) for y in range(300, 650, 5) for x in range(200, 900, 5)]
    world.distance += 170  # um segundo na velocidade normal, sem mexer a câmera
    painter.draw(display, world, 0, reduced)
    after = [display.get_at((x, y)) for y in range(300, 650, 5) for x in range(200, 900, 5)]
    changed = sum(sum(abs(a[i] - b[i]) for i in range(3)) > 20 for a, b in zip(before, after))
    assert changed / len(before) > 0.55  # não basta um punhado de linhas/partículas


def test_banks_approach_with_same_world_distance_and_repeat_continuously(display):
    route = WatercolorWorld(Assets()).route
    before = route.placements(10, 0)
    after = route.placements(50, 0)
    assert all((z - 40, x, index, side) in after for z, x, index, side in before if z - 40 >= 60)
    assert before == route.placements(10 + route.SPACING * 48, 0)


def test_pause_freezes_route_and_drawing_does_not_change_game_state(display):
    painter = WatercolorWorld(Assets())
    world = World(BIOMES["amazonia"])
    original = world.distance, list(world.entities), world.visual
    painter.draw(display, world, 0)
    picture = pygame.image.tostring(display, "RGB")
    painter.draw(display, world, 0)
    assert picture == pygame.image.tostring(display, "RGB")
    assert original == (world.distance, list(world.entities), world.visual)


def test_ground_rescales_only_small_bands_never_full_images_in_flight(display, monkeypatch):
    painter = WatercolorWorld(Assets())
    world = World(BIOMES["caatinga"])
    painter.route.prepare_ground()
    ground = painter.route.ground
    assert ground is not None
    ground.paint(display, world.biome.key, 0, 0, (230, 220, 190))

    def forbidden(*args, **kwargs):
        raise AssertionError("chão deve usar as faixas já preparadas")

    original_scale = pygame.transform.scale

    def scale_band(source, size, dest=None):
        assert source.get_width() == 1024 and source.get_height() == 3 and size[1] == 3
        return original_scale(source, size, dest)

    monkeypatch.setattr(pygame.transform, "scale", scale_band)
    monkeypatch.setattr(pygame.transform, "smoothscale", forbidden)
    monkeypatch.setattr(pygame.image, "load", forbidden)
    for distance in (1, 2, 100, 1300, 10000):
        ground.paint(display, world.biome.key, distance, 55, (230, 220, 190))


@pytest.mark.parametrize("size", [(1, 1), (40, 30)])
def test_empty_or_tiny_bank_atlas_falls_back_instead_of_dividing_by_zero(display, monkeypatch, size):
    assets = Assets()
    original = assets.sprite
    empty = pygame.Surface(size, pygame.SRCALPHA)
    monkeypatch.setattr(
        assets, "sprite", lambda folder, name: empty if name.startswith("banks_") else original(folder, name)
    )
    painter = WatercolorWorld(assets)
    assert painter.draw(display, World(BIOMES["amazonia"]), 0) is False


def test_missing_mobile_atlas_warms_procedural_fallback(app):
    app.view.watercolor.route.ground = None
    app.view.set_biome(BIOMES["amazonia"])
    assert len(list(app.view.warm_tasks())) > 10
