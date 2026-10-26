"""Recuperação ambiental pelo voo, sem recursos nem aceleração passiva."""

from __future__ import annotations

import random

from dobramundo import config as C
from dobramundo.content.biomes import BIOMES
from dobramundo.content.items import WASTE_KEYS
from dobramundo.game.entities import Entity
from dobramundo.game.run import FlightRun
from dobramundo.game.settlement import apply_run
from dobramundo.game.world import World
from dobramundo.profile_model import Profile
from dobramundo.scenes.flight import FlightScene


def test_active_recovery_moves_shared_progress_but_not_speed_or_spawn_progress():
    run = FlightRun(BIOMES["amazonia"], rng=random.Random(11), city_restoration=12.0)
    before_speed = run.speed
    before_spawn = run.world.spawn_restoration
    before_resources = dict(run.resources)
    before_score = run.score

    run.add_active_recovery(15.0)

    assert run.restoration == 27.0
    assert run.world.visual == 12.0  # render catches up through ease_visual()
    assert run.world.spawn_restoration == before_spawn
    assert run.speed == before_speed
    assert run.resources == before_resources and run.score == before_score


def test_collection_accelerates_recovery_and_keeps_speed_gain_separate():
    run = FlightRun(BIOMES["amazonia"], "normal", rng=random.Random(12))
    run.add_active_recovery(10.0)
    after_passive = run.restoration
    passive_speed = run.speed
    entity = Entity(800.0, 0.0, "waste", 20.0, WASTE_KEYS[0])

    run.collect_waste(entity)

    assert run.restoration == after_passive + C.NORMAL_RESTORATION_PER_TRASH
    assert run.world.spawn_restoration == C.START_RESTORATION + C.NORMAL_RESTORATION_PER_TRASH
    assert run.speed > passive_speed  # only the earned local ramp accelerates the airplane
    assert run.resources[WASTE_KEYS[0]] > 0 and run.score > 0


def test_tutorial_or_nonspawn_run_does_not_gain_active_recovery():
    run = FlightRun(BIOMES["amazonia"], spawn_enabled=False)
    before = run.restoration
    run.add_active_recovery(60.0)
    assert run.restoration == before


def test_recovery_changes_visual_landscape_without_changing_spawn_threat_share():
    world = World(BIOMES["amazonia"], rng=random.Random(13), restoration=C.START_RESTORATION)
    world.add_restoration(70.0, earned=False)
    world.ease_visual(60.0)

    assert world.solar_share() > 0.0  # the city's visible transformation continues
    assert world.spawn_solar_share() == 0.0
    assert not world.spawn_is_solar(1000.0)  # passive recovery never selects solar threats


def test_passive_recovery_is_persisted_as_city_progress_only():
    profile = Profile()
    run = FlightRun(BIOMES["amazonia"], rng=random.Random(14))
    run.add_active_recovery(20.0)
    before_resources = dict(run.resources)
    before_points = run.score

    apply_run(profile, run)

    assert profile.transformacao_cidades["amazonia"] == run.restoration
    assert profile.recursos == before_resources
    assert profile.pontos == before_points == 0


def test_passive_recovery_at_complete_city_does_not_award_third_star():
    parts = {part: 1 for part in BIOMES["amazonia"].required_parts}
    run = FlightRun(
        BIOMES["amazonia"],
        "normal",
        parts=parts,
        city_restoration=100.0,
        starting_stars=2,
    )

    run.add_active_recovery(30.0)

    assert run.restoration == 100.0
    assert run.stars == 2
    assert not run.complete
    assert not any(name in ("star", "complete") for name, _ in run.take_events())

    run.collect_waste(Entity(800.0, 0.0, "waste", 20.0, WASTE_KEYS[0]))
    assert run.stars == 3
    assert ("star", 3) in run.take_events()


def test_flight_scene_does_not_recover_during_warmup_or_pause(app):
    scene = FlightScene(app, "amazonia")
    starting = scene.run.restoration
    app.view.warm_queue = [("teste", lambda: None)]
    app.view._warmup_index = 0
    scene.update(1.0)
    assert scene.run.restoration == starting

    app.view._warmup_index = 1
    scene.paused = True
    scene.update(1.0)
    assert scene.run.restoration == starting

    scene.paused = False
    scene.run.world.entities.clear()
    scene.run.world.advance = lambda dt, dz: None
    scene.update(0.04)
    assert scene.run.restoration > starting
