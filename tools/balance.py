"""Cenários sintéticos com controle dinâmico para comparar a economia do voo.

O agente deste simulador usa comandos de posição, resposta real do Player, atraso
de entrada, decisões perdidas, colisões do jogo, pausas e interrupções. Não é uma
criança, teste de usabilidade nem previsão de conforto motor. Os resultados só
descrevem o modelo e devem ser conferidos em uso mediado.

Uso: python tools/balance.py --voos 10 --erro 0.2 --pausa 10 --interromper 120 --json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dobramundo import config as C  # noqa: E402
from dobramundo.content.biomes import BIOMES  # noqa: E402
from dobramundo.content.items import WASTE_KEYS  # noqa: E402
from dobramundo.content.progress import PLANE_PARTS, VILLAGE_UPGRADES  # noqa: E402
from dobramundo.game.run import FlightRun  # noqa: E402
from dobramundo.game.world import find_reachable_route  # noqa: E402

DT = 1.0 / 60.0
LIMIT_S = 1200.0
ANTICIPATION_S = 3.0


def command_for(player, point: Tuple[float, float]) -> Tuple[float, float]:
    """Converte um ponto do mundo em comando posicional (-1..1) para o Player real."""
    x, y = point
    ax = max(-1.0, min(1.0, x / C.MAX_PLAYER_X))
    top = C.MAX_ALTITUDE - C.REST_ALTITUDE if y >= C.REST_ALTITUDE else C.REST_ALTITUDE - C.MIN_ALTITUDE
    ay = (y - C.REST_ALTITUDE) / max(1.0, top)
    return ax, max(-1.0, min(1.0, ay))


def desired_command(
    run: FlightRun,
    rng: random.Random,
    collect_share: float,
    error_rate: float,
    reaction_s: float,
    latency_s: float,
    counts: Dict[str, int],
) -> Tuple[float, float]:
    """Controlador simples; decide por alvo e deixa a física/sensores do jogo resolver o movimento."""
    threats = [
        entity
        for entity in run.world.entities
        if entity.spec is not None
        and not entity.hit
        and not entity.passed
        and not entity.dodged
        and entity.z > C.PLAYER_Z
    ]
    if threats:
        obstacle = min(threats, key=lambda entity: entity.z)
        eta = (obstacle.z - C.PLAYER_Z) / max(1.0, run.speed)
        if eta <= reaction_s + latency_s + ANTICIPATION_S:
            if "balance_decided" not in vars(obstacle):
                obstacle.balance_decided = True
                if rng.random() < error_rate:
                    obstacle.balance_missed = True
                    counts["decisoes_perdidas"] += 1
                else:
                    route = find_reachable_route([obstacle], run.mode)
                    if route:
                        obstacle.balance_point = route[0]
                    else:
                        obstacle.balance_missed = True
                        counts["sem_rota_simplificada"] += 1
            point = vars(obstacle).get("balance_point")
            if point is not None:
                return command_for(run.player, point)

    for entity in run.world.entities:
        point = vars(entity).get("balance_target")
        if entity.kind == "waste" and point is not None and not entity.collected and entity.z > C.PLAYER_Z:
            return command_for(run.player, point)

    horizon = run.speed * (reaction_s + latency_s + ANTICIPATION_S + 0.5)
    wastes = sorted(
        (
            entity
            for entity in run.world.entities
            if entity.kind == "waste"
            and not entity.collected
            and entity.z > C.PLAYER_Z
            and entity.z <= C.PLAYER_Z + horizon
        ),
        key=lambda entity: entity.z,
    )
    for waste in wastes:
        if "balance_decided" in vars(waste):
            continue
        waste.balance_decided = True
        if rng.random() > collect_share:
            counts["nao_tentadas"] += 1
            continue
        if rng.random() < error_rate:
            counts["decisoes_perdidas"] += 1
            continue
        waste.balance_target = (waste.x, min(C.MAX_ALTITUDE, max(C.MIN_ALTITUDE, waste.y)))
        counts["alvos_de_coleta"] += 1
        return command_for(run.player, waste.balance_target)
    return command_for(run.player, (0.0, C.REST_ALTITUDE))


def simulate(
    mode: str,
    share: float,
    seed: int,
    biome: str = "amazonia",
    error_rate: float = 0.0,
    pause_per_minute: float = 0.0,
    interrupt_after: float = 0.0,
    session_limit_s: int = 0,
    reaction_s: float = 0.35,
    latency_s: float = 0.25,
    exploration: bool = False,
    assistance: bool = False,
) -> dict:
    """Roda um cenário sintético com a dinâmica de posição e colisões reais do jogo."""
    rng = random.Random(seed ^ 0xB41A6CE)
    run = FlightRun(
        BIOMES[biome],
        mode,
        {},
        seed=seed,
        intro=mode == "normal",
        focus=False,
        session_limit_s=session_limit_s,
        exploration=exploration,
        predictable_assistance=assistance,
    )
    stage_times = []
    counts = {"decisoes_perdidas": 0, "sem_rota_simplificada": 0, "nao_tentadas": 0, "alvos_de_coleta": 0}
    wall_s = 0.0
    pause_left = 0.0
    next_pause = 60.0 if pause_per_minute else float("inf")
    requested = (0.0, 0.0)
    applied = requested
    pending: Optional[Tuple[Tuple[float, float], float]] = None
    max_displacement = 0.0
    while not run.finished and wall_s < LIMIT_S:
        if interrupt_after > 0 and run.flight_time >= interrupt_after:
            run.interrupted = not run.complete
            run.finished = True
            break
        if pause_left > 0:
            pause_left = max(0.0, pause_left - DT)
            wall_s += DT
            continue
        if run.flight_time >= next_pause:
            run.pause_count += 1
            pause_left = pause_per_minute
            run.pause_duration_s += pause_per_minute
            next_pause += 60.0
            continue

        target = desired_command(run, rng, share, error_rate, reaction_s, latency_s, counts)
        if target != requested:
            requested = target
            pending = (target, run.flight_time + latency_s)
        if pending is not None and run.flight_time >= pending[1]:
            applied, pending = pending[0], None

        stage = run.stage
        run.update(DT, target=applied)
        max_displacement = max(
            max_displacement,
            (run.player.x * run.player.x + (run.player.y - C.START_ALTITUDE) ** 2) ** 0.5,
        )
        wall_s += DT
        if run.stage != stage:
            stage_times.append(wall_s)
    if run.complete:
        run.finished = True
    if not run.complete and not run.game_over and not run.interrupted and wall_s >= LIMIT_S:
        run.interrupted = True
        run.finished = True
    return {
        "biome": biome,
        "mode": mode,
        "seed": run.seed,
        "seconds_active": round(run.flight_time, 3),
        "seconds_wall": round(wall_s, 3),
        "max_player_displacement": round(max_displacement, 3),
        "stage_times_s": [round(value, 3) for value in stage_times],
        "restoration": round(run.restoration, 2),
        "resources": dict(run.resources),
        "resource_total": sum(run.resources.values()),
        "collected": run.waste_collected,
        "hits": run.hits,
        "max_lives": run.max_lives,
        "lives_left": run.lives,
        "completed": run.complete,
        "game_over": run.game_over,
        "interrupted": run.interrupted,
        "session_timeout": run.timeout,
        "pause_count": run.pause_count,
        "pause_seconds": round(run.pause_duration_s, 3),
        "controller_counts": counts,
        "exploration": exploration,
        "assistance": assistance,
    }


def collection_costs() -> Dict[str, int]:
    costs = {key: 0 for key in WASTE_KEYS}
    for upgrade in VILLAGE_UPGRADES:
        for key, amount in upgrade.cost.items():
            costs[key] += amount
    for part in PLANE_PARTS:
        for level in part.level_costs:
            for key, amount in level.items():
                costs[key] += amount
    return costs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--coleta", type=float, default=0.4, help="chance de tentar alinhar com cada resíduo")
    parser.add_argument("--erro", type=float, default=0.1, help="decisões de movimento perdidas (0..1)")
    parser.add_argument("--pausa", type=float, default=0.0, help="segundos de pausa após cada minuto ativo")
    parser.add_argument(
        "--interromper", type=float, default=0.0, help="interrompe após estes segundos ativos; 0 desativa"
    )
    parser.add_argument(
        "--limite", type=int, choices=C.SESSION_LIMITS_S, default=0, help="limite de sessão em segundos"
    )
    parser.add_argument("--reacao", type=float, default=0.35, help="atraso sintético antes de iniciar a manobra")
    parser.add_argument("--latencia", type=float, default=0.25, help="atraso sintético até aplicar o comando")
    parser.add_argument("--exploracao", action="store_true", help="modo que não elimina após as vidas")
    parser.add_argument("--assistencia", action="store_true", help="cinco vidas e 2 s de proteção após batida")
    parser.add_argument("--voos", type=int, default=10)
    parser.add_argument("--seed-inicial", type=int, default=1)
    parser.add_argument("--bioma", choices=tuple(BIOMES), default="amazonia")
    parser.add_argument("--json", action="store_true", help="imprime o relatório em JSON")
    parser.add_argument("--out", type=Path, help="grava o relatório JSON neste caminho")
    args = parser.parse_args()
    if not 0 <= args.coleta <= 1 or not 0 <= args.erro <= 1:
        parser.error("--coleta e --erro devem estar entre 0 e 1")
    if args.voos <= 0 or min(args.pausa, args.interromper, args.reacao, args.latencia) < 0:
        parser.error("--voos deve ser positivo; tempos não podem ser negativos")

    records = [
        simulate(
            mode,
            args.coleta,
            args.seed_inicial + i,
            biome=args.bioma,
            error_rate=args.erro,
            pause_per_minute=args.pausa,
            interrupt_after=args.interromper,
            session_limit_s=args.limite,
            reaction_s=args.reacao,
            latency_s=args.latencia,
            exploration=args.exploracao,
            assistance=args.assistencia,
        )
        for mode in ("normal", "dificil")
        for i in range(args.voos)
    ]
    costs = collection_costs()
    means = {
        mode: {
            key: sum(record["resources"][key] for record in records if record["mode"] == mode) / args.voos
            for key in costs
        }
        for mode in ("normal", "dificil")
    }
    report = {
        "model": "dynamic-position-agent-v1",
        "limitations": [
            "synthetic controller, not a child or usability study",
            "approach decisions use simplified one-obstacle route targets",
            "results do not establish comfort, fairness, or physical reachability",
        ],
        "parameters": {
            "biome": args.bioma,
            "collect_attempt_probability": args.coleta,
            "deliberate_decision_error_probability": args.erro,
            "pause_seconds_per_active_minute": args.pausa,
            "interrupt_after_active_seconds": args.interromper,
            "session_limit_seconds": args.limite,
            "reaction_seconds": args.reacao,
            "input_latency_seconds": args.latencia,
            "exploration": args.exploracao,
            "assistance": args.assistencia,
            "flight_count_per_mode": args.voos,
            "seed_start": args.seed_inicial,
        },
        "collection_costs": costs,
        "mean_resources_by_mode": means,
        "runs": records,
    }
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("Cenário sintético com física e colisões reais do jogo; não é teste humano nem previsão de conforto.")
        print("Custos de coleção por recurso: " + ", ".join(f"{key} {amount}" for key, amount in costs.items()))
        for mode in ("normal", "dificil"):
            subset = [record for record in records if record["mode"] == mode]
            average_wall = sum(record["seconds_wall"] for record in subset) / len(subset) / 60
            completions = sum(record["completed"] for record in subset)
            game_overs = sum(record["game_over"] for record in subset)
            interruptions = sum(record["interrupted"] for record in subset)
            hits = sum(record["hits"] for record in subset) / len(subset)
            resource_text = ", ".join(f"{key} {means[mode][key]:.1f}" for key in costs)
            print(
                f"{mode}: duração parede média {average_wall:.1f} min; completou {completions}/{len(subset)}, "
                f"game over {game_overs}, interrupções {interruptions}, batidas médias {hits:.1f}"
            )
            print(f"  média de recursos por voo: {resource_text}")
    if args.out:
        print(f"Relatório JSON: {args.out}")


if __name__ == "__main__":
    main()
