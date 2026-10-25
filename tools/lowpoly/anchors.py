"""Onde o piloto senta em cada avião: medido nos sprites antigos com e sem boneco.

Para cada vista (voo e menu) e cada avião, compara o sprite "__riding" (com o
boneco montado do estúdio 3D) com o "__none" (sem piloto): alinha os dois
verticalmente e pega a caixa dos pixels que mudaram (cor ou transparência).
Essa caixa, nas coordenadas do sprite sem piloto, é onde o piloto novo entra.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image, ImageFilter

PLANES = [
    "dart",
    "glider",
    "stubby",
    "binder",
    "needle",
    "hoverboard",
    "crane",
    "accordion",
    "jetfighter",
    "tailboom",
    "bis14",
]
VIEWS = {"flight": "plane_sprites", "menu": "plane_menu"}


def load(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("RGBA")).astype(np.int32)


def changed(none: np.ndarray, riding: np.ndarray, shift: int) -> np.ndarray:
    h, w = none.shape[:2]
    sub = riding[shift : shift + h, :w]
    alpha_n, alpha_r = none[..., 3] > 40, sub[..., 3] > 40
    color = np.abs(sub[..., :3] - none[..., :3]).sum(axis=2) > 90
    return (alpha_r & ~alpha_n) | (alpha_r & alpha_n & color)


def measure(assets: Path, plane: str, folder: str) -> List[int]:
    none = load(assets / folder / f"{plane}__none.png")
    riding = load(assets / folder / f"{plane}__riding.png")
    extra = riding.shape[0] - none.shape[0]
    best_shift, best_score = 0, None
    for shift in range(0, max(0, extra) + 1):
        score = changed(none, riding, shift).sum()
        if best_score is None or score < best_score:
            best_shift, best_score = shift, score
    diff = changed(none, riding, best_shift)
    full = np.zeros(riding.shape[:2], dtype=bool)
    full[best_shift : best_shift + none.shape[0], : none.shape[1]] = diff
    # pixels acima do sprite sem piloto (cabeça que passa do topo)
    if best_shift > 0:
        full[:best_shift] = riding[:best_shift, ..., 3] > 40
    # abertura morfológica: some o contorno serrilhado, fica o corpo do boneco
    image = Image.fromarray((full * 255).astype(np.uint8), "L")
    image = image.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    box = image.getbbox()
    if box is None:
        return [0, 0, 0, 0]
    x0, y0, x1, y1 = box
    return [int(x0), int(y0 - best_shift), int(x1), int(y1 - best_shift)]


def measure_all(assets: Path) -> Dict[str, Dict[str, List[int]]]:
    return {view: {plane: measure(assets, plane, folder) for plane in PLANES} for view, folder in VIEWS.items()}
