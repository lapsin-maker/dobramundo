"""A montagem não deve distribuir builds reprovados nem perder mudanças visuais."""

import json
import tarfile

import pytest
from PIL import Image

from dobramundo.selftest import REQUIRED_SPRITES, check_report
from tools.package_release import validate_tar, verified_build
from tools.visual_regression import compare


def test_build_guard_requires_native_detector(tmp_path):
    path = tmp_path / "self_test.json"
    path.write_text(json.dumps({"status": "ok", "camera": {"detector": "unavailable"}}))
    with pytest.raises(ValueError, match="detector"):
        verified_build(tmp_path)


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
