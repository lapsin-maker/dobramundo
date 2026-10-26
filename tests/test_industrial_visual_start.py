"""A abertura da pista deve parecer industrial antes de clarear gradualmente."""

from __future__ import annotations

from dobramundo import config as C
from dobramundo.content.biomes import BIOMES
from dobramundo.engine.painted_route import PaintedRoute
from dobramundo.engine.watercolor import WatercolorWorld
from dobramundo.engine.world_view import WorldView


def test_horizon_blend_preserves_industrial_start_and_reaches_both_stages():
    assert WatercolorWorld.stage_mix(4.99) == (0, 0, 0)

    first_at_nine = WatercolorWorld.stage_mix(9)
    assert first_at_nine[:2] == (0, 1)
    assert 0 < first_at_nine[2] <= 2  # só um começo discreto da mistura

    at_first_threshold = WatercolorWorld.stage_mix(C.ERA_SPAN)
    assert at_first_threshold == (1, 2, 0)
    assert WatercolorWorld.stage_mix(2 * C.ERA_SPAN) == (2, 2, 0)


def test_bank_blend_has_distance_delay_without_a_visual_jump():
    near_z, far_z = 100.0, C.FOG_END
    assert PaintedRoute.stage_blend(5.0, near_z) == (0, 0, 0.0)
    assert PaintedRoute.stage_blend(5.0, far_z) == (0, 1, 0.0)

    for z in (near_z, 500.0, far_z):
        delay = 4.0 * (1.0 - max(0.0, min(1.0, z / C.FOG_END)))
        first_start = 5.0 + delay
        first_end = C.ERA_SPAN + delay
        assert PaintedRoute.stage_blend(first_start, z) == (0, 1, 0.0)
        before = PaintedRoute.stage_blend(first_end - 0.001, z)
        after = PaintedRoute.stage_blend(first_end, z)
        assert before[0:2] == (0, 1)
        assert before[2] > 0.999
        assert after == (1, 2, 0.0)

        second_end = 2 * C.ERA_SPAN + delay
        assert PaintedRoute.stage_blend(second_end - 0.001, z)[2] > 0.999
        assert PaintedRoute.stage_blend(second_end, z) == (2, 2, 0.0)


def test_industrial_bank_composition_favors_settlement_and_port_over_foliage():
    indices = [PaintedRoute.scenery_index(slot, -1, 0) for slot in range(8)]
    assert indices == [0, 2, 0, 1, 0, 1, 2, 1]
    assert sum(index in (0, 1) for index in indices) == 6
    assert all(PaintedRoute.scenery_index(slot, -1, 1) != 0 for slot in range(8))


def test_legacy_fallback_resolves_stage_indices_for_all_progress_regions():
    biome = BIOMES["amazonia"]
    for visual in (5, 20, 48, 80):
        first, second, blend = WorldView.fallback_stage_looks(biome, visual)
        assert first in biome.stages
        assert second in biome.stages
        assert 0.0 <= blend <= 1.0
