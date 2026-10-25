"""Teste de fumaça (--self-test N): percorre todas as telas e voa as duas fases.

Útil para validar o executável empacotado (sem interação). Grava
self_test.json na pasta de dados com sprites carregados, tempos de quadro
por fase (média e p95, em ms) e o resultado de cada voo.
"""

from __future__ import annotations

import json
import random
import re
import sys
import time
from typing import Dict, List

import pygame

from . import __version__
from .content.biomes import BIOME_ORDER
from .paths import bundle_dir, is_frozen, user_data_dir
from .persistence import Profile


def _frame_stats(times: List[float]) -> Dict[str, float]:
    if not times:
        return {"media_ms": 0.0, "p95_ms": 0.0}
    ordered = sorted(times)
    return {
        "media_ms": round(sum(times) / len(times) * 1000, 2),
        "p95_ms": round(ordered[int(len(ordered) * 0.95) - 1] * 1000, 2),
    }


def pose_check() -> dict:
    """O detector de pose carrega? (bibliotecas e modelo empacotados; não abre a webcam)."""
    from .input.camera import create_landmarker
    from .paths import find_pose_model

    model = find_pose_model()
    result = {"modelo": str(model) if model else None, "detector": "não testado"}
    if model is None:
        return result
    try:
        landmarker = create_landmarker(model)
        landmarker.close()
        result["detector"] = "ok"
    except ImportError as exc:
        result["detector"] = f"bibliotecas ausentes ({exc.name})"
    except Exception as exc:  # modelo corrompido, runtime do MediaPipe etc.
        result["detector"] = f"erro ({exc.__class__.__name__})"
        # PyInstallerImportError esconde a causa do OSError. Preserve o nome da
        # biblioteca/erro para o CI, mas não caminhos absolutos do executor.
        detail = _safe_error_detail(exc)
        if detail:
            result["detector_detalhe"] = detail
    return result


def _safe_error_detail(exc: Exception) -> str:
    """Detalhe diagnóstico sem diretórios locais ou traceback no relatório público."""
    message = str(exc)
    cause = exc.__cause__
    if cause is not None:
        message = f"{message}; causa {cause.__class__.__name__}: {cause}"
    # Reduz caminhos absolutos Windows/POSIX ao nome final (por ex. libxyz.so).
    message = re.sub(
        r"(?i)(?:[a-z]:[\\/]|/)[^'\"\r\n;:]+",
        lambda match: match.group(0).replace("\\", "/").rsplit("/", 1)[-1],
        message,
    )
    return message[:240]


REQUIRED_SPRITES = (
    "biome_sprites",
    "era_final_sprites",
    "waste_sprites",
    "plane_sprites",
    "plane_menu",
    "pilot_layers",
    "ui",
    "ground",
)


def check_report(report: dict, require_camera: bool) -> List[str]:
    """Critérios de aprovação: sprites carregados, voos que avançam e (no build) câmera."""
    failures = [f"pasta de sprites vazia: {name}" for name in REQUIRED_SPRITES if not report["sprites"].get(name)]
    for biome, flight in report["voos"].items():
        if flight["estagio"] < 2:
            failures.append(f"o voo em {biome} não chegou ao estágio 3")
        if flight.get("segundos_ativos", 0) <= 0 or flight.get("distancia", 0) <= 0:
            failures.append(f"o voo em {biome} não avançou após o preparo")
    if require_camera and report["camera"]["detector"] != "ok":
        failures.append(f"detector de pose: {report['camera']['detector']}")
    return failures


