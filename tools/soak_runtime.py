"""Percurso prolongado com trocas de cenas; métricas sem câmera ou perfil real.

python tools/soak_runtime.py --out <pasta> --cycles 12 --frames 1200
Tempo simulado difere de tempo de parede. RSS inclui caches/allocator do processo.
Não prova estabilidade no console físico nem ergonomia dos controles.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import sys
import time
from pathlib import Path

from benchmark_runtime import resident_bytes, stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cycles", type=int, default=12)
    parser.add_argument("--frames", type=int, default=1200)
    args = parser.parse_args()
    if args.cycles < 2 or args.frames < 1:
        parser.error("Use pelo menos 2 ciclos e 1 quadro")
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        DOBRAMUNDO_DATA_DIR=str(args.out / "perfil-sintetico"),
        PYGAME_HIDE_SUPPORT_PROMPT="1",
    )
    import pygame

    from dobramundo import __version__
    from dobramundo.app import App
    from dobramundo.persistence import Profile
    from dobramundo.scenes import make_scene

    profile = Profile()
    profile.consentimento = True
    profile.piloto_montado = True
    profile.tutorial_visto = True
    profile.opcoes.limite_voo_s = 0
    app = App(audio=False, profile=profile)
    app.save = lambda: None  # a medição não é um save de jogador
    started = time.perf_counter()
    report = {
        "version": __version__,
        "cycles": [],
        "camera": False,
        "dt_s": 1 / 60,
        "scope": "synthetic rendering and scene lifecycle; not physical acceptance",
    }
    dt = 1 / 60
    failures = []
    try:
        for cycle in range(args.cycles):
            biome = ("amazonia", "caatinga")[cycle % 2]
            app.options.alto_contraste = bool((cycle // 2) % 2)
            app.apply_options()
            samples = []
            for name in ("vila", "mapa", "piloto", "hangar", "preparar"):
                app.go(make_scene(app, name))
                for _ in range(6):
                    app.step(dt, [])
            scene = make_scene(app, "voo", biome)
            scene.run.invincible = True  # render stress only; economy uses tools/balance.py
            scene.run.focus.enabled = False
            app.go(scene)
            for frame in range(args.frames):
                if frame in (args.frames // 3, 2 * args.frames // 3):
                    scene.run.add_restoration(34)
                app.input.pressed = {pygame.K_LEFT if math.sin(frame / 50) < 0 else pygame.K_RIGHT}
                tick = time.perf_counter()
                app.step(dt, [])
                samples.append((time.perf_counter() - tick) * 1000)
            entity_count = len(scene.run.world.entities)
            if entity_count > 300:
                failures.append(f"objetos sem poda no ciclo {cycle}: {entity_count}")
            app.input.pressed.clear()
            app.go(make_scene(app, "vila"))
            app.step(dt, [])
            del scene
            gc.collect()
            loaded = getattr(app.assets, "_loaded", {})
            surface_bytes = sum(s.get_pitch() * s.get_height() for s in loaded.values() if s is not None)
            report["cycles"].append(
                {
                    "cycle": cycle,
                    "biome": biome,
                    "contrast": app.options.alto_contraste,
                    "rss_bytes": resident_bytes() or None,
                    "loaded_surface_bytes": surface_bytes,
                    "loaded_images": len(loaded),
                    "renderer_caches": app.view.cache_stats(),
                    "entities": entity_count,
                    **stats(samples),
                }
            )
        report["wall_seconds"] = round(time.perf_counter() - started, 3)
        report["simulated_seconds"] = round(args.cycles * (args.frames + 31) * dt, 3)
        report["failures"] = failures
        report["status"] = "ok" if not failures else "failed"
        (args.out / "soak.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        app.input.stop_camera()
        pygame.quit()
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
