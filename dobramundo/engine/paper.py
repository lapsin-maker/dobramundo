"""Formas de papel recortado desenhadas por código: morros, rio, caminho, árvores,
gente pequena e sombras, todas com traço de tinta, na linguagem da logo.

Usadas pela vila-base e pela abertura. Nada aqui depende de assets: um desenho
simples e consistente vale mais que um sprite sem contexto.
"""

from __future__ import annotations

import math
import random
from typing import List, Sequence, Tuple

import pygame

from ..util import Color, lerp_color

INK = (28, 44, 92)
Point = Tuple[float, float]


def ink_polygon(screen: pygame.Surface, points: Sequence[Point], fill: Color, ink: Color = INK, width: int = 3) -> None:
    """Polígono preenchido com contorno de tinta."""
    pts = [(int(x), int(y)) for x, y in points]
    if len(pts) < 3:
        return
    pygame.draw.polygon(screen, fill, pts)
    pygame.draw.polygon(screen, ink, pts, width)


def blob(
    screen: pygame.Surface, circles: Sequence[Tuple[float, float, float]], fill: Color, ink: Color = INK, width: int = 3
) -> None:
    """União de círculos (copa de árvore, nuvem, arbusto) com um só contorno."""
    for cx, cy, r in circles:
        pygame.draw.circle(screen, ink, (int(cx), int(cy)), int(r) + width)
    for cx, cy, r in circles:
        pygame.draw.circle(screen, fill, (int(cx), int(cy)), int(r))


def shadow(screen: pygame.Surface, center: Point, width: int, height: int, alpha: int = 60) -> None:
    """Sombra elíptica suave sob um objeto (mancha de aquarela)."""
    if width < 2 or height < 2:
        return
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    pygame.draw.ellipse(surf, (20, 30, 60, alpha), surf.get_rect())
    screen.blit(surf, surf.get_rect(center=(int(center[0]), int(center[1]))))


def hill_points(x0: float, x1: float, base_y: float, height: float, bumps: int, seed: int) -> List[Point]:
    """Contorno de um morro arredondado (ondas de seno somadas), fechado por baixo."""
    rng = random.Random(seed)
    phases = [rng.uniform(0, 6.28) for _ in range(3)]
    points: List[Point] = []
    steps = 28
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = (
            base_y
            - height
            * (
                0.55
                + 0.3 * math.sin(t * math.pi)
                + 0.1 * math.sin(t * bumps * 3.1 + phases[0])
                + 0.05 * math.sin(t * 7 + phases[1])
            )
            * math.sin(t * math.pi) ** 0.5
        )
        points.append((x, y))
    points += [(x1, base_y + 200), (x0, base_y + 200)]
    return points


def ribbon(center_line: Sequence[Point], widths: Sequence[float]) -> List[Point]:
    """Polígono de uma faixa (rio, caminho) a partir da linha central e das larguras."""
    left: List[Point] = []
    right: List[Point] = []
    n = len(center_line)
    for i, (x, y) in enumerate(center_line):
        px, py = center_line[max(0, i - 1)]
        nx, ny = center_line[min(n - 1, i + 1)]
        dx, dy = nx - px, ny - py
        length = math.hypot(dx, dy) or 1.0
        ox, oy = -dy / length * widths[i] / 2, dx / length * widths[i] / 2
        left.append((x + ox, y + oy))
        right.append((x - ox, y - oy))
    return left + right[::-1]


def bezier(p0: Point, p1: Point, p2: Point, p3: Point, steps: int = 24) -> List[Point]:
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1 - t
        x = u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1]
        out.append((x, y))
    return out


