"""Configuração da suíte do Dobramundo: sem janela nem áudio, dados isolados.

Os sprites são carregados uma única vez por sessão (engine.assets.shared_assets),
então a suíte inteira roda em poucos segundos.
"""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path

# Deve vir antes de qualquer uso do pygame/SDL.
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import pygame  # noqa: E402
import pytest  # noqa: E402

from dobramundo import config as C  # noqa: E402
from dobramundo import paths  # noqa: E402
from dobramundo.content.biomes import BIOMES  # noqa: E402
from dobramundo.game.run import FlightRun  # noqa: E402
from dobramundo.persistence import Profile  # noqa: E402

DT = 1.0 / 60.0


@pytest.fixture(scope="session", autouse=True)
def display():
    pygame.init()
    surface = pygame.display.set_mode((C.WIDTH, C.HEIGHT))
    yield surface
    pygame.quit()


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    """Perfil e relatórios em tmp_path; nenhum save antigo do projeto é lido."""
    folder = tmp_path / "dados"
    monkeypatch.setenv(paths.DATA_DIR_ENV, str(folder))
    monkeypatch.setattr(paths, "legacy_data_dirs", lambda: [tmp_path / "legado"])
    import dobramundo.persistence as persistence

    monkeypatch.setattr(persistence, "legacy_data_dirs", lambda: [tmp_path / "legado"])
    paths.reset_data_dir_cache()
    yield folder
    paths.reset_data_dir_cache()


def make_run(biome: str = "amazonia", mode: str = "dificil", parts=None, clear: bool = True) -> FlightRun:
    """Voo determinístico; com clear=True, sem objetos (os testes os inserem à mão)."""
    run = FlightRun(BIOMES[biome], mode, parts or {}, rng=random.Random(1))
    run.player.maneuver = None
    if clear:
        run.world.entities.clear()
        run.world.spawn_pattern = lambda z: None
    return run


def advance(run: FlightRun, seconds: float, ix: float = 0.0, iy: float = 0.0) -> None:
    for _ in range(int(round(seconds / DT))):
        run.update(DT, ix, iy)


@pytest.fixture
def run():
    return make_run()


@pytest.fixture
def app(monkeypatch):
    from dobramundo.app import App

    profile = Profile()
    profile.consentimento = True
    instance = App(audio=False, profile=profile)
    yield instance
    instance.input.stop_camera()
