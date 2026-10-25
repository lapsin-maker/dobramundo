"""Malha low-poly: triângulos com cor e "parte" (para separar camadas do piloto).

Espaço do modelo: y para cima, chão em y = 0, frente para +z, direita para +x.
As primitivas aceitam uma matriz 4x4 (``at``) que posiciona a peça.
"""

from __future__ import annotations

import math
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np

Vec = Tuple[float, float, float]
RGB = Tuple[int, int, int]


# ---------------------------------------------------------------- matrizes
def identity() -> np.ndarray:
    return np.eye(4)


def translate(x: float = 0.0, y: float = 0.0, z: float = 0.0) -> np.ndarray:
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


def scale(sx: float, sy: Optional[float] = None, sz: Optional[float] = None) -> np.ndarray:
    m = np.eye(4)
    m[0, 0], m[1, 1], m[2, 2] = sx, sx if sy is None else sy, sx if sz is None else sz
    return m


def rotate_x(deg: float) -> np.ndarray:
    a = math.radians(deg)
    m = np.eye(4)
    m[1, 1], m[1, 2], m[2, 1], m[2, 2] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return m


def rotate_y(deg: float) -> np.ndarray:
    a = math.radians(deg)
    m = np.eye(4)
    m[0, 0], m[0, 2], m[2, 0], m[2, 2] = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    return m


def rotate_z(deg: float) -> np.ndarray:
    a = math.radians(deg)
    m = np.eye(4)
    m[0, 0], m[0, 1], m[1, 0], m[1, 1] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return m


def chain(*matrices: np.ndarray) -> np.ndarray:
    """Composição da esquerda para a direita: chain(A, B) aplica B e depois A."""
    out = np.eye(4)
    for m in matrices:
        out = out @ m
    return out


def hexcolor(value: str) -> RGB:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def shade(color: RGB, factor: float) -> RGB:
    return tuple(int(max(0, min(255, c * factor))) for c in color)  # type: ignore[return-value]


def mix(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))  # type: ignore[return-value]


