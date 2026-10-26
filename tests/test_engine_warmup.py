from pathlib import Path

import pygame

from dobramundo.content.biomes import BIOMES
from dobramundo.engine.assets import Assets
from dobramundo.engine.contracts import PlaneLook
from dobramundo.engine.paper_items import PaperItems
from dobramundo.engine.world_view import WorldView


def test_biome_warmup_queue_is_side_effect_free_until_a_step(display):
    assets = Assets()
    view = WorldView(assets)
    before = {Path(path).stem for path in assets._loaded}

    view.set_biome(BIOMES["amazonia"])

    after = {Path(path).stem for path in assets._loaded}
    assert not {"amazonia_0", "banks_amazonia", "fauna_sprint3"} & (after - before)
    assert view.warmup_pending
    assert view.warmup_progress == 0.0
    assert len(view.warm_queue) > 20
    assert view.warmup_status == "Preparando paisagem"

    view.step_warm_up(0.01)

    assert view.warmup_progress == 1 / len(view.warm_queue)
    assert view.warmup_last_task_ms >= 0.0
    assert view.warmup_timings and view.warmup_timings[-1][0] == "Preparando paisagem"
    assert view.watercolor.backdrops["amazonia"][0] is not None


def test_only_selected_flight_look_is_queued_and_prepared_incrementally(display, monkeypatch):
    view = WorldView(Assets())
    view.set_biome(BIOMES["amazonia"])
    selected = PlaneLook("bis14", "azul", "jornal", {"pele": "clara"})
    calls = []
    monkeypatch.setattr(view.skin, "base", lambda plane, mode: calls.append(("base", plane, mode)))
    monkeypatch.setattr(
        view.skin,
        "painted",
        lambda plane, mode, color, pattern: calls.append(("paint", plane, color, pattern)),
    )
    monkeypatch.setattr(
        view.skin.pilots,
        "compose",
        lambda mode, pilot, pose=None: calls.append(("pilot", mode, pose)),
    )
    monkeypatch.setattr(
        view.skin,
        "surface",
        lambda plane, mode, color, pattern, pilot: calls.append(("surface", plane, mode)),
    )

    initial_total = len(view.warm_queue)
    view.prepare_look(selected)
    assert len(view.warm_queue) == initial_total + 4
    assert not calls
    view.prepare_look(selected)
    assert len(view.warm_queue) == initial_total + 4

    while view.warmup_pending:
        view.step_warm_up(0.01)

    assert calls == [
        ("base", "bis14", "flight"),
        ("paint", "bis14", "azul", "jornal"),
        ("pilot", "flight", "back_seated"),
        ("surface", "bis14", "flight"),
    ]
    # Entering again must revisit the look: a cache eviction can happen between flights.
    view.prepare_look(selected)
    assert view.warmup_pending
    assert len(view.warm_queue) == 4  # completed jobs must not accumulate on repeat flights
    assert view.warmup_timings == []
    while view.warmup_pending:
        view.step_warm_up(0.01)
    assert calls[:4] == calls[4:]
    assert len(view.warmup_timings) == 4


def test_warmup_keeps_every_task_timing_in_current_bounded_queue(display):
    view = WorldView(Assets())
    view.warm_queue = [(str(index), lambda: None) for index in range(80)]
    while view.warmup_pending:
        view.step_warm_up(1)
    assert len(view.warmup_timings) == 80
    assert view.warmup_timings[0][0] == "0"


def test_first_view_is_prepared_offscreen_without_advancing_rules(display, monkeypatch):
    from dobramundo.game.run import FlightRun

    view = WorldView(Assets())
    run = FlightRun(BIOMES["amazonia"], "normal", {}, seed=7, intro=False)
    look = PlaneLook("bis14", "azul", "liso", {})
    frames = []
    monkeypatch.setattr(view, "draw_run", lambda canvas, r, appearance: frames.append((canvas, r, appearance)))
    before = run.flight_time, run.world.distance
    view.prepare_first_frame(run, look)
    assert not frames
    view.step_warm_up(1)
    assert len(frames) == 1 and frames[0][0] is not display
    assert frames[0][1:] == (run, look)
    assert (run.flight_time, run.world.distance) == before
    assert view.warm_queue[0][1] == view._prepared_task


def test_painted_ground_samples_every_pixel_inside_each_batched_band(display):
    from dobramundo.engine.assets import Assets
    from dobramundo.engine.ground import compute_ground_rows
    from dobramundo.engine.painted_route import PaintedGround, PaintedRoute

    painter = PaintedRoute(Assets())
    painter.prepare_ground()
    assert painter.ground is not None
    assert PaintedGround.ROW_HEIGHT == 3
    assert painter.ground.rows == compute_ground_rows()[:: PaintedGround.ROW_HEIGHT]


def test_regional_obstacle_details_use_existing_assets_without_changing_silhouette(display):
    assets = Assets()
    items = PaperItems()
    names = items.regional_art_names("amazonia")
    scenery = assets.scenery_for(names)
    assert set(names) <= set(scenery)
    generic = {kind: items.canonical[("obstacle", kind, False)].copy() for kind in ("low", "gate", "tower")}

    items.set_region_scenery("amazonia", scenery)

    for kind in ("low", "gate", "tower"):
        regional = items.canonical[("obstacle-regional", "amazonia", kind, False)]
        assert pygame.image.tobytes(regional, "RGBA") != pygame.image.tobytes(generic[kind], "RGBA")
        assert regional.get_bounding_rect(min_alpha=1) == generic[kind].get_bounding_rect(min_alpha=1)
        assert items.canonical[("obstacle", kind, False)] is not regional
