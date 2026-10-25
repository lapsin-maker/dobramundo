"""Contratos das paisagens: eras completas, fallback e movimento opcional."""

import pygame
import pytest

from dobramundo.content.biomes import BIOMES
from dobramundo.engine.assets import Assets
from dobramundo.engine.watercolor import WatercolorWorld
from dobramundo.game.world import World


@pytest.mark.parametrize("biome", ["amazonia", "caatinga"])
def test_each_city_has_three_distinct_complete_stages(biome, display):
    painter = WatercolorWorld(Assets())
    stages = [painter.backdrop(biome, value) for value in (12, 53, 88)]
    assert all(surface is not None for surface in stages)
    fingerprints = [pygame.image.tostring(surface, "RGB") for surface in stages]
    assert len(set(fingerprints)) == 3
    # Redesenhar um estado estável não transforma ou aloca outra paisagem.
    assert painter.backdrop(biome, 88) is stages[2]


def test_reduced_motion_stops_parallax_and_flow_but_keeps_progress(display):
    painter = WatercolorWorld(Assets())
    world = World(BIOMES["amazonia"])
    world.set_restoration(12)
    assert painter.draw(display, world, -100, True)
    original = pygame.image.tostring(display, "RGB")
    world.distance += 400
    assert painter.draw(display, world, 100, True)
    assert pygame.image.tostring(display, "RGB") == original
    world.set_restoration(88)
    painter.draw(display, world, 100, True)
    assert pygame.image.tostring(display, "RGB") != original


def test_incomplete_art_pack_uses_entire_procedural_fallback(monkeypatch, display):
    assets = Assets()
    monkeypatch.setattr(assets, "folder", lambda *_: {"amazonia_0": display})
    painter = WatercolorWorld(assets)
    assert painter.backdrop("amazonia", 12) is None


def test_transition_never_mutates_source_art(display):
    painter = WatercolorWorld(Assets())
    layers = painter.load("caatinga")
    before = [(surface.get_alpha(), pygame.image.tostring(surface, "RGB")) for surface in layers]
    for value in (34, 38, 44, 68, 72, 76):
        assert painter.backdrop("caatinga", value) is not None
    assert before == [(surface.get_alpha(), pygame.image.tostring(surface, "RGB")) for surface in layers]
