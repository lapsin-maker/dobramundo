"""Estilo "papel e aquarela" aplicado aos sprites: sombreamento em degraus, traço
de tinta no contorno e nas quebras de forma, e grão de papel.

A logo do Dobramundo é aquarela sobre papel; os sprites vinham de kits low-poly
com sombreamento contínuo e sem contorno, cada um com uma cara. Este filtro dá a
todos a mesma linguagem, sem remodelar nada:

- cel shading: o valor (claridade) de cada pixel é empurrado para 5 degraus,
  mantendo a cor; a saturação sobe um pouco (tinta mais viva);
- tinta: contorno de 2 px na cor da "tinta" (azul-marinho da logo) misturada com
  a cor do próprio pixel, e um escurecimento nas quebras internas de claridade;
- papel: grão suave multiplicado por cima (duas frequências), determinístico.

Uso:
    python tools/stylize.py                   # todas as pastas de sprites
    python tools/stylize.py --folders biome_sprites waste_sprites
    python tools/stylize.py --preview saida.png --only AM_Samauma CA_Mandacaru

Os PNGs são sobrescritos no lugar (o git guarda os originais). O build de assets
(tools/build_assets.py) chama ``stylize_image`` em cada sprite gerado.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
INK = (16, 36, 88)  # azul-marinho da tinta
FOLDERS = (
    "biome_sprites",
    "era_final_sprites",
    "dieselpunk_sprites",
    "scenario_sprites",
    "skyline_sprites",
    "waste_sprites",
    "powerup_sprites",
    "plane_sprites",
    "plane_menu",
)
# Aviões: papel branco; traço mais fino e cinza-azulado, para não "sujar" o papel.
LIGHT_INK_FOLDERS = ("plane_sprites", "plane_menu")


def rgb_to_hsv(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(axis=-1), rgb.min(axis=-1)
    delta = mx - mn
    h = np.zeros_like(mx)
    nz = delta > 1e-6
    rc = np.where(nz, (mx - r) / np.maximum(delta, 1e-6), 0)
    gc = np.where(nz, (mx - g) / np.maximum(delta, 1e-6), 0)
    bc = np.where(nz, (mx - b) / np.maximum(delta, 1e-6), 0)
    h = np.where(mx == r, bc - gc, np.where(mx == g, 2.0 + rc - bc, 4.0 + gc - rc))
    h = np.where(nz, (h / 6.0) % 1.0, 0.0)
    s = np.where(mx > 1e-6, delta / np.maximum(mx, 1e-6), 0.0)
    return h, s, mx


def hsv_to_rgb(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    i = np.floor(h * 6.0).astype(int) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    table = [(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]
    out = np.zeros(h.shape + (3,), dtype=np.float32)
    for k, (rr, gg, bb) in enumerate(table):
        m = i == k
        out[m] = np.stack([rr[m], gg[m], bb[m]], axis=-1)
    return out


def paper_grain(shape: Tuple[int, int], seed: str, strength: float) -> np.ndarray:
    """Grão de papel: ruído fino mais manchas largas, entre 1 - strength e 1."""
    rng = np.random.default_rng(int(hashlib.md5(seed.encode()).hexdigest()[:8], 16))
    h, w = shape
    fine = rng.random((h, w), dtype=np.float32)
    coarse = rng.random((max(1, h // 12), max(1, w // 12)), dtype=np.float32)
    coarse = np.asarray(Image.fromarray((coarse * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)) / 255.0
    noise = 0.55 * fine + 0.45 * coarse
    return 1.0 - strength * noise


def stylize_image(
    image: Image.Image,
    seed: str = "",
    levels: int = 5,
    posterize: float = 0.65,
    saturation: float = 1.12,
    ink=INK,
    ink_mix: float = 0.6,
    outline: int = 2,
    grain: float = 0.08,
) -> Image.Image:
    """Aplica o estilo a um sprite RGBA e devolve outro RGBA do mesmo tamanho."""
    rgba = np.asarray(image.convert("RGBA"), dtype=np.float32) / 255.0
    rgb, alpha = rgba[..., :3], rgba[..., 3]
    h, s, v = rgb_to_hsv(rgb)
    # 1) degraus de claridade (suaves: mistura do valor quantizado com o original)
    stepped = np.round(v * (levels - 1)) / (levels - 1)
    v2 = np.clip(v * (1 - posterize) + stepped * posterize, 0.0, 1.0)
    s2 = np.clip(s * saturation, 0.0, 1.0)
    out = hsv_to_rgb(h, s2, v2)
    # 2) traço nas quebras internas: onde a claridade muda muito entre vizinhos
    pad = np.pad(v2, 1, mode="edge")
    gx = np.abs(pad[1:-1, 2:] - pad[1:-1, :-2])
    gy = np.abs(pad[2:, 1:-1] - pad[:-2, 1:-1])
    edges = np.clip((np.maximum(gx, gy) - 0.18) * 3.0, 0.0, 1.0) * (alpha > 0.5)
    out = out * (1.0 - 0.35 * edges[..., None])
    # 3) contorno externo: pixels transparentes vizinhos de pixels opacos viram tinta
    mask = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    grown = np.asarray(mask.filter(ImageFilter.MaxFilter(2 * outline + 1)), dtype=np.float32) / 255.0
    rim = np.clip(grown - alpha, 0.0, 1.0)
    ink_rgb = np.array(ink, dtype=np.float32) / 255.0
    # a cor da tinta puxa um pouco a cor do pixel opaco mais próximo (contorno "pintado")
    blurred = np.asarray(image.convert("RGBA").filter(ImageFilter.GaussianBlur(outline)), dtype=np.float32) / 255.0
    local = blurred[..., :3] * 0.45
    rim_color = ink_rgb * ink_mix + local * (1 - ink_mix)
    out = np.where(rim[..., None] > 0, rim_color, out)
    alpha_out = np.clip(alpha + rim * 0.92, 0.0, 1.0)
    # bordas do próprio desenho também recebem um pouco de tinta (linha de 1 px por dentro)
    inner = np.asarray(mask.filter(ImageFilter.MinFilter(3)), dtype=np.float32) / 255.0
    inner_rim = np.clip(alpha - inner, 0.0, 1.0) * (alpha > 0.5)
    out = out * (1.0 - 0.45 * inner_rim[..., None]) + ink_rgb * (0.45 * inner_rim[..., None])
    # 4) grão de papel
    out = out * paper_grain(alpha.shape, seed, grain)[..., None]
    result = np.dstack([np.clip(out, 0, 1) * 255, alpha_out * 255]).astype(np.uint8)
    return Image.fromarray(result, "RGBA")


def params_for(folder: str) -> dict:
    if folder in LIGHT_INK_FOLDERS:
        return {"ink": (70, 86, 120), "ink_mix": 0.5, "outline": 1, "posterize": 0.35, "grain": 0.05, "saturation": 1.0}
    if folder == "skyline_sprites":
        return {"outline": 1, "posterize": 0.5, "grain": 0.05}
    return {}


def files_in(folders: Iterable[str], only: Iterable[str] = ()) -> List[Tuple[str, Path]]:
    wanted = set(only)
    out = []
    for folder in folders:
        for path in sorted((ASSETS / folder).glob("*.png")):
            if not wanted or path.stem in wanted:
                out.append((folder, path))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--folders", nargs="*", default=list(FOLDERS))
    parser.add_argument("--only", nargs="*", default=())
    parser.add_argument("--preview", type=Path, help="não sobrescreve: grava antes/depois nesta imagem")
    args = parser.parse_args()
    files = files_in(args.folders, args.only)
    if args.preview:
        pairs = []
        for folder, path in files[:12]:
            before = Image.open(path).convert("RGBA")
            pairs.append((before, stylize_image(before, path.stem, **params_for(folder))))
        cell = 220
        sheet = Image.new("RGBA", (cell * 2 + 30, (cell + 10) * len(pairs) + 10), (235, 232, 224, 255))
        for i, (a, b) in enumerate(pairs):
            for j, im in enumerate((a, b)):
                thumb = im.copy()
                thumb.thumbnail((cell, cell))
                sheet.alpha_composite(thumb, (10 + j * (cell + 10), 10 + i * (cell + 10)))
        sheet.save(args.preview)
        print(f"prévia em {args.preview}")
        return 0
    for folder, path in files:
        image = Image.open(path).convert("RGBA")
        stylize_image(image, path.stem, **params_for(folder)).save(path, optimize=True)
        print(f"{folder}/{path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
