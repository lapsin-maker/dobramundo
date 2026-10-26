from __future__ import annotations

import random

from dobramundo.content.biomes import BIOMES
from dobramundo.game.entities import Entity, entity_hitbox
from dobramundo.game.missions import MissionTracker
from dobramundo.game.run import FlightRun
from dobramundo.scenes.flight import FlightScene
from dobramundo.scenes.preparation import PreparationScene
from tools.balance import simulate


def make_run(**kwargs) -> FlightRun:
    return FlightRun(BIOMES["amazonia"], "normal", intro=False, focus=False, **kwargs)


def test_explicit_seed_reproduces_route_and_mission_sequence():
    first = make_run(seed=31821)
    second = make_run(seed=31821)

    def signature(run):
        return [(entity.z, entity.x, entity.kind, entity.sprite) for entity in run.world.entities]

    assert signature(first) == signature(second)
    assert first.seed == second.seed == 31821


def test_community_seed_names_region_and_biases_without_removing_other_obstacles():
    seed = 20261025
    amazon = make_run(seed=seed, community_challenge=True)
    caatinga = FlightRun(BIOMES["caatinga"], "normal", seed=seed, intro=False, focus=False, community_challenge=True)
    assert amazon.world.challenge_theme.key == "encontro_das_aguas"
    assert caatinga.world.challenge_theme.key == "pomares_do_sao_francisco"
    assert amazon.world.challenge_theme.decorations == ("river", "boat")
    preferred = amazon.world.challenge_theme.preferred_obstacle
    assert amazon.world.choose_obstacle_kind(0.1) == preferred
    assert amazon.world.choose_obstacle_kind(0.99) != preferred
    assert make_run(seed=seed).world.challenge_theme is None


def test_entity_hitbox_method_matches_the_physics_helper():
    entity = Entity(500.0, -1, "waste", 36.0, "papel")
    assert entity.hitbox() == entity_hitbox(entity)


def test_seed_is_recorded_when_rng_is_injected_without_changing_rng_sequence():
    left_rng = random.Random(441)
    right_rng = random.Random(441)
    left = FlightRun(BIOMES["amazonia"], "normal", rng=left_rng, intro=False, focus=False)
    right = FlightRun(BIOMES["amazonia"], "normal", rng=right_rng, intro=False, focus=False)
    assert left.seed == right.seed
    assert [(e.z, e.x, e.kind) for e in left.world.entities] == [(e.z, e.x, e.kind) for e in right.world.entities]
    replay = make_run(seed=left.seed)
    assert [(e.z, e.x, e.kind) for e in left.world.entities] == [(e.z, e.x, e.kind) for e in replay.world.entities]


def test_short_session_ends_as_partial_result_not_elimination():
    run = make_run(seed=9, session_limit_s=120, exploration=True)
    run.invincible = True
    # Reduz o relógio só para o teste exercitar a borda sem simular dois minutos.
    run.session_limit_s = 1
    for _ in range(24):
        run.update(0.05)
        if run.finished:
            break
    assert run.finished and run.timeout
    assert run.interrupted and not run.complete and not run.game_over
    assert run.flight_time == 1.0
    assert run.summary()["tempo_esgotado"] == 1


def test_exploration_rearms_after_last_heart_and_keeps_counting_errors():
    run = make_run(seed=15, exploration=True)
    run.lives = 1
    run.take_hit()
    assert run.hits == 1
    assert run.lives == run.max_lives
    assert not run.finished and not run.game_over
    assert ("exploration_continue", 1) in run.events


def test_collection_counter_does_not_count_mission_reward_resources():
    run = make_run(seed=73)
    waste = Entity(500.0, 0, "waste", 36.0, "papel")
    run.collect_waste(waste)
    assert run.waste_collected == 1
    assert run.resources["papel"] == 4
    assert run.summary()["coletas"] == 1


def test_predictable_assistance_is_fixed_at_takeoff_and_visible_in_summary():
    regular = make_run(seed=18)
    assisted = make_run(seed=18, predictable_assistance=True)
    assert regular.max_lives == 3
    assert assisted.max_lives == 5
    assisted.take_hit()
    assert assisted.lives == 4
    assert assisted.invulnerable_timer == 2.0
    assert assisted.summary()["assistencia_previsivel"] == 1


def test_first_objective_waits_until_opening_lessons_end_and_uses_available_targets():
    missions = MissionTracker("normal", random.Random(4), intro=True)
    missions.update(22.0, {"coletar": {"papel": 2}, "desviar": 0, "portal": 0, "powerup": 0})
    assert missions.current is None
    missions.update(0.49, {"coletar": {"papel": 2}, "desviar": 0, "portal": 0, "powerup": 0})
    assert missions.current is None
    missions.update(0.02, {"coletar": {"papel": 1}, "desviar": 0, "portal": 0, "powerup": 0})
    assert missions.current is not None
    assert missions.current.kind == "coletar"
    assert missions.current.waste == "papel"
    assert missions.current.target == 1


def test_tracker_waits_instead_of_offering_an_objective_with_no_supply():
    missions = MissionTracker("normal", random.Random(2))
    missions.wait = 0.0
    missions.update(0.01, {"coletar": {}, "desviar": 0, "portal": 0, "powerup": 0})
    assert missions.current is None
    missions.update(0.5, {"coletar": {}, "desviar": 0, "portal": 1, "powerup": 0})
    assert missions.current is not None
    assert missions.current.kind == "portal"
    assert missions.current.target == 1


