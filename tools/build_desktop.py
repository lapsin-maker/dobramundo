"""Build nativo com self-test isolado; não remove dist/, saves ou outras entregas.

Instale requirements-webcam.txt + pyinstaller com constraints-build.txt antes.
O executável é gerado em dist/Dobramundo; Python 3.12 no sistema de destino.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_linux_egl_runtime(require_camera: bool) -> None:
    """Confere as bibliotecas gráficas de sistema usadas pelo MediaPipe no Linux."""
    if not require_camera or not sys.platform.startswith("linux"):
        return
    requirements = (
        ("libEGL.so.1", "libegl1"),
        ("libGLESv2.so.2", "libgles2"),
    )
    for library, package in requirements:
        try:
            ctypes.CDLL(library)
        except OSError as exc:
            raise RuntimeError(
                f"O detector MediaPipe no Linux requer {library}; instale o pacote de sistema {package} "
                "(Debian/Ubuntu) antes do build e da execução."
            ) from exc


def build(onefile: bool = False, require_camera: bool = True) -> Path:
    reports = ROOT / "build" / "desktop-selftest"
    reports.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    git_root = ROOT if (ROOT / ".git").exists() else Path(__file__).resolve().parents[1]
    build_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=git_root, text=True).strip()
    github_sha = os.environ.get("GITHUB_SHA")
    ci_run_id = os.environ.get("GITHUB_RUN_ID")
    ci_attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
    provenance = {
        "build_commit": build_commit,
        "github_sha": github_sha,
        "github_run_id": ci_run_id,
        "github_run_attempt": ci_attempt,
    }
    (reports / "self_test.json").write_text(
        json.dumps({"status": "building", "run_id": run_id, **provenance}) + "\n",
        encoding="utf-8",
    )
    if github_sha and github_sha != build_commit:
        raise RuntimeError("GITHUB_SHA difere do checkout usado para gerar o executável")
    require_linux_egl_runtime(require_camera)
    env = dict(os.environ, DOBRA_ONEFILE="1" if onefile else "0")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--workpath",
            str(ROOT / "build" / "pyinstaller"),
            "--distpath",
            str(ROOT / "dist"),
            str(ROOT / "Dobramundo.spec"),
        ],
        cwd=ROOT,
        env=env,
        check=True,
    )
    folder = ROOT / "dist" if onefile else ROOT / "dist" / "Dobramundo"
    executable = folder / ("Dobramundo.exe" if sys.platform == "win32" else "Dobramundo")
    if not executable.is_file():
        raise RuntimeError("Executável ausente após PyInstaller")
    for name in ("README.md", "LICENSE"):
        shutil.copy2(ROOT / name, folder / name)
    # Cada execução usa uma pasta nova; não pode confundir relatório antigo com sucesso.
    import tempfile

    with tempfile.TemporaryDirectory(prefix="run-", dir=str(reports)) as temporary:
        env.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="dummy", DOBRAMUNDO_DATA_DIR=temporary)
        command = [str(executable), "--self-test", "1200"]
        if require_camera:
            command.append("--exigir-camera")
        completed = subprocess.run(command, cwd=folder, env=env, check=False, timeout=180)
        report = Path(temporary) / "self_test.json"
        data = json.loads(report.read_text(encoding="utf-8"))
        # Relatório de build público não precisa dos caminhos absolutos do executor.
        for key in tuple(data):
            if key in ("paths", "bundle_dir", "data_dir", "asset_dirs", "log", "profile"):
                data.pop(key)
        camera = data.get("camera", {})
        camera["modelo"] = bool(camera.get("modelo"))
        data["run_id"] = run_id
        data.update(provenance)
        (reports / "self_test.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        completed.check_returncode()
        if data.get("status") != "ok":
            raise RuntimeError("Self-test do executável não confirmou status ok")
    return executable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onefile", action="store_true")
    parser.add_argument(
        "--sem-camera", action="store_true", help="build de teclado, explicitamente sem exigir detector"
    )
    args = parser.parse_args()
    try:
        print(build(args.onefile, not args.sem_camera))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        report = ROOT / "build" / "desktop-selftest" / "self_test.json"
        data = json.loads(report.read_text(encoding="utf-8")) if report.is_file() else {}
        data.update(status="failed", failure_type=type(exc).__name__)
        if isinstance(exc, subprocess.CalledProcessError):
            data["exit_code"] = exc.returncode
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
