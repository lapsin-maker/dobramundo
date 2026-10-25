"""Capturas reprodutíveis das telas e estados de erro, usando perfil sintético."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ.update(
        SDL_VIDEODRIVER="dummy",
        SDL_AUDIODRIVER="dummy",
        PYGAME_HIDE_SUPPORT_PROMPT="1",
        DOBRAMUNDO_DATA_DIR=str(args.out / "perfil-sintetico"),
    )
    import pygame

    from dobramundo.app import App
    from dobramundo.persistence import Profile, create_profile_slot
    from dobramundo.scenes import make_scene

    profile = Profile()
    profile.consentimento = True
    app = App(audio=False, profile=profile)
    report = {"screens": [], "layout_failures": []}

    def capture(name, scene, frames=6):
        app.go(scene)
        for _ in range(frames):
            app.step(1 / 60, [])
        screen_rect = app.canvas.get_rect()
        for button in scene.menu.buttons:
            if not screen_rect.contains(button.rect):
                report["layout_failures"].append({"screen": name, "button": button.key, "rect": list(button.rect)})
        for index, button in enumerate(scene.menu.buttons):
            for other in scene.menu.buttons[index + 1 :]:
                if button.rect.colliderect(other.rect):
                    report["layout_failures"].append({"screen": name, "overlap": [button.key, other.key]})
        pygame.image.save(app.canvas, args.out / (name + ".png"))
        report["screens"].append(name)

    try:
        for name in ("vila", "mapa", "hangar", "piloto", "preparar", "opcoes"):
            capture(name, make_scene(app, name))
        for enabled in (False, True):
            app.options.modo_exploracao = enabled
            app.options.assistencia_previsivel = enabled
            app.options.limite_voo_s = 120 if enabled else 0
            scene = make_scene(app, "preparar")
            scene.page = "meu_voo"
            capture("meu-voo-" + str(int(enabled)), scene)
        for _ in range(5):
            create_profile_slot()
        capture("perfis", make_scene(app, "perfis"))
        scene = make_scene(app, "perfis")
        scene.error = "Não foi possível salvar este piloto. A troca foi cancelada."
        capture("perfis-erro", scene)
        app.storage_notice = "O perfil estava danificado; recuperei o último salvamento íntegro. Confira o progresso."
        capture("vila-recuperacao", make_scene(app, "vila"))
        app.storage_notice = None
        app.options.limite_voo_s = 0
        app.profile.piloto_montado = True
        app.profile.piloto.update(pele="pele4", cabelo="crespo", cor_cabelo="preto", roupa="amarela", olhos="castanhos")
        for biome in ("amazonia", "caatinga"):
            for contrast in (False, True):
                app.options.alto_contraste = contrast
                app.apply_options()
                scene = make_scene(app, "voo", biome, seed=20261025, intro_override=False)
                scene.run.invincible = True
                scene.run.add_restoration(68)
                capture(biome + ("-contraste" if contrast else ""), scene, frames=120)
        (args.out / "captures.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    finally:
        app.input.stop_camera()
        pygame.quit()
    print(json.dumps(report, ensure_ascii=False))
    return int(bool(report["layout_failures"]))


if __name__ == "__main__":
    raise SystemExit(main())
