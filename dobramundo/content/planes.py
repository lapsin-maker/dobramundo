"""Aviões de papel, pintura (cores e padrões) e manobras."""

from __future__ import annotations

import json
import math
from typing import Dict, List, NamedTuple, Optional, Tuple

from ..paths import asset_dir_candidates

# 11 dobraduras de voo distinto, entre elas uma miniatura do 14-Bis (GDD, seção 6).
PLANE_MODELS: List[Tuple[str, str]] = [
    ("dart", "Jato Alongado"),
    ("glider", "Planador Largo"),
    ("stubby", "Asa Curta"),
    ("binder", "Avião de Fichário"),
    ("needle", "Bico Agulha"),
    ("hoverboard", "Asa Retangular"),
    ("crane", "Tsuru (Pássaro)"),
    ("accordion", "Sanfona"),
    ("jetfighter", "Caça de Papel"),
    ("tailboom", "Planador de Haste Longa"),
    ("bis14", "14-Bis (Miniatura)"),
]
PLANE_KEYS = [key for key, _ in PLANE_MODELS]
DEFAULT_PLANE = "dart"

# Cores aplicadas ao papel (o piloto não muda). "original" usa as cores do estúdio.
PLANE_COLORS: List[Tuple[str, str, Optional[Tuple[int, int, int]]]] = [
    ("original", "Original", None),
    ("branco", "Branco papel", (250, 250, 246)),
    ("vermelho", "Vermelho", (229, 57, 53)),
    ("laranja", "Laranja", (251, 140, 0)),
    ("amarelo", "Amarelo", (253, 216, 53)),
    ("verde", "Verde", (67, 160, 71)),
    ("menta", "Verde-água", (38, 198, 160)),
    ("ciano", "Ciano", (0, 188, 212)),
    ("azul", "Azul", (30, 136, 229)),
    ("anil", "Anil", (63, 81, 181)),
    ("roxo", "Roxo", (142, 36, 170)),
    ("rosa", "Rosa", (236, 64, 122)),
    ("dourado", "Dourado", (212, 175, 55)),
    ("kraft", "Papelão kraft", (196, 160, 110)),
    ("grafite", "Grafite", (84, 90, 100)),
]
PLANE_COLOR_KEYS = [key for key, _, _ in PLANE_COLORS]

# Padrões: texturas 256x256 em assets/plane_patterns "vestidas" no papel pelo mapa UV.
# O jornal é gratuito: é o papel reciclado da abertura do jogo.
PLANE_PATTERNS: List[Tuple[str, str]] = [
    ("liso", "Liso (só a cor)"),
    ("jornal", "Jornal"),
    ("papel_reciclado", "Papel reciclado"),
    ("kraft", "Kraft pardo"),
    ("caderno_pautado", "Caderno pautado"),
    ("eco_folhas", "Folhas"),
    ("bolinhas", "Bolinhas"),
    ("listras_papel", "Listras de papel"),
    ("origami_seigaiha", "Origami seigaiha"),
    ("blueprint", "Planta técnica"),
    ("aquarela", "Aquarela"),
    ("camuflado", "Camuflado selva"),
    ("deserto", "Camuflado deserto"),
    ("artico", "Camuflado ártico"),
    ("listras", "Listras de corrida"),
    ("xadrez", "Xadrez de corrida"),
    ("hexagonal", "Fibra hexagonal"),
    ("tigre", "Tigre"),
    ("chamas", "Chamas"),
    ("raios", "Raios solares"),
    ("pop_art", "Pop art"),
    ("prisma", "Prisma"),
    ("brasil", "Brasil"),
    ("cyberpunk", "Neon"),
    ("plasma", "Plasma"),
    ("galaxia", "Galáxia"),
]
PLANE_PATTERN_KEYS = [key for key, _ in PLANE_PATTERNS]
FREE_PATTERNS = frozenset({"liso", "jornal"})
DEFAULT_PATTERN = "jornal"

