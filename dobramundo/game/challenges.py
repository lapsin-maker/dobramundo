"""Desafios comunitários reproduzíveis com identidade de cada bioma."""

from __future__ import annotations

from typing import NamedTuple, Optional, Tuple

from .. import config as C


class ChallengeTheme(NamedTuple):
    """Pista regional para render e geração; decorações são tags, não assets carregados."""

    key: str
    title: str
    preferred_obstacle: str
    decorations: Tuple[str, ...]


REGIONAL_CHALLENGES = {
    "amazonia": (
        ChallengeTheme("encontro_das_aguas", "Encontro das águas", "gate", ("river", "boat")),
        ChallengeTheme("porto_de_manaus", "Porto de Manaus", "low", ("boat", "river")),
        ChallengeTheme("igarapes", "Igarapés", "gate", ("river", "trees")),
        ChallengeTheme("trilha_da_floresta", "Trilha da floresta", "tower", ("trees", "fauna")),
    ),
    "caatinga": (
        ChallengeTheme("pomares_do_sao_francisco", "Pomares do São Francisco", "low", ("fruit_trees", "river")),
        ChallengeTheme("ribeira_de_petrolina", "Ribeira de Petrolina", "gate", ("river", "tram")),
        ChallengeTheme("energia_do_sertao", "Energia do sertão", "tower", ("solar", "wind")),
        ChallengeTheme("travessia_da_caatinga", "Travessia da Caatinga", "low", ("trees", "river")),
    ),
}


def challenge_theme_for(biome_key: str, seed: Optional[int]) -> Optional[ChallengeTheme]:
    """Mapeia somente as sementes publicadas; sementes aleatórias não ganham rótulo regional."""
    if seed is None or seed not in C.COMMUNITY_CHALLENGE_SEEDS:
        return None
    themes = REGIONAL_CHALLENGES.get(biome_key)
    if themes is None:
        return None
    return themes[C.COMMUNITY_CHALLENGE_SEEDS.index(seed)]