def test_unfinished_mission_expires_without_reward_then_reoffers_from_supply():
    missions = MissionTracker("normal", random.Random(7))
    missions.current = MissionTracker("normal", random.Random(9)).pick()
    missions.progress = 1
    assert missions.current is not None
    assert not missions.update(59.9)
    assert missions.current is not None
    assert missions.update(0.1)
    assert missions.current is None
    assert missions.progress == 0 and missions.completed == 0 and missions.expired == 1
    supply = {"coletar": {"metal": 1}, "desviar": 0, "portal": 0, "powerup": 0}
    assert not missions.update(2.49, supply)
    assert missions.current is None
    assert not missions.update(0.02, supply)
    assert missions.current is not None
    assert missions.current.target == 1


def test_community_objective_can_prioritize_needed_build_material_without_forcing_it():
    missions = MissionTracker("normal", random.Random(3), preferred_waste="metal")
    offered = {
        "coletar": {"metal": 2, "papel": 2},
        "desviar": 3,
        "portal": 1,
        "powerup": 1,
    }
    seen = [missions.pick(offered) for _ in range(40)]
    assert any(mission.kind == "coletar" and mission.waste == "metal" for mission in seen)
    assert any(mission.kind != "coletar" or mission.waste != "metal" for mission in seen)


def test_preparation_exposes_sessions_exploration_assistance_and_community_seed(app):
    scene = PreparationScene(app)
    scene.build()
    assert any(button.key == "meu_voo" for button in scene.menu.buttons)
    scene.open_my_flight()
    keys = {button.key for button in scene.menu.buttons}
    assert {"duracao_voo", "exploracao", "assistencia", "desafio_comunitario"} <= keys
    for button in scene.menu.buttons:
        assert 0 <= button.rect.left < button.rect.right <= 1100
        assert 0 <= button.rect.top < button.rect.bottom <= 675
    for index, button in enumerate(scene.menu.buttons):
        for other in scene.menu.buttons[index + 1 :]:
            assert not button.rect.colliderect(other.rect)
    explore = next(button for button in scene.menu.buttons if button.key == "exploracao")
    scene.menu.activate(explore)
    assert app.options.modo_exploracao is True
    assert any(button.key == "exploracao" and button.selected for button in scene.menu.buttons)
    next(button for button in scene.menu.buttons if button.key == "duracao_voo").action()
    next(button for button in scene.menu.buttons if button.key == "assistencia").action()
    next(button for button in scene.menu.buttons if button.key == "desafio_comunitario").action()
    assert app.options.limite_voo_s == 120
    assert app.options.assistencia_previsivel is True
    assert app.options.semente_desafio == 20261025


def test_flight_scene_uses_selected_seed_and_replay_preserves_intro_and_preset(app):
    app.profile.modo = "dificil"
    app.profile.voos_fase["amazonia"] = 1
    app.options.limite_voo_s = 180
    app.options.modo_exploracao = True
    app.options.assistencia_previsivel = True
    app.options.semente_desafio = 20261025
    app.profile.recursos["papel"] = 0
    app.profile.recursos["plastico"] = 99
    scene = FlightScene(app, "amazonia")
    run = scene.run
    assert run.seed == 20261025
    assert run.session_limit_s == 180
    assert run.exploration and run.predictable_assistance
    assert run.community_challenge and run.world.challenge_theme.key == "encontro_das_aguas"
    assert run.mission_preferred_waste == "papel"
    app.profile.recursos["papel"] = 99
    app.profile.recursos["plastico"] = 0
    replay = FlightScene(
        app,
        "amazonia",
        seed=run.seed,
        mode=run.mode,
        session_limit_s=run.session_limit_s,
        exploration=run.exploration,
        predictable_assistance=run.predictable_assistance,
        intro_override=run.intro,
        community_challenge=run.community_challenge,
        mission_preferred_waste=run.mission_preferred_waste,
        mission_preference_fixed=True,
    )
    assert replay.run.seed == run.seed
    assert replay.run.intro == run.intro is False
    assert replay.run.world.challenge_theme.key == run.world.challenge_theme.key
    assert replay.run.mission_preferred_waste == run.mission_preferred_waste == "papel"
    assert [(entity.z, entity.x, entity.kind, entity.sprite) for entity in replay.run.world.entities] == [
        (entity.z, entity.x, entity.kind, entity.sprite) for entity in run.world.entities
    ]


def test_balance_agent_uses_motion_and_returns_partial_interruption_metrics():
    record = simulate(
        "normal",
        1.0,
        42,
        error_rate=0.0,
        interrupt_after=5.0,
        reaction_s=0.35,
        latency_s=0.1,
    )
    assert record["seed"] == 42
    assert 5.0 <= record["seconds_active"] <= 5.05
    assert record["interrupted"] and not record["completed"]
    assert record["max_player_displacement"] > 0.0
    assert "hits" in record and "resources" in record and "pause_seconds" in record


def test_balance_pause_is_wall_time_not_flight_time():
    record = simulate(
        "normal",
        0.0,
        2026,
        pause_per_minute=2.0,
        interrupt_after=61.0,
        exploration=True,
        assistance=True,
        # Revisiting a restored city keeps the flight open past the scheduled pause.
        city_restoration=100.0,
    )
    assert record["pause_count"] == 1
    assert record["pause_seconds"] == 2.0
    assert 61.0 <= record["seconds_active"] <= 61.05
    assert 2.0 <= record["seconds_wall"] - record["seconds_active"] <= 2.1
    assert record["interrupted"]
