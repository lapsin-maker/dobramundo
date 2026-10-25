"""Rasterizador numpy: malha low-poly -> sprite RGBA (e mapa de partes).

Mesma convenção de tools/legado/render_models.py: projeção ortográfica em vista 3/4
(yaw -35°, pitch 24°), luz difusa vinda da esquerda e de cima, supersampling 3x
com alfa pré-multiplicado. Cada face recebe uma leve variação de tom (facetado).
"""

from __future__ import annotations

import math
from typing import Dict, List, NamedTuple, Optional, Tuple

import numpy as np
from PIL import Image

from .mesh import Mesh

SUPERSAMPLE = 3
PADDING = 4
LIGHT = (-0.45, 0.75, 0.55)


class Frame(NamedTuple):
    """Enquadramento fixo (para várias camadas do mesmo modelo saírem alinhadas)."""

    min_xy: Tuple[float, float]
    max_xy: Tuple[float, float]
    scale: float
    size: Tuple[int, int]


def rotation(yaw: float, pitch: float) -> np.ndarray:
    y, p = math.radians(yaw), math.radians(pitch)
    ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    rx = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    return rx @ ry


def camera_points(mesh: Mesh, yaw: float, pitch: float) -> np.ndarray:
    rot = rotation(yaw, pitch)
    return np.stack(mesh.tris) @ rot.T if mesh.tris else np.zeros((0, 3, 3))


def make_frame(mesh: Mesh, yaw: float, pitch: float, sprite_max: int) -> Frame:
    pts = camera_points(mesh, yaw, pitch).reshape(-1, 3)
    mn, mx = pts.min(axis=0), pts.max(axis=0)
    span = max(mx[0] - mn[0], mx[1] - mn[1]) or 1.0
    scale = (sprite_max - 2 * PADDING) * SUPERSAMPLE / span
    w = int(math.ceil((mx[0] - mn[0]) * scale)) + 2 * PADDING * SUPERSAMPLE
    h = int(math.ceil((mx[1] - mn[1]) * scale)) + 2 * PADDING * SUPERSAMPLE
    w += (-w) % SUPERSAMPLE
    h += (-h) % SUPERSAMPLE
    return Frame((float(mn[0]), float(mn[1])), (float(mx[0]), float(mx[1])), float(scale), (w, h))


def face_jitter(index: int, amount: float) -> float:
    """Variação determinística de tom por face (aspecto facetado)."""
    value = math.sin(index * 12.9898 + 78.233) * 43758.5453
    return 1.0 + (value - math.floor(value) - 0.5) * 2 * amount


def rasterize(
    mesh: Mesh,
    yaw: float = -35.0,
    pitch: float = 24.0,
    sprite_max: int = 368,
    frame: Optional[Frame] = None,
    ambient: float = 0.45,
    gain: float = 1.0,
    jitter: float = 0.035,
    light=LIGHT,
    white_parts: Tuple[str, ...] = (),
):
    """Devolve (cor HxWx3 float, cobertura HxW, id da parte HxW int, nomes das partes, frame)."""
    frame = frame or make_frame(mesh, yaw, pitch, sprite_max)
    cam = camera_points(mesh, yaw, pitch)
    w, h = frame.size
    sx = (cam[..., 0] - frame.min_xy[0]) * frame.scale + PADDING * SUPERSAMPLE
    sy = (frame.max_xy[1] - cam[..., 1]) * frame.scale + PADDING * SUPERSAMPLE
    sz = cam[..., 2]
    color = np.zeros((h, w, 3), dtype=np.float32)
    mask = np.zeros((h, w), dtype=np.float32)
    ids = np.full((h, w), -1, dtype=np.int32)
    zbuf = np.full((h, w), -np.inf)
    lvec = np.array(light, dtype=float)
    lvec /= np.linalg.norm(lvec)
    names: List[str] = sorted(set(mesh.parts))
    part_index: Dict[str, int] = {name: i for i, name in enumerate(names)}
    for t in range(len(mesh.tris)):
        pa, pb, pc = cam[t]
        normal = np.cross(pb - pa, pc - pa)
        length = np.linalg.norm(normal)
        if length == 0:
            continue
        normal /= length
        if normal[2] < 0:
            normal = -normal  # malhas sem orientação garantida
        light_amount = ambient + (1.0 - ambient) * max(0.0, float(normal @ lvec))
        xs, ys = sx[t], sy[t]
        x0, x1 = max(int(xs.min()), 0), min(int(xs.max()) + 1, w - 1)
        y0, y1 = max(int(ys.min()), 0), min(int(ys.max()) + 1, h - 1)
        if x0 > x1 or y0 > y1:
            continue
        denom = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(denom) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        l0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / denom
        l1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / denom
        l2 = 1.0 - l0 - l1
        inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not inside.any():
            continue
        depth = l0 * sz[t, 0] + l1 * sz[t, 1] + l2 * sz[t, 2]
        region = zbuf[y0 : y1 + 1, x0 : x1 + 1]
        visible = inside & (depth > region)
        if not visible.any():
            continue
        part = mesh.parts[t]
        base = (255, 255, 255) if part in white_parts else mesh.colors[t]
        tone = light_amount * gain * face_jitter(t, jitter)
        emit = mesh.emits[t]
        rgb = np.clip(np.array(base, dtype=np.float32) / 255.0 * (tone * (1 - emit) + emit), 0.0, 1.0)
        region[visible] = depth[visible]
        color[y0 : y1 + 1, x0 : x1 + 1][visible] = rgb
        mask[y0 : y1 + 1, x0 : x1 + 1][visible] = 1.0
        ids[y0 : y1 + 1, x0 : x1 + 1][visible] = part_index[part]
    return color, mask, ids, names, frame


def downsample(color: np.ndarray, coverage: np.ndarray) -> Image.Image:
    """Reduz a supersamostragem com alfa pré-multiplicado (bordas suaves)."""
    h, w = coverage.shape
    out_w, out_h = w // SUPERSAMPLE, h // SUPERSAMPLE
    premult = Image.fromarray((color * coverage[..., None] * 255).astype(np.uint8), "RGB").resize(
        (out_w, out_h), Image.BOX
    )
    alpha = Image.fromarray((coverage * 255).astype(np.uint8), "L").resize((out_w, out_h), Image.BOX)
    a = np.asarray(alpha, dtype=np.float32) / 255.0
    rgb = np.asarray(premult, dtype=np.float32) / 255.0
    with np.errstate(divide="ignore", invalid="ignore"):
        rgb = np.where(a[..., None] > 0, rgb / np.maximum(a[..., None], 1e-6), 0.0)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 1) * 255, a * 255]).astype(np.uint8), "RGBA")


def render(mesh: Mesh, yaw: float = -35.0, pitch: float = 24.0, sprite_max: int = 368, **kwargs) -> Image.Image:
    color, mask, _, _, _ = rasterize(mesh, yaw, pitch, sprite_max, **kwargs)
    return downsample(color, mask)


def render_layers(
    mesh: Mesh, yaw: float, pitch: float, frame: Frame, white_parts: Tuple[str, ...] = (), **kwargs
) -> Dict[str, Image.Image]:
    """Uma imagem por parte, só com os pixels em que a parte é visível na cena inteira."""
    color, mask, ids, names, _ = rasterize(mesh, yaw, pitch, frame=frame, white_parts=white_parts, **kwargs)
    layers = {}
    for index, name in enumerate(names):
        layer_mask = mask * (ids == index)
        if layer_mask.any():
            layers[name] = downsample(color, layer_mask)
    return layers
