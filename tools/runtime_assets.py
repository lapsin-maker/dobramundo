"""Inventário único dos pacotes: fontes de edição permanecem no Git.

Prepara PNG em resolução de uso; nunca remove uma fonte do repositório.
Se uma variante não está disponível, inclui seu original como fallback.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator, Tuple

ASSET_EXTS = {".png", ".json", ".ogg", ".wav", ".task", ".ico", ".ttf", ".txt"}
SPECIAL_PREPARED = {f"{biome}_{stage}.png" for biome in ("amazonia", "caatinga") for stage in range(3)}
SPECIAL_PREPARED.update(f"planes_{view}_{group}.png" for view in ("flight", "menu") for group in "abc")
SPECIAL_PREPARED.add("planes_flight_a_clean.png")
SUPERSEDED = {
    "terrain_tiles.png": "terrain_tiles_v3.png",
    "village_start.png": "village_industrial_v3.png",
    "village_start_v2.png": "village_industrial_v3.png",
    "village_intermediate.png": "village_transition_v3.png",
    "village_clean.png": "village_final.png",
}


def runtime_assets(root: Path, console: bool = False) -> Iterator[Tuple[Path, Path]]:
    """(fonte, caminho relativo a assets) sem originais redundantes."""
    assets = root / "assets"
    catalog = assets / "watercolor_prepared" / "asset_catalog.json"
    variants = {}
    if catalog.is_file():
        for record in json.loads(catalog.read_text(encoding="utf-8"))["assets"]:
            variant = record.get("runtime_variant", {})
            path = assets / variant.get("file", "missing")
            if path.is_file():
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if digest != variant.get("sha256"):
                    raise ValueError(f"Variante preparada divergente: {path.name}; execute prepare_assets.py")
                variants[record["file"]] = path
    emitted = set()
    for file in sorted(assets.rglob("*")):
        if not file.is_file() or file.suffix.lower() not in ASSET_EXTS:
            continue
        relative = file.relative_to(assets)
        if console and (relative.parts[0] == "pose_model" or file.suffix in (".task", ".tflite")):
            continue
        if relative.parts[0] == "watercolor_prepared" and file.suffix == ".png":
            continue  # emitido pelo registro da fonte, abaixo
        if relative.parts[0] == "watercolor" and file.suffix == ".png":
            replacement = SUPERSEDED.get(file.name)
            if replacement and (assets / "watercolor" / replacement).is_file():
                continue
            if file.name in variants:
                file = variants[file.name]
                if file.name in SPECIAL_PREPARED:
                    relative = Path("watercolor_prepared") / file.name
        if relative in emitted:
            raise ValueError(f"Destino repetido no pacote: {relative}")
        emitted.add(relative)
        yield file, relative


def inventory(root: Path, console: bool = False) -> dict:
    records = [
        {
            "path": relative.as_posix(),
            "bytes": source.stat().st_size,
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        }
        for source, relative in runtime_assets(root, console)
    ]
    return {"schema": 1, "console": console, "total_bytes": sum(item["bytes"] for item in records), "files": records}
