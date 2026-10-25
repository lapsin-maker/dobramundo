"""Benchmark CPU reproduzível; grava somente métricas e capturas sintéticas opcionais.

python tools/benchmark_runtime.py --out <pasta> [--frames 600] [--screenshots]
Sem webcam por padrão. Compare processos novos, no mesmo equipamento e sem builds em paralelo.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def resident_bytes() -> int:
    if os.name != "nt":
        try:
            # Linux: páginas residentes, não o espaço virtual reservado.
            pages = int(Path("/proc/self/statm").read_text(encoding="ascii").split()[1])
            return pages * os.sysconf("SC_PAGE_SIZE")
        except (OSError, ValueError, IndexError, AttributeError):
            pass
        return 0  # indisponível nesta medição; não significa consumo zero
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            )
        ]

    data = Counters()
    data.cb = ctypes.sizeof(data)
    handle = ctypes.windll.kernel32.GetCurrentProcess
    handle.restype = wintypes.HANDLE
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    return int(data.WorkingSetSize) if query(handle(), ctypes.byref(data), data.cb) else 0


def stats(values: list) -> dict:
    ordered = sorted(values)
    if not ordered:
        return {}
    return {
        "median_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 3),
        "p99_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.99))], 3),
        "max_ms": round(ordered[-1], 3),
    }


def instrument(obj, name: str, samples: dict, key: str) -> None:
    original = getattr(obj, name)

    def measured(*args, **kwargs):
        start = time.perf_counter()
        result = original(*args, **kwargs)
        samples.setdefault(key, []).append((time.perf_counter() - start) * 1000)
        return result

    setattr(obj, name, measured)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--frames", type=int, default=600)
    parser.add_argument("--screenshots", action="store_true")
    parser.add_argument("--paced", action="store_true", help="cede a CPU para mirar 60 quadros/s, como o jogo")
    parser.add_argument(
        "--camera", action="store_true", help="abre webcam local para medir CPU concorrente; sem salvar vídeo"
    )
    parser.add_argument("--device", type=int, default=0)
    args = parser.parse_args()
    if args.frames < 1:
        parser.error("--frames deve ser maior que zero")
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        PYGAME_HIDE_SUPPORT_PROMPT="1",
        DOBRAMUNDO_DATA_DIR=str(args.out / "perfil-benchmark"),
    )
    import pygame

    from dobramundo.app import App
    from dobramundo.content.biomes import BIOMES
    from dobramundo.game.run import FlightRun
    from dobramundo.persistence import Profile
    from dobramundo.scenes.flight import FlightScene

    memory_before = resident_bytes()
    start = time.perf_counter()
    app = App(audio=False, profile=Profile(consentimento=True, piloto_montado=True))
    init_ms = (time.perf_counter() - start) * 1000
    memory_after = resident_bytes()
    watercolor = [(path, surf) for path, surf in app.assets._loaded.items() if "watercolor" in path]
    report = {
        "conditions": "CPU; SDL dummy; no camera; 1100x650; fresh process; 60 warmup frames per case",
        "pacing": "60 fps target, sleep excluded from frame timings" if args.paced else "uncapped stress",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "camera_clock_resolution_ms": time.get_clock_info("monotonic").resolution * 1000,
        "startup_ms": round(init_ms, 2),
        "rss_before_bytes": memory_before,
        "rss_after_bytes": memory_after,
        "rss_delta_bytes": memory_after - memory_before,
        "startup_watercolor_count": len(watercolor),
        "startup_watercolor_bytes": sum(s.get_pitch() * s.get_height() for _, s in watercolor),
        "seed": 7,
        "flights": {},
    }
    camera = None
    if args.camera:
        from dobramundo.input.camera import PoseCameraSource
        from dobramundo.paths import find_pose_model

        camera = PoseCameraSource(find_pose_model(), args.device)
        camera.start()
        deadline = time.monotonic() + 15
        while camera.snapshot()[0] == 0 and camera.error is None and time.monotonic() < deadline:
            time.sleep(0.05)
        report["camera_start"] = camera.diagnostics()
        report["camera_ready"] = camera.snapshot()[0] > 0 and camera.error is None
        report["conditions"] = report["conditions"].replace("no camera", "local camera inference running concurrently")
        report["latency_basis"] = (
            "read-return to present-call completion; excludes sensor buffering and physical display latency"
        )
    app.save = lambda: None
    samples = {}
    instrument(app.view, "background", samples, "background")
    instrument(app.view.watercolor, "backdrop", samples, "horizon")
    instrument(app.view.watercolor.route.ground, "paint", samples, "ground")
    instrument(app.view, "desaturate", samples, "desaturate")
    instrument(app.view, "draw_run", samples, "world")
    instrument(app, "present", samples, "present")
    for city in ("amazonia", "caatinga"):
        for contrast in (False, True):
            setup_started = time.perf_counter()
            scene = FlightScene(app, city)
            scene.run = FlightRun(BIOMES[city], "normal", {}, seed=7, intro=False)
            scene.run.invincible = True
            app.go(scene)
            app.options.alto_contraste = contrast
            app.apply_options()
            scene_setup_ms = (time.perf_counter() - setup_started) * 1000
            values = []
            warmup_values = []
            camera_age = []
            samples.clear()
            for frame in range(args.frames + 60):
                if frame == 60:
                    samples.clear()
                # A continuous, deterministic trip through both stage changes.
                target_restoration = min(95, 5 + frame * 90 / max(1, args.frames + 59))
                scene.run.add_restoration(target_restoration - scene.run.restoration)
                start = time.perf_counter()
                app.step(1 / 60, [])
                elapsed_ms = (time.perf_counter() - start) * 1000
                if frame < 60:
                    warmup_values.append(elapsed_ms)
                if frame >= 60:
                    values.append(elapsed_ms)
                    if camera is not None:
                        captured_at = camera.snapshot_with_metadata()[3]
                        if captured_at is not None:
                            camera_age.append((time.monotonic() - captured_at) * 1000)
                if args.paced:
                    time.sleep(max(0.0, 1 / 60 - (time.perf_counter() - start)))
            label = city + ("_contrast" if contrast else "_normal")
            report["flights"][label] = {
                "frame": stats(values),
                "scene_setup_ms": round(scene_setup_ms, 3),
                "warmup": stats(warmup_values),
                "first_frame_ms": round(warmup_values[0], 3),
                "frames_measured": len(values),
                "within_60fps_budget_fraction": round(sum(v <= 1000 / 60 for v in values) / len(values), 4),
                "components": {k: stats(v) for k, v in samples.items()},
                "rss_bytes": resident_bytes(),
                "renderer_caches": app.view.cache_stats(),
            }
            if camera is not None:
                report["flights"][label]["latest_camera_result_age_at_present"] = stats(camera_age)
                report["flights"][label]["camera"] = camera.diagnostics()
            if args.screenshots:
                pygame.image.save(app.canvas, str(args.out / (label + ".png")))
            print(label, report["flights"][label]["frame"], flush=True)
    if camera is not None:
        camera.stop(timeout=2)
        report["camera_thread_stopped"] = not camera.running
        report["camera_end"] = camera.diagnostics()
    camera_ok = camera is None or (
        report["camera_ready"]
        and report["camera_thread_stopped"]
        and report["camera_end"]["error"] is None
        and report["camera_end"]["published"] - report["camera_start"]["published"] >= 5
    )
    report["status"] = "ok" if camera_ok else "insufficient_camera"
    (args.out / "runtime.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    app.input.stop_camera()
    pygame.quit()
    print("startup", {k: v for k, v in report.items() if k != "flights"}, flush=True)
    return 0 if camera_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
