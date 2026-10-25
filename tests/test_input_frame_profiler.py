"""A apresentação é atribuída à leitura usada, não à última leitura publicada."""

import pytest

from dobramundo.input.pose import SEGMENTS, BodyControl
from tools.frame_profiler import FrameProfiler


class Source:
    error = None
    seq = 1
    captured_at = 10.0

    def snapshot_with_metadata(self):
        return self.seq, [(0.5, 0.5, 1.0)] * 33, None, self.captured_at, self.captured_at + 0.01, 10.0


def test_present_keeps_consumed_sequence_even_when_source_advances(monkeypatch):
    clock = [10.02]
    monkeypatch.setattr("dobramundo.input.pose.time.monotonic", lambda: clock[0])
    source = Source()
    body = BodyControl(source, SEGMENTS["cabeca"])
    body.poll(1 / 60)
    clock[0] = 10.04
    body.note_rendered()
    source.seq, source.captured_at = 2, 10.05
    clock[0] = 10.06
    stamp = body.note_presented()
    assert stamp.sequence == 1
    assert stamp.milliseconds()["capture_to_present"] == pytest.approx(60)
    assert stamp.milliseconds()["consume_to_canvas"] == pytest.approx(20)
    assert stamp.milliseconds()["canvas_to_present"] == pytest.approx(20)
    assert set(vars(stamp)) == {"sequence", "captured_at", "consumed_at", "rendered_at", "presented_at", "usable"}


def test_nested_profiler_subtracts_child_and_unwinds_after_error():
    clock = [0.0]
    profiler = FrameProfiler(lambda: clock[0])

    class Work:
        def inner(self):
            clock[0] += 0.003

        def outer(self):
            clock[0] += 0.002
            self.inner()
            clock[0] += 0.005

        def broken(self):
            raise ValueError("test")

    work = Work()
    for name in ("inner", "outer", "broken"):
        profiler.instrument(work, name, name)
    work.outer()
    assert profiler.samples["outer"] == pytest.approx([10])
    assert profiler.exclusive["outer"] == pytest.approx([7])
    assert profiler.exclusive["inner"] == pytest.approx([3])
    with pytest.raises(ValueError):
        work.broken()
    assert profiler.stack == []
