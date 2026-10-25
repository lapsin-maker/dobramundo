"""Compare the current painted ground with a selected Git revision.

CPU-only measurement with SDL's dummy display; it never starts a webcam.
Example: ``python tools/benchmark_ground.py --baseline-ref HEAD --frames 80``
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def baseline_class(reference: str):
    try:
        source = subprocess.check_output(
            ["git", "show", f"{reference}:dobramundo/engine/painted_route.py"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Não foi possível ler PaintedGround em {reference}: {exc}") from None
    namespace = {
        "__name__": "dobramundo.engine._benchmark_baseline_painted_route",
        "__package__": "dobramundo.engine",
    }
    exec(compile(source, f"{reference}:dobramundo/engine/painted_route.py", "exec"), namespace)
    return namespace["PaintedGround"]


def pixel_metrics(surface, horizon: int) -> dict:
    import pygame

    previous = None
    identical = 0
    rows = 0
    for y in range(horizon + 1, surface.get_height()):
        # A compact row snapshot is sufficient for exact repeated-row detection.
        current = pygame.image.tostring(surface.subsurface((0, y, surface.get_width(), 1)), "RGB")
        if previous == current:
            identical += 1
        previous = current
        rows += 1
    return {
        "identical_adjacent_rows": round(identical / max(1, rows - 1), 4),
        "distinct_vertical_transitions": rows - 1 - identical,
        "sampled_rows": rows,
    }


def run_case(cls, atlas, biome: str, frames: int, pygame, config) -> dict:
    painter = cls(atlas)
    if hasattr(painter, "prepare_vertical_mip"):
        for name in tuple(painter.vertical_mips):
            while painter.vertical_mips[name][-1].get_height() > 16:
                painter.prepare_vertical_mip(name)
    surface = pygame.display.get_surface()
    samples = []
    first_ms = None
    for frame in range(frames):
        distance = frame * 2.8
        cam = frame * 0.12
        surface.fill((12, 15, 18))
        started = time.perf_counter()
        painter.paint(surface, biome, distance, cam, (230, 220, 190))
        elapsed = (time.perf_counter() - started) * 1000.0
        if first_ms is None:
            first_ms = elapsed
        samples.append(elapsed)
    # Compare raster quality at the same deterministic state for each renderer.
    surface.fill((12, 15, 18))
    painter.paint(surface, biome, max(0, frames - 1) * 2.8, max(0, frames - 1) * 0.12, (230, 220, 190))
    ordered = sorted(samples)
    index = min(len(ordered) - 1, int(len(ordered) * 0.95))
    return {
        "frames": frames,
        "first_frame_ms": round(first_ms or 0.0, 3),
        "median_ms": round(statistics.median(samples), 3),
        "p95_ms": round(ordered[index], 3),
        "max_ms": round(max(samples), 3),
        **pixel_metrics(surface, config.HORIZON_Y),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default="HEAD", help="Git ref supplying the comparison renderer")
    parser.add_argument("--frames", type=int, default=80, help="rendered frames per biome and renderer")
    args = parser.parse_args()
    if args.frames < 5 or args.frames > 10000:
        parser.error("--frames deve ficar entre 5 e 10000")

    import pygame

    pygame.init()
    pygame.display.set_mode((1100, 650))
    from dobramundo import config as C
    from dobramundo.engine.assets import Assets
    from dobramundo.engine.painted_route import PaintedGround

    assets = Assets()
    atlas = assets.sprite("watercolor", "terrain_tiles_v3")
    if atlas is None:
        atlas = assets.sprite("watercolor", "terrain_tiles")
    if atlas is None:
        raise SystemExit("Atlas de terreno ausente; comparação não disponível.")
    old_ground = baseline_class(args.baseline_ref)
    results = {}
    for biome in ("amazonia", "caatinga"):
        results[f"{biome}:baseline"] = run_case(old_ground, atlas, biome, args.frames, pygame, C)
        results[f"{biome}:current"] = run_case(PaintedGround, atlas, biome, args.frames, pygame, C)
    print(
        json.dumps(
            {
                "measurement": "painted_ground_only",
                "display": "SDL dummy software surface 1100x650",
                "baseline_ref": args.baseline_ref,
                "frames_per_case": args.frames,
                "camera": False,
                "results": results,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
