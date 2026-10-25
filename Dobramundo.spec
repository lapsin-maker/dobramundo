# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec do Dobramundo.
#
# Uso:
#   pyinstaller --noconfirm --clean Dobramundo.spec                 (pasta, padrão)
#   DOBRA_ONEFILE=1 pyinstaller --noconfirm --clean Dobramundo.spec (arquivo único)
#   DOBRA_CONSOLE=1 ...  mantém a janela de console (depuração)
#
# Toda a pasta assets/ entra no pacote (sprites, sons, modelo de pose).

import os
from pathlib import Path

ROOT = Path(SPECPATH).resolve()
ONEFILE = os.environ.get("DOBRA_ONEFILE") == "1"
CONSOLE = os.environ.get("DOBRA_CONSOLE") == "1"
ASSET_EXTS = {".png", ".json", ".ogg", ".wav", ".task", ".ico"}

datas = []
for file in sorted((ROOT / "assets").rglob("*")):
    if file.is_file() and file.suffix.lower() in ASSET_EXTS:
        datas.append((str(file), str(Path("assets") / file.parent.relative_to(ROOT / "assets"))))

icon = str(ROOT / "assets" / "icon.ico") if (ROOT / "assets" / "icon.ico").is_file() else None

a = Analysis(
    [str(ROOT / "run_dobramundo.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "unittest", "pydoc", "pytest", "matplotlib", "PIL", "soundfile"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="Dobramundo", debug=False, strip=False,
              upx=False, runtime_tmpdir=None, console=CONSOLE, icon=icon)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Dobramundo", debug=False, strip=False,
              upx=False, console=CONSOLE, icon=icon)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Dobramundo")
