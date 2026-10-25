"""Revisão independente de percurso, transições, zoom e fauna regional."""

from __future__ import annotations

import pytest

from dobramundo import config as C
from dobramundo.content.biomes import BIOMES
from dobramundo.content.planes import DEFAULT_PLANE
from dobramundo.engine.accessible_view import screen_point, viewport
from dobramundo.engine.assets import Assets
from dobramundo.engine.painted_route import PaintedRoute
from dobramundo.engine.regional_life import RegionalLife
from dobramundo.engine.sprites import project
from dobramundo.engine.watercolor import WatercolorWorld
from dobramundo.engine.world_view import PlaneLook, WorldView
from dobramundo.game.entities import Entity
from dobramundo.game.world import World


def _stage_weights(stage_blend, visual, z):
    a, b, mix = stage_blend(visual, z)
    return {a: 1.0} if a == b else {stage: weight for stage, weight in ((a, 1.0 - mix), (b, mix)) if weight > 1e-9}


def test_route_stage_blend_is_continuous_and_reaches_horizon_first():
    far, near = C.FOG_END, C.NEAR_CLIP_Z
    before = _stage_weights(PaintedRoute.stage_blend, C.ERA_SPAN - 1e-5, far)
    at = _stage_weights(PaintedRoute.stage_blend, C.ERA_SPAN, far)
    assert before == at
    far_mix = _stage_weights(PaintedRoute.stage_blend, C.ERA_SPAN + 8, far)[1]
    near_mix = _stage_weights(PaintedRoute.stage_blend, C.ERA_SPAN + 8, near).get(1, 0.0)
    assert far_mix == pytest.approx(0.5, abs=0.02)
    assert near_mix < far_mix
    far_second = _stage_weights(PaintedRoute.stage_blend, 2 * C.ERA_SPAN + 6, far)[2]
    near_second = _stage_weights(PaintedRoute.stage_blend, 2 * C.ERA_SPAN + 6, near).get(2, 0.0)
    assert near_second < far_second


@pytest.mark.parametrize("distance", [0.0, 219.9, 220.0, 1050.0, 10000.0])
def test_scenery_geometry_is_identical_across_stages_and_loops_by_world_period(display, distance):
    route = WatercolorWorld(Assets()).route
    stages = [route.placements(distance, stage) for stage in range(3)]

    def geometry(placements):
        return [(z, x, side) for z, x, _, side in placements]

    def signature(placements):
        return [(round(z, 6), x, index, side) for z, x, index, side in placements]

    assert geometry(stages[0]) == geometry(stages[1]) == geometry(stages[2])
    periodic = route.placements(distance + route.SPACING * 24, 0)
    assert signature(stages[0]) == signature(periodic)
    closer = route.placements(distance + 10, 0)
    assert all(
        (round(z - 10, 6), x, index, side) in signature(closer)
        for z, x, index, side in stages[0]
        if z - 10 >= C.NEAR_CLIP_Z and z - 10 <= C.FOG_END
    )
    reduced = route.placements(distance, 0, reduced=True)
    assert len(reduced) <= len(stages[0])
    assert all((z, x, side) in geometry(stages[0]) for z, x, _, side in reduced)


def test_zoom_keeps_plane_and_world_anchors_inside_frame_at_reachable_edges():
    plane_w, plane_h = 246, 227  # limites de imagem adotados pelo renderer a PLAYER_Z
    for world_x in (-C.MAX_PLAYER_X, C.MAX_PLAYER_X):
        for world_y in (C.MIN_ALTITUDE, C.MAX_ALTITUDE):
            center = project(world_x, world_y, C.PLAYER_Z, world_x * C.CAMERA_FOLLOW)[:2]
            rect = viewport(1.6, (round(center[0]), round(center[1])), (plane_w, plane_h))
            corners = [
                screen_point((center[0] + dx * plane_w / 2, center[1] + dy * plane_h / 2), rect)
                for dx in (-1, 1)
                for dy in (-1, 1)
            ]
            assert min(p[0] for p in corners) >= -1
            assert max(p[0] for p in corners) <= C.WIDTH + 1
            assert min(p[1] for p in corners) >= -1
            assert max(p[1] for p in corners) <= C.HEIGHT + 1
            # Qualquer hitbox/alerta desenhado no mesmo canvas recebe exatamente a mesma transformação.
            point = (center[0] + 40, center[1] + 30)
            transformed = screen_point(point, rect)
            assert transformed == pytest.approx(
                ((point[0] - rect.x) * C.WIDTH / rect.width, (point[1] - rect.y) * C.HEIGHT / rect.height)
            )


