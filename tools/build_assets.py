"""Gera os sprites low-poly do Dobramundo a partir dos modelos em tools/lowpoly.

Uso:
    python tools/build_assets.py                      # todos os modelos
    python tools/build_assets.py --only AM_Samauma CA_Mandacaru
    python tools/build_assets.py --prefix AM_ --sheet folha.png   # e uma folha de contato
    python tools/build_assets.py --pilot              # camadas do piloto e ancoragem

Requer numpy e Pillow (só para gerar; o jogo usa os PNGs prontos).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from lowpoly import models_amazonia, models_caatinga, models_common  # noqa: E402,F401
from lowpoly.kit import REGISTRY  # noqa: E402
from lowpoly.raster import render  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from stylize import params_for, stylize_image  # noqa: E402

ASSETS = ROOT / "assets"


def contact_sheet(images, path: Path, cell: int = 220) -> None:
    columns = 6
    rows = (len(images) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * cell, rows * (cell + 18)), (210, 214, 206, 255))
    draw = ImageDraw.Draw(sheet)
    for i, (name, image) in enumerate(images):
        thumb = image.copy()
        thumb.thumbnail((cell - 8, cell - 8))
        x, y = (i % columns) * cell, (i // columns) * (cell + 18)
        sheet.alpha_composite(thumb, (x + (cell - thumb.width) // 2, y + cell - thumb.height))
        draw.text((x + 4, y + cell + 2), name, fill=(20, 20, 20, 255))
    sheet.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="*", help="nomes dos modelos")
    parser.add_argument("--prefix", help="só os modelos com este prefixo (AM_, CA_, VL_...)")
    parser.add_argument("--sheet", type=Path, help="grava também uma folha de contato")
    parser.add_argument("--pilot", action="store_true", help="gera as camadas do piloto")
    args = parser.parse_args()
    if args.pilot:
        from lowpoly.pilot import build_pilot

        build_pilot(ASSETS)
        return
    names = sorted(REGISTRY)
    if args.only:
        names = [n for n in names if n in set(args.only)]
    if args.prefix:
        names = [n for n in names if n.startswith(args.prefix)]
    images = []
    for name in names:
        spec = REGISTRY[name]
        start = time.perf_counter()
        image = stylize_image(render(spec.build(), **spec.render), name, **params_for(spec.folder))
        folder = ASSETS / spec.folder
        folder.mkdir(parents=True, exist_ok=True)
        image.save(folder / f"{name}.png", optimize=True)
        images.append((name, image))
        print(f"{name:28s} {image.size[0]:4d}x{image.size[1]:<4d} {time.perf_counter() - start:5.1f}s")
    if args.sheet and images:
        contact_sheet(images, args.sheet)


if __name__ == "__main__":
    main()
