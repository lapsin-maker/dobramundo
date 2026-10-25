"""Ponto de entrada: python -m dobramundo [--self-test [N]] [--sem-som]."""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path
from typing import List, Optional

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from . import APP_NAME  # noqa: E402
from .paths import user_data_dir  # noqa: E402


def first_scene(app):
    """Abertura (1ª vez) -> aviso ao supervisor (1ª vez) -> calibração (controle corporal) -> vila."""
    from .scenes.calibration import CalibrationScene
    from .scenes.consent import ConsentScene
    from .scenes.intro import IntroScene
    from .scenes.village import VillageScene

    scene = VillageScene(app)
    if app.input.uses_body:
        scene = CalibrationScene(app, return_to=scene)
    if not app.profile.consentimento:
        scene = ConsentScene(app, scene)
    # A abertura completa aparece na primeira vez; depois fica em Opções > "Ver a abertura".
    return scene if app.profile.abertura_vista else IntroScene(app, scene)


def show_message(title: str, text: str) -> None:
    """Mensagem simples ao usuário (sem traceback)."""
    if sys.platform.startswith("win"):
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, text, title, 0x40)
            return
        except Exception:
            pass
    stream = sys.stderr or sys.stdout
    if stream is not None:
        print(f"{title}: {text}", file=stream)


def log_crash() -> Optional[Path]:
    try:
        path = user_data_dir() / "dobramundo_erro.log"
        path.write_text(traceback.format_exc(), encoding="utf-8")
        return path
    except OSError:
        return None


def arg_value(argv: List[str], flag: str) -> Optional[str]:
    if flag in argv:
        index = argv.index(flag)
        if index + 1 < len(argv) and not argv[index + 1].startswith("--"):
            return argv[index + 1]
    return None


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    import pygame

    try:
        if "--self-test" in argv:
            from .selftest import run_self_test

            value = arg_value(argv, "--self-test")
            return run_self_test(int(value) if value and value.isdigit() else 240)
        from .app import App

        app = App(audio="--sem-som" not in argv)
        app.run(first_scene(app))
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        path = log_crash()
        where = f"\nDetalhes técnicos em:\n{path}" if path else ""
        show_message(APP_NAME, "O jogo encontrou um erro e precisou ser fechado." + where)
        return 1
    finally:
        if pygame.get_init():
            pygame.quit()


if __name__ == "__main__":
    sys.exit(main())
