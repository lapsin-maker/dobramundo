import math

from dobramundo import config as C
from dobramundo.content.progress import PLANE_PARTS, plane_stats, stars_for
from dobramundo.game.player import Player


def test_purchased_parts_do_not_change_flight_comfort_or_collision_tolerance():
    empty = plane_stats({})
    completed = plane_stats({part.key: 2 for part in PLANE_PARTS})

    assert empty == completed
    assert empty.response == 1.0
    assert empty.max_speed == 1.0
    assert empty.hitbox == 0.88
    assert empty.dead_zone == 1.0
    assert empty.roll == 1.0
    assert Player(empty).hitbox() == Player(completed).hitbox()


def test_baseline_collision_tolerance_is_common_and_smaller_than_art_bounds():
    stats = plane_stats({})
    box = Player(stats).hitbox()

    assert box.x_max - box.x_min == C.PLANE_WIDTH * 0.42 * stats.hitbox * 2
    assert math.isclose(box.y_max - box.y_min, C.PLANE_HEIGHT * stats.hitbox)
    assert stats.hitbox < 1.0


def test_parts_remain_a_collection_and_expedition_star_requirement():
    requirements = {"leme": 1, "quilha": 1}

    assert stars_for(100.0, requirements, {}) == 2
    assert stars_for(100.0, requirements, {"leme": 1, "quilha": 1}) == 3
    assert all(part.level_costs for part in PLANE_PARTS)
    assert all(
        "mais rápido" not in part.description and "mais agilidade" not in part.description
        for part in PLANE_PARTS
    )

