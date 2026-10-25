"""Peças reutilizáveis: paleta, copas, folhas de palmeira, casas, painéis solares, janelas.

Cada catálogo (models_*.py) registra seus modelos com @model("Nome", pasta, **render),
e tools/build_assets.py renderiza todos.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, NamedTuple, Optional, Sequence, Tuple

import numpy as np

from .mesh import RGB, Mesh, chain, hexcolor, mix, rotate_x, rotate_y, rotate_z, scale, scatter, shade, translate

# ------------------------------------------------------------------- paleta
P = {
    "bark": hexcolor("6b4a33"),
    "bark_light": hexcolor("a08668"),
    "bark_gray": hexcolor("8d8577"),
    "leaf": hexcolor("3f8f3a"),
    "leaf_dark": hexcolor("2b6b2e"),
    "leaf_light": hexcolor("6fb84a"),
    "leaf_dry": hexcolor("9aa05a"),
    "cactus": hexcolor("4f8f5a"),
    "cactus_dark": hexcolor("3a6e45"),
    "wood": hexcolor("9a6a3e"),
    "wood_dark": hexcolor("6e4a2a"),
    "plank": hexcolor("b8865a"),
    "rust": hexcolor("8a4a2a"),
    "rust_dark": hexcolor("5a3220"),
    "steel": hexcolor("6f7780"),
    "steel_dark": hexcolor("464c54"),
    "concrete": hexcolor("9a958c"),
    "soot": hexcolor("3a3532"),
    "white": hexcolor("f1ede4"),
    "cream": hexcolor("e9dcc0"),
    "terracotta": hexcolor("c46a3a"),
    "tile": hexcolor("b0502e"),
    "solar": hexcolor("1f3b73"),
    "solar_frame": hexcolor("c9ced6"),
    "glass": hexcolor("8fd3e0"),
    "water": hexcolor("2f8f9a"),
    "gold": hexcolor("d9a441"),
    "brass": hexcolor("b8893a"),
    "green_roof": hexcolor("5aa64a"),
    "red": hexcolor("d64532"),
    "blue": hexcolor("2f6fc0"),
    "yellow": hexcolor("f2c037"),
    "pink": hexcolor("e8909a"),
    "salmon": hexcolor("e8a07a"),
    "sand": hexcolor("d8c08a"),
    "clay": hexcolor("b5784a"),
    "purple": hexcolor("5a2a5a"),
    "orange": hexcolor("e07a2a"),
}


class Spec(NamedTuple):
    build: Callable[[], Mesh]
    folder: str
    render: dict


REGISTRY: Dict[str, Spec] = {}


def model(name: str, folder: str = "biome_sprites", **render):
    """Registra um modelo para o build (render = yaw, pitch, sprite_max...)."""

    def wrap(fn: Callable[[], Mesh]) -> Callable[[], Mesh]:
        REGISTRY[name] = Spec(fn, folder, render)
        return fn

    return wrap


# ------------------------------------------------------------------- flora
def canopy(
    mesh: Mesh,
    center: Tuple[float, float, float],
    radius: float,
    color: RGB,
    blobs: int = 6,
    seed: int = 1,
    flat: float = 0.7,
    spread: float = 0.9,
    rings: int = 3,
    segments: int = 7,
) -> Mesh:
    """Copa feita de várias bolhas low-poly sobrepostas (luz e sombra nas facetas)."""
    rng = np.random.default_rng(abs(int(seed)))
    cx, cy, cz = center
    for i in range(blobs):
        a = 2 * math.pi * i / blobs + rng.uniform(-0.3, 0.3)
        d = radius * spread * (0.35 + 0.5 * rng.uniform())
        r = radius * (0.45 + 0.25 * rng.uniform())
        tone = shade(color, 0.86 + 0.28 * rng.uniform())
        mesh.sphere(
            r,
            tone,
            rings,
            segments,
            at=translate(cx + d * math.cos(a), cy + rng.uniform(-0.2, 0.25) * radius, cz + d * math.sin(a)),
            squash=(1.0, flat, 1.0),
            jitter=0.12,
            seed=seed * 31 + i,
        )
    mesh.sphere(
        radius * 0.7,
        shade(color, 1.08),
        rings,
        segments,
        at=translate(cx, cy + radius * 0.25, cz),
        squash=(1.0, flat, 1.0),
        jitter=0.1,
        seed=seed * 7,
    )
    return mesh


def frond(
    mesh: Mesh,
    base: Tuple[float, float, float],
    yaw: float,
    length: float,
    droop: float,
    color: RGB,
    width: float = 0.18,
    segments: int = 4,
) -> Mesh:
    """Folha de palmeira: tira que arqueia para baixo (palmeiras, açaí, carnaúba)."""
    bx, by, bz = base
    pts = []
    for i in range(segments + 1):
        t = i / segments
        x = length * t
        y = -droop * length * t * t + 0.25 * length * t
        pts.append((x, y))
    m = chain(translate(bx, by, bz), rotate_y(yaw))
    for i in range(segments):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        w0 = width * length * (1.0 - 0.6 * i / segments)
        w1 = width * length * (1.0 - 0.6 * (i + 1) / segments)
        corners = np.array([(x0, y0, -w0), (x1, y1, -w1), (x1, y1, w1), (x0, y0, w0)], dtype=float)
        hom = np.hstack([corners, np.ones((4, 1))]) @ m.T
        a, b, c, d = (tuple(p[:3]) for p in hom)
        mid = tuple((np.array(a) + np.array(d)) / 2 + np.array([0, 0.02 * length, 0]))
        tone = shade(color, 0.92 + 0.12 * (i % 2))
        mesh.tri(a, b, mid, tone)
        mesh.tri(mid, b, c, shade(tone, 0.9))
        mesh.tri(mid, c, d, tone)
    return mesh


def palm_crown(
    mesh: Mesh,
    top: Tuple[float, float, float],
    count: int,
    length: float,
    droop: float,
    color: RGB,
    seed: int = 0,
    width: float = 0.16,
) -> Mesh:
    rng = np.random.default_rng(abs(int(seed)))
    for i in range(count):
        yaw = 360.0 * i / count + rng.uniform(-12, 12)
        frond(
            mesh,
            top,
            yaw,
            length * rng.uniform(0.85, 1.1),
            droop * rng.uniform(0.8, 1.2),
            shade(color, rng.uniform(0.9, 1.1)),
            width,
        )
    return mesh


def trunk(
    mesh: Mesh,
    height: float,
    radius: float,
    color: RGB,
    top_ratio: float = 0.7,
    segments: int = 7,
    lean: float = 0.0,
    at: Optional[np.ndarray] = None,
    rings: int = 1,
) -> Mesh:
    """Tronco (em anéis, para poder inclinar); lean desloca o topo em x."""
    base = at if at is not None else np.eye(4)
    step = height / rings
    for i in range(rings):
        r0 = radius * (1 - (1 - top_ratio) * i / rings)
        r1 = radius * (1 - (1 - top_ratio) * (i + 1) / rings)
        dx = lean * (i / rings) ** 2 * height
        mesh.cylinder(
            r0,
            step * 1.02,
            shade(color, 1.0 - 0.05 * (i % 2)),
            segments,
            r1,
            at=chain(base, translate(dx, i * step, 0), rotate_z(-lean * 25 * (i + 1) / rings)),
            caps=i == rings - 1,
        )
    return mesh


# ------------------------------------------------------------- arquitetura
def windows_row(
    mesh: Mesh,
    width: float,
    y: float,
    z: float,
    count: int,
    size: Tuple[float, float],
    color: RGB = P["glass"],
    frame: Optional[RGB] = None,
    emit: float = 0.25,
    x0: Optional[float] = None,
    facing: str = "front",
) -> Mesh:
    """Janelas como placas finas na fachada (front = +z, side = +x em x = z)."""
    w, h = size
    start = -width / 2 + width / (count * 2) if x0 is None else x0
    step = width / count
    for i in range(count):
        cx = start + i * step
        if facing == "front":
            at = translate(cx, y, z + 0.01)
            if frame:
                mesh.box((w * 1.25, h * 1.2, 0.02), frame, at=chain(at, translate(0, -h * 0.1, 0)))
            mesh.box((w, h, 0.03), color, at=at, emit=emit)
        else:
            at = chain(translate(z + 0.01, y, cx), rotate_y(90))
            if frame:
                mesh.box((w * 1.25, h * 1.2, 0.02), frame, at=chain(at, translate(0, -h * 0.1, 0)))
            mesh.box((w, h, 0.03), color, at=at, emit=emit)
    return mesh


def gable_roof(
    mesh: Mesh,
    width: float,
    depth: float,
    height: float,
    y: float,
    color: RGB,
    overhang: float = 0.1,
    gable: Optional[RGB] = None,
) -> Mesh:
    """Telhado de duas águas (cumeeira ao longo de z)."""
    w, d, o = width / 2 + overhang, depth / 2 + overhang, overhang
    ridge = y + height
    mesh.quad((-w, y - o * 0.4, d), (0, ridge, d), (0, ridge, -d), (-w, y - o * 0.4, -d), color)
    mesh.quad((0, ridge, d), (w, y - o * 0.4, d), (w, y - o * 0.4, -d), (0, ridge, -d), shade(color, 0.92))
    g = gable or color
    mesh.tri((-width / 2, y, depth / 2), (width / 2, y, depth / 2), (0, ridge - 0.02, depth / 2), g)
    mesh.tri((-width / 2, y, -depth / 2), (width / 2, y, -depth / 2), (0, ridge - 0.02, -depth / 2), g)
    return mesh


def solar_panel(
    mesh: Mesh,
    at: np.ndarray,
    size: Tuple[float, float] = (0.9, 0.55),
    tilt: float = 25.0,
    cells: Tuple[int, int] = (3, 2),
) -> Mesh:
    """Painel fotovoltaico inclinado com moldura e células."""
    w, d = size
    base = chain(at, rotate_x(-tilt))
    mesh.box((w + 0.06, 0.04, d + 0.06), P["solar_frame"], at=base)
    cw, cd = w / cells[0], d / cells[1]
    for i in range(cells[0]):
        for j in range(cells[1]):
            mesh.box(
                (cw * 0.9, 0.02, cd * 0.88),
                shade(P["solar"], 1.0 + 0.08 * ((i + j) % 2)),
                at=chain(base, translate(-w / 2 + cw * (i + 0.5), 0.04, -d / 2 + cd * (j + 0.5))),
                emit=0.12,
            )
    return mesh


def stilts(
    mesh: Mesh,
    width: float,
    depth: float,
    height: float,
    color: RGB,
    count: Tuple[int, int] = (3, 2),
    thickness: float = 0.08,
) -> Mesh:
    for i in range(count[0]):
        for j in range(count[1]):
            x = -width / 2 + width * i / max(1, count[0] - 1)
            z = -depth / 2 + depth * j / max(1, count[1] - 1)
            mesh.box((thickness, height, thickness), color, at=translate(x, 0, z))
    return mesh


def flowers(
    mesh: Mesh, center: Tuple[float, float, float], radius: float, color: RGB, count: int, seed: int, size: float = 0.06
) -> Mesh:
    cx, cy, cz = center
    for k, (dx, dz) in enumerate(scatter(count, radius, seed)):
        mesh.sphere(size, color, 2, 5, at=translate(cx + dx, cy + 0.02 * (k % 3), cz + dz))
    return mesh


def lattice_tower(
    mesh: Mesh, base_w: float, top_w: float, height: float, levels: int, color: RGB, thickness: float = 0.05
) -> Mesh:
    """Torre treliçada de base quadrada (linhas de transmissão, guindastes)."""
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for lvl in range(levels):
        y0, y1 = height * lvl / levels, height * (lvl + 1) / levels
        w0 = base_w + (top_w - base_w) * lvl / levels
        w1 = base_w + (top_w - base_w) * (lvl + 1) / levels
        for k in range(4):
            ax, az = corners[k]
            bx, bz = corners[(k + 1) % 4]
            mesh.beam((ax * w0 / 2, y0, az * w0 / 2), (ax * w1 / 2, y1, az * w1 / 2), thickness, color)
            mesh.beam((ax * w0 / 2, y0, az * w0 / 2), (bx * w1 / 2, y1, bz * w1 / 2), thickness * 0.6, color)
            mesh.beam((ax * w1 / 2, y1, az * w1 / 2), (bx * w1 / 2, y1, bz * w1 / 2), thickness * 0.7, color)
    return mesh


def smoke(mesh: Mesh, top: Tuple[float, float, float], size: float, puffs: int = 3, seed: int = 0) -> Mesh:
    """Fumaça cinza que se abre e se afasta da chaminé."""
    x, y, z = top
    for i in range(puffs):
        tone = mix(hexcolor("6e6862"), hexcolor("b4aea6"), i / max(1, puffs - 1))
        mesh.sphere(
            size * (1.1 + 0.55 * i),
            tone,
            3,
            8,
            at=translate(x + 0.45 * size * i, y + size * (0.6 + 1.25 * i), z),
            squash=(1.0, 0.75, 1.0),
            jitter=0.18,
            seed=seed + i,
        )
    return mesh


def band_cylinder(
    mesh: Mesh,
    radius: float,
    height: float,
    colors: Sequence[RGB],
    bands: int,
    top_radius: Optional[float] = None,
    segments: int = 10,
    at: Optional[np.ndarray] = None,
) -> Mesh:
    """Cilindro com faixas de cor (chaminés listradas, faróis)."""
    r1 = radius if top_radius is None else top_radius
    base = at if at is not None else np.eye(4)
    step = height / bands
    for i in range(bands):
        ra = radius + (r1 - radius) * i / bands
        rb = radius + (r1 - radius) * (i + 1) / bands
        mesh.cylinder(
            ra,
            step,
            colors[i % len(colors)],
            segments,
            rb,
            at=chain(base, translate(0, i * step, 0)),
            caps=i == bands - 1,
        )
    return mesh


__all__ = [
    "P",
    "model",
    "REGISTRY",
    "canopy",
    "frond",
    "palm_crown",
    "trunk",
    "windows_row",
    "gable_roof",
    "solar_panel",
    "stilts",
    "flowers",
    "lattice_tower",
    "smoke",
    "band_cylinder",
    "mix",
    "shade",
    "scale",
    "rotate_x",
    "rotate_y",
    "rotate_z",
    "translate",
    "chain",
    "Mesh",
    "hexcolor",
]
