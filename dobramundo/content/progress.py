"""Progressão: melhorias da vila-base, peças do avião e regra das estrelas.

Ciclo do GDD (seção 4): a criança decola da vila-base, coleta resíduos e
conquista até três estrelas por fase; de volta à base, converte os recursos em
melhorias da vila e em peças reaproveitadas do avião, que completam a coleção e
podem ser necessárias à terceira estrela. O conforto de controle é comum desde
o primeiro voo e não é comprado.
"""

from __future__ import annotations

from typing import Dict, Mapping, NamedTuple, Tuple

from ..config import ERA_SPAN

Cost = Dict[str, int]  # tipo de resíduo -> quantidade
COST_SCALE = 12  # escala dos custos posteriores; primeiras obras têm preço de entrada próprio.


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
        {"papel": 8, "plastico": 8},
        "VL_PontoTroca",
        (150, 470, 120),
    ),
    VillageUpgrade(
        "horta",
        "Horta urbana",
        "Alimento fresco plantado no meio da vila.",
        {"papel": 24, "vidro": 16},
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
        "Asa de papelão reforçada para a coleção de peças da expedição.",
        (scaled({"papel": 10, "plastico": 6}), scaled({"papel": 18, "plastico": 12, "metal": 6})),
    ),
    PlanePart(
        "leme",
        "Leme reaproveitado",
        "Tampa reaproveitada, recortada para completar o conjunto do avião.",
        (scaled({"plastico": 10, "metal": 6}), scaled({"plastico": 16, "metal": 12, "vidro": 6})),
    ),
    PlanePart(
        "quilha",
        "Quilha de lata",
        "Lata dobrada em uma peça de coleção para a próxima expedição.",
        (scaled({"metal": 10, "vidro": 6}), scaled({"metal": 16, "vidro": 12, "papel": 6})),
    ),
)
PART_KEYS = tuple(p.key for p in PLANE_PARTS)
PART_BY_KEY = {p.key: p for p in PLANE_PARTS}
MAX_PART_LEVEL = 2


class PlaneStats(NamedTuple):
    """Conforto de voo comum; peças não alteram controle nem colisão."""

    response: float = 1.0
    max_speed: float = 1.0
    hitbox: float = 0.88  # tolerância base, igual antes/depois de construir peças
    roll: float = 1.0
    dead_zone: float = 1.0


def plane_stats(parts: Mapping[str, int]) -> PlaneStats:
    """Retorna a linha de base confortável, independente das peças instaladas.

    As peças continuam sendo construções colecionáveis e podem ser requisito de
    expedição/estrela, mas não compram velocidade, sensibilidade ou tolerância.
    """
    del parts  # a assinatura continua estável para os saves e chamadas existentes
    return PlaneStats()


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
