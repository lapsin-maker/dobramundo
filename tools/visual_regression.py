"""Compara PNGs de menus com referência revisada, tolerando pequenas diferenças de raster."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def compare(reference: Path, actual: Path) -> dict:
    with Image.open(reference) as first, Image.open(actual) as second:
        if first.size != second.size:
            return {"ok": False, "reason": "size", "expected": first.size, "actual": second.size}
        difference = ImageChops.difference(first.convert("RGB"), second.convert("RGB"))
        mean = sum(ImageStat.Stat(difference).mean) / 3
        red, green, blue = difference.split()
        worst_channel = ImageChops.lighter(ImageChops.lighter(red, green), blue)
        changed = sum(worst_channel.histogram()[33:]) / (first.width * first.height)
    return {
        "ok": mean <= 1.0 and changed <= 0.01,
        "mean_absolute_channel_error": mean,
        "fraction_pixels_difference_over_32": changed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--actual", type=Path, required=True)
    args = parser.parse_args()
    files = sorted(args.reference.glob("*.png"))
    if not files:
        parser.error("nenhuma referência PNG; não aprovar uma comparação vazia")
    results = {
        path.name: compare(path, args.actual / path.name)
        if (args.actual / path.name).is_file()
        else {"ok": False, "reason": "missing"}
        for path in files
    }
    print(json.dumps(results, indent=2))
    return int(any(not item["ok"] for item in results.values()))


if __name__ == "__main__":
    raise SystemExit(main())
