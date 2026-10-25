"""Opções do piloto (GDD, seção 6): tom de pele, cabelo, óculos e acessórios, sem
marcação de gênero; cadeira de rodas e aparelho auditivo são itens comuns.

As camadas do piloto ficam em assets/pilot_layers e são geradas por
tools/build_assets.py; a cor da pele, do cabelo e da roupa é aplicada no jogo.
"""

from __future__ import annotations

from typing import List, NamedTuple, Optional, Tuple

from ..util import Color, rgb


class Option(NamedTuple):
    key: str
    label: str
    color: Optional[Color] = None


SKIN_TONES: List[Option] = [
    Option("pele1", "Tom 1", rgb("f6d3b3")),
    Option("pele2", "Tom 2", rgb("e8b48a")),
    Option("pele3", "Tom 3", rgb("c98e62")),
    Option("pele4", "Tom 4", rgb("a0673f")),
    Option("pele5", "Tom 5", rgb("7a4a2a")),
    Option("pele6", "Tom 6", rgb("4f2f1b")),
    # tons de fantasia: a criança pode ser da cor que quiser
    Option("roxo", "Roxo", rgb("a97bdc")),
    Option("azul", "Azul", rgb("6fb3e8")),
    Option("verde", "Verde", rgb("7ccf86")),
    Option("rosa", "Rosa", rgb("f4a3bf")),
]
HAIR_STYLES: List[Option] = [
    Option("curto", "Curto"),
    Option("cacheado", "Cacheado"),
    Option("crespo", "Black power"),
    Option("longo", "Longo"),
    Option("trancas", "Tranças"),
    Option("coque", "Coque"),
    Option("franja", "Franja"),
    Option("chiquinhas", "Maria-chiquinha"),
    Option("puffs", "Afro puffs"),
    Option("moicano", "Moicano"),
    Option("hijab", "Lenço (hijab)"),
    Option("raspado", "Raspado"),
]
HAIR_COLORS: List[Option] = [
    Option("preto", "Preto", rgb("1e1a18")),
    Option("castanho", "Castanho", rgb("5a3a22")),
    Option("ruivo", "Ruivo", rgb("b5522a")),
    Option("loiro", "Loiro", rgb("e0b85a")),
    Option("grisalho", "Grisalho", rgb("b8b8b8")),
    Option("azul", "Azul", rgb("3a7bd5")),
    Option("rosa", "Rosa", rgb("e86aa6")),
    Option("verde", "Verde", rgb("3fae5a")),
    Option("roxo", "Roxo", rgb("8e5ad1")),
    Option("branco", "Branco", rgb("f2f2f2")),
]
SHIRT_COLORS: List[Option] = [
    Option("amarela", "Amarela", rgb("f9c22e")),
    Option("verde", "Verde", rgb("3fae5a")),
    Option("azul", "Azul", rgb("2f7fd6")),
    Option("vermelha", "Vermelha", rgb("e2483d")),
    Option("roxa", "Roxa", rgb("8e5ad1")),
    Option("laranja", "Laranja", rgb("f07c2a")),
    Option("rosa", "Rosa", rgb("f06292")),
    Option("turquesa", "Turquesa", rgb("1fb0a8")),
]
GLASSES: List[Option] = [
    Option("nenhum", "Sem óculos"),
    Option("redondo", "Óculos redondos"),
    Option("quadrado", "Óculos quadrados"),
    Option("sol", "Óculos de sol"),
]
ACCESSORIES: List[Option] = [
    Option("nenhum", "Nenhum"),
    Option("bone", "Boné"),
    Option("lenco", "Lenço"),
    Option("abafador", "Abafador de ruído"),
    Option("capacete", "Capacete de aviador"),
    Option("flor", "Flor"),
    Option("tiara", "Tiara"),
    Option("coroa", "Coroa de papel"),
]
# Itens assistivos: opções comuns, sem destaque especial no menu.
HEARING_AID: List[Option] = [Option("nao", "Sem aparelho auditivo"), Option("sim", "Aparelho auditivo")]
WHEELCHAIR: List[Option] = [Option("nao", "Sem cadeira de rodas"), Option("sim", "Cadeira de rodas")]

PILOT_FIELDS: Tuple[Tuple[str, str, List[Option]], ...] = (
    ("pele", "Pele", SKIN_TONES),
    ("cabelo", "Cabelo", HAIR_STYLES),
    ("cor_cabelo", "Cor do cabelo", HAIR_COLORS),
    ("roupa", "Roupa", SHIRT_COLORS),
    ("oculos", "Óculos", GLASSES),
    ("acessorio", "Acessório", ACCESSORIES),
    ("aparelho", "Aparelho auditivo", HEARING_AID),
    ("cadeira", "Cadeira de rodas", WHEELCHAIR),
)
DEFAULT_PILOT = {
    "pele": "pele3",
    "cabelo": "cacheado",
    "cor_cabelo": "preto",
    "roupa": "amarela",
    "oculos": "nenhum",
    "acessorio": "nenhum",
    "aparelho": "nao",
    "cadeira": "nao",
}


def option_keys(options: List[Option]) -> List[str]:
    return [o.key for o in options]


def find_option(options: List[Option], key: str) -> Option:
    for option in options:
        if option.key == key:
            return option
    return options[0]


def normalize_pilot(data: object) -> dict:
    """Completa e valida a escolha do piloto vinda do save."""
    result = dict(DEFAULT_PILOT)
    if isinstance(data, dict):
        for field, _, options in PILOT_FIELDS:
            value = data.get(field)
            if value in option_keys(options):
                result[field] = value
    return result