def tree(
    screen: pygame.Surface, base: Point, height: float, canopy: Color, trunk: Color, seed: int = 0, ink: Color = INK
) -> None:
    """Árvore de papel: tronco curto e copa de três a cinco bolas."""
    rng = random.Random(seed)
    x, y = base
    shadow(screen, (x, y), int(height * 0.9), int(height * 0.22), 50)
    pygame.draw.line(screen, ink, (int(x), int(y)), (int(x), int(y - height * 0.45)), max(3, int(height * 0.12)))
    pygame.draw.line(screen, trunk, (int(x), int(y)), (int(x), int(y - height * 0.45)), max(1, int(height * 0.12) - 2))
    r = height * 0.26
    circles = [(x, y - height * 0.7, r)]
    for _k in range(rng.randint(2, 4)):
        a = rng.uniform(0, 6.28)
        circles.append(
            (x + math.cos(a) * r * 0.9, y - height * 0.7 + math.sin(a) * r * 0.6 - r * 0.2, r * rng.uniform(0.6, 0.85))
        )
    blob(screen, circles, canopy, ink, 3)
    light = lerp_color(canopy, (255, 255, 255), 0.25)
    pygame.draw.circle(screen, light, (int(x - r * 0.3), int(y - height * 0.8)), int(r * 0.35))


def person(
    screen: pygame.Surface, feet: Point, height: float, shirt: Color, skin: Color, phase: float = 0.0, ink: Color = INK
) -> None:
    """Figura pequena de papel: cabeça redonda, corpo arredondado, perninhas que andam."""
    x, y = feet
    step = math.sin(phase) * height * 0.12
    shadow(screen, (x, y), int(height * 0.7), int(height * 0.18), 45)
    for dx in (-1, 1):
        pygame.draw.line(
            screen,
            ink,
            (int(x + dx * height * 0.1), int(y - height * 0.35)),
            (int(x + dx * height * 0.1 + dx * step), int(y)),
            max(2, int(height * 0.1)),
        )
    body = pygame.Rect(0, 0, int(height * 0.42), int(height * 0.45))
    body.midbottom = (int(x), int(y - height * 0.3))
    pygame.draw.rect(screen, ink, body.inflate(4, 4), border_radius=int(height * 0.14))
    pygame.draw.rect(screen, shirt, body, border_radius=int(height * 0.12))
    head_r = int(height * 0.19)
    pygame.draw.circle(screen, ink, (int(x), int(y - height * 0.78)), head_r + 2)
    pygame.draw.circle(screen, skin, (int(x), int(y - height * 0.78)), head_r)


def wave_lines(
    screen: pygame.Surface, center_line: Sequence[Point], color: Color, t: float, count: int = 10, seed: int = 1
) -> None:
    """Tracinhos de água que andam ao longo do rio."""
    rng = random.Random(seed)
    n = len(center_line)
    for k in range(count):
        u = (rng.random() + t * 0.05 * (1 + k % 3)) % 1.0
        i = min(n - 2, int(u * (n - 1)))
        x, y = center_line[i]
        off = rng.uniform(-0.3, 0.3)
        pygame.draw.line(
            screen, color, (int(x - 9 + off * 20), int(y + off * 30)), (int(x + 9 + off * 20), int(y + off * 30)), 2
        )


def smoke(screen: pygame.Surface, origin: Point, t: float, amount: float, seed: int = 0) -> None:
    """Fumaça de chaminé: bolhas que sobem e somem (amount 0..1)."""
    if amount <= 0.02:
        return
    rng = random.Random(seed)
    for k in range(5):
        life = (t * 0.35 + k / 5 + rng.random()) % 1.0
        r = 10 + life * 26
        x = origin[0] + math.sin(t * 0.8 + k) * 10 + life * 30
        y = origin[1] - life * 120
        surf = pygame.Surface((int(r * 2), int(r * 2)), pygame.SRCALPHA)
        pygame.draw.circle(surf, (120, 118, 112, int(110 * amount * (1 - life))), (int(r), int(r)), int(r))
        screen.blit(surf, (int(x - r), int(y - r)))


def sparkles(screen: pygame.Surface, area: pygame.Rect, t: float, amount: float, color: Color, seed: int = 3) -> None:
    """Pétalas/borboletas de papel flutuando (amount 0..1)."""
    if amount <= 0.05:
        return
    rng = random.Random(seed)
    for k in range(int(12 * amount)):
        x = area.left + (rng.random() * area.width + t * (12 + k * 3)) % area.width
        y = area.top + (rng.random() * area.height + math.sin(t * 1.5 + k) * 10) % area.height
        a = t * 4 + k
        w = 3 + 2 * abs(math.cos(a))
        pygame.draw.ellipse(screen, color, (int(x - w), int(y - 2), int(2 * w), 4))
