"""Confere as medidas de colisão dos obstáculos contra os próprios sprites (alfa).

Para cada obstáculo dos biomas, converte pixels em unidades do mundo pela altura
visual (visual_height) e mostra, ao lado do valor usado no jogo:
    low   -> topo sólido (o avião passa por cima acima disso)
    gate  -> vão livre no centro (o avião passa por baixo abaixo disso)
    tower -> largura sólida na faixa de voo (desvie para o lado)

Uso: python tools/measure_obstacles.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dobramundo import config as C  # noqa: E402
from dobramundo.content.biomes import BIOMES  # noqa: E402
from dobramundo.engine.assets import SCENERY_FOLDERS  # noqa: E402


def alpha(name: str):
    for folder in SCENERY_FOLDERS:
        path = ROOT / "assets" / folder / f"{name}.png"
        if path.is_file():
            return np.asarray(Image.open(path).convert("RGBA"))[..., 3] > 60
    return None


def measure(spec) -> str:
    mask = alpha(spec.sprite)
    if mask is None:
        return "sem sprite"
    h, w = mask.shape
    unit = spec.visual_height / h  # mundo por pixel
    rows = np.nonzero(mask.any(axis=1))[0]
    if spec.kind == "low":
        top = (h - rows.min()) * unit
        return f"topo {top:6.1f}  (jogo {spec.y_max:.0f})"
    if spec.kind == "gate":
        column = mask[:, w // 2 - 3 : w // 2 + 3].any(axis=1)
        solid = np.nonzero(column)[0]
        clearance = (h - solid.max()) * unit if len(solid) else 0.0
        bottom_solid = [y for y in solid if y > h * 0.4]
        free = (h - max(bottom_solid)) * unit if bottom_solid else spec.visual_height
        return f"vão {free:6.1f}  (jogo {spec.y_min:.0f})  [coluna central sólida até {clearance:.0f}]"
    band = [int(h - y / unit) for y in (C.MIN_ALTITUDE, C.MAX_ALTITUDE) if 0 < h - y / unit < h]
    lo, hi = (min(band), max(band)) if len(band) == 2 else (0, h)
    cols = np.nonzero(mask[lo:hi].any(axis=0))[0]
    width = (cols.max() - cols.min() + 1) * unit if len(cols) else 0.0
    return f"largura {width:6.1f}  (jogo {spec.width:.0f})"


def main() -> None:
    for biome in BIOMES.values():
        for stage, table in (("industrial", biome.industrial_obstacles), ("solar", biome.solar_obstacles)):
            for kind, specs in table.items():
                for spec in specs:
                    print(f"{biome.key:9s} {stage:10s} {kind:5s} {spec.sprite:26s} {measure(spec)}")


if __name__ == "__main__":
    main()
