"""Prepare runtime-sized flight backdrops and aircraft atlases.

The watercolor originals stay untouched. The generated PNGs live beside the
game assets in ``assets/watercolor_prepared`` and are optional at runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from dobramundo import config as C  # noqa: E402

SOURCE = ROOT / "assets" / "watercolor"
OUTPUT = ROOT / "assets" / "watercolor_prepared"
BACKDROPS = tuple(f"{biome}_{stage}" for biome in ("amazonia", "caatinga") for stage in range(3))
PREPARED_SIZES = {name: (C.WIDTH + 32, C.HEIGHT) for name in BACKDROPS}
PLANE_ATLASES = (
    "planes_flight_a",
    "planes_flight_a_clean",
    "planes_flight_b",
    "planes_flight_c",
    "planes_menu_a",
    "planes_menu_b",
    "planes_menu_c",
)
PREPARED_SIZES.update({name: (768, 512) for name in PLANE_ATLASES})
BACKDROP_SIZE = (C.WIDTH + 32, C.HEIGHT)

ATLAS_LAYOUTS = {
    "banks_amazonia": {"grid": [4, 3], "pivot": "cell bottom-center", "use": "river margins"},
    "banks_caatinga": {"grid": [4, 3], "pivot": "cell bottom-center", "use": "desert margins"},
    "fauna_sprint3": {"grid": [3, 2], "pivot": "cell bottom-center", "use": "non-colliding distant fauna"},
    "items_refined": {
        "grid": [4, 2],
        "order": ["paper", "plastic", "metal", "glass", "shield", "magnet", "repair", "blank"],
        "pivot": "cell center",
        "use": "collectibles and power-ups",
    },
    "obstacles_refined": {
        "grid": [3, 2],
        "order": ["industrial low", "industrial gate", "industrial tower", "solar low", "solar gate", "solar tower"],
        "pivot": "bottom-center; gate crop ends at physical beam edge",
        "use": "collision visuals",
    },
    "pilot_base": {
        "grid": [2, 2],
        "row_split": "710/1295 of source height",
        "pivot": "cropped pose origin",
        "use": "customizable pilot",
    },
    "pilot_hair_front": {"grid": [4, 3], "pivot": "fitted to pilot head anchor", "use": "front hair layer"},
    "pilot_hair_back": {"grid": [4, 3], "pivot": "fitted to pilot head anchor", "use": "back hair layer"},
    "pilot_mobility": {"grid": [2, 2], "pivot": "pilot pose origin", "use": "mobility aids"},
    "planes_flight_a": {"grid": [2, 2], "pivot": "plane center", "use": "flight aircraft"},
    "planes_flight_a_clean": {"grid": [2, 2], "pivot": "plane center", "use": "flight aircraft fallback"},
    "planes_flight_b": {"grid": [2, 2], "pivot": "plane center", "use": "flight aircraft"},
    "planes_flight_c": {"grid": [2, 2], "pivot": "plane center", "use": "flight aircraft"},
    "planes_menu_a": {"grid": [2, 2], "pivot": "plane center", "use": "menu aircraft"},
    "planes_menu_b": {"grid": [2, 2], "pivot": "plane center", "use": "menu aircraft"},
    "planes_menu_c": {"grid": [2, 2], "pivot": "plane center", "use": "menu aircraft"},
    "terrain_tiles_v3": {"grid": [2, 2], "pivot": "repeating tile", "use": "ground materials"},
    "terrain_tiles": {"grid": [2, 2], "pivot": "repeating tile", "use": "legacy ground fallback"},
    "village_props": {"grid": [4, 2], "pivot": "cell bottom-center", "use": "community upgrades"},
    "villagers_sprint3": {"grid": [3, 2], "pivot": "cropped cell bottom-center", "use": "village residents"},
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def alpha_bounds(image: pygame.Surface):
    if not image.get_masks()[3]:
        return None
    bounds = image.get_bounding_rect(min_alpha=1)
    return [bounds.x, bounds.y, bounds.width, bounds.height] if bounds.width and bounds.height else None


def prepare_variant(image: pygame.Surface, target_size: tuple[int, int]) -> pygame.Surface:
    """Smoothscale an image to its explicit target size."""
    return pygame.transform.smoothscale(image, target_size)


def build_manifest(generate: bool = True) -> dict:
    if generate:
        OUTPUT.mkdir(parents=True, exist_ok=True)
    records = []
    generation_records = []
    for metadata_path in sorted(SOURCE.glob("generation*.json")):
        generation_records.append({"file": metadata_path.name, "sha256": sha256(metadata_path)})
    for path in sorted(SOURCE.glob("*.png")):
        image = pygame.image.load(str(path))
        record = {
            "file": path.name,
            "sha256": sha256(path),
            "dimensions": list(image.get_size()),
            "source_bytes": path.stat().st_size,
            "alpha_bounds": alpha_bounds(image),
            "atlas": ATLAS_LAYOUTS.get(path.stem),
        }
        if path.stem in PREPARED_SIZES:
            output_path = OUTPUT / path.name
            target = PREPARED_SIZES[path.stem]
            is_backdrop = path.stem in BACKDROPS
            record["runtime_variant"] = {
                "file": f"watercolor_prepared/{path.name}",
                "dimensions": list(target),
                "pivot": None
                if is_backdrop
                else ("atlas cells preserve row-major order; pivot handled by runtime cropper"),
                "use": (
                    "flight backdrop; logical canvas plus 32 px parallax overscan"
                    if is_backdrop
                    else "aircraft atlas; 384×256 px cells, scaled from 768×512 originals"
                ),
            }
            if generate:
                pygame.image.save(prepare_variant(image, target), str(output_path))
            if output_path.is_file():
                record["runtime_variant"]["sha256"] = sha256(output_path)
                record["runtime_variant"]["bytes"] = output_path.stat().st_size
        records.append(record)
    manifest = {
        "schema": 1,
        "generator": "tools/prepare_assets.py",
        "generated_with": f"pygame {pygame.version.ver}",
        "provenance": {
            "credit_file": "assets/watercolor/CREDITOS.txt",
            "generation_metadata": generation_records,
            "method": (
                "project-integrated image generation; local metadata is recorded, but is not a pixel-level source map"
            ),
        },
        "license": "CC BY 4.0 project package; see root LICENSE and assets/watercolor/CREDITOS.txt.",
        "logical_canvas": [C.WIDTH, C.HEIGHT],
        "prepared_sizes": {name: list(size) for name, size in sorted(PREPARED_SIZES.items())},
        "backdrop_target": list(BACKDROP_SIZE),
        "backdrop_method": "pygame.transform.smoothscale; same raster operation as runtime fallback",
        "assets": records,
    }
    if generate:
        payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        (OUTPUT / "asset_catalog.json").write_text(payload, encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="inspect source metadata without changing prepared outputs",
    )
    args = parser.parse_args()
    manifest = build_manifest(generate=not args.manifest_only)
    generated = sum(1 for item in manifest["assets"] if "runtime_variant" in item)
    print(f"Assets cataloged: {len(manifest['assets'])}; prepared runtime variants: {generated}; output: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
