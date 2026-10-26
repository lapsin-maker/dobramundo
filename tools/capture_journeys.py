"""Captura jornadas temporais curtas para conferir emendas, estágios e obras.

As imagens usam o renderer pygame real e um perfil sintético. O manifesto registra
as distâncias/estados usados; a animação serve para inspeção visual, não para medir
física, desempenho ou experiência de crianças.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _save_gif(frames, path: Path) -> None:
    import pygame
    from PIL import Image

    images = [Image.frombytes("RGB", frame.get_size(), pygame.image.tostring(frame, "RGB")) for frame in frames]
    # Reduz o peso do artefato sem alterar a proporção do quadro lógico.
    images = [image.resize((550, 325), Image.Resampling.LANCZOS) for image in images]
    images[0].save(path, save_all=True, append_images=images[1:], duration=90, loop=0, optimize=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True, help="pasta externa para GIFs, PNGs e manifesto")
    parser.add_argument("--frames", type=int, default=30, choices=(24, 30, 36))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        PYGAME_HIDE_SUPPORT_PROMPT="1",
        DOBRAMUNDO_DATA_DIR=str(args.out / "perfil-sintetico"),
    )

    import pygame

    from dobramundo import config as C
    from dobramundo.app import App
    from dobramundo.content.biomes import BIOMES
    from dobramundo.content.progress import VILLAGE_UPGRADES
    from dobramundo.engine.painted_route import PaintedGround, PaintedRoute
    from dobramundo.persistence import Profile
    from dobramundo.scenes import make_scene

    profile = Profile()
    profile.consentimento = True
    app = App(audio=False, profile=profile)
    manifest = {
        "profile": "synthetic",
        "renderer": "pygame real; GIFs downscaled to 550x325",
        "frames_per_gif": args.frames,
        "journeys": [],
        "works": [],
        "limitations": [
            "amostragem visual deterministica; nao representa controles ou fisica de um voo",
            "reduzir movimento afeta efeitos do renderer; distancia de mundo ainda avanca entre quadros",
        ],
    }

    def render_flight(biome_key: str, reduced: bool, kind: str, values: list[float], world_values: list[float]):
        app.options.reduzir_movimento = reduced
        app.options.alto_contraste = False
        app.apply_options()
        scene = make_scene(app, "voo", biome_key, seed=20261025, intro_override=False)
        app.go(scene)
        app.advance(0.0, [])
        for _ in range(1600):
            if not app.view.warmup_pending:
                break
            app.advance(0.0, [])
        if app.view.warmup_pending:
            raise RuntimeError(f"a preparação visual não terminou: {biome_key}")

        scene.started = True
        scene.banners.clear()
        scene.run.world.entities.clear()
        scene.run.beams.clear()
        frames = []
        samples = []
        for index, (distance, visual) in enumerate(zip(values, world_values)):
            world = scene.run.world
            world.distance = float(distance)
            world.visual = float(visual)
            world.restoration = float(visual)
            # Cenografia sem entidades mantém a leitura do chão e das margens.
            world.entities.clear()
            scene.draw(app.canvas)
            frames.append(app.canvas.copy())
            samples.append(
                {
                    "frame": index,
                    "distance": round(float(distance), 2),
                    "visual_restoration": round(float(visual), 2),
                    "horizon_stage_mix": list(app.view.watercolor.stage_mix(float(visual))),
                    "bank_stage_mix_by_depth": {
                        str(depth): list(PaintedRoute.stage_blend(float(visual), depth)) for depth in (100, 500, 1500)
                    },
                }
            )
        path = args.out / f"{biome_key}-{kind}-reduzir-{int(reduced)}.gif"
        _save_gif(frames, path)
        manifest["journeys"].append(
            {
                "file": path.name,
                "biome": biome_key,
                "reduced_motion": reduced,
                "journey": kind,
                "samples": samples,
            }
        )

    try:
        for biome_key in BIOMES:
            tile = PaintedGround.TILE_Z
            seam_center = tile * 2
            offsets = [((index / (args.frames - 1)) - 0.5) * 220 for index in range(args.frames)]
            for reduced in (False, True):
                render_flight(
                    biome_key,
                    reduced,
                    "emenda",
                    [seam_center + offset for offset in offsets],
                    [C.START_RESTORATION] * args.frames,
                )
                for stage in (1, 2):
                    start = C.START_RESTORATION if stage == 1 else C.ERA_SPAN
                    end = C.ERA_SPAN * stage
                    # Include the early continuous blend and the four-point delay
                    # of the near bank, with samples outside both endpoints.
                    visual_values = [
                        start - 2 + (end - start + 8) * index / (args.frames - 1) for index in range(args.frames)
                    ]
                    render_flight(
                        biome_key,
                        reduced,
                        "mudanca-estagio-" + str(stage),
                        [900 + 8 * index for index in range(args.frames)],
                        visual_values,
                    )

        # Pares capturados na mesma cena para manter câmera, escala e perfil iguais.
        app.options.reduzir_movimento = True
        app.apply_options()
        village_scene = make_scene(app, "vila")
        app.go(village_scene)
        app.advance(0.0, [])
        for index, upgrade in enumerate(VILLAGE_UPGRADES):
            for owned, state in ((index, "antes"), (index + 1, "depois")):
                profile.vila = [item.key for item in VILLAGE_UPGRADES[:owned]]
                village_scene.build()
                village_scene.draw(app.canvas)
                filename = f"obra-{index + 1:02d}-{upgrade.key}-{state}.png"
                pygame.image.save(app.canvas, args.out / filename)
                manifest["works"].append(
                    {
                        "file": filename,
                        "upgrade": upgrade.key,
                        "state": state,
                        "owned_before_capture": [item.key for item in VILLAGE_UPGRADES[:owned]],
                    }
                )

        manifest_path = args.out / "journeys.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {"journeys": len(manifest["journeys"]), "works": len(manifest["works"]), "manifest": str(manifest_path)}
            )
        )
    finally:
        app.input.stop_camera()
        pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
