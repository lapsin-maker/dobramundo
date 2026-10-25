"""Opções do piloto (GDD, seção 6): tom de pele, cabelo, óculos e acessórios, sem
marcação de gênero; cadeira de rodas e aparelho auditivo são itens comuns.

O piloto é desenhado por código em engine/paper_pilot.py e montado no avião
por engine/pilot.py. As camadas antigas em assets/pilot_layers são preservadas
para compatibilidade com as ferramentas anteriores de produção.
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
# A ausência de escolha é diferente de uma escolha de tom: o primeiro piloto usa
# papel creme como rosto provisório, sem predefinir a identidade da criança.
UNSELECTED = "sem_escolha"
SKIN_CHOICES: List[Option] = [Option(UNSELECTED, "Escolher depois", rgb("f5e9d2")), *SKIN_TONES]
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
HAIR_CHOICES: List[Option] = [Option(UNSELECTED, "Escolher depois"), *HAIR_STYLES]
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
HAIR_COLOR_CHOICES: List[Option] = [Option(UNSELECTED, "Escolher depois", rgb("f5e9d2")), *HAIR_COLORS]
SHIRT_COLORS: List[Option] = [
    Option("papel", "Papel", rgb("efe2c2")),
    Option("amarela", "Amarela", rgb("f9c22e")),
    Option("verde", "Verde", rgb("3fae5a")),
    Option("azul", "Azul", rgb("2f7fd6")),
    Option("vermelha", "Vermelha", rgb("e2483d")),
    Option("roxa", "Roxa", rgb("8e5ad1")),
    Option("laranja", "Laranja", rgb("f07c2a")),
    Option("rosa", "Rosa", rgb("f06292")),
    Option("turquesa", "Turquesa", rgb("1fb0a8")),
]
EYE_COLORS: List[Option] = [
    Option("castanhos", "Castanhos", rgb("6a3e28")),
    Option("azuis", "Azuis", rgb("2785bd")),
    Option("verdes", "Verdes", rgb("34855a")),
    Option("mel", "Mel", rgb("ba7a25")),
    Option("violeta", "Violeta", rgb("8357aa")),
    Option("cinza", "Cinza", rgb("687783")),
]
EYE_CHOICES: List[Option] = [Option(UNSELECTED, "Escolher depois"), *EYE_COLORS]
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
WALKER: List[Option] = [Option("nao", "Sem andador"), Option("sim", "Andador")]

PILOT_FIELDS: Tuple[Tuple[str, str, List[Option]], ...] = (
    ("pele", "Pele", SKIN_TONES),
    ("cabelo", "Cabelo", HAIR_STYLES),
    ("cor_cabelo", "Cor do cabelo", HAIR_COLORS),
    ("roupa", "Roupa", SHIRT_COLORS),
    ("olhos", "Olhos", EYE_COLORS),
    ("oculos", "Óculos", GLASSES),
    ("acessorio", "Acessório", ACCESSORIES),
    ("aparelho", "Aparelho auditivo", HEARING_AID),
    ("cadeira", "Cadeira de rodas", WHEELCHAIR),
    ("andador", "Andador", WALKER),
)
DEFAULT_PILOT = {
    "pele": UNSELECTED,
    "cabelo": UNSELECTED,
    "cor_cabelo": UNSELECTED,
    "roupa": "papel",
    "olhos": UNSELECTED,
    "oculos": "nenhum",
    "acessorio": "nenhum",
    "aparelho": "nao",
    "cadeira": "nao",
    "andador": "nao",
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
        if data.get("pele") == UNSELECTED:
            result["pele"] = UNSELECTED
        if data.get("cabelo") == UNSELECTED:
            result["cabelo"] = UNSELECTED
        if data.get("cor_cabelo") == UNSELECTED:
            result["cor_cabelo"] = UNSELECTED
        if data.get("olhos") == UNSELECTED:
            result["olhos"] = UNSELECTED
    # Saves antigos não têm ``andador`` e continuam iguais. Se um perfil editado
    # tiver os dois dispositivos por corrupção/manual edit, prioriza a cadeira.
    if result["cadeira"] == "sim":
        result["andador"] = "nao"
    return result