def run_self_test(frames: int, require_camera: bool = False) -> int:
    from .app import App
    from .scenes.about import AboutScene
    from .scenes.flight import FlightScene
    from .scenes.hangar import HangarScene
    from .scenes.intro import IntroScene
    from .scenes.map import MapScene
    from .scenes.options import OptionsScene
    from .scenes.pilot import PilotScene
    from .scenes.preparation import PreparationScene
    from .scenes.projection import ProjectionScene
    from .scenes.tutorial import DwellPracticeScene
    from .scenes.upgrades import UpgradesScene
    from .scenes.village import VillageScene

    profile = Profile()
    profile.consentimento = True
    app = App(audio=False, profile=profile)
    app.save = lambda: None  # não mexe no perfil real do jogador
    dt = 1.0 / 60.0
    report: dict = {
        "versao": __version__,
        "frozen": is_frozen(),
        "bundle_dir": str(bundle_dir()),
        "data_dir": str(user_data_dir()),
        "pygame": pygame.version.ver,
    }
    assets = app.assets
    report["sprites"] = {
        name: len(assets.folder(name))
        for name in (
            "biome_sprites",
            "era_final_sprites",
            "dieselpunk_sprites",
            "scenario_sprites",
            "waste_sprites",
            "powerup_sprites",
            "plane_sprites",
            "plane_menu",
            "pilot_layers",
            "ui",
            "ground",
        )
    }
    screens = {}
    for name, scene in (
        ("abertura", IntroScene(app)),
        ("vila", VillageScene(app)),
        ("mapa", MapScene(app)),
        ("hangar", HangarScene(app)),
        ("hangar_padrao", HangarScene(app, "padrao")),
        ("piloto", PilotScene(app)),
        ("selecao", DwellPracticeScene(app)),
        ("preparar", PreparationScene(app)),
        ("melhorias", UpgradesScene(app)),
        ("melhorias_aviao", UpgradesScene(app, "aviao")),
        ("opcoes", OptionsScene(app)),
        ("projecao", ProjectionScene(app)),
        ("sobre", AboutScene(app)),
        ("ods", AboutScene(app, "ods")),
    ):
        app.go(scene)
        times = []
        for _ in range(6):
            start = time.perf_counter()
            app.step(dt, [])
            times.append(time.perf_counter() - start)
        screens[name] = _frame_stats(times[1:])
    report["telas"] = screens
    flights = {}
    rng = random.Random(3)
    for biome in BIOME_ORDER:
        scene = FlightScene(app, biome)
        scene.run.invincible = True  # o teste não termina em game over
        app.go(scene)
        preparation_frames = 0
        for _ in range(1800):
            if app.scene is scene and not app.view.warmup_pending:
                break
            app.step(0.0, [])
            preparation_frames += 1
        else:
            raise RuntimeError(f"O preparo do voo em {biome} não terminou")
        times: List[float] = []
        per_stage = max(1, frames // 3)
        for frame in range(frames):
            # Mantém a carga de desenho pelos N quadros; conclusão e recompensas
            # têm testes de regras e capturas de resultado separados.
            scene.run.complete = False
            scene.run.complete_timer = 0.0
            if frame % per_stage == 0 and frame:  # força a passagem pelos três estágios
                scene.run.add_restoration(100.0 / 3.0)
            if frame % 40 == 0:
                key = rng.choice((pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN))
                app.input.pressed = {key}
            start = time.perf_counter()
            app.step(dt, [])
            times.append(time.perf_counter() - start)
        run = scene.run
        flights[biome] = {
            "quadros": frames,
            "quadros_preparo": preparation_frames,
            "segundos_ativos": round(run.flight_time, 3),
            "distancia": round(run.world.distance, 3),
            "carga_sintetica": "invencivel; encerramento por conclusao desativado",
            "transformacao": round(run.restoration, 1),
            "estrelas": run.stars,
            "estagio": run.stage,
            "recursos": run.resources,
            "pontos": run.score,
            **_frame_stats(times[10:]),
        }
    report["voos"] = flights
    report["camera"] = pose_check()
    failures = check_report(report, require_camera)
    report["falhas"] = failures
    report["status"] = "ok" if not failures else "falhou"
    app.input.stop_camera()
    path = user_data_dir() / "self_test.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if sys.stdout is not None:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not failures else 1
