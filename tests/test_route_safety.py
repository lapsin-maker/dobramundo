import random

from dobramundo import config as C
from dobramundo.content.biomes import BIOMES
from dobramundo.content.items import ObstacleSpec
from dobramundo.content.progress import plane_stats
from dobramundo.game.entities import Entity
from dobramundo.game.player import Player
from dobramundo.game.world import (
    ROUTE_CONTROL_FACTOR,
    ROUTE_POSITION_RESPONSE,
    ROUTE_REACTION_MARGIN_S,
    ROUTE_REVERSAL_MARGIN_S,
    ROUTE_Z_HALF,
    RoutePlanner,
    World,
    _axis_reach_limit,
    find_reachable_route,
)


def test_reference_route_avoids_an_obstacle_and_checks_full_collision_volume():
    obstacle = ObstacleSpec("tower", "chimney", 100.0, 160.0, 0.0, 400.0)
    entity = Entity(700.0, 0, "tower", 0.0, obstacle.sprite, obstacle)

    route = find_reachable_route([entity], "dificil")

    assert route
    assert all(abs(x - entity.x) > obstacle.width / 2 + 130 * .42 * .88 for x, _y in route)


def test_route_model_rejects_a_wall_covering_all_lanes_and_altitudes():
    wall = ObstacleSpec("tower", "wall", 500.0, 2000.0, 0.0, 400.0)
    walls = [Entity(520.0, lane, "tower", 0.0, wall.sprite, wall) for lane in (-1, 0, 1)]

    assert find_reachable_route(walls, "dificil") is None


def test_seeded_worlds_preserve_obstacles_and_have_a_reference_route():
    for biome in BIOMES.values():
        for mode in ("normal", "dificil"):
            for seed in range(3):
                world = World(biome, mode, random.Random(seed), restoration=(5.0, 50.0, 90.0)[seed])

                assert world.route_planner.frontier
                if seed == 0:
                    assert find_reachable_route(world.entities, mode) is not None
                assert world.route_obstacles_kept + world.route_obstacles_skipped == world.route_obstacles_requested
                assert world.route_obstacles_kept >= world.route_obstacles_requested * 0.8


def test_advance_records_spawned_entities_at_their_actual_absolute_position():
    world = World(BIOMES["amazonia"], "dificil", random.Random(1))
    world.entities.clear()
    world.route_planner.reset(C.PLAYER_Z)
    world.spawn_pattern = lambda z: world.add_reachable_obstacle(z, 1, "low", False)

    expected_distance = 0.0
    for dz in (50.0, 80.0, 60.0):
        world.segments = [0.0]
        expected_distance += dz
        world.advance(dz / C.BASE_SPEED, dz)
        newest = world.entities[-1]
        assert newest.z == 220.0
        absolute_z = world.distance + newest.z
        assert absolute_z == expected_distance + 220.0
        assert world.route_planner.last_group.end == absolute_z - C.PLAYER_Z + ROUTE_Z_HALF


def test_tutorial_obstacles_keep_the_initial_route_origin():
    world = World(BIOMES["amazonia"], "normal", random.Random(4), intro=True)
    origin = world.route_planner.base_player_global

    for position in tuple(position for _kind, position in world.pending_lessons):
        world.distance = position - C.TRACK_LENGTH
        world.spawn_lessons()

    assert world.route_tutorial_failures == 0
    assert world.route_planner.base_player_global == origin == C.PLAYER_Z
    assert world.route_planner.last_group is not None
    world.distance = world.intro_until
    assert world.add_reachable_obstacle(3000.0, 1, "low", False)
    assert world.route_planner.base_player_global == origin


def test_route_motion_bound_is_conservative_for_both_player_controllers():
    margin = ROUTE_REACTION_MARGIN_S + ROUTE_REVERSAL_MARGIN_S
    movement_time = 0.25
    step = C.MAX_DT
    predicted = _axis_reach_limit(
        0.0,
        1.0,
        movement_time,
        C.MAX_LATERAL_SPEED * plane_stats({}).max_speed * ROUTE_CONTROL_FACTOR,
        -C.MAX_PLAYER_X,
        C.MAX_PLAYER_X,
        ROUTE_POSITION_RESPONSE,
        C.FLIGHT_RESPONSE,
    )

    for position_control in (True, False):
        player = Player()
        frames = round(margin / step)
        for _ in range(frames):
            if position_control:
                player.update(step, 0.0, 0.0, (0.0, player.y))
            else:
                player.update(step, 0.0, 0.0)
        for _ in range(round(movement_time / step)):
            if position_control:
                player.update(step, 0.0, 0.0, (C.MAX_PLAYER_X, player.y))
            else:
                player.update(step, 1.0, 0.0)
        assert player.x >= predicted


def test_planner_uses_worst_case_speed_for_each_difficulty():
    normal = RoutePlanner("normal")
    difficult = RoutePlanner("dificil")

    assert normal.speed == difficult.speed * C.NORMAL_SPEED_FACTOR