def test_zoom_fallback_plane_sets_the_correct_viewport_focus(display, run, monkeypatch):
    view = WorldView(Assets())
    view.high_contrast = True
    view.contrast_scale = 1.6
    monkeypatch.setattr(view.skin, "surface", lambda *args, **kwargs: None)
    run.world.entities.clear()
    run.player.x = C.MAX_PLAYER_X
    run.player.y = C.MIN_ALTITUDE
    run.player.cam_x = run.player.x * C.CAMERA_FOLLOW
    view.draw_run(display, run, PlaneLook(DEFAULT_PLANE))
    assert view.player_rect.center != (123, 90)  # não usa o retângulo inicial como âncora
    top_left = view.screen_point(view.player_rect.topleft)
    bottom_right = view.screen_point(view.player_rect.bottomright)
    assert top_left[0] >= 0 and bottom_right[0] <= C.WIDTH
    assert top_left[1] >= 0 and bottom_right[1] <= C.HEIGHT


def test_fauna_nao_cria_entidades_e_fica_fora_do_alcance_lateral(display):
    life = RegionalLife(Assets())
    world = World(BIOMES["amazonia"])
    world.set_restoration(45)
    world.distance = 7600  # sequência dos botos
    world.entities.clear()
    before = (world.distance, list(world.entities), world.elapsed, world.visual)
    event = life.encounter(world, reduced=True)
    assert event is not None
    assert abs(event[0]) > C.MAX_PLAYER_X
    assert event[4] == 0.0  # movimento reduzido elimina a animação
    life.draw(display, world, 0, True)
    assert (world.distance, list(world.entities), world.elapsed, world.visual) == before


def test_fauna_suprime_ameaca_e_reaparece_sem_salto_apos_poda(display):
    life = RegionalLife(Assets())
    world = World(BIOMES["amazonia"])
    world.set_restoration(45)
    world.distance = 600
    obstacle = Entity(C.PLAYER_Z, 0, "low")
    world.entities = [obstacle]
    suppressed = life.encounter(world, False)
    assert suppressed is not None and suppressed[5] == 0.0
    obstacle.z = C.PLAYER_Z - 70  # limite exato de pruning do mundo
    world.distance += 70
    at_prune_boundary = life.encounter(world, False)[5]
    assert 0.0 < at_prune_boundary < 0.5
    world.entities.clear()
    world.distance += 70
    after_prune = life.encounter(world, False)[5]
    assert 0.0 < after_prune - at_prune_boundary <= 70 / 220 + 1e-6
    paused = life.encounter(world, False)[5]
    assert paused == pytest.approx(after_prune)  # redraw/pausa não avança envelope


def test_watercolor_ground_line_buffers_have_a_fixed_bound(display):
    painter = WatercolorWorld(Assets())
    painter.route.prepare_ground()
    ground = painter.route.ground
    assert ground is not None
    world = World(BIOMES["caatinga"])
    ground.paint(display, world.biome.key, 0, 0, (230, 220, 190))
    assert len(ground.line_buffers) <= 4 * len(ground.rows)
    memory_bytes = sum(
        buffer[0].get_pitch() * buffer[0].get_height() + buffer[2].get_pitch() * buffer[2].get_height()
        for buffer in ground.line_buffers.values()
    )
    assert memory_bytes < 32 * 1024 * 1024
