"""Valida o modelo geométrico de rotas em milhares de pistas determinísticas.

Uso: python tools/check_routes.py --seeds 1000
O resultado valida apenas o contrato do planner, não a alcançabilidade física.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dobramundo import config as C  # noqa: E402
from dobramundo.content.biomes import BIOMES  # noqa: E402
from dobramundo.game.world import RoutePlanner, World, find_reachable_route  # noqa: E402


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * fraction))
    return round(ordered[index], 3)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=1000)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error("--seeds precisa ser maior que zero")

    route_insert_ms: list[float] = []
    spawn_pattern_ms: list[float] = []
    original_try_add = RoutePlanner.try_add
    original_spawn_pattern = World.spawn_pattern

    def timed_try_add(planner, entity, entity_global_z):
        started = time.perf_counter()
        result = original_try_add(planner, entity, entity_global_z)
        route_insert_ms.append((time.perf_counter() - started) * 1000.0)
        return result

    def timed_spawn_pattern(world, z):
        started = time.perf_counter()
        result = original_spawn_pattern(world, z)
        spawn_pattern_ms.append((time.perf_counter() - started) * 1000.0)
        return result

    RoutePlanner.try_add = timed_try_add
    World.spawn_pattern = timed_spawn_pattern

    report = {
        "contract": {
            "origin": "center at START_ALTITUDE",
            "reaction_margin_s": 0.35,
            "reversal_margin_s": 0.15,
            "dynamics": (
                "minimum of saturated POSITION_RESPONSE and accelerating FLIGHT_RESPONSE displacement envelopes"
            ),
            "movement_speed_fraction": 0.75,
            "grid": "x=10 world units, y=11 world units plus start/rest/max",
            "collision": "entity obstacle AABB expanded by baseline plane AABB",
            "limitation": "deterministic reference route only; no claim of physical/user reachability",
        },
        "runs": {},
    }
    failures = []
    independent_checks = independent_passes = 0
    for biome_key, biome in BIOMES.items():
        for mode in ("normal", "dificil"):
            attempted = kept = adjusted = skipped = route_success = 0
            lane_counts = {-1: 0, 0: 0, 1: 0}
            kind_counts = {"low": 0, "gate": 0, "tower": 0}
            for seed in range(args.seeds):
                restoration = (5.0, 50.0, 90.0)[seed % 3]
                world = World(biome, mode, random.Random(seed), restoration=restoration)
                route_found = bool(world.route_planner.frontier)
                if seed < min(25, args.seeds):
                    independent_checks += 1
                    independent_route = find_reachable_route(world.entities, mode)
                    independent_passes += independent_route is not None
                    route_found = route_found and independent_route is not None
                attempted += world.route_obstacles_requested
                kept += world.route_obstacles_kept
                adjusted += world.route_obstacles_adjusted
                skipped += world.route_obstacles_skipped
                route_success += route_found
                for entity in world.entities:
                    if entity.spec is not None:
                        lane_counts[entity.lane] += 1
                        if entity.kind in kind_counts:
                            kind_counts[entity.kind] += 1
                if not route_found or world.route_tutorial_failures:
                    failures.append({"biome": biome_key, "mode": mode, "seed": seed})
            key = f"{biome_key}:{mode}"
            report["runs"][key] = {
                "seeds": args.seeds,
                "routes_found": route_success,
                "obstacles_requested": attempted,
                "obstacles_kept": kept,
                "obstacles_adjusted": adjusted,
                "obstacles_skipped": skipped,
                "keep_rate": round(kept / attempted, 4) if attempted else 1.0,
                "lanes": lane_counts,
                "kinds": kind_counts,
            }
            print(f"{key}: {route_success}/{args.seeds} rotas", file=sys.stderr, flush=True)

    advancement = {"worlds": 0, "cycles_per_world": 500, "tutorial_failures": 0, "empty_frontiers": 0}
    for biome in BIOMES.values():
        for mode in ("normal", "dificil"):
            factor = C.NORMAL_SPEED_FACTOR if mode == "normal" else 1.0
            for intro in (False, True):
                for seed in range(min(10, args.seeds)):
                    world = World(biome, mode, random.Random(seed + 10000), intro=intro)
                    for _ in range(advancement["cycles_per_world"]):
                        speed = (
                            C.BASE_SPEED
                            + world.restoration * C.RESTORATION_SPEED_GAIN
                            + world.difficulty * C.DIFFICULTY_SPEED_GAIN
                        ) * factor
                        dt = 0.05
                        world.advance(dt, speed * dt)
                        world.prune()
                    advancement["worlds"] += 1
                    advancement["tutorial_failures"] += world.route_tutorial_failures
                    advancement["empty_frontiers"] += not bool(world.route_planner.frontier)
                    if world.route_tutorial_failures or not world.route_planner.frontier:
                        failures.append({"biome": biome.key, "mode": mode, "seed": seed, "intro": intro})
    report["independent_full_validation"] = {
        "checks": independent_checks,
        "passed": independent_passes,
    }
    report["advancement_checks"] = advancement

    report["timings_ms"] = {
        "route_insert": {
            "samples": len(route_insert_ms),
            "p95": percentile(route_insert_ms, 0.95),
            "p99": percentile(route_insert_ms, 0.99),
            "max": round(max(route_insert_ms), 3) if route_insert_ms else 0.0,
        },
        "spawn_pattern": {
            "samples": len(spawn_pattern_ms),
            "p95": percentile(spawn_pattern_ms, 0.95),
            "p99": percentile(spawn_pattern_ms, 0.99),
            "max": round(max(spawn_pattern_ms), 3) if spawn_pattern_ms else 0.0,
        },
    }

    report["failures"] = failures
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
