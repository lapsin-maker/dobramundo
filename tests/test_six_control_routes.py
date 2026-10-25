"""O mesmo espaço navegável pelos seis segmentos, com landmarks sintéticos."""

import pytest
from helpers import CAL_READINGS, FakeSource, landmarks

from dobramundo import config as C
from dobramundo.engine.orientation import game_to_screen, screen_to_game
from dobramundo.input.api import SEGMENTS, InputHub


@pytest.mark.parametrize("segment_key", sorted(SEGMENTS))
def test_all_body_segments_reach_every_menu_edge(segment_key):
    source = FakeSource()
    hub = InputHub()
    hub.source_factory = lambda: source
    hub.set_segment(segment_key)
    segment = SEGMENTS[segment_key]

    def hold(x, y):
        for _ in range(CAL_READINGS):
            source.show(landmarks({index: (x, y) for index in segment.landmarks}))
            hub.update(1 / 30)

    hold(0.5, 0.5)
    assert hub.body.calibrated
    for x, y, edge in (
        (0.8, 0.5, (C.WIDTH - 1, C.HEIGHT // 2)),
        (0.2, 0.5, (0, C.HEIGHT // 2)),
        (0.5, 0.2, (C.WIDTH // 2, 0)),
        (0.5, 0.8, (C.WIDTH // 2, C.HEIGHT - 1)),
    ):
        hold(x, y)
        assert hub.body_pointer() == edge


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
@pytest.mark.parametrize("mirrored", [False, True])
def test_projected_corners_and_center_keep_same_target(rotation, mirrored):
    for point in ((0, 0), (0, 1), (1, 0), (1, 1), (0.5, 0.5)):
        shown = game_to_screen(*point, rotation, mirrored)
        assert screen_to_game(*shown, rotation, mirrored) == pytest.approx(point)
