"""Contratos de memória/carregamento e composição sem depender do tempo da máquina."""

from __future__ import annotations

from pathlib import Path

import pygame
import pytest

from dobramundo import config as C
from dobramundo import core
from dobramundo.content.biomes import BIOMES
from dobramundo.engine.assets import SCENERY_FOLDERS, Assets, load_image
from dobramundo.engine.cache import BoundedCache
from dobramundo.engine.painted_pilot import PaintedPilot
from dobramundo.engine.watercolor import WatercolorWorld
from dobramundo.engine.world_view import WorldView
from dobramundo.scenes.base import Scene


def test_pilot_loads_its_layers_without_decoding_other_scenes(display):
    assets = Assets()
    painter = PaintedPilot(assets)
    assert painter.available
    assert not assets._loaded  # atlas descartados depois de recortar poses e camadas
    assert not any("pilot_" in str(path) for path in assets._loaded)
    assert not {"pilot_base", "pilot_hair_front", "pilot_hair_back", "pilot_mobility"} & set(painter.sprites)
    assert not any("front_standing" in source_cache for source_cache in assets._folders.values())


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


def test_bounded_cache_respects_decoded_pixel_budget_and_dict_mutators(display):
    cache = BoundedCache(10, byte_limit=512)
    surfaces = [pygame.Surface((8, 8)) for _ in range(4)]
    cache.update({"a": surfaces[0], "b": surfaces[1]})
    assert cache.bytes == 512
    cache.setdefault("c", surfaces[2])
    assert cache.bytes == 512 and "a" not in cache
    cache.popitem()
    assert cache.bytes == 512 - surfaces[2].get_pitch() * surfaces[2].get_height()
    cache |= {"too-large": pygame.Surface((40, 40))}
    assert "too-large" not in cache
    cache.clear()
    assert not cache and cache.bytes == 0
    with pytest.raises(TypeError):
        cache.pop("missing", None, None)


def test_assets_release_folder_drops_decoded_reference_and_reload_is_clean(display, tmp_path, monkeypatch):
    source_dir = tmp_path / "override-assets"
    source_dir.mkdir()
    image = pygame.Surface((24, 18), pygame.SRCALPHA)
    image.fill((20, 60, 100, 255))
    pygame.image.save(image, str(source_dir / "fixture.png"))
    monkeypatch.setattr("dobramundo.engine.assets.asset_dir_candidates", lambda name: [source_dir])
    assets = Assets()
    first = assets.sprite("watercolor", "fixture")
    assert first is not None and assets.cache_stats()["loaded_images"] == 1
    assert assets.release_folder("watercolor", ("fixture",)) == 1
    assert assets.cache_stats()["loaded_images"] == 0
    second = assets.sprite("watercolor", "fixture")
    assert second is not None and second.get_size() == image.get_size()


def test_world_view_defers_scenery_and_releases_active_biome_cache(display):
    assets = Assets()
    view = WorldView(assets)
    assert assets._scenery is None
    assert not any(Path(path).parent.name in SCENERY_FOLDERS for path in assets._loaded)

    view.set_biome(BIOMES["amazonia"])
    view.ensure_scenery()
    active_count = sum(Path(path).parent.name in SCENERY_FOLDERS for path in assets._loaded)
    assert active_count > 0
    view.release_biome_cache("amazonia")
    assert view.biome is None and not view.scenery
    assert sum(Path(path).parent.name in SCENERY_FOLDERS for path in assets._loaded) < active_count


def test_prepared_backdrop_raster_matches_original_runtime_scale(display):
    assets = Assets()
    prepared = assets.sprite("watercolor_prepared", "amazonia_0")
    source = assets.sprite("watercolor", "amazonia_0")
    assert prepared is not None and source is not None
    expected = pygame.transform.smoothscale(source, (C.WIDTH + 32, C.HEIGHT))
    assert pygame.image.tobytes(prepared, "RGB") == pygame.image.tobytes(expected, "RGB")


def test_prepared_backdrop_release_removes_only_source_cache_entries(display):
    painter = WatercolorWorld(Assets())
    layers = painter.load("amazonia")
    assert len(layers) == 3 and all(layer.get_size() == (C.WIDTH + 32, C.HEIGHT) for layer in layers)
    assert not any("amazonia_0" in key for key in painter.assets._loaded)


def test_prepared_plane_atlas_is_used_and_original_fallback_remains(display, monkeypatch):
    from dobramundo.content.planes import PLANE_KEYS
    from dobramundo.engine.painted_planes import PaintedPlanes

    source = pygame.Surface((100, 100), pygame.SRCALPHA)
    pygame.draw.polygon(
        source,
        (70, 100, 130, 255),
        [(45, 2), (35, 25), (40, 27), (35, 48), (65, 48), (60, 27), (65, 25)],
    )
    prepared = source.copy()

    class FakeAssets:
        def __init__(self, prepared_available):
            self.prepared_available = prepared_available
            self.lookups = []

        def sprite(self, folder, name):
            self.lookups.append((folder, name))
            if folder == "watercolor_prepared" and self.prepared_available:
                return prepared
            if folder == "watercolor":
                return source
            return None

    for prepared_available, expected_folder in ((True, "watercolor_prepared"), (False, "watercolor")):
        assets = FakeAssets(prepared_available)
        atlas = PaintedPlanes(assets)._atlas(PLANE_KEYS[0], "flight")
        assert atlas is not None
        assert (expected_folder, "planes_flight_a_clean") in assets.lookups


def test_prepared_aircraft_atlases_are_recorded_with_runtime_dimensions():
    from dobramundo.engine.assets import Assets

    assets = Assets()
    image = assets.sprite("watercolor_prepared", "planes_flight_a_clean")
    assert image is not None and image.get_size() == (768, 512)


def test_theme_tags_bias_only_existing_stage_scenery():
    from types import SimpleNamespace

    from dobramundo.game.challenges import ChallengeTheme

    specs = [("AM_Samauma", 420.0), ("CA_Aerogerador", 360.0), ("CA_Mangueira", 250.0)]
    tree_theme = SimpleNamespace(challenge_theme=ChallengeTheme("trees", "Árvores", "low", ("trees",)))
    combined_theme = SimpleNamespace(challenge_theme=ChallengeTheme("wind", "Energia", "tower", ("trees", "wind")))
    green = WorldView.theme_specs(tree_theme, specs, "green")
    solar = WorldView.theme_specs(combined_theme, specs, "solar")
    assert green.count(specs[0]) > specs.count(specs[0])
    assert solar.count(specs[0]) > specs.count(specs[0])
    assert solar.count(specs[1]) > specs.count(specs[1])
    assert solar.count(specs[2]) == specs.count(specs[2])
