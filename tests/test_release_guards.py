"""A montagem não deve distribuir builds reprovados nem perder mudanças visuais."""

import json
import subprocess
import tarfile
import zipfile

import pytest
from PIL import Image

from dobramundo import __version__
from dobramundo.selftest import REQUIRED_SPRITES, check_report
from tools.package_release import (
    assert_clean_checkout,
    assert_tracked_inputs,
    github_run_id,
    portable_sources,
    validate_cartridge_sources,
    validate_tar,
    verified_build,
    write_batch,
)
from tools.visual_regression import compare


def test_build_guard_requires_native_detector(tmp_path):
    path = tmp_path / "self_test.json"
    path.write_text(json.dumps({"status": "ok", "camera": {"detector": "unavailable"}}))
    with pytest.raises(ValueError, match="detector"):
        verified_build(tmp_path)


def _successful_build_report(**overrides):
    report = {
        "status": "ok",
        "versao": __version__,
        "run_id": "local-build-123",
        "build_commit": "a" * 40,
        "github_sha": "a" * 40,
        "github_run_id": "12345",
        "github_run_attempt": "2",
        "camera": {"detector": "ok"},
    }
    report.update(overrides)
    return report


def test_build_guard_binds_version_commit_and_ci_run(tmp_path):
    path = tmp_path / "self_test.json"
    path.write_text(json.dumps(_successful_build_report()), encoding="utf-8")
    assert verified_build(tmp_path, "a" * 40, "12345")["run_id"] == "local-build-123"

    for report, expected_commit, expected_run, message in (
        (_successful_build_report(versao="0.0.0"), "a" * 40, "12345", "versão"),
        (_successful_build_report(), "b" * 40, "12345", "commit"),
        (_successful_build_report(), "a" * 40, "54321", "execução de CI"),
    ):
        path.write_text(json.dumps(report), encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            verified_build(tmp_path, expected_commit, expected_run)

    path.write_text(json.dumps(_successful_build_report()), encoding="utf-8")
    with pytest.raises(ValueError, match="tentativa de CI"):
        verified_build(tmp_path, "a" * 40, "12345", "1")


def test_ci_run_id_accepts_actions_metadata_or_url():
    assert github_run_id({"databaseId": 123, "url": "https://github.com/o/r/actions/runs/456"}) == "123"
    assert github_run_id({"url": "https://github.com/o/r/actions/runs/456"}) == "456"
    assert github_run_id({"url": "https://example.test/run/456"}) is None


def test_ci_run_attempt_aliases():
    from tools.package_release import github_run_attempt

    assert github_run_attempt({"runAttempt": 2}) == "2"
    assert github_run_attempt({"run_attempt": 3}) == "3"


def test_portable_source_inventory_matches_cartridge_exclusions(tmp_path):
    package = tmp_path / "dobramundo"
    (package / "input").mkdir(parents=True)
    portable = package / "engine.py"
    desktop = package / "app.py"
    camera = package / "input" / "camera.py"
    for path in (portable, desktop, camera):
        path.write_text("# module\n", encoding="utf-8")

    sources = portable_sources(tmp_path)
    assert set(sources) == {"dobramundo/engine.py"}

    cartridge = tmp_path / "cartucho.ttea"
    with zipfile.ZipFile(cartridge, "w") as archive:
        archive.write(portable, "dobramundo/engine.py")
    with zipfile.ZipFile(cartridge) as archive:
        validate_cartridge_sources(archive, tmp_path)

    with zipfile.ZipFile(cartridge, "a") as archive:
        archive.write(desktop, "dobramundo/app.py")
    with zipfile.ZipFile(cartridge) as archive:
        with pytest.raises(ValueError, match="Fontes portáteis"):
            validate_cartridge_sources(archive, tmp_path)


def test_batch_launcher_always_uses_crlf(tmp_path):
    path = tmp_path / "launcher.bat"
    write_batch(path, "@echo off\nstart game.exe\n")
    data = path.read_bytes()
    assert data == b"@echo off\r\nstart game.exe\r\n"


def test_release_clean_guard_rejects_untracked_files_and_inventory(tmp_path):
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    tracked = tmp_path / "source.py"
    tracked.write_text("# tracked\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "source.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "initial",
        ],
        check=True,
        capture_output=True,
    )
    assert_clean_checkout(tmp_path)

    assert_tracked_inputs([tracked], root=tmp_path)
    ignored_or_untracked = tmp_path / "dobramundo" / "extra.py"
    ignored_or_untracked.parent.mkdir()
    ignored_or_untracked.write_text("# untracked\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fora do commit"):
        assert_clean_checkout(tmp_path)
    with pytest.raises(ValueError, match="não rastreadas"):
        assert_tracked_inputs([ignored_or_untracked], root=tmp_path)


def test_source_inventory_rejects_duplicate_zip_members(tmp_path):
    package = tmp_path / "dobramundo"
    package.mkdir()
    source = package / "module.py"
    source.write_text("# module\n", encoding="utf-8")
    cartridge = tmp_path / "cartucho.ttea"
    with zipfile.ZipFile(cartridge, "w") as archive:
        archive.write(source, "dobramundo/module.py")
        archive.write(source, "dobramundo/module.py")
    with zipfile.ZipFile(cartridge) as archive:
        with pytest.raises(ValueError, match="duplicados"):
            validate_cartridge_sources(archive, tmp_path)


def test_selftest_does_not_pass_a_flight_stuck_in_preparation():
    report = {
        "sprites": {name: 1 for name in REQUIRED_SPRITES},
        "voos": {"amazonia": {"estagio": 2, "segundos_ativos": 0, "distancia": 0}},
        "camera": {"detector": "ok"},
    }
    assert check_report(report, True) == ["o voo em amazonia não avançou após o preparo"]


def test_visual_comparison_catches_loss_of_a_button(tmp_path):
    a, b = tmp_path / "reference.png", tmp_path / "actual.png"
    image = Image.new("RGB", (100, 100), "white")
    image.paste("blue", (10, 10, 70, 40))
    image.save(a)
    image.save(b)
    assert compare(a, b)["ok"]
    Image.new("RGB", (100, 100), "white").save(b)
    assert not compare(a, b)["ok"]


@pytest.mark.parametrize("link,ok", [("../lib.so", True), ("../../../outside", False), ("/tmp/outside", False)])
def test_linux_links_stay_inside_package(tmp_path, link, ok):
    path = tmp_path / "linux.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        executable = tarfile.TarInfo("Dobramundo/Dobramundo")
        executable.mode = 0o755
        archive.addfile(executable)
        shared = tarfile.TarInfo("Dobramundo/_internal/module/lib.so")
        shared.type = tarfile.SYMTYPE
        shared.linkname = link
        archive.addfile(shared)
    if ok:
        validate_tar(path)
    else:
        with pytest.raises(ValueError, match="Link inseguro"):
            validate_tar(path)
