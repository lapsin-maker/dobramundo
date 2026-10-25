import pygame
import pytest

from dobramundo import config as C
from dobramundo.content.biomes import BIOMES
from dobramundo.engine.accessible_view import viewport
from dobramundo.engine.assets import Assets
from dobramundo.engine.world_view import WorldView
from dobramundo.game.entities import Entity
from dobramundo.game.world import World


@pytest.mark.parametrize("scale", [1.0, 1.3, 1.6])
@pytest.mark.parametrize("lane", [-8, 8])
def test_magnified_view_marks_clipped_threats_without_changing_hitbox(display, scale, lane):
    view = WorldView(Assets())
    view.cam = 0.0
    obstacle = Entity(C.PLAYER_Z + 300, lane, "gate")
    world = World(BIOMES["amazonia"])
    world.entities = [obstacle]
    before = obstacle.hitbox()
    crop = viewport(scale, (C.WIDTH / 2, C.HORIZON_Y + 190), (150, 120))
    display.fill((0, 0, 0))

    marked = view.draw_edge_threats(display, world, crop)

    assert marked == (0 if scale == 1.0 else 1)
    after = obstacle.hitbox()
    assert (before.x_min, before.x_max, before.y_min, before.y_max, before.z_min, before.z_max) == (
        after.x_min,
        after.x_max,
        after.y_min,
        after.y_max,
        after.z_min,
        after.z_max,
    )
    if scale > 1.0:
        assert any(pygame.image.tobytes(display, "RGB"))


@pytest.mark.parametrize(
    ("kind", "z", "crop", "edge"),
    [
        ("gate", 600.0, pygame.Rect(250, 180, 600, 220), "top"),
        ("low", 300.0, pygame.Rect(250, 0, 600, 350), "bottom"),
    ],
)
def test_edge_indicators_cover_vertical_crop_boundaries(display, kind, z, crop, edge):
    view = WorldView(Assets())
    view.cam = 0.0
    world = World(BIOMES["amazonia"])
    spec = BIOMES["amazonia"].industrial_obstacles[kind][0]
    world.entities = [Entity(z, 0, kind, spec=spec)]
    display.fill((0, 0, 0))

    assert view.draw_edge_threats(display, world, crop) == 1
    if edge == "top":
        region = display.subsurface((crop.left, crop.top, crop.width, 40))
    else:
        region = display.subsurface((crop.left, crop.bottom - 40, crop.width, 40))
    assert any(pygame.image.tobytes(region, "RGB"))


def test_edge_indicators_skip_hit_passed_and_behind_obstacles(display):
    view = WorldView(Assets())
    view.cam = 0.0
    world = World(BIOMES["amazonia"])
    hit = Entity(C.PLAYER_Z + 300, 8, "gate", hit=True)
    passed = Entity(C.PLAYER_Z + 300, -8, "low", passed=True)
    behind = Entity(C.PLAYER_Z - 1, 8, "tower")
    world.entities = [hit, passed, behind]
    crop = viewport(1.6, (C.WIDTH / 2, C.HORIZON_Y + 190), (150, 120))

    assert view.draw_edge_threats(display, world, crop) == 0
