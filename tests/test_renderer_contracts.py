"""O desenho aceita dados de leitura sem importar regras de voo."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pygame

from dobramundo.content.biomes import BIOMES
from dobramundo.engine.assets import Assets
from dobramundo.engine.contracts import RenderContext
from dobramundo.engine.world_view import WorldView


def test_renderer_import_does_not_import_game_rules():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import dobramundo.engine.world_view; "
            "assert not any(k.startswith('dobramundo.game.') for k in sys.modules)",
        ],
        env=dict(os.environ, PYGAME_HIDE_SUPPORT_PROMPT="1"),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_background_composition_consumes_typed_frame_context(display, monkeypatch):
    view = WorldView(Assets())
    world = SimpleNamespace(biome=BIOMES["amazonia"])
    context = RenderContext(world, 42.0, 3.5, True, True, 1.4)
    seen = []
    monkeypatch.setattr(
        view.watercolor,
        "draw",
        lambda screen, state, cam, reduced: seen.append((state, cam, reduced)) or True,
    )
    monkeypatch.setattr(view, "desaturate", lambda screen: seen.append("contrast"))

    view.compose_background(display, context)

    assert seen == [(world, 42.0, True), "contrast"]
    assert view.cam == 42.0


def test_entity_bounds_come_from_read_contract(monkeypatch):
    pygame.init()
    pygame.display.set_mode((8, 8))
    view = WorldView(Assets())
    view.show_hitboxes = True
    monkeypatch.setattr(view.watercolor, "has_backdrop", lambda key: True)
    monkeypatch.setattr(view.paper_items, "draw", lambda *args: None)
    bounds = SimpleNamespace(x_min=-10, x_max=10, y_min=20, y_max=40, z_min=200, z_max=220)
    observed = []
    entity = SimpleNamespace(hitbox=lambda: observed.append(bounds) or bounds)
    view.draw_entity(pygame.Surface((100, 100)), SimpleNamespace(biome=BIOMES["amazonia"]), entity)
    assert observed == [bounds]


def test_switch_biome_releases_previous_backgrounds():
    pygame.init()
    pygame.display.set_mode((8, 8))
    view = WorldView(Assets())
    view.set_biome(BIOMES["amazonia"])
    sky_only = {decor.sprite for decor in BIOMES["amazonia"].sky_decor}
    sky_only.add(BIOMES["amazonia"].horizon_vehicle[0])
    assert not sky_only & {Path(path).stem for path in view.assets._loaded}
    for name in sky_only:
        view.sky.prepare_decor(name)
    assert sky_only & {Path(path).stem for path in view.assets._loaded}
    view.watercolor.load("amazonia")
    assert "amazonia" in view.watercolor.backdrops
    view.set_biome(BIOMES["caatinga"])
    assert "amazonia" not in view.watercolor.backdrops
    assert view.biome is BIOMES["caatinga"]
    previous_only = sky_only - {decor.sprite for decor in BIOMES["caatinga"].sky_decor}
    previous_only.discard(BIOMES["caatinga"].horizon_vehicle[0])
    assert not previous_only & {Path(path).stem for path in view.assets._loaded}
