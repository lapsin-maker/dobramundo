"""Caminhos do jogo, tanto na execução direta (python -m dobramundo) quanto no
executável do PyInstaller.

Assets: procurados em assets/<pasta>/ ao lado do executável (permite trocar um
sprite sem recompilar) e, depois, dentro do pacote do PyInstaller.
Dados do jogador: %APPDATA%/Dobramundo (Windows), ~/.local/share/Dobramundo
(Linux) ou save/ do projeto quando roda pelo código-fonte.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from . import APP_NAME

DATA_DIR_ENV = "DOBRAMUNDO_DATA_DIR"
LEGACY_APP_NAME = "EcoRunner"  # nome do protótipo; os saves antigos são migrados
POSE_MODEL_NAME = "pose_landmarker_lite.task"


def is_frozen() -> bool:
    """True quando o jogo roda a partir do executável do PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Pasta do executável (empacotado) ou raiz do projeto (código-fonte)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    """Pasta dos arquivos embutidos (sys._MEIPASS no PyInstaller)."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else app_dir()


def asset_dir_candidates(name: str) -> List[Path]:
    """Ordem de busca de uma pasta de assets: ao lado do executável primeiro."""
    candidates: List[Path] = []
    for base in (app_dir(), bundle_dir()):
        path = base / "assets" / name
        if path not in candidates:
            candidates.append(path)
    return candidates


def find_asset_dir(name: str) -> Optional[Path]:
    for path in asset_dir_candidates(name):
        if path.is_dir():
            return path
    return None


def find_asset_file(folder: str, filename: str) -> Optional[Path]:
    for path in asset_dir_candidates(folder):
        candidate = path / filename
        if candidate.is_file():
            return candidate
    return None


def find_pose_model() -> Optional[Path]:
    """Modelo do MediaPipe Pose (assets/pose_model), ou None se faltar."""
    return find_asset_file("pose_model", POSE_MODEL_NAME)


def platform_data_dir(app_name: str = APP_NAME) -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / app_name
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / app_name


def _is_writable_dir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


_data_dir_cache: Optional[Path] = None


def user_data_dir() -> Path:
    """Pasta gravável para o perfil, logs e relatórios.

    Ordem: variável DOBRAMUNDO_DATA_DIR (testes) -> pasta do sistema (executável)
    ou save/ do projeto (código-fonte) -> pasta do sistema -> pasta temporária.
    Nunca grava dentro do pacote somente leitura.
    """
    global _data_dir_cache
    if _data_dir_cache is not None:
        return _data_dir_cache
    candidates: List[Path] = []
    override = os.environ.get(DATA_DIR_ENV)
    if override:
        candidates.append(Path(override))
    if not is_frozen():
        candidates.append(app_dir() / "save")
    candidates.append(platform_data_dir())
    candidates.append(Path(tempfile.gettempdir()) / APP_NAME)
    for path in candidates:
        if _is_writable_dir(path):
            _data_dir_cache = path
            return path
    _data_dir_cache = candidates[-1]
    return _data_dir_cache


def reset_data_dir_cache() -> None:
    """Esquece a pasta escolhida (usado pelos testes ao trocar DOBRAMUNDO_DATA_DIR)."""
    global _data_dir_cache
    _data_dir_cache = None


def legacy_data_dirs() -> List[Path]:
    """Onde o protótipo Eco Runner guardava recorde e configuração."""
    dirs = [platform_data_dir(LEGACY_APP_NAME)]
    if not is_frozen():
        dirs.insert(0, app_dir() / "save")
    return dirs
