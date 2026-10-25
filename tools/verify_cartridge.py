"""Renderiza o conteúdo montado do cartucho sem buscar assets no checkout.

Complementa o tsdk check; não simula o rastreamento nem o console físico.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    stage = args.stage.resolve()
    if not (stage / "ttea.toml").is_file():
        parser.error("pasta não contém cartucho montado")
    sys.path.insert(0, str(stage))
    os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
    import pygame

    import dobramundo
    from dobramundo.core import GameCore
    from dobramundo.persistence import Profile

    if stage not in Path(dobramundo.__file__).resolve().parents:
        raise RuntimeError("O teste importou o checkout em vez do cartucho")
    pygame.init()
    pygame.display.set_mode((1100, 650))
    report = {"version": dobramundo.__version__, "status": "running", "screens": [], "flights": {}}
    with tempfile.TemporaryDirectory(prefix="dobramundo-cartridge-") as data:
        os.environ["DOBRAMUNDO_DATA_DIR"] = data
        core = GameCore(Profile(), audio=False, save=lambda profile: True)
        core.platform = "ttea"
        try:
            for name in ("abertura", "vila", "mapa", "hangar", "piloto", "melhorias", "opcoes", "preparar", "sobre"):
                core.go(core.create_scene(name))
                for _ in range(6):
                    core.advance(1 / 60, [])
                report["screens"].append(name)
            for biome in ("amazonia", "caatinga"):
                scene = core.create_scene("voo", biome, seed=7, intro_override=False)
                scene.run.invincible = True
                core.go(scene)
                for frame in range(900):
                    if frame == 400:
                        scene.run.add_restoration(42)
                    core.advance(1 / 60, [])
                if core.view.warmup_pending or scene.run.flight_time <= 1:
                    raise RuntimeError("O cartucho ficou preso no preparo")
                report["flights"][biome] = {
                    "active_seconds": scene.run.flight_time,
                    "distance": scene.run.world.distance,
                }
            report["status"] = "ok"
        finally:
            core.shutdown()
            pygame.quit()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
