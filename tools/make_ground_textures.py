"""Gera as texturas de chão da Caatinga (vista de cima, repetíveis sem emenda).

    dry_soil.png  despertar do sertão: solo ocre-avermelhado, capim seco e pedrinhas
    agreste.png   Petrolina solarpunk: solo recuperado, verde da caatinga e flores

Uso: python tools/make_ground_textures.py [--out assets/ground]
Requer numpy e Pillow (o jogo usa os PNGs prontos).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from make_grass_texture import HEIGHT, WIDTH, periodic_noise
from PIL import Image


def blend(base: np.ndarray, color, amount: np.ndarray) -> np.ndarray:
    return base * (1 - amount[..., None]) + np.array(color, dtype=np.float32) * amount[..., None]


def speckle(rgb: np.ndarray, rng: np.random.Generator, colors, count: int, size: int = 2) -> None:
    for _ in range(count):
        y, x = int(rng.integers(0, HEIGHT)), int(rng.integers(0, WIDTH))
        color = np.array(colors[int(rng.integers(0, len(colors)))], dtype=np.float32)
        for dx in range(size):
            rgb[y, (x + dx) % WIDTH] = color


def make_dry_soil(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    shape = (HEIGHT, WIDTH)
    broad, mid, fine = (periodic_noise(rng, shape, s) for s in (20.0, 7.0, 1.3))
    mix = np.clip(0.5 * broad + 0.3 * mid + 0.2 * fine, 0, 1)
    rgb = blend(np.full(shape + (3,), (150, 96, 58), np.float32), (196, 142, 88), mix)
    grass = np.clip((mid - 0.55) / 0.3, 0, 1) * 0.55  # capim seco em tufos
    rgb = blend(rgb, (168, 160, 92), grass)
    speckle(rgb, rng, [(120, 112, 100), (210, 196, 170), (98, 70, 46)], 120)  # pedrinhas
    speckle(rgb, rng, [(110, 140, 70)], 25, 2)  # brotos verdes do despertar
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def make_agreste(seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    shape = (HEIGHT, WIDTH)
    broad, mid, fine = (periodic_noise(rng, shape, s) for s in (18.0, 6.0, 1.2))
    mix = np.clip(0.45 * broad + 0.35 * mid + 0.2 * fine, 0, 1)
    rgb = blend(np.full(shape + (3,), (92, 132, 62), np.float32), (150, 170, 84), mix)
    soil = np.clip((broad - 0.68) / 0.25, 0, 1) * 0.6  # manchas de solo ocre
    rgb = blend(rgb, (178, 130, 80), soil)
    speckle(rgb, rng, [(250, 214, 80), (240, 240, 230), (232, 120, 150)], 80)  # flores da caatinga
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parents[1] / "assets" / "ground")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    make_dry_soil(11).save(args.out / "dry_soil.png", optimize=True)
    make_agreste(12).save(args.out / "agreste.png", optimize=True)
    print("texturas:", args.out / "dry_soil.png", args.out / "agreste.png")


if __name__ == "__main__":
    main()
