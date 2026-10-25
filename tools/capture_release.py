"""Capturas reprodutíveis com perfil sintético; voos omitem partículas transitórias no quadro final."""

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
    parser.add_argument(
        "--reference", action="store_true", help="reduz movimento para comparação visual determinística"
    )
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
    profile.opcoes.reduzir_movimento = args.reference
    app = App(audio=False, profile=profile)
    report = {
        "profile": "synthetic",
        "flight_capture_note": "after 120 frames, clear transient run.beams and draw one clean final frame",
        "screens": [],
        "layout_failures": [],
    }

    def capture(name, scene, frames=6, clean_flight=False):
        app.go(scene)
        for _ in range(frames):
            app.step(1 / 60, [])
        for _ in range(600):
            if not getattr(scene, "waiting_for_assets", False) and not getattr(app.view, "warmup_pending", False):
                break
            app.step(1 / 60, [])
        else:
            report["layout_failures"].append({"screen": name, "error": "warmup did not finish"})
        if clean_flight:
            scene.run.beams.clear()
            scene.draw(app.canvas)
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
        from dobramundo.content.progress import VILLAGE_UPGRADES
        from dobramundo.scenes.intro import PAGES
        from dobramundo.scenes.options import OPTION_PAGES

        for page, _, _ in OPTION_PAGES:
            scene = make_scene(app, "opcoes")
            scene.section = page
            capture("opcoes-" + page, scene)
        for page in range(len(PAGES)):
            scene = make_scene(app, "abertura")
            scene._manual_page = page
            scene.time = sum(PAGES[:page]) + 1
            capture("historia-" + str(page), scene)
        for stage, count in (
            ("industrial", 0),
            ("transicao", len(VILLAGE_UPGRADES) // 2),
            ("solarpunk", len(VILLAGE_UPGRADES)),
        ):
            profile.vila = [item.key for item in VILLAGE_UPGRADES[:count]]
            capture("vila-" + stage, make_scene(app, "vila"))
        profile.vila = []
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
                capture(biome + ("-contraste" if contrast else ""), scene, frames=120, clean_flight=True)
            for stage, progress in (("industrial", 5), ("transicao", 48), ("solarpunk", 100)):
                app.options.alto_contraste = False
                app.apply_options()
                profile.transformacao_cidades[biome] = progress
                scene = make_scene(app, "voo", biome, seed=20261025, intro_override=False)
                scene.run.invincible = True
                capture(biome + "-" + stage, scene, frames=60, clean_flight=True)
            scene.run.complete = True
            scene.run.stars = 2  # sem peças compradas, o resultado ensina o próximo passo
            scene.run.resources.update(papel=12, plastico=8, metal=4, vidro=8)
            scene.run.score = 520
            capture("resultado-" + biome, make_scene(app, "resultado", scene.run))
        profile.transformacao_cidades["amazonia"] = 42
        profile.estrelas["amazonia"] = 1
        scene = make_scene(app, "voo", "amazonia", seed=20261025, intro_override=False)
        scene.run.timeout = True
        scene.run.flight_time = 120
        scene.run.resources.update(papel=8, plastico=4, metal=4, vidro=4)
        scene.run.score = 325
        capture("resultado-tempo", make_scene(app, "resultado", scene.run))
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
