"""Captura telas reais e mede renderização; não modifica arte nem o perfil do jogador.

Uso: python tools/qa_sprint3.py --out <pasta> [--record]
As gravações são ensaios determinísticos de cenário, com progressão visual forçada.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, required=True)
parser.add_argument("--record", action="store_true")
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=True)
os.environ.update(
    SDL_VIDEODRIVER="dummy",
    SDL_AUDIODRIVER="dummy",
    DOBRAMUNDO_DATA_DIR=str(args.out / "perfil-qa"),
    PYGAME_HIDE_SUPPORT_PROMPT="1",
)

import pygame  # noqa: E402

from dobramundo.app import App  # noqa: E402
from dobramundo.content.pilot import DEFAULT_PILOT  # noqa: E402
from dobramundo.content.progress import VILLAGE_UPGRADES  # noqa: E402
from dobramundo.game.entities import Entity  # noqa: E402
from dobramundo.persistence import Profile  # noqa: E402
from dobramundo.scenes.flight import FlightScene  # noqa: E402
from dobramundo.scenes.hangar import HangarScene  # noqa: E402
from dobramundo.scenes.intro import PAGES, IntroScene  # noqa: E402
from dobramundo.scenes.map import MapScene  # noqa: E402
from dobramundo.scenes.options import OptionsScene  # noqa: E402
from dobramundo.scenes.pilot import PilotScene  # noqa: E402
from dobramundo.scenes.preparation import PreparationScene  # noqa: E402
from dobramundo.scenes.result import ResultScene  # noqa: E402
from dobramundo.scenes.tutorial import DwellPracticeScene  # noqa: E402
from dobramundo.scenes.upgrades import UpgradesScene  # noqa: E402
from dobramundo.scenes.village import VillageScene  # noqa: E402


def stats(values):
    values = sorted(values)
    return {
        "median_ms": round(statistics.median(values), 3),
        "p95_ms": round(values[int(len(values) * 0.95)], 3),
        "p99_ms": round(values[int(len(values) * 0.99)], 3),
        "max_ms": round(max(values), 3),
    }


def capture(name):
    pygame.image.save(app.canvas, str(args.out / (name + ".png")))


profile = Profile(consentimento=True, piloto_montado=True)
profile.piloto.update(pele="pele4", cabelo="crespo", cor_cabelo="castanho", olhos="mel", roupa="laranja")
app = App(audio=False, profile=profile)
app.save = lambda: None
report = {"conditions": "SDL dummy; CPU; no webcam; warmup 60 frames; logical 1100x650", "flights": {}}
for count, name in ((0, "inicial"), (4, "intermediaria"), (8, "final")):
    profile.vila = [item.key for item in VILLAGE_UPGRADES[:count]]
    app.go(VillageScene(app))
    app.step(1 / 60, [])
    capture("vila-" + name)
profile.vila = []
look = profile.piloto.copy()
profile.piloto = DEFAULT_PILOT.copy()
app.go(PilotScene(app))
app.step(1 / 60, [])
capture("piloto-neutro")
profile.piloto = {**look, "cadeira": "sim", "oculos": "redondo"}
app.go(PilotScene(app))
app.step(1 / 60, [])
capture("piloto-acessivel")
profile.piloto = look
for name, scene in (
    ("mapa", MapScene(app)),
    ("hangar", HangarScene(app)),
    ("opcoes", OptionsScene(app)),
    ("preparar", PreparationScene(app)),
    ("mirar", DwellPracticeScene(app)),
    ("pecas", UpgradesScene(app, "aviao")),
):
    app.go(scene)
    app.step(1 / 60, [])
    capture(name)
intro = IntroScene(app)
app.go(intro)
app.step(1 / 60, [])
for page in range(4):
    intro._manual_page = page
    intro.time = sum(PAGES[:page]) + PAGES[page] * 0.62
    intro.build()
    intro.draw(app.canvas)
    capture("historia-" + str(page + 1))

for city in ("amazonia", "caatinga"):
    flight = FlightScene(app, city)
    flight.run.invincible = True
    app.go(flight)
    app.step(1 / 60, [])
    flight.banners.clear()
    flight.run.world.entities.clear()
    flight.run.world.spawn_pattern = lambda z: None
    for high_contrast in (False, True):
        app.options.alto_contraste = high_contrast
        app.apply_options()
        values = []
        gameplay_frames = []
        for _frame in range(660):
            start = time.perf_counter()
            app.step(1 / 60, [])
            values.append((time.perf_counter() - start) * 1000)
            if args.record and not high_contrast and _frame >= 60 and _frame % 3 == 0:
                from PIL import Image

                preview = pygame.transform.smoothscale(app.canvas, (660, 390))
                gameplay_frames.append(Image.frombytes("RGB", preview.get_size(), pygame.image.tobytes(preview, "RGB")))
        report["flights"][city + ("_contrast" if high_contrast else "_normal")] = stats(values[60:])
        capture(city + ("-contraste" if high_contrast else "-normal"))
        if gameplay_frames:
            gameplay_frames[0].save(
                args.out / ("voo-" + city + ".webp"),
                save_all=True,
                append_images=gameplay_frames[1:],
                duration=50,
                loop=0,
                quality=74,
                method=3,
            )
            gameplay_frames.clear()
    # Stress: player at each useful extreme, strongest allowed enlargement.
    app.options.escala_contraste = 1.6
    app.apply_options()
    for x, y, name in ((-220, 22, "esq-baixo"), (220, 155, "dir-cima")):
        flight.run.player.x, flight.run.player.y = x, y
        flight.run.player.cam_x = x * 0.12
        flight.draw(app.canvas)
        capture(city + "-contraste-" + name)
    app.options.alto_contraste = False
    app.options.escala_contraste = 1.3
    app.apply_options()
    flight.run.player.x, flight.run.player.y = 0, 95
    flight.run.player.cam_x = 0
    flight.run.world.entities = [
        Entity(500, -1, "waste", y=100, sprite="papel"),
        Entity(850, 0, "magnet", y=105),
        Entity(600, 1, "low", spec=flight.biome.industrial_obstacles["low"][0]),
    ]
    flight.run.shield_timer, flight.run.magnet_timer = 4, 5
    for contrast in (False, True):
        app.options.alto_contraste = contrast
        app.apply_options()
        flight.draw(app.canvas)
        capture(city + "-legibilidade" + ("-contraste" if contrast else ""))
    app.options.alto_contraste = False
    app.apply_options()
    flight.run.shield_timer = flight.run.magnet_timer = 0
    if args.record:
        from PIL import Image

        # 96 s at 340 units/s = 6 cycles of the bank-layout period (24*220).
        # We sample native world drawing at 10fps; the stage progression is
        # forced for QA, not claimed to be a player completing a flight.
        frames = []
        render_times = []
        flight.run.world.entities.clear()
        flight.run.missions.current = None
        flight.banners.clear()
        for frame in range(960):
            elapsed = frame / 10
            world = flight.run.world
            world.distance = elapsed * 340
            world.visual = 5 + 90 * frame / 959
            world.restoration = world.visual
            flight.run.stage = world.stage
            app.view.elapsed = elapsed
            flight.run.player.cam_x = 36 * math.sin(elapsed / 9)
            start = time.perf_counter()
            flight.draw(app.canvas)
            render_times.append((time.perf_counter() - start) * 1000)
            preview = pygame.transform.smoothscale(app.canvas, (660, 390))
            frames.append(Image.frombytes("RGB", preview.get_size(), pygame.image.tobytes(preview, "RGB")))
            if frame in (310, 355, 675, 740):
                capture(f"{city}-transicao-{frame}")
        frames[0].save(
            args.out / ("percurso-" + city + ".webp"),
            save_all=True,
            append_images=frames[1:],
            duration=100,
            loop=0,
            quality=72,
            method=3,
        )
        report[city + "_route"] = {
            "duration_s": 96,
            "distance": 32606,
            "bank_cycles": 6.17,
            "capture_size": [660, 390],
            "capture_fps": 10,
            "render": stats(render_times[60:]),
        }
        frames.clear()
    print(city, report["flights"], flush=True)

result_run = flight.run
result_run.resources = {"papel": 20, "plastico": 20, "metal": 20, "vidro": 20}
result_run.score = 250
result_run.stars = 2
app.go(ResultScene(app, result_run))
app.step(1 / 60, [])
capture("resultado")

(args.out / "qa-render.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
app.input.stop_camera()
pygame.quit()
