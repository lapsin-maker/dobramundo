"""Prepara a logo do Dobramundo (aquarela sobre fundo branco) para o jogo.

Gera, a partir da arte original:
    assets/ui/logo.png    logo com fundo transparente (o branco vira alfa)
    assets/ui/icone.png   ícone quadrado (aviãozinho de papel da logo) para a janela
    assets/icon.ico       ícone do executável do Windows (16 a 256 px)

O branco do papel é removido "desmisturando" cada pixel do branco: para uma
aquarela sobre papel, cor = alfa * tinta + (1 - alfa) * branco.

Uso: python tools/make_logo.py CAMINHO_DA_ARTE [--out assets]
Requer: numpy, Pillow (só para gerar; o jogo não precisa).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

LOGO_WIDTH = 900
ICON_BOX = (0.755, 0.04, 0.985, 0.30)  # recorte do avião de papel (frações da arte)


def unblend_white(image: Image.Image, floor: float = 0.06) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    alpha = 1.0 - rgb.min(axis=2)  # quanto o pixel se afasta do branco
    alpha = np.clip((alpha - floor) / (1.0 - floor), 0.0, 1.0)
    safe = np.maximum(alpha, 1e-4)[..., None]
    paint = np.clip((rgb - (1.0 - safe)) / safe, 0.0, 1.0)
    rgba = np.dstack([paint * 255.0, alpha * 255.0]).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def convex_hull(points: np.ndarray) -> list:
    """Envoltória convexa (cadeia monótona) de pontos (x, y)."""
    pts = sorted(set(map(tuple, points.tolist())))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def solidify_plane(rgba: Image.Image, box) -> Image.Image:
    """O avião de papel é creme, quase branco: dentro do contorno dele o alfa fica cheio."""
    from PIL import ImageDraw

    x0, y0, x1, y1 = box
    region = np.asarray(rgba.crop(box))
    ys, xs = np.nonzero(region[..., 3] > 90)
    # Só a ponta do avião (metade direita do recorte): o rastro de tinta continua translúcido.
    keep = xs > region.shape[1] * 0.42
    hull = convex_hull(np.stack([xs[keep] + x0, ys[keep] + y0], axis=1))
    mask = Image.new("L", rgba.size, 0)
    if len(hull) >= 3:
        ImageDraw.Draw(mask).polygon(hull, fill=255)
    alpha = np.maximum(np.asarray(rgba.getchannel("A")), np.asarray(mask))
    art = np.asarray(rgba).copy()
    art[..., 3] = alpha
    return Image.fromarray(art, "RGBA")


def trim(image: Image.Image, pad: int = 8) -> Image.Image:
    box = image.getchannel("A").point(lambda a: 255 if a > 12 else 0).getbbox()
    if box is None:
        return image
    x0, y0, x1, y1 = box
    return image.crop((max(0, x0 - pad), max(0, y0 - pad), min(image.width, x1 + pad), min(image.height, y1 + pad)))


def square(image: Image.Image, size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    scale = size / max(image.size)
    fitted = image.resize((max(1, int(image.width * scale)), max(1, int(image.height * scale))), Image.LANCZOS)
    canvas.paste(fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2), fitted)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "assets")
    args = parser.parse_args()
    art = Image.open(args.source).convert("RGB")
    w, h = art.size
    box = (int(ICON_BOX[0] * w), int(ICON_BOX[1] * h), int(ICON_BOX[2] * w), int(ICON_BOX[3] * h))
    clean = solidify_plane(unblend_white(art), box)
    # Onde o alfa foi preenchido, a cor volta a ser a do papel original (não a "desmisturada").
    original = np.asarray(art.convert("RGBA")).copy()
    merged = np.asarray(clean).copy()
    filled = np.asarray(clean)[..., 3] > np.asarray(unblend_white(art))[..., 3]
    merged[filled, :3] = original[filled, :3]
    clean = Image.fromarray(merged, "RGBA")
    logo = trim(clean)
    ratio = LOGO_WIDTH / logo.width
    logo = logo.resize((LOGO_WIDTH, int(logo.height * ratio)), Image.LANCZOS)
    (args.out / "ui").mkdir(parents=True, exist_ok=True)
    logo.save(args.out / "ui" / "logo.png", optimize=True)
    plane = trim(clean.crop(box), 4)
    icon = square(plane, 256)
    backdrop = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    from PIL import ImageDraw

    ImageDraw.Draw(backdrop).ellipse((4, 4, 252, 252), fill=(27, 58, 138, 255))
    backdrop.alpha_composite(square(plane, 210), (23, 23))
    backdrop.save(args.out / "ui" / "icone.png", optimize=True)
    backdrop.save(
        args.out / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    print("logo", logo.size, "icone", icon.size)


if __name__ == "__main__":
    main()
