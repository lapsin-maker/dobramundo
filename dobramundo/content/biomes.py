"""Fases do jogo: cada uma é uma cidade brasileira no seu bioma.

Toda fase tem três estágios de paisagem (GDD, seção 4), que se sucedem aos
33,3% e 66,7% de transformação:
    0  cidade industrial (dieselpunk)      - peças do kit industrial + toques regionais
    1  despertar ecológico                 - flora do bioma e construções restauradas
    2  cidade solarpunk                    - arquitetura art nouveau (EF_EdificioArtNouveau, Teatro
                                            Amazonas), energia limpa, flora

As listas de cenário são (nome do sprite, altura no mundo) e seguem ordem fixa,
sem sorteio. Sprites com prefixo AM_/CA_ ficam em assets/biome_sprites, EF_ em
assets/era_final_sprites e os demais nos kits industriais.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Tuple

from ..util import Color, rgb
from .items import ObstacleTable, gate, low, obstacle_table, tower

Spec = Tuple[str, float]
Specs = List[Spec]
SkylineLayout = List[Tuple[str, int]]


class StageLook(NamedTuple):
    name: str
    sky_top: Color
    sky_horizon: Color
    ground: Color  # chão liso de reserva (sem textura)
    road_even: Color
    road_odd: Color
    lane_line: Color
    accent: Color  # cor de destaque do HUD e dos menus neste estágio


class SkyDecor(NamedTuple):
    sprite: str
    top: int  # px
    height: int  # px
    speed: float  # px/s
    parallax: float


class Biome(NamedTuple):
    key: str
    name: str  # nome do bioma
    city: str
    state: str
    stages: Tuple[StageLook, StageLook, StageLook]
    polluted_haze: Color
    # estágio 0: cidade industrial
    industrial_mid: Specs
    industrial_margin: Specs
    industrial_obstacles: ObstacleTable
    # estágio 1: despertar ecológico
    green_mid: Specs
    green_margin: Specs
    restored: Specs
    green_skyline: SkylineLayout
    green_ground: str
    # estágio 2: cidade solarpunk
    solar_mid: Specs
    solar_margin: Specs
    landmark: Spec
    solar_skyline: SkylineLayout
    solar_obstacles: ObstacleTable
    solar_ground: str
    solar_road: Optional[str]  # textura da pista no estágio 3 (None = cor lisa)
    horizon_vehicle: Tuple[str, int, float, float]  # sprite, altura px, velocidade, paralaxe
    sky_decor: Tuple[SkyDecor, ...]
    river: bool  # a pista é um rio (Amazônia: Rio Negro)
    map_point: Tuple[float, float]  # longitude, latitude da cidade (mapa)
    required_parts: Dict[str, int]  # peças do avião exigidas para a 3ª estrela
    music: str  # prefixo das trilhas em assets/audio
    industrial_skyline: SkylineLayout = ()  # silhuetas regionais no horizonte do estágio industrial


# ------------------------------------------------------------- kit industrial
# Fileira junto à pista (estágio 0): peças pequenas do kit, comuns às duas cidades.
INDUSTRIAL_MARGIN: Specs = [
    ("fuel_barrel", 62.0),
    ("valve_manifold", 88.0),
    ("rusted_crate", 52.0),
    ("cable_reel", 78.0),
    ("steam_pipe_straight", 58.0),
    ("control_panel", 92.0),
    ("diesel_generator", 82.0),
    ("amber_light", 48.0),
    ("steam_pipe_tee", 74.0),
    ("boiler_compressor", 96.0),
    ("steam_pipe_corner", 70.0),
    ("metal_walkway", 56.0),
]


def industrial_mid(regional: Specs) -> Specs:
    """Fileira de fundo do estágio 0: estruturas do kit com peças regionais intercaladas."""
    base: Specs = [
        ("industrial_tower_a", 400.0),
        ("fabrica", 186.0),
        ("pressure_tank", 200.0),
        ("factory_wall_a", 190.0),
        ("chamine", 310.0),
        ("fixed_crane", 360.0),
        ("cargo_elevator", 200.0),
        ("caldeira", 190.0),
        ("industrial_chimney", 320.0),
        ("factory_wall_b", 190.0),
        ("tubos_valvula", 190.0),
        ("industrial_fan", 120.0),
        ("background_silo", 420.0),
        ("tambores", 119.0),
        ("metal_support", 180.0),
        ("lixo", 125.0),
        ("industrial_stairs", 200.0),
        ("sucata", 145.0),
        ("hangar_door_a", 240.0),
        ("SCN_CaixaIndustrial_Cenario", 155.0),
        ("power_pylon", 430.0),
        ("distant_factory", 260.0),
    ]
    mixed: Specs = []
    step = max(1, len(base) // max(1, len(regional)))
    regional_iter = iter(regional)
    for i, spec in enumerate(base):
        mixed.append(spec)
        if i % step == step - 1:
            extra = next(regional_iter, None)
            if extra is not None:
                mixed.append(extra)
    # uma peça regional a cada duas do kit: a cidade aparece desde o começo da fase
    out: Specs = []
    for i, item in enumerate(base):
        out.append(item)
        if i % 2 == 1 and regional:
            out.append(regional[(i // 2) % len(regional)])
    return out


INDUSTRIAL_OBSTACLES_COMMON = (
    low("tambores", 110.0, 150.0, 100.0),
    low("cacamba", 105.0, 165.0, 96.0),
    gate("tubos_valvula", 175.0, 200.0, 105.0),
    tower("chamine", 330.0, 80.0),
    tower("caldeira", 230.0, 140.0),
)

SOLAR_DECOR = (
    SkyDecor("EF_Dirigivel", 72, 44, 14.0, 0.10),
    SkyDecor("EF_BalaoSolar", 98, 46, -6.0, 0.14),
    SkyDecor("EF_BalaoSolar", 58, 26, 4.0, 0.08),
)

# ------------------------------------------------------------------ Manaus
AMAZONIA = Biome(
    key="amazonia",
    name="Amazônia",
    city="Manaus",
    state="AM",
    stages=(
        StageLook(
            "Manaus industrial",
            rgb("2a3340"),  # céu de chumbo, úmido
            rgb("7d7366"),  # névoa cinza-amarelada baixa sobre o rio
            rgb("2a2622"),
            rgb("23272a"),  # rio escuro com óleo
            rgb("1f2326"),
            rgb("5c6a5a"),
            rgb("ff7043"),
        ),
        StageLook(
            "Despertar das águas",
            rgb("2f7fc1"),
            rgb("cfe6a8"),
            rgb("2f6b3a"),
            rgb("3a2414"),
            rgb("33200f"),
            rgb("c9a46c"),
            rgb("69f0ae"),
        ),
        StageLook(
            "Manaus solarpunk",
            rgb("29b6f6"),
            rgb("fff59d"),
            rgb("3f8f4a"),
            rgb("1f8f8c"),
            rgb("1b8381"),
            rgb("c8f7ee"),
            rgb("ffd54f"),
        ),
    ),
    polluted_haze=(96, 92, 84),  # fumaça úmida, cinza
    industrial_skyline=[("AM_GuindastePorto", 118), ("AM_Termeletrica", 86), ("AM_Containers", 44)],
    industrial_mid=industrial_mid([("AM_Termeletrica", 270.0), ("AM_GuindastePorto", 380.0), ("AM_Containers", 150.0)]),
    industrial_margin=INDUSTRIAL_MARGIN,
    industrial_obstacles=obstacle_table(
        *INDUSTRIAL_OBSTACLES_COMMON,
        low("AM_Balsa", 100.0, 190.0, 88.0),
        gate("AM_PassarelaPalafita", 170.0, 230.0, 110.0),
        tower("AM_ChamineTermeletrica", 330.0, 62.0),
    ),
    green_mid=[
        ("AM_Samauma", 430.0),
        ("AM_Acaizeiro", 310.0),
        ("AM_Buriti", 330.0),
        ("AM_Seringueira", 300.0),
        ("AM_Samauma", 400.0),
        ("AM_Acaizeiro", 290.0),
        ("AM_Buriti", 320.0),
        ("AM_Seringueira", 280.0),
    ],
    green_margin=[("AM_Heliconia", 90.0), ("AM_Acaizeiro", 170.0), ("AM_VitoriaRegia", 34.0), ("AM_Buriti", 180.0)],
    restored=[("AM_Palafita", 170.0), ("AM_CasaFlutuante", 140.0)],
    green_skyline=[
        ("AM_Samauma", 76),
        ("AM_Acaizeiro", 58),
        ("AM_Buriti", 62),
        ("AM_Seringueira", 56),
        ("AM_Samauma", 70),
        ("AM_Acaizeiro", 52),
    ],
    green_ground="grass",
    solar_mid=[
        ("EF_ResidencialTerracos", 385.0),
        ("AM_Samauma", 420.0),
        ("AM_PalafitaSolar", 200.0),
        ("AM_Acaizeiro", 300.0),
        ("EF_ApartamentosExo", 400.0),
        ("AM_Buriti", 320.0),
        ("EF_CentroComunitario", 245.0),
        ("AM_Seringueira", 300.0),
        ("EF_HubMobilidade", 210.0),
        ("AM_PalafitaSolar", 200.0),
        ("EF_EscolaTaipa", 175.0),
        ("EF_EdificioArtNouveau", 430.0),
        ("AM_Samauma", 420.0),
    ],
    solar_margin=[
        ("EF_PosteSolar", 125.0),
        ("AM_Heliconia", 90.0),
        ("EF_BancoJardim", 45.0),
        ("AM_Acaizeiro", 190.0),
        ("EF_TotemSinal", 86.0),
        ("AM_BarcoSolar", 100.0),
        ("EF_PosteSolar", 125.0),
        ("AM_VitoriaRegia", 34.0),
        ("EF_Floreira", 40.0),
        ("AM_Buriti", 200.0),
        ("EF_Bicicletario", 73.0),
        ("AM_Heliconia", 80.0),
        ("EF_ArvoreArtNouveau", 200.0),
    ],
    landmark=("AM_TeatroAmazonas", 440.0),
    solar_skyline=[
        ("EF_ResidencialTerracos", 104),
        ("AM_Samauma", 72),
        ("AM_TeatroAmazonas", 122),
        ("EF_ApartamentosExo", 112),
        ("AM_PonteEstaiada", 84),
        ("EF_MercadoBambu", 50),
        ("AM_Buriti", 62),
        ("EF_CentroComunitario", 64),
        ("EF_TorreEolica", 118),
        ("AM_Acaizeiro", 60),
    ],
    solar_obstacles=obstacle_table(
        low("EF_LotusSolar", 100.0, 146.0, 82.0),
        low("EF_Compostor", 100.0, 170.0, 88.0),
        low("AM_VitoriaRegiaSolar", 80.0, 180.0, 71.0),
        gate("EF_PassarelaFauna", 160.0, 277.0, 110.0),
        gate("EF_ArcoTrepadeira", 140.0, 180.0, 110.0),
        gate("AM_PassarelaCopa", 175.0, 260.0, 100.0),
        tower("EF_TorreEolica", 330.0, 16.0),
        tower("AM_TorreBioenergia", 320.0, 58.0),
        tower("EF_FotoBiorreator", 330.0, 60.0),
    ),
    solar_ground="meadow",
    solar_road=None,
    horizon_vehicle=("AM_BarcoRegional", 22, 40.0, 0.25),
    sky_decor=SOLAR_DECOR,
    river=True,
    map_point=(-60.02, -3.10),
    required_parts={"estabilizador": 1},
    music="amazonia",
)

# ---------------------------------------------------------------- Petrolina
CAATINGA = Biome(
    key="caatinga",
    name="Caatinga",
    city="Petrolina",
    state="PE",
    stages=(
        StageLook(
            "Petrolina industrial",
            rgb("8a6a3a"),  # céu de poeira, sol forte
            rgb("d9b57a"),  # horizonte ocre lavado
            rgb("6b5436"),
            rgb("5a4a3a"),  # asfalto empoeirado
            rgb("52432f"),
            rgb("b48a4a"),
            rgb("ff8a3d"),
        ),
        StageLook(
            "Despertar do sertão",
            rgb("3a8fd6"),
            rgb("f2dc9b"),
            rgb("9b7a4a"),
            rgb("7a5a3a"),
            rgb("6e5034"),
            rgb("e2c27a"),
            rgb("ffca28"),
        ),
        StageLook(
            "Petrolina solarpunk",
            rgb("1fa2f0"),
            rgb("fff2b0"),
            rgb("8fae5a"),
            rgb("a1887f"),
            rgb("8d6e63"),
            rgb("ffe082"),
            rgb("ffd54f"),
        ),
    ),
    polluted_haze=(176, 140, 86),  # poeira ocre, seca
    industrial_skyline=[("CA_TorreTransmissao", 130), ("CA_CaixaDagua", 96), ("CA_Galpao", 58)],
    industrial_mid=industrial_mid([("CA_Galpao", 170.0), ("CA_TorreTransmissao", 420.0), ("CA_CaixaDagua", 300.0)]),
    industrial_margin=INDUSTRIAL_MARGIN,
    industrial_obstacles=obstacle_table(
        *INDUSTRIAL_OBSTACLES_COMMON,
        low("CA_CaminhaoPipa", 110.0, 190.0, 97.0),
        low("CA_Carroca", 95.0, 170.0, 84.0),
        gate("CA_PorticoIrrigacao", 175.0, 260.0, 112.0),
        tower("CA_TorreTransmissao", 340.0, 64.0),
    ),
    green_mid=[
        ("CA_Juazeiro", 260.0),
        ("CA_Mandacaru", 250.0),
        ("CA_Carnauba", 340.0),
        ("CA_Umbuzeiro", 230.0),
        ("CA_Mandacaru", 280.0),
        ("CA_Juazeiro", 250.0),
        ("CA_Carnauba", 320.0),
        ("CA_Umbuzeiro", 220.0),
    ],
    green_margin=[("CA_XiqueXique", 70.0), ("CA_Mandacaru", 140.0), ("CA_Macambira", 50.0), ("CA_XiqueXique", 60.0)],
    restored=[("CA_CasaTaipa", 130.0), ("CA_CisternaPlacas", 95.0)],
    green_skyline=[
        ("CA_Juazeiro", 58),
        ("CA_Mandacaru", 64),
        ("CA_Carnauba", 76),
        ("CA_Umbuzeiro", 52),
        ("CA_Mandacaru", 70),
        ("CA_Juazeiro", 54),
    ],
    green_ground="dry_soil",
    solar_mid=[
        ("EF_ResidencialTerracos", 385.0),
        ("CA_Mangueira", 250.0),
        ("CA_UsinaSolar", 100.0),
        ("CA_Juazeiro", 260.0),
        ("CA_Aerogerador", 360.0),
        ("CA_Videira", 110.0),
        ("EF_CentroComunitario", 245.0),
        ("CA_Carnauba", 330.0),
        ("EF_MercadoBambu", 190.0),
        ("CA_Mandacaru", 270.0),
        ("EF_EscolaTaipa", 175.0),
        ("EF_EdificioArtNouveau", 430.0),
        ("CA_Mangueira", 250.0),
    ],
    solar_margin=[
        ("EF_PosteSolar", 125.0),
        ("CA_XiqueXique", 70.0),
        ("EF_BancoJardim", 45.0),
        ("CA_Mandacaru", 150.0),
        ("EF_TotemSinal", 86.0),
        ("EF_Bicicletario", 73.0),
        ("EF_PosteSolar", 125.0),
        ("CA_CisternaPlacas", 80.0),
        ("EF_Floreira", 40.0),
        ("CA_Videira", 90.0),
        ("CA_Umbuzeiro", 170.0),
        ("EF_BancoJardim", 45.0),
        ("EF_ArvoreArtNouveau", 200.0),
    ],
    landmark=("CA_Carranca", 320.0),
    solar_skyline=[
        ("EF_ResidencialTerracos", 104),
        ("CA_Aerogerador", 130),
        ("CA_PonteSaoFrancisco", 70),
        ("EF_ApartamentosExo", 112),
        ("CA_Aerogerador", 120),
        ("CA_Mangueira", 62),
        ("EF_CentroComunitario", 64),
        ("CA_Carnauba", 80),
        ("EF_EscolaTaipa", 46),
        ("CA_Aerogerador", 125),
    ],
    solar_obstacles=obstacle_table(
        low("CA_CisternaPlacas", 95.0, 160.0, 84.0),
        low("EF_CanteiroBiorretencao", 85.0, 180.0, 76.0),
        low("EF_Compostor", 100.0, 170.0, 88.0),
        gate("CA_PorticoSolar", 175.0, 260.0, 104.0),
        gate("EF_PergolaPraca", 145.0, 250.0, 110.0),
        gate("EF_ViadutoPomar", 187.0, 250.0, 110.0),
        tower("CA_Aerogerador", 330.0, 16.0),
        tower("CA_MandacaruGigante", 300.0, 34.0),
        tower("EF_TorreWarka", 300.0, 80.0),
    ),
    solar_ground="agreste",
    solar_road="paver_road",
    horizon_vehicle=("EF_BondeVLT", 17, 46.0, 0.25),
    sky_decor=SOLAR_DECOR,
    river=False,
    map_point=(-40.50, -9.39),
    required_parts={"leme": 1, "quilha": 1},
    music="caatinga",
)

BIOMES: Dict[str, Biome] = {AMAZONIA.key: AMAZONIA, CAATINGA.key: CAATINGA}
BIOME_ORDER = ("amazonia", "caatinga")


class LockedBiome(NamedTuple):
    """Bioma anunciado para versões futuras (aparece bloqueado no mapa)."""

    key: str
    name: str
    color: Color


LOCKED_BIOMES = (
    LockedBiome("cerrado", "Cerrado", rgb("c9b458")),
    LockedBiome("mata_atlantica", "Mata Atlântica", rgb("3f9a5a")),
    LockedBiome("pantanal", "Pantanal", rgb("5fb3a6")),
    LockedBiome("pampa", "Pampa", rgb("a7c96b")),
)
BIOME_MAP_COLORS: Dict[str, Color] = {
    "amazonia": rgb("2e8b57"),
    "caatinga": rgb("d9a441"),
    **{b.key: b.color for b in LOCKED_BIOMES},
}


def all_obstacle_specs() -> Dict[str, ObstacleTable]:
    """Tabelas de obstáculos de todas as fases (para validar sprites e colisões)."""
    tables: Dict[str, ObstacleTable] = {}
    for biome in BIOMES.values():
        tables[f"{biome.key}:industrial"] = biome.industrial_obstacles
        tables[f"{biome.key}:solar"] = biome.solar_obstacles
    return tables


def biome_sprite_names(biome: Biome) -> List[str]:
    """Todos os sprites de cenário que a fase usa."""
    names = set()
    for specs in (
        biome.industrial_mid,
        biome.industrial_margin,
        biome.green_mid,
        biome.green_margin,
        biome.restored,
        biome.solar_mid,
        biome.solar_margin,
        [biome.landmark],
    ):
        names.update(name for name, _ in specs)
    for layout in (biome.green_skyline, biome.solar_skyline):
        names.update(name for name, _ in layout)
    for table in (biome.industrial_obstacles, biome.solar_obstacles):
        for specs in table.values():
            names.update(spec.sprite for spec in specs)
    names.add(biome.horizon_vehicle[0])
    names.update(decor.sprite for decor in biome.sky_decor)
    return sorted(names)
