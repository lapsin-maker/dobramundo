"""Funções numéricas e de cor usadas em todo o jogo."""

from __future__ import annotations

from typing import Tuple

from .config import FOG_END, FOG_START

Color = Tuple[int, int, int]


def clamp(value: float, low: float, high: float) -> float:
    """Limita value ao intervalo [low, high]."""
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    """Interpolação linear de a até b (t limitado a 0..1)."""
    return a + (b - a) * clamp(t, 0.0, 1.0)


def lerp_color(a: Color, b: Color, t: float) -> Color:
    """Mistura duas cores RGB (t = 0 dá a, t = 1 dá b)."""
    t = clamp(t, 0.0, 1.0)
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t), round(a[2] + (b[2] - a[2]) * t))


def smoothstep(t: float) -> float:
    """0..1 com início e fim suaves (derivada zero nas pontas)."""
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def haze_at(z: float) -> float:
    """Quanto da neblina cobre algo na profundidade z: 0 perto, 1 no fim da pista."""
    return clamp((z - FOG_START) / (FOG_END - FOG_START), 0.0, 1.0)


def rgb(hex_color: str) -> Color:
    """'#1b3a8a' -> (27, 58, 138)."""
    hex_color = hex_color.lstrip("#")
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def points_text(value: int) -> str:
    """Número com separador de milhar brasileiro (1.234)."""
    return f"{value:,}".replace(",", ".")