# ------------------------------------------------------------------- malha
class Mesh:
    def __init__(self) -> None:
        self.tris: List[np.ndarray] = []  # cada um: array 3x3 (vértices)
        self.colors: List[RGB] = []
        self.parts: List[str] = []
        self.emits: List[float] = []  # brilho próprio (0..1): janelas, painéis, luzes

    def __len__(self) -> int:
        return len(self.tris)

    def tri(
        self, a: Sequence[float], b: Sequence[float], c: Sequence[float], color: RGB, part: str = "", emit: float = 0.0
    ) -> None:
        self.tris.append(np.array([a, b, c], dtype=np.float64))
        self.colors.append(tuple(int(v) for v in color))  # type: ignore[arg-type]
        self.parts.append(part)
        self.emits.append(emit)

    def quad(self, a, b, c, d, color: RGB, part: str = "", emit: float = 0.0) -> None:
        self.tri(a, b, c, color, part, emit)
        self.tri(a, c, d, color, part, emit)

    def poly(self, points: Sequence[Sequence[float]], color: RGB, part: str = "", emit: float = 0.0) -> None:
        """Polígono convexo (leque a partir do primeiro vértice)."""
        for i in range(1, len(points) - 1):
            self.tri(points[0], points[i], points[i + 1], color, part, emit)

    def extend(self, other: Mesh, at: Optional[np.ndarray] = None) -> Mesh:
        for tri, color, part, emit in zip(other.tris, other.colors, other.parts, other.emits):
            self.tris.append(apply(at, tri) if at is not None else tri.copy())
            self.colors.append(color)
            self.parts.append(part)
            self.emits.append(emit)
        return self

    def transformed(self, at: np.ndarray) -> Mesh:
        return Mesh().extend(self, at)

    def recolor(self, color: RGB, part: Optional[str] = None) -> Mesh:
        self.colors = [color for _ in self.colors]
        if part is not None:
            self.parts = [part for _ in self.parts]
        return self

    def bounds(self) -> Tuple[np.ndarray, np.ndarray]:
        points = np.concatenate(self.tris) if self.tris else np.zeros((1, 3))
        return points.min(axis=0), points.max(axis=0)

    # ------------------------------------------------------------ primitivas
    def box(
        self,
        size: Vec,
        color: RGB,
        at: Optional[np.ndarray] = None,
        part: str = "",
        emit: float = 0.0,
        top: Optional[RGB] = None,
        bottom: bool = False,
    ) -> Mesh:
        """Caixa com a base no chão local (y de 0 a altura), centrada em x e z."""
        w, h, d = size[0] / 2, size[1], size[2] / 2
        p = [(-w, 0, -d), (w, 0, -d), (w, 0, d), (-w, 0, d), (-w, h, -d), (w, h, -d), (w, h, d), (-w, h, d)]
        p = [tuple(v) for v in apply(at, np.array(p, dtype=float))]
        faces = [(3, 2, 6, 7), (1, 0, 4, 5), (2, 1, 5, 6), (0, 3, 7, 4), (7, 6, 5, 4)]
        if bottom:
            faces.append((0, 1, 2, 3))
        for i, f in enumerate(faces):
            self.quad(*(p[k] for k in f), color=(top or color) if i == 4 else color, part=part, emit=emit)
        return self

    def cylinder(
        self,
        radius: float,
        height: float,
        color: RGB,
        segments: int = 8,
        top_radius: Optional[float] = None,
        at: Optional[np.ndarray] = None,
        part: str = "",
        emit: float = 0.0,
        caps: bool = True,
        top_color: Optional[RGB] = None,
        offset: float = 0.0,
    ) -> Mesh:
        """Tronco de cone vertical (raio base, raio topo), base em y = 0."""
        r2 = radius if top_radius is None else top_radius
        ring0, ring1 = [], []
        for i in range(segments):
            a = 2 * math.pi * (i + offset) / segments
            ring0.append((radius * math.cos(a), 0.0, radius * math.sin(a)))
            ring1.append((r2 * math.cos(a), height, r2 * math.sin(a)))
        ring0 = [tuple(v) for v in apply(at, np.array(ring0))]
        ring1 = [tuple(v) for v in apply(at, np.array(ring1))]
        for i in range(segments):
            j = (i + 1) % segments
            if r2 > 1e-9:
                self.quad(ring0[i], ring0[j], ring1[j], ring1[i], color, part, emit)
            else:
                self.tri(ring0[i], ring0[j], ring1[i], color, part, emit)
        if caps and r2 > 1e-9:
            self.poly(ring1[::-1], top_color or color, part, emit)
        return self

    def cone(
        self,
        radius: float,
        height: float,
        color: RGB,
        segments: int = 8,
        at: Optional[np.ndarray] = None,
        part: str = "",
        emit: float = 0.0,
    ) -> Mesh:
        return self.cylinder(radius, height, color, segments, 0.0, at, part, emit, caps=False)

    def sphere(
        self,
        radius: float,
        color: RGB,
        rings: int = 4,
        segments: int = 8,
        at: Optional[np.ndarray] = None,
        part: str = "",
        emit: float = 0.0,
        squash: Vec = (1.0, 1.0, 1.0),
        jitter: float = 0.0,
        seed: int = 0,
    ) -> Mesh:
        """Esfera low-poly centrada na origem local (jitter deforma os vértices: copas)."""
        rng = np.random.default_rng(abs(int(seed)))
        grid = []
        for r in range(rings + 1):
            phi = math.pi * r / rings
            row = []
            for s in range(segments):
                theta = 2 * math.pi * s / segments + (0.5 * math.pi / segments if r % 2 else 0)
                k = 1.0 + (rng.uniform(-jitter, jitter) if 0 < r < rings else 0.0)
                row.append(
                    (
                        radius * k * math.sin(phi) * math.cos(theta) * squash[0],
                        radius * math.cos(phi) * squash[1],
                        radius * k * math.sin(phi) * math.sin(theta) * squash[2],
                    )
                )
            grid.append([tuple(v) for v in apply(at, np.array(row))])
        for r in range(rings):
            for s in range(segments):
                t = (s + 1) % segments
                a, b, c, d = grid[r][s], grid[r][t], grid[r + 1][t], grid[r + 1][s]
                if r == 0:
                    self.tri(a, c, d, color, part, emit)
                elif r == rings - 1:
                    self.tri(a, b, d, color, part, emit)
                else:
                    self.quad(a, b, c, d, color, part, emit)
        return self

    def prism(
        self,
        outline: Sequence[Tuple[float, float]],
        height: float,
        color: RGB,
        at: Optional[np.ndarray] = None,
        part: str = "",
        emit: float = 0.0,
        top: Optional[RGB] = None,
        base: float = 0.0,
    ) -> Mesh:
        """Extrusão vertical de um polígono convexo (x, z) de y = base até base + height."""
        low = [tuple(v) for v in apply(at, np.array([(x, base, z) for x, z in outline], dtype=float))]
        high = [tuple(v) for v in apply(at, np.array([(x, base + height, z) for x, z in outline], dtype=float))]
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            self.quad(low[i], low[j], high[j], high[i], color, part, emit)
        self.poly(high, top or color, part, emit)
        return self

    def slab(
        self,
        outline: Sequence[Tuple[float, float]],
        depth: float,
        color: RGB,
        at: Optional[np.ndarray] = None,
        part: str = "",
        emit: float = 0.0,
        side: Optional[RGB] = None,
    ) -> Mesh:
        """Extrusão em z de um polígono convexo no plano xy (fachadas, arcos, placas)."""
        d = depth / 2
        front = [tuple(v) for v in apply(at, np.array([(x, y, d) for x, y in outline], dtype=float))]
        back = [tuple(v) for v in apply(at, np.array([(x, y, -d) for x, y in outline], dtype=float))]
        n = len(outline)
        for i in range(n):
            j = (i + 1) % n
            self.quad(front[i], front[j], back[j], back[i], side or color, part, emit)
        self.poly(front, color, part, emit)
        self.poly(back[::-1], color, part, emit)
        return self

    def lathe(
        self,
        profile: Sequence[Tuple[float, float]],
        color: RGB,
        segments: int = 10,
        at: Optional[np.ndarray] = None,
        part: str = "",
        emit: float = 0.0,
        colors: Optional[Sequence[RGB]] = None,
    ) -> Mesh:
        """Sólido de revolução: profile = [(raio, y), ...] de baixo para cima."""
        rings = []
        for radius, y in profile:
            ring = [
                (radius * math.cos(2 * math.pi * s / segments), y, radius * math.sin(2 * math.pi * s / segments))
                for s in range(segments)
            ]
            rings.append([tuple(v) for v in apply(at, np.array(ring))])
        for k in range(len(rings) - 1):
            band = colors[k] if colors is not None and k < len(colors) else color
            for s in range(segments):
                t = (s + 1) % segments
                a, b, c, d = rings[k][s], rings[k][t], rings[k + 1][t], rings[k + 1][s]
                if profile[k + 1][0] < 1e-9:
                    self.tri(a, b, d, band, part, emit)
                elif profile[k][0] < 1e-9:
                    self.tri(a, c, d, band, part, emit)
                else:
                    self.quad(a, b, c, d, band, part, emit)
        return self

    def beam(
        self, start: Vec, end: Vec, thickness: float, color: RGB, part: str = "", emit: float = 0.0, segments: int = 4
    ) -> Mesh:
        """Barra entre dois pontos (treliças, cabos, galhos)."""
        a, b = np.array(start, dtype=float), np.array(end, dtype=float)
        axis = b - a
        length = float(np.linalg.norm(axis))
        if length < 1e-9:
            return self
        m = align_y(axis / length)
        m[:3, 3] = a
        return self.cylinder(thickness / 2, length, color, segments, at=m, part=part, emit=emit)


def align_y(direction: np.ndarray) -> np.ndarray:
    """Matriz que leva o eixo y para a direção dada."""
    y = direction / np.linalg.norm(direction)
    helper = np.array([1.0, 0.0, 0.0]) if abs(y[0]) < 0.9 else np.array([0.0, 0.0, 1.0])
    x = np.cross(helper, y)
    x /= np.linalg.norm(x)
    z = np.cross(x, y)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2] = x, y, z
    return m


def apply(at: Optional[np.ndarray], points: np.ndarray) -> np.ndarray:
    if at is None:
        return points
    homogeneous = np.hstack([points, np.ones((len(points), 1))])
    return (homogeneous @ at.T)[:, :3]


def scatter(count: int, radius: float, seed: int) -> Iterable[Tuple[float, float]]:
    """Pontos determinísticos num disco (folhas, frutos, pedras)."""
    rng = np.random.default_rng(abs(int(seed)))
    for _ in range(count):
        r = radius * math.sqrt(rng.uniform(0, 1))
        a = rng.uniform(0, 2 * math.pi)
        yield r * math.cos(a), r * math.sin(a)
