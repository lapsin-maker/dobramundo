"""Progressão: melhorias da vila-base, peças do avião e regra das estrelas.

Ciclo do GDD (seção 4): a criança decola da vila-base, coleta resíduos e
conquista até três estrelas por fase; de volta à base, converte os recursos em
melhorias da vila e em peças reaproveitadas do avião, que ampliam estabilidade e
controle e são necessárias à terceira estrela.
"""

from __future__ import annotations

from typing import Dict, Mapping, NamedTuple, Tuple

from ..config import ERA_SPAN

Cost = Dict[str, int]  # tipo de resíduo -> quantidade
COST_SCALE = 12  # custos-base x 12: tudo comprado em ~11 voos no Normal e ~5 no Difícil (tools/balance.py)


def scaled(cost: Cost) -> Cost:
    return {key: amount * COST_SCALE for key, amount in cost.items()}


# Recursos por resíduo coletado. No Normal cada coleta é 4x mais rara e rende 4x mais.
RESOURCES_PER_WASTE = {"normal": 4, "dificil": 1}


class VillageUpgrade(NamedTuple):
    key: str
    name: str
    description: str
    cost: Cost
    sprite: str  # sprite de cenário (VL_ em assets/biome_sprites)
    slot: Tuple[int, int, int]  # posição na cena da vila: x (px), base y (px), altura (px)


VILLAGE_UPGRADES: Tuple[VillageUpgrade, ...] = (
    VillageUpgrade(
        "ponto_troca",
        "Ponto de troca",
        "Separa os resíduos e os transforma em recursos.",
        scaled({"papel": 6, "plastico": 6}),
        "VL_PontoTroca",
        (150, 470, 120),
    ),
    VillageUpgrade(
        "horta",
        "Horta urbana",
        "Alimento fresco plantado no meio da vila.",
        scaled({"papel": 8, "vidro": 6}),
        "VL_Horta",
        (330, 520, 70),
    ),
    VillageUpgrade(
        "paineis",
        "Painéis solares",
        "Microgeração de energia limpa nos telhados.",
        scaled({"metal": 12, "vidro": 10}),
        "VL_PaineisSolares",
        (560, 455, 110),
    ),
    VillageUpgrade(
        "compostor",
        "Compostor",
        "Restos orgânicos viram adubo para a horta.",
        scaled({"plastico": 8, "metal": 6}),
        "EF_Compostor",
        (440, 500, 80),
    ),
    VillageUpgrade(
        "cisterna",
        "Cisterna",
        "Guarda a água da chuva para regar e beber.",
        scaled({"plastico": 10, "metal": 8}),
        "CA_CisternaPlacas",
        (760, 480, 105),
    ),
    VillageUpgrade(
        "bicicletario",
        "Bicicletário",
        "Bicicletas no lugar dos carros a diesel.",
        scaled({"metal": 10, "plastico": 6}),
        "EF_Bicicletario",
        (660, 535, 60),
    ),
    VillageUpgrade(
        "telhado_verde",
        "Telhado verde",
        "Plantas no telhado refrescam as casas.",
        scaled({"papel": 12, "vidro": 8}),
        "VL_TelhadoVerde",
        (250, 430, 170),
    ),
    VillageUpgrade(
        "turbina",
        "Turbina eólica",
        "O vento também gera energia para a vila.",
        scaled({"metal": 16, "vidro": 10, "papel": 6}),
        "EF_TorreEolica",
        (930, 470, 260),
    ),
)
VILLAGE_KEYS = tuple(u.key for u in VILLAGE_UPGRADES)
VILLAGE_BY_KEY = {u.key: u for u in VILLAGE_UPGRADES}


class PlanePart(NamedTuple):
    key: str
    name: str
    description: str
    level_costs: Tuple[Cost, ...]  # custo de cada nível (1, 2)


PLANE_PARTS: Tuple[PlanePart, ...] = (
    PlanePart(
        "estabilizador",
        "Estabilizador",
        "Asa de papelão: o avião balança menos e a colisão fica mais justa.",
        (scaled({"papel": 10, "plastico": 6}), scaled({"papel": 18, "plastico": 12, "metal": 6})),
    ),
    PlanePart(
        "leme",
        "Leme reaproveitado",
        "Tampa de garrafa no leme: o avião responde mais rápido.",
        (scaled({"plastico": 10, "metal": 6}), scaled({"plastico": 16, "metal": 12, "vidro": 6})),
    ),
    PlanePart(
        "quilha",
        "Quilha de lata",
        "Lata dobrada na quilha: mais agilidade e controle mais fino.",
        (scaled({"metal": 10, "vidro": 6}), scaled({"metal": 16, "vidro": 12, "papel": 6})),
    ),
)
PART_KEYS = tuple(p.key for p in PLANE_PARTS)
PART_BY_KEY = {p.key: p for p in PLANE_PARTS}
MAX_PART_LEVEL = 2


class PlaneStats(NamedTuple):
    """Efeito das peças sobre o voo (multiplicadores; 1.0 = avião sem peças)."""

    response: float = 1.0  # rapidez com que o avião atinge a velocidade pedida
    max_speed: float = 1.0  # velocidade lateral e vertical máximas
    hitbox: float = 1.0  # tamanho da caixa de colisão do avião
    roll: float = 1.0  # inclinação visual nas curvas
    dead_zone: float = 1.0  # zona morta do controle corporal (menor = mais fino)


def plane_stats(parts: Mapping[str, int]) -> PlaneStats:
    stab = parts.get("estabilizador", 0)
    rudder = parts.get("leme", 0)
    keel = parts.get("quilha", 0)
    return PlaneStats(
        response=1.0 + 0.18 * rudder,
        max_speed=1.0 + 0.08 * keel,
        hitbox=1.0 - 0.07 * stab,
        roll=1.0 - 0.2 * stab,
        dead_zone=1.0 - 0.25 * keel,
    )


# -------------------------------------------------------------------- estrelas
STAR_THRESHOLDS = (ERA_SPAN, 2 * ERA_SPAN, 100.0)  # despertar, solarpunk, cidade completa


def parts_ok(required: Mapping[str, int], installed: Mapping[str, int]) -> bool:
    return all(installed.get(key, 0) >= level for key, level in required.items())


def stars_for(restoration: float, required: Mapping[str, int], installed: Mapping[str, int]) -> int:
    """Estrelas de um voo: 1 ao despertar (33,3%), 2 no solarpunk (66,7%), 3 com a
    cidade completa (100%) e as peças exigidas pela fase instaladas no avião."""
    stars = sum(1 for limit in STAR_THRESHOLDS[:2] if restoration >= limit - 1e-6)
    if restoration >= STAR_THRESHOLDS[2] - 1e-6:
        stars = 3 if parts_ok(required, installed) else 2
    return stars


def can_afford(wallet: Mapping[str, int], cost: Mapping[str, int]) -> bool:
    return all(wallet.get(key, 0) >= amount for key, amount in cost.items())


def missing(wallet: Mapping[str, int], cost: Mapping[str, int]) -> Cost:
    return {key: amount - wallet.get(key, 0) for key, amount in cost.items() if wallet.get(key, 0) < amount}
