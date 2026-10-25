"""Mede webcam e detector por alguns segundos sem salvar quadros nem pontos.

Exemplo: ``python tools/benchmark_camera.py --seconds 8 --device 0``.
Idade é contada desde o retorno de ``VideoCapture.read``; OpenCV não fornece
um timestamp de exposição confiável para todas as webcams/backends.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dobramundo.input.camera import PoseCameraSource  # noqa: E402
from dobramundo.paths import find_pose_model  # noqa: E402

WARMUP_TIMEOUT_S = 15.0
STOP_TIMEOUT_S = 15.0
MIN_SAMPLES = 5
POLL_INTERVAL_S = 0.05


def benchmark(seconds: float, device: int, model_path: Optional[Path]) -> dict:
    source = PoseCameraSource(model_path, camera_index=device)
    started = time.monotonic()
    ready = False
    sample_started = None
    sample_finished = None
    baseline = None
    sample_end_metrics = None
    try:
        source.start()
        warmup_deadline = started + WARMUP_TIMEOUT_S
        while time.monotonic() < warmup_deadline:
            current = source.diagnostics()
            if current["published"] >= 1:
                ready = True
                break
            if current["error"] is not None or not source.running:
                break
            time.sleep(POLL_INTERVAL_S)
        if ready:
            sample_started = time.monotonic()
            baseline = source.diagnostics()
            sample_deadline = sample_started + seconds
            while time.monotonic() < sample_deadline:
                current = source.diagnostics()
                if current["error"] is not None or not source.running:
                    break
                time.sleep(POLL_INTERVAL_S)
            sample_finished = time.monotonic()
            sample_end_metrics = source.diagnostics()
    finally:
        source.stop(timeout=STOP_TIMEOUT_S)
    metrics = source.diagnostics()
    sample_seconds = (
        max(0.0, sample_finished - sample_started)
        if sample_started is not None and sample_finished is not None
        else 0.0
    )
    if baseline is None or sample_end_metrics is None:
        deltas = {key: 0 for key in ("frames_read", "inferences", "published", "stale_dropped", "read_failures")}
    else:
        deltas = {
            key: max(0, sample_end_metrics[key] - baseline[key])
            for key in ("frames_read", "inferences", "published", "stale_dropped", "read_failures")
        }
    sample_complete = sample_seconds >= max(0.0, seconds - POLL_INTERVAL_S * 2)
    stopped = not source.running
    successful = (
        ready and sample_complete and deltas["published"] >= MIN_SAMPLES and stopped and metrics["error"] is None
    )
    resolution = metrics["resolution"]
    return {
        "status": "ok" if successful else "insufficient",
        "reason": None
        if successful
        else "warmup, amostras mínimas, janela completa, erro ou encerramento da thread não confirmados",
        "device": device,
        "requested_seconds": seconds,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "warmup_timeout_seconds": WARMUP_TIMEOUT_S,
        "time_to_first_result_seconds": round(sample_started - started, 3) if sample_started is not None else None,
        "measurement_seconds": round(sample_seconds, 3),
        "measurement_window_complete": sample_complete,
        "minimum_samples": MIN_SAMPLES,
        "samples_in_window": deltas["published"],
        "resolution": list(resolution) if resolution is not None else None,
        "frames_read": deltas["frames_read"],
        "inferences": deltas["inferences"],
        "published": deltas["published"],
        "published_total": metrics["published"],
        "stale_dropped": deltas["stale_dropped"],
        "read_failures": deltas["read_failures"],
        "capture_fps": round(deltas["frames_read"] / sample_seconds, 2) if sample_seconds > 0 else None,
        "inference_fps": round(deltas["inferences"] / sample_seconds, 2) if sample_seconds > 0 else None,
        "last_inference_ms": round(metrics["inference_ms"], 2),
        "startup_ms": round(metrics["startup_ms"], 2) if metrics["startup_ms"] is not None else None,
        "capture_interval_ms": round(metrics["capture_interval_ms"], 2),
        "inference_interval_ms": round(metrics["inference_interval_ms"], 2),
        "last_result_age_ms": (
            round(metrics["last_result_age_ms"], 2) if metrics["last_result_age_ms"] is not None else None
        ),
        "last_published_age_ms": (round(metrics["result_age_ms"], 2) if metrics["result_age_ms"] is not None else None),
        "error_count": metrics["errors"],
        "error": metrics["error"],
        "thread_still_running_after_stop": not stopped,
        "age_basis": "monotonic time immediately after VideoCapture.read returns",
        "sensor_exposure_timestamp_available": False,
        "image_or_landmarks_saved": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=8.0, help="duração, entre 1 e 30 segundos")
    parser.add_argument("--device", type=int, default=0, help="índice da webcam local")
    parser.add_argument("--model", type=Path, default=find_pose_model(), help="modelo de pose local")
    parser.add_argument("--output", type=Path, help="arquivo JSON opcional")
    args = parser.parse_args()
    if not 1.0 <= args.seconds <= 30.0:
        parser.error("--seconds deve ficar entre 1 e 30")
    report = benchmark(args.seconds, args.device, args.model)
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(f"Métricas gravadas em {args.output}")
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
