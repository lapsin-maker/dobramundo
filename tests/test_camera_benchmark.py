"""Benchmark harness logic, using a synthetic source and never opening a camera."""

from __future__ import annotations

from tools import benchmark_camera


class SyntheticSource:
    def __init__(self, model_path, camera_index=0, publish=True):
        self.error = None
        self.running = False
        self.publish = publish
        self.count = 0

    def start(self):
        self.running = True

    def stop(self, timeout=0.0):
        self.running = False

    def diagnostics(self):
        if self.running:
            self.count += 1
        published = self.count if self.publish else 0
        return {
            "frames_read": self.count,
            "inferences": published,
            "published": published,
            "stale_dropped": 0,
            "read_failures": 0,
            "capture_fps": 0.0,
            "inference_fps": 0.0,
            "inference_ms": 7.0,
            "startup_ms": 10.0 if published else None,
            "capture_interval_ms": 40.0,
            "inference_interval_ms": 45.0,
            "last_result_age_ms": 20.0 if published else None,
            "result_age_ms": 10.0 if published else None,
            "errors": 0,
            "resolution": (640, 480),
            "error": self.error,
        }


def test_benchmark_warms_up_then_measures_a_separate_sample_window(monkeypatch):
    monkeypatch.setattr(benchmark_camera, "PoseCameraSource", SyntheticSource)
    monkeypatch.setattr(benchmark_camera, "POLL_INTERVAL_S", 0.001)
    report = benchmark_camera.benchmark(0.02, 0, None)

    assert report["status"] == "ok"
    assert report["time_to_first_result_seconds"] is not None
    assert report["measurement_window_complete"]
    assert report["samples_in_window"] >= 5
    assert report["capture_fps"] is not None and report["inference_fps"] is not None
    assert report["thread_still_running_after_stop"] is False
    assert report["image_or_landmarks_saved"] is False


def test_benchmark_reports_insufficient_when_no_results_are_published(monkeypatch):
    monkeypatch.setattr(benchmark_camera, "PoseCameraSource", lambda model, camera_index=0: SyntheticSource(
        model, camera_index, publish=False
    ))
    monkeypatch.setattr(benchmark_camera, "WARMUP_TIMEOUT_S", 0.01)
    monkeypatch.setattr(benchmark_camera, "POLL_INTERVAL_S", 0.001)
    report = benchmark_camera.benchmark(0.02, 0, None)

    assert report["status"] == "insufficient"
    assert report["samples_in_window"] == 0
    assert report["measurement_seconds"] == 0.0
    assert report["capture_fps"] is None
