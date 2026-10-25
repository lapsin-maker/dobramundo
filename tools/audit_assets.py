"""Verify original asset hashes and prepared runtime images against the manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "assets"
MANIFEST = ASSET_ROOT / "watercolor_prepared" / "asset_catalog.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit(manifest_path: Path = MANIFEST) -> list[str]:
    import pygame

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    provenance = manifest.get("provenance", {})
    for source_record in provenance.get("generation_metadata", []):
        metadata = ASSET_ROOT / "watercolor" / source_record["file"]
        if not metadata.is_file() or sha256(metadata) != source_record["sha256"]:
            errors.append(f"metadado de geração ausente ou hash divergente: {source_record['file']}")
    for record in manifest.get("assets", []):
        source = ASSET_ROOT / "watercolor" / record["file"]
        if not source.is_file() or sha256(source) != record["sha256"]:
            errors.append(f"original ausente ou hash divergente: {record['file']}")
            continue
        source_image = pygame.image.load(str(source))
        if list(source_image.get_size()) != record["dimensions"]:
            errors.append(f"dimensão original divergente: {record['file']}")
        variant = record.get("runtime_variant")
        if variant:
            prepared = ASSET_ROOT / variant["file"]
            if not prepared.is_file() or sha256(prepared) != variant.get("sha256"):
                errors.append(f"variante ausente ou hash divergente: {variant['file']}")
                continue
            if list(pygame.image.load(str(prepared)).get_size()) != variant["dimensions"]:
                errors.append(f"dimensão da variante divergente: {variant['file']}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    errors = audit(args.manifest)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    variants = sum("runtime_variant" in asset for asset in data.get("assets", []))
    print(f"OK: {len(data.get('assets', []))} originals and {variants} prepared variants verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
