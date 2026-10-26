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
    parser.add_argument(
        "--camera-control",
        action="store_true",
        help="usa a leitura real da webcam no controle e mede sua sequência consumida",
    )
    parser.add_argument("--window", action="store_true", help="apresenta uma janela real em vez de SDL dummy")
    parser.add_argument("--empty-pilot", action="store_true", help="reproduz a carga sem avatar do benchmark 1.5")
    parser.add_argument("--biome", choices=("all", "amazonia", "caatinga"), default="all")
    parser.add_argument("--contrast", choices=("both", "no", "yes"), default="both")
    args = parser.parse_args()
    if args.camera_control:
        args.camera = True
        args.paced = True
    if args.frames < 1:
        parser.error("--frames deve ser maior que zero")
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        PYGAME_HIDE_SUPPORT_PROMPT="1",
        DOBRAMUNDO_DATA_DIR=str(args.out / "perfil-benchmark"),
    )
    if args.window:
        os.environ.pop("SDL_VIDEODRIVER", None)
    import pygame

    from dobramundo import __version__
    from dobramundo.app import App
    from dobramundo.content.biomes import BIOMES
    from dobramundo.game.run import FlightRun
    from dobramundo.persistence import Profile
    from dobramundo.scenes.flight import FlightScene

    memory_before = resident_bytes()
    start = time.perf_counter()
    profile = Profile(consentimento=True, piloto_montado=True)
    if not args.empty_pilot:
        profile.piloto.update(
            pele="pele4", cabelo="crespo", cor_cabelo="preto", roupa="amarela", olhos="castanhos", oculos="redondo"
        )
    app = App(audio=False, profile=profile)
    init_ms = (time.perf_counter() - start) * 1000
    memory_after = resident_bytes()
    watercolor = [(path, surf) for path, surf in app.assets._loaded.items() if "watercolor" in path]
    report = {
        "version": __version__,
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
        "pilot": "empty (1.5 comparison)" if args.empty_pilot else "customized synthetic avatar",
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
    if args.camera_control:
        app.input.source = camera
        app.profile.controle = "cabeca"
        app.input.set_segment("cabeca")
        report["conditions"] += "; real camera samples consumed by head control; visibility/calibration reported"
    if args.window:
        report["conditions"] = report["conditions"].replace("SDL dummy", "native window")
    from dobramundo.engine.painted_route import PaintedGround
    from tools.frame_profiler import FrameProfiler

    profiler = FrameProfiler()
    samples = profiler.samples
    profiler.instrument(app.view, "background", "background")
    profiler.instrument(app.view.watercolor, "backdrop", "horizon")
    profiler.instrument(PaintedGround, "paint", "ground")
    profiler.instrument(app.view, "desaturate", "desaturate")
    profiler.instrument(app.view, "draw_run", "world")
    profiler.instrument(app.view, "_draw_run", "entities_and_effects")
    profiler.instrument(app.view, "draw_player", "plane")
    profiler.instrument(app.view.watercolor.route, "draw", "route_and_banks")
    profiler.instrument(FlightRun, "update", "rules_update")
    profiler.instrument(FlightScene, "draw_hud", "hud")
    profiler.instrument(FlightScene, "draw", "scene")
    profiler.instrument(app, "advance", "canvas")
    profiler.instrument(app.input, "update", "input")
    profiler.instrument(app, "present", "present")
    cities = ("amazonia", "caatinga") if args.biome == "all" else (args.biome,)
    contrasts = (False, True) if args.contrast == "both" else (args.contrast == "yes",)
    for city in cities:
        for contrast in contrasts:
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
            consumed = {}
            usable_frames = 0
            sequences = set()
            profiler.clear()
            frame = 0
            preparation = []
            first_interactive_ms = None
            loading_started = time.perf_counter()
            loading_elapsed_ms = 0.0
            iterations = 0
            while frame < args.frames + 60:
                iterations += 1
                if iterations > args.frames + 1860:
                    raise RuntimeError("O preparo do voo não terminou")
                if frame == 60:
                    profiler.clear()
                # A continuous, deterministic trip through both stage changes.
                target_restoration = min(95, 5 + frame * 90 / max(1, args.frames + 59))
                scene.run.add_restoration(target_restoration - scene.run.restoration)
                was_preparing = app.next_scene is not None or getattr(app.view, "warmup_pending", False)
                start = time.perf_counter()
                app.step(1 / 60, [])
                elapsed_ms = (time.perf_counter() - start) * 1000
                preparing = was_preparing or getattr(app.view, "warmup_pending", False)
                if preparing:
                    preparation.append(elapsed_ms)
                    if args.paced:
                        time.sleep(max(0.0, 1 / 60 - (time.perf_counter() - start)))
                    continue
                if first_interactive_ms is None:
                    first_interactive_ms = elapsed_ms
                    loading_elapsed_ms = (time.perf_counter() - loading_started) * 1000
                if frame < 60:
                    warmup_values.append(elapsed_ms)
                if frame >= 60:
                    values.append(elapsed_ms)
                    if camera is not None:
                        captured_at = camera.snapshot_with_metadata()[3]
                        if captured_at is not None:
                            camera_age.append((time.monotonic() - captured_at) * 1000)
                    body = app.input.body
                    if args.camera_control and body is not None and body.presented_frame is not None:
                        stamp = body.presented_frame
                        sequences.add(stamp.sequence)
                        usable_frames += int(stamp.usable)
                        for metric, value in stamp.milliseconds().items():
                            consumed.setdefault(metric, []).append(value)
                if args.paced:
                    time.sleep(max(0.0, 1 / 60 - (time.perf_counter() - start)))
                frame += 1
            label = city + ("_contrast" if contrast else "_normal")
            report["flights"][label] = {
                "frame": stats(values),
                "scene_setup_ms": round(scene_setup_ms, 3),
                "warmup": stats(warmup_values),
                "first_preparation_frame_ms": round(preparation[0], 3) if preparation else None,
                "first_interactive_frame_ms": round(first_interactive_ms, 3),
                "preparation_frames": len(preparation),
                "preparation_frame_cost": stats(preparation) if preparation else None,
                "time_until_first_interactive_ms": round(loading_elapsed_ms, 3),
                "preparation_tasks": list(app.view.warmup_timings),
                "frames_measured": len(values),
                "within_60fps_budget_fraction": round(sum(v <= 1000 / 60 for v in values) / len(values), 4),
                "components": {k: stats(v) for k, v in samples.items()},
                "components_exclusive": {k: stats(v) for k, v in profiler.exclusive.items()},
                "rss_bytes": resident_bytes(),
                "renderer_caches": app.view.cache_stats(),
            }
            if args.camera_control:
                report["flights"][label]["consumed_control"] = {
                    "timings": {k: stats(v) for k, v in consumed.items()},
                    "unique_sequences": len(sequences),
                    "usable_frames": usable_frames,
                    "fraction_usable": usable_frames / max(1, len(values)),
                    "basis": (
                        "same consumed sequence through canvas and present call; excludes sensor and display delay"
                    ),
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
