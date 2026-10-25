"""Contratos de memória/carregamento e composição sem depender do tempo da máquina."""

from __future__ import annotations

import pygame
import pytest

from dobramundo import core
from dobramundo.engine.assets import Assets, load_image
from dobramundo.engine.painted_pilot import PaintedPilot
from dobramundo.engine.watercolor import WatercolorWorld
from dobramundo.scenes.base import Scene


def test_pilot_loads_its_layers_without_decoding_other_scenes(display):
    assets = Assets()
    painter = PaintedPilot(assets)
    assert painter.available
    loaded = {path.replace("\\", "/").rsplit("/", 1)[-1] for path in assets._loaded}
    assert loaded == {"pilot_base.png", "pilot_hair_front.png", "pilot_hair_back.png", "pilot_mobility.png"}
    source_cache = next(iter(assets._folders.values()))
    assert "front_standing" not in source_cache  # pose derivada não contamina a biblioteca


@pytest.mark.parametrize("hole", [False, True])
def test_opaque_conversion_preserves_interior_transparency(display, tmp_path, hole):
    source = pygame.Surface((16, 16), pygame.SRCALPHA)
    source.fill((30, 80, 190, 255))
    if hole:
        source.set_at((8, 8), (30, 80, 190, 80))
    path = tmp_path / "opacity.png"
    pygame.image.save(source, str(path))
    loaded = load_image(path)
    assert bool(loaded.get_flags() & pygame.SRCALPHA) == hole
    assert loaded.get_at((8, 8)) == source.get_at((8, 8))


@pytest.mark.parametrize("city", ["amazonia", "caatinga"])
def test_transition_culls_only_pixels_hidden_by_ground(display, city):
    painter = WatercolorWorld(Assets())
    cutoff = painter.route.ground.rows[0][0]
    for visual in (34, 40, 47, 68, 73, 78):
        full = painter.backdrop(city, visual)
        horizon = painter.backdrop(city, visual, cutoff)
        rect = pygame.Rect(0, 0, full.get_width(), cutoff)
        assert pygame.image.tobytes(full.subsurface(rect), "RGB") == pygame.image.tobytes(
            horizon.subsurface(rect), "RGB"
        )


def test_contrast_reuses_buffers_and_updates_contents(app):
    app.canvas.fill((240, 20, 80))
    app.view.desaturate(app.canvas)
    before = app.canvas.get_at((10, 10))
    buffers = app.view.gray_buffers
    app.canvas.fill((20, 230, 70))
    app.view.desaturate(app.canvas)
    assert app.view.gray_buffers is buffers
    assert app.canvas.get_at((10, 10)) != before  # nunca congelar cenário cinza em cache


def test_warmup_does_not_start_after_expensive_frame(app, monkeypatch):
    app.go(Scene(app))
    times = iter((1.0, 1.020))
    monkeypatch.setattr(core.time, "perf_counter", lambda: next(times))
    budgets = []
    monkeypatch.setattr(app.view, "step_warm_up", budgets.append)
    app.advance(1 / 60, [])
    assert budgets == [0.0]
