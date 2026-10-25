"""O pacote inclui uma única cópia de runtime e mantém fallback se faltar preparo."""

import hashlib
import json
from pathlib import Path

import pytest

from tools.runtime_assets import runtime_assets


def _fixture(tmp_path):
    original = tmp_path / "assets/watercolor/amazonia_0.png"
    prepared = tmp_path / "assets/watercolor_prepared/amazonia_0.png"
    original.parent.mkdir(parents=True)
    prepared.parent.mkdir(parents=True)
    original.write_bytes(b"source")
    prepared.write_bytes(b"runtime")
    catalog = prepared.with_name("asset_catalog.json")
    catalog.write_text(
        json.dumps(
            {
                "assets": [
                    {
                        "file": original.name,
                        "runtime_variant": {
                            "file": "watercolor_prepared/amazonia_0.png",
                            "sha256": hashlib.sha256(b"runtime").hexdigest(),
                        },
                    }
                ]
            }
        )
    )
    return original, prepared


def test_inventory_uses_one_variant_and_preserves_source(tmp_path):
    original, prepared = _fixture(tmp_path)
    items = list(runtime_assets(tmp_path))
    assert (prepared, Path("watercolor_prepared/amazonia_0.png")) in items
    assert all(source != original for source, _ in items)
    assert original.read_bytes() == b"source"


def test_missing_prepared_asset_keeps_original(tmp_path):
    original, prepared = _fixture(tmp_path)
    prepared.unlink()
    assert (original, Path("watercolor/amazonia_0.png")) in list(runtime_assets(tmp_path))


def test_invalid_variant_refuses_packaging(tmp_path):
    _, prepared = _fixture(tmp_path)
    prepared.write_bytes(b"changed")
    with pytest.raises(ValueError, match="divergente"):
        list(runtime_assets(tmp_path))


def test_console_excludes_model_but_keeps_licenses(tmp_path):
    _fixture(tmp_path)
    model = tmp_path / "assets/pose_model/pose.task"
    model.parent.mkdir()
    model.write_bytes(b"model")
    license_file = tmp_path / "assets/watercolor/CREDITOS.txt"
    license_file.write_text("credit")
    files = list(runtime_assets(tmp_path, console=True))
    assert all(source != model for source, _ in files)
    assert any(source == license_file for source, _ in files)
