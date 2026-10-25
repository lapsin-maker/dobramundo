"""Regressões da progressão entre voos e de recompensas sem duplicação."""

from __future__ import annotations

import random

from conftest import make_run

from dobramundo import config as C
from dobramundo.content.biomes import BIOMES
from dobramundo.content.items import WASTE_KEYS
from dobramundo.game.entities import Entity
from dobramundo.game.run import FlightRun
from dobramundo.game.settlement import apply_run
from dobramundo.scenes.flight import FlightScene
from dobramundo.scenes.preparation import PreparationScene


def test_city_progress_is_persisted_and_the_next_flight_keeps_local_speed_ramp(app):
    run = make_run()
    run.add_restoration(24)
    saved_speed = run.speed
    apply_run(app.profile, run)

    next_flight = FlightScene(app, "amazonia")
    assert app.profile.transformacao_cidades["amazonia"] == run.restoration
    assert next_flight.run.restoration == run.restoration
    assert next_flight.run.local_restoration == C.START_RESTORATION
    assert next_flight.run.speed < saved_speed


def test_legacy_stars_seed_a_compatible_city_visual(app):
    app.profile.estrelas["amazonia"] = 2
    app.profile.transformacao_cidades.pop("amazonia", None)
    flight = FlightScene(app, "amazonia")
    assert flight.run.restoration == 2 * C.ERA_SPAN
    assert flight.run.stars == 2


def test_partial_settlement_keeps_city_progress_and_is_idempotent(app):
    run = make_run()
    run.interrupted = True
    run.resources["papel"] = 3
    run.add_restoration(12)
    before_flights = app.profile.voos

    first = apply_run(app.profile, run)
    again = apply_run(app.profile, run)

    assert first == again
    assert app.profile.transformacao_cidades["amazonia"] == run.restoration
    assert app.profile.voos == before_flights + 1
    assert app.profile.recursos["papel"] == 3
    assert app.profile.estrelas.get("amazonia", 0) == run.stars
    assert app.profile.historico[-1]["interrompida"] == 1


def test_city_at_100_does_not_end_replay_or_repeat_existing_stars():
    run = FlightRun(
        BIOMES["amazonia"],
        "normal",
        {},
        rng=random.Random(4),
        city_restoration=100,
        starting_stars=2,
    )
    run.player.maneuver = None
    run.world.entities.clear()
    run.world.spawn_pattern = lambda z: None

    assert run.restoration == 100
    assert run.stars == 2
    assert not run.complete and not run.finished
    run.add_restoration(1)
    assert run.stars == 2
    assert not run.complete and not any(event[0] in ("star", "complete") for event in run.take_events())


def test_city_at_100_can_award_new_part_star_without_recompleting():
    parts = {part: 1 for part in BIOMES["amazonia"].required_parts}
    run = FlightRun(
        BIOMES["amazonia"],
        parts=parts,
        city_restoration=100,
        starting_stars=2,
        seed=1,
    )
    run.add_restoration(1)
    events = run.take_events()
    assert run.stars == 3
    assert ("star", 3) in events
    assert not run.complete and not any(name == "complete" for name, _ in events)


def test_city_bonus_does_not_accelerate_the_local_speed_ramp():
    normal = make_run(mode="normal")
    normal.collect_waste(Entity(800, 0, "waste", 20, WASTE_KEYS[0]))
    assert normal.local_restoration == C.START_RESTORATION + C.NORMAL_SPEED_RESTORATION_PER_TRASH
    assert normal.restoration == C.START_RESTORATION + C.NORMAL_RESTORATION_PER_TRASH

    difficult = make_run(mode="dificil")
    difficult.collect_waste(Entity(800, 0, "waste", 20, WASTE_KEYS[0]))
    assert difficult.local_restoration == C.START_RESTORATION + C.DIFFICULT_SPEED_RESTORATION_PER_TRASH
    assert difficult.restoration == C.START_RESTORATION + C.RESTORATION_PER_TRASH


def test_replay_keeps_seed_and_uses_current_city_state(app):
    app.profile.transformacao_cidades["amazonia"] = 68.0
    run = FlightRun(BIOMES["amazonia"], seed=71, city_restoration=24.0)
    result = app.create_scene("resultado", run)
    result.build()
    replay = result.menu.buttons[0]
    assert replay.label == "Voar de novo"
    assert replay.sublabel == "Nova decolagem · progresso mantido"

    result.again()
    assert app.next_scene.run.seed == 71
    assert app.next_scene.run.restoration == 68.0


def test_first_three_flights_get_default_assistance_until_explicit_choice(app):
    app.profile.apoio_escolhido = False
    app.profile.voos = 0
    app.options.assistencia_previsivel = False
    assert FlightScene(app, "amazonia").run.predictable_assistance
    app.profile.voos = 2
    assert FlightScene(app, "amazonia").run.predictable_assistance
    app.profile.voos = 3
    assert not FlightScene(app, "amazonia").run.predictable_assistance

    app.profile.voos = 0
    app.profile.apoio_escolhido = True
    assert not FlightScene(app, "amazonia").run.predictable_assistance
    scene = PreparationScene(app)
    scene.set_option("assistencia_previsivel", True)
    assert app.profile.apoio_escolhido
    assert FlightScene(app, "amazonia").run.predictable_assistance


def test_spawn_disabled_policy_keeps_a_backdrop_world_empty():
    import random

    from dobramundo.game.world import World

    world = World(BIOMES["amazonia"], rng=random.Random(7), intro=True, spawn_enabled=False)
    assert not world.entities
    world.advance(10.0, 1000.0)
    assert not world.entities
