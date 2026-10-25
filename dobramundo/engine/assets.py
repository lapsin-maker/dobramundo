"""Carregamento preguiçoso dos assets (PNG, JSON).

Consultas por pasta ou nomes são cacheadas; cada PNG decodificado é compartilhado
entre as consultas. sprite() lê apenas a imagem pedida. Um PNG colocado em
assets/<pasta>/ ao lado do executável substitui o embutido.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Optional

import pygame

from ..log import log
from ..paths import asset_dir_candidates

# Pastas de cenário que formam um único espaço de nomes (os nomes não se repetem).
SCENERY_FOLDERS = ("dieselpunk_sprites", "scenario_sprites", "era_final_sprites", "biome_sprites")

SpriteSet = Dict[str, pygame.Surface]


def display_format(surface: pygame.Surface, alpha: bool = False) -> pygame.Surface:
    """Converte para o formato da tela (desenho mais rápido); sem tela aberta, devolve igual."""
    try:
        return surface.convert_alpha() if alpha else surface.convert()
    except pygame.error:
        return surface


def load_image(path: Path, alpha: bool = True) -> Optional[pygame.Surface]:
    try:
        image = pygame.image.load(str(path))
    except (OSError, pygame.error) as exc:
        log.warning("imagem não carregou: %s (%s)", path, exc)
        return None
    # O arquivo pode ser RGBA mesmo quando todos os pixels são opacos.
    # Detectar uma vez evita pagar composição alfa em cada desenho de fundo.
    needs_alpha = alpha and image.get_colorkey() is not None
    if alpha and image.get_masks()[3]:
        opaque_pixels = pygame.mask.from_surface(image, 254).count()
        needs_alpha = needs_alpha or opaque_pixels != image.get_width() * image.get_height()
    return display_format(image, needs_alpha)


class Assets:
    """Biblioteca de sprites por pasta, com cache."""

    def __init__(self) -> None:
        self._folders: Dict[str, SpriteSet] = {}
        self._loaded: Dict[str, pygame.Surface] = {}
        self._scenery: Optional[SpriteSet] = None

    def folder(self, name: str, names: Optional[Iterable[str]] = None) -> SpriteSet:
        """Todos os PNGs da pasta (ou só os nomes pedidos, se informados)."""
        key = name if names is None else f"{name}|{','.join(sorted(names))}"
        cached = self._folders.get(key)
        if cached is not None:
            return cached
        wanted = None if names is None else set(names)
        sprites: SpriteSet = {}
        # Do pacote para o lado do executável: a pasta de maior prioridade sobrescreve.
        for directory in reversed(asset_dir_candidates(name)):
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.png")):
                if wanted is not None and path.stem not in wanted:
                    continue
                image = self._loaded.get(str(path))
                if image is None:
                    image = load_image(path)
                    if image is not None:
                        self._loaded[str(path)] = image
                if image is not None:
                    sprites[path.stem] = image
        self._folders[key] = sprites
        return sprites

    def sprite(self, folder: str, name: str) -> Optional[pygame.Surface]:
        return self.folder(folder, names=(name,)).get(name)

    @property
    def scenery(self) -> SpriteSet:
        """Todos os sprites de cenário (kits industriais, solarpunk e biomas)."""
        if self._scenery is None:
            merged: SpriteSet = {}
            for folder in SCENERY_FOLDERS:
                merged.update(self.folder(folder))
            self._scenery = merged
        return self._scenery

    @staticmethod
    def json(folder: str, filename: str) -> Optional[dict]:
        for directory in asset_dir_candidates(folder):
            path = directory / filename
            if path.is_file():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                if isinstance(data, dict):
                    return data
        return None


_shared: Optional[Assets] = None


def shared_assets() -> Assets:
    """Instância única (as cenas e os testes compartilham os sprites já carregados)."""
    global _shared
    if _shared is None:
        _shared = Assets()
    return _shared
