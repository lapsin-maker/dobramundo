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
from .cache import BoundedCache

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
    """Biblioteca de sprites por pasta, com cache e liberação seletiva."""

    def __init__(self) -> None:
        # Índices de nomes/caminhos apenas: não mantenha uma segunda coleção de
        # superfícies escondida além do cache de imagens decodificadas.
        self._folders: BoundedCache = BoundedCache(64)
        self._loaded: BoundedCache = BoundedCache(256, 48 * 1024 * 1024)
        self._scenery: Optional[SpriteSet] = None

    def folder(self, name: str, names: Optional[Iterable[str]] = None) -> SpriteSet:
        """Todos os PNGs da pasta (ou só os nomes pedidos, se informados)."""
        names = None if names is None else tuple(names)
        paths = self._paths(name, names)
        sprites: SpriteSet = {}
        for stem, path in paths:
            image = self._loaded.get(path)
            if image is None:
                image = load_image(Path(path))
                if image is not None:
                    self._loaded[path] = image
            if image is not None:
                sprites[stem] = image
        return sprites

    def _paths(self, name: str, names: Optional[Iterable[str]] = None):
        names = None if names is None else tuple(names)
        key = name if names is None else f"{name}|{','.join(sorted(names))}"
        paths = self._folders.get(key)
        if paths is None:
            wanted = None if names is None else set(names)
            by_name = {}
            # Do pacote para o lado do executável: a pasta de maior prioridade sobrescreve.
            for directory in reversed(asset_dir_candidates(name)):
                if not directory.is_dir():
                    continue
                for path in sorted(directory.glob("*.png")):
                    if wanted is None or path.stem in wanted:
                        by_name[path.stem] = str(path)
            paths = tuple(sorted(by_name.items()))
            self._folders[key] = paths
        return paths

    def names(self, folder: str) -> tuple[str, ...]:
        """List image stems without decoding pixels; useful for task-wise warm-up."""
        return tuple(stem for stem, _path in self._paths(folder))

    def has(self, folder: str, name: str) -> bool:
        """Check an image's indexed presence without decoding its pixels."""
        return any(stem == name for stem, _path in self._paths(folder, (name,)))

    def sprite(self, folder: str, name: str) -> Optional[pygame.Surface]:
        return self.folder(folder, names=(name,)).get(name)

    def scenery_for(self, names: Iterable[str]) -> SpriteSet:
        """Carrega somente os nomes de cenário de que a vista ativa precisa."""
        wanted = set(names)
        merged: SpriteSet = {}
        for folder in SCENERY_FOLDERS:
            merged.update(self.folder(folder, names=wanted))
        return merged

    def release_folder(self, name: str, names: Optional[Iterable[str]] = None) -> int:
        """Solta referências de cache a uma pasta, ou a nomes específicos.

        Superfícies que uma cena ainda mantém continuam válidas; seus donos devem
        soltar essas referências antes de pedir descarte seletivo.
        """
        wanted = None if names is None else set(names)
        folder_keys = [key for key in self._folders if key == name or key.startswith(name + "|")]
        candidate_paths = set()
        for key in folder_keys:
            candidate_paths.update(path for stem, path in self._folders[key] if wanted is None or stem in wanted)
            del self._folders[key]
        removed = 0
        still_indexed = {path for paths in self._folders.values() for _, path in paths}
        for path in candidate_paths - still_indexed:
            if path in self._loaded:
                del self._loaded[path]
                removed += 1
        if name in SCENERY_FOLDERS:
            self._scenery = None
        return removed

    def release_scenery(self, names: Optional[Iterable[str]] = None) -> int:
        removed = 0
        for folder in SCENERY_FOLDERS:
            removed += self.release_folder(folder, names)
        return removed

    def cache_stats(self) -> dict:
        """Contagens e bytes estimados das superfícies retidas no cache da biblioteca."""
        seen = set()
        retained = sum(BoundedCache.value_bytes(image, seen) for image in self._loaded.values())
        if self._scenery is not None:
            retained += BoundedCache.value_bytes(self._scenery, seen)
        return {
            "loaded_images": len(self._loaded),
            "loaded_surface_bytes": self._loaded.bytes,
            "unique_retained_surface_bytes": retained,
            "folder_views": len(self._folders),
        }

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
