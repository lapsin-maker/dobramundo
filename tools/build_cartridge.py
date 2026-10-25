"""Monta o cartucho do Dobramundo para o console T-TEA (.ttea) e o valida.

O cartucho leva o pacote do jogo sem as partes que são só do executável (janela,
webcam com MediaPipe, self-test) e os assets sem o modelo de pose: no console, a
janela, a câmera e o modelo são do próprio console. A pasta montada fica em
build/cartucho/ e o arquivo em dist/dobramundo-<versão>.ttea.

Requer a ferramenta de cartuchos do T-TEA (comando ``tsdk``, Python 3.14). Uso:

    python tools/build_cartridge.py [--tsdk CAMINHO_DO_TSDK] [--so-montar]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dobramundo import __version__  # noqa: E402
from dobramundo.content import texts  # noqa: E402

STAGE = ROOT / "build" / "cartucho"
# Partes que só o executável usa (o console não deixa o cartucho abrir janela nem câmera).
DESKTOP_ONLY = {"app.py", "main.py", "__main__.py", "selftest.py", "input/camera.py"}
SKIP_ASSETS = {"pose_model"}

MANIFEST = f"""[game]
id = "dobramundo"
version = "{__version__}"
entrypoint = "dobramundo.cartridge:Dobramundo"
tracking_profile = "body"
resolution = [1100, 650]
game_api = 1
requires_ttea = ">=2.0,<3"
assets = ["assets"]
licenses = ["CREDITOS.md"]

[game.name]
pt-BR = "Dobramundo"
en = "Dobramundo"

[game.description]
pt-BR = "{texts.TAGLINE}"
en = "Fold the paper, fly and transform the city."
"""

PYPROJECT = f"""[project]
name = "dobramundo"
version = "{__version__}"
requires-python = ">=3.14"
dependencies = ["t-tea>=2.0,<3"]
"""


def credits_text() -> str:
    lines = ["# Dobramundo: créditos e licenças", ""]
    for label, value in texts.CREDITS:
        lines.append(f"- **{label}:** {value}")
    lines += [
        "",
        "Código, imagens e sons do Dobramundo: equipe do projeto. A licença de distribuição ainda",
        "será definida pela equipe; até lá, todos os direitos são reservados aos autores.",
        "",
        "O cartucho não inclui bibliotecas nem modelos de terceiros: a câmera e o rastreamento",
        "do corpo são do console T-TEA.",
    ]
    return "\n".join(lines) + "\n"


def ignore_package(folder: str, names):
    relative = Path(folder).relative_to(ROOT / "dobramundo").as_posix()
    skipped = {"__pycache__"}
    for name in names:
        path = name if relative == "." else f"{relative}/{name}"
        if path in DESKTOP_ONLY or name.endswith((".pyc", ".pyo")):
            skipped.add(name)
    return skipped


def ignore_assets(folder: str, names):
    return {n for n in names if n in SKIP_ASSETS or n.endswith((".task", ".tflite")) or n.startswith(".")}


def stage() -> Path:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    shutil.copytree(ROOT / "dobramundo", STAGE / "dobramundo", ignore=ignore_package)
    shutil.copytree(ROOT / "assets", STAGE / "assets", ignore=ignore_assets)
    (STAGE / "ttea.toml").write_text(MANIFEST, encoding="utf-8")
    (STAGE / "pyproject.toml").write_text(PYPROJECT, encoding="utf-8")
    (STAGE / "CREDITOS.md").write_text(credits_text(), encoding="utf-8")
    return STAGE


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tsdk", default="tsdk", help="comando ou caminho do tsdk")
    parser.add_argument("--so-montar", action="store_true", help="só monta a pasta, sem validar nem gerar")
    args = parser.parse_args()
    folder = stage()
    print(f"Cartucho montado em {folder}")
    if args.so_montar:
        return 0
    output = ROOT / "dist" / f"dobramundo-{__version__}.ttea"
    output.parent.mkdir(exist_ok=True)
    for command in ([args.tsdk, "check", str(folder)], [args.tsdk, "build", str(folder), "--output", str(output)]):
        print("$", " ".join(command))
        if subprocess.call(command) != 0:
            return 1
    print(f"Cartucho: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
