"""Um build que falha não pode reutilizar evidência de sucesso anterior."""

import json
import subprocess
import sys

import pytest

from dobramundo.selftest import _safe_error_detail
from tools import build_desktop


def test_failed_build_invalidates_the_previous_success(tmp_path, monkeypatch):
    monkeypatch.setattr(build_desktop, "ROOT", tmp_path)
    report = tmp_path / "build" / "desktop-selftest" / "self_test.json"
    report.parent.mkdir(parents=True)
    report.write_text('{"status":"ok","run_id":"old"}', encoding="utf-8")

    def fail(command, **kwargs):
        raise subprocess.CalledProcessError(7, command)

    monkeypatch.setattr(build_desktop.subprocess, "run", fail)
    monkeypatch.setattr(build_desktop, "require_linux_egl_runtime", lambda required: None)
    monkeypatch.setattr(sys, "argv", ["build_desktop.py"])
    with pytest.raises(subprocess.CalledProcessError):
        build_desktop.main()
    current = json.loads(report.read_text(encoding="utf-8"))
    assert current["status"] == "failed"
    assert current["exit_code"] == 7
    assert current["run_id"] != "old"


def test_missing_linux_runtime_invalidates_old_success_before_build(tmp_path, monkeypatch):
    monkeypatch.setattr(build_desktop, "ROOT", tmp_path)
    monkeypatch.setattr(build_desktop.sys, "platform", "linux")
    monkeypatch.setattr(sys, "argv", ["build_desktop.py"])
    report = tmp_path / "build" / "desktop-selftest" / "self_test.json"
    report.parent.mkdir(parents=True)
    report.write_text('{"status":"ok","run_id":"old"}', encoding="utf-8")

    def missing(name):
        raise OSError(name)

    monkeypatch.setattr(build_desktop.ctypes, "CDLL", missing)
    with pytest.raises(RuntimeError, match="libegl1"):
        build_desktop.main()
    current = json.loads(report.read_text(encoding="utf-8"))
    assert current["status"] == "failed" and current["run_id"] != "old"


@pytest.mark.parametrize(
    "library",
    [
        r"C:\Users\João Vítor\project\libmediapipe.dll",
        "/home/runner/project/libmediapipe.so",
    ],
)
def test_native_error_preserves_library_without_local_directories(library):
    error = RuntimeError(f"Failed to load '{library}'")
    error.__cause__ = OSError("libEGL.so.1: cannot open shared object file")
    detail = _safe_error_detail(error)
    assert "libmediapipe" in detail and "libEGL.so.1" in detail
    assert not any(value in detail for value in ("Users", "João", "runner", "/home", "project"))