# Loja de padrões (colecionismo): paga com os pontos somados de todos os voos.
PATTERN_PRICES: Dict[str, int] = {
    "papel_reciclado": 300,
    "kraft": 300,
    "caderno_pautado": 500,
    "eco_folhas": 500,
    "bolinhas": 700,
    "listras_papel": 700,
    "camuflado": 900,
    "deserto": 900,
    "artico": 900,
    "listras": 1100,
    "xadrez": 1100,
    "hexagonal": 1300,
    "tigre": 1300,
    "origami_seigaiha": 1600,
    "chamas": 1600,
    "raios": 1800,
    "pop_art": 1800,
    "prisma": 2200,
    "blueprint": 2200,
    "brasil": 2500,
    "aquarela": 3000,
    "cyberpunk": 3500,
    "plasma": 4000,
    "galaxia": 5000,
}


def pattern_label(key: str) -> str:
    return PLANE_PATTERNS[PLANE_PATTERN_KEYS.index(key)][1] if key in PLANE_PATTERN_KEYS else key


def color_label(key: str) -> str:
    return PLANE_COLORS[PLANE_COLOR_KEYS.index(key)][1] if key in PLANE_COLOR_KEYS else key


def color_value(key: str) -> Optional[Tuple[int, int, int]]:
    return PLANE_COLORS[PLANE_COLOR_KEYS.index(key)][2] if key in PLANE_COLOR_KEYS else None


# ----------------------------------------------------------------- manobras
class ManeuverStyle(NamedTuple):
    """Manobra só visual (a colisão usa a posição real do avião)."""

    label: str
    duration: float  # segundos no jogo
    sway: float  # deslocamento lateral máximo (em larguras do avião)
    lift: float  # deslocamento vertical máximo (em larguras do avião)
    depth: float  # quanto o avião encolhe ao se afastar (dz = 1)


MANEUVER_STYLES: Dict[str, ManeuverStyle] = {
    "tonneau": ManeuverStyle("Tonneau (giro de 360°)", 0.95, 0.35, 0.3, 0.2),
    "looping": ManeuverStyle("Looping vertical", 1.5, 0.3, 0.55, 0.3),
    "cobra": ManeuverStyle("Manobra cobra", 1.2, 0.3, 0.4, 0.25),
    "decolagem": ManeuverStyle("Decolagem", 1.4, 0.4, 0.5, 0.3),
}
POWERUP_MANEUVERS = {"shield": "looping", "magnet": "tonneau", "repair": "cobra"}
START_MANEUVER = "decolagem"

ManeuverRow = Tuple[float, float, float, float, float, float]  # t, roll, pitch, dx, dy, dz


def builtin_maneuvers() -> Dict[str, List[ManeuverRow]]:
    """Curvas de reserva (mesmo formato do JSON), usadas se o arquivo faltar."""
    curves: Dict[str, List[ManeuverRow]] = {}
    n = 33
    for name in MANEUVER_STYLES:
        rows: List[ManeuverRow] = []
        for i in range(n):
            t = i / (n - 1)
            s = math.sin(math.pi * t)
            if name == "tonneau":
                rows.append((t, -360.0 * t, 0.0, 0.2 * math.sin(2 * math.pi * t), s, 0.4 * s))
            elif name == "looping":
                rows.append(
                    (t, 0.0, 360.0 * t, 0.0, (1 - math.cos(2 * math.pi * t)) / 2, 0.5 * math.sin(2 * math.pi * t))
                )
            elif name == "cobra":
                rows.append((t, 0.0, 78.0 * s * s, 0.0, 0.25 * s, s))
            else:
                rows.append((t, 0.0, 20.0 * (1 - t), 0.0, -0.25 * (1 - t), -(1 - t)))
        curves[name] = rows
    return curves


def load_maneuvers() -> Dict[str, List[ManeuverRow]]:
    """Lê assets/maneuvers/maneuvers.json (curvas extraídas das animações glTF)."""
    curves = builtin_maneuvers()
    for folder in asset_dir_candidates("maneuvers"):
        path = folder / "maneuvers.json"
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for name in MANEUVER_STYLES:
                rows = data.get(name, {}).get("samples")
                if rows and len(rows) >= 2 and all(len(r) == 6 for r in rows):
                    curves[name] = [tuple(float(v) for v in r) for r in rows]  # type: ignore[misc]
            break
        except (OSError, ValueError, TypeError, AttributeError):
            continue
    return curves
