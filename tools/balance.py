"""Simula voos para conferir o equilíbrio: duração da fase, coletas e recursos por voo.

Um "piloto" automático pega cada resíduo que chega até o avião com probabilidade
--coleta (0,4 = a criança pega 4 de cada 10) e o voo é invencível, para medir só o
ritmo da transformação. Use depois de mexer em config.py ou content/progress.py.

Uso: python tools/balance.py [--coleta 0.4] [--voos 6]
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dobramundo import config as C  # noqa: E402
from dobramundo.content.biomes import BIOMES  # noqa: E402
from dobramundo.content.progress import PLANE_PARTS, VILLAGE_UPGRADES  # noqa: E402
from dobramundo.game.run import FlightRun  # noqa: E402

DT = 1.0 / 60.0
LIMIT_S = 1200.0


def simulate(mode: str, share: float, seed: int, biome: str = "amazonia"):
    """Devolve (segundos até 100%, coletas, recursos, segundos por estágio)."""
    rng = random.Random(seed)
    # como no jogo: abertura didática sempre no Normal (no Difícil, só no primeiro voo da fase)
    run = FlightRun(BIOMES[biome], mode, {}, rng=random.Random(seed), intro=mode == "normal")
    run.invincible = True
    stage_times = []
    t = 0.0
    while not run.complete and t < LIMIT_S:
        for entity in run.world.entities:
            # a decisão fica no próprio objeto: id() se repete quando objetos antigos são liberados
            if entity.kind != "waste" or hasattr(entity, "decided") or entity.z > C.PLAYER_Z + 60:
                continue
            entity.decided = rng.random() < share
            if entity.decided:
                run.player.x, run.player.y = entity.x, min(C.MAX_ALTITUDE, entity.y)
        stage = run.stage
        run.update(DT)
        t += DT
        if run.stage != stage:
            stage_times.append(t)
    collected = sum(1 for n, _ in run.events if n == "collect")
    return t, sum(run.resources.values()), stage_times, collected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--coleta", type=float, default=0.4, help="fração dos resíduos que a criança pega")
    parser.add_argument("--voos", type=int, default=10)
    args = parser.parse_args()
    village = sum(sum(u.cost.values()) for u in VILLAGE_UPGRADES)
    parts = sum(sum(c.values()) for p in PLANE_PARTS for c in p.level_costs)
    print(f"Custo total: vila {village}, peças {parts} (soma {village + parts})")
    for mode in ("normal", "dificil"):
        results = [simulate(mode, args.coleta, seed) for seed in range(args.voos)]
        minutes = sum(r[0] for r in results) / len(results) / 60
        resources = sum(r[1] for r in results) / len(results)
        stages = [sum(r[2][i] for r in results if len(r[2]) > i) / len(results) / 60 for i in range(2)]
        print(
            f"{mode:8s} coletando {args.coleta:.0%}: fase em {minutes:4.1f} min "
            f"(estágio 2 aos {stages[0]:.1f} min, 3 aos {stages[1]:.1f} min), "
            f"~{resources:.0f} recursos por voo -> tudo comprado em ~{(village + parts) / max(1, resources):.0f} voos"
        )


if __name__ == "__main__":
    main()
