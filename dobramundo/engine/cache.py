"""Cache com limite de itens: ao lotar, descarta os mais antigos, um a um.

Esvaziar o cache inteiro de uma vez obrigava a refazer dezenas de imagens no
mesmo quadro (engasgo visível); descartar aos poucos espalha esse custo.
"""

from __future__ import annotations

import weakref
from collections import OrderedDict
from typing import Any, Dict, Hashable

import pygame


class CacheBudget:
    """Shared, surface-aware budget for disposable renderer caches.

    Base artwork is intentionally pinned by its owning renderer; this manager
    trims derived cache entries. Subsurfaces are charged to their backing
    surface, once across every registered cache.
    """

    def __init__(self, byte_limit: int) -> None:
        self.byte_limit = max(0, int(byte_limit))
        self._caches = {}
        self._order = OrderedDict()
        self._entry_surfaces = {}
        self._surface_refs = {}
        self._retained = 0

    @staticmethod
    def _root_surface(surface):
        root = surface
        while True:
            parent = root.get_parent()
            if parent is None or parent is root:
                return root
            root = parent

    @classmethod
    def _surface_bytes(cls, value, seen):
        if isinstance(value, pygame.Surface):
            root = cls._root_surface(value)
            identity = id(root)
            if identity in seen:
                return 0
            seen.add(identity)
            return root.get_pitch() * root.get_height()
        if isinstance(value, dict):
            return sum(cls._surface_bytes(item, seen) for item in value.values())
        if isinstance(value, (list, tuple, set)):
            return sum(cls._surface_bytes(item, seen) for item in value)
        return 0

    @classmethod
    def _surface_sizes(cls, value, found):
        if isinstance(value, pygame.Surface):
            root = cls._root_surface(value)
            found[id(root)] = root.get_pitch() * root.get_height()
        elif isinstance(value, dict):
            for item in value.values():
                cls._surface_sizes(item, found)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                cls._surface_sizes(item, found)

    def touch(self, cache, key, value) -> None:
        cache_id = id(cache)
        if cache_id not in self._caches:
            self._caches[cache_id] = weakref.ref(cache, lambda _ref, cid=cache_id: self._drop_cache(cid))
        entry = (cache_id, key)
        surfaces = {}
        self._surface_sizes(value, surfaces)
        self._entry_surfaces[entry] = surfaces
        added_bytes = 0
        for surface_id, size in surfaces.items():
            count, current_size = self._surface_refs.get(surface_id, (0, size))
            if count == 0:
                self._retained += size
                added_bytes += size
            self._surface_refs[surface_id] = (count + 1, current_size)
        self._order[entry] = None
        if self.byte_limit and added_bytes > self.byte_limit:
            cache._evict(key)
            return
        self.trim()

    def _drop_cache(self, cache_id) -> None:
        self._caches.pop(cache_id, None)
        for entry in [entry for entry in self._entry_surfaces if entry[0] == cache_id]:
            self.forget_id(entry)

    def forget_id(self, entry) -> None:
        self._order.pop(entry, None)
        for surface_id in self._entry_surfaces.pop(entry, {}):
            count, size = self._surface_refs[surface_id]
            if count <= 1:
                self._surface_refs.pop(surface_id, None)
                self._retained = max(0, self._retained - size)
            else:
                self._surface_refs[surface_id] = (count - 1, size)

    def forget(self, cache, key) -> None:
        self.forget_id((id(cache), key))

    def retained_bytes(self) -> int:
        return self._retained

    def metrics(self) -> dict:
        """Lookup counters for currently live registered caches (not total RSS)."""
        counters = {"get_hits": 0, "get_misses": 0, "evictions": 0, "live_caches": 0}
        for reference in self._caches.values():
            cache = reference()
            if cache is not None:
                counters["live_caches"] += 1
                counters["get_hits"] += cache.get_hits
                counters["get_misses"] += cache.get_misses
                counters["evictions"] += cache.evictions
        return counters

    def trim(self) -> int:
        """Evict globally oldest entries until within budget; returns count."""
        removed = 0
        while self.byte_limit and self.retained_bytes() > self.byte_limit:
            if not self._order:
                break
            entry = next(iter(self._order))
            cache_id, key = entry
            reference = self._caches.get(cache_id)
            cache = reference() if reference is not None else None
            if cache is None:
                self.forget_id(entry)
            elif key in cache:
                cache._evict(key)
                removed += 1
            else:
                self.forget_id(entry)
        return removed


# Renderer caches are derived data. 192 MiB leaves headroom over the measured
# working set while preventing the sum of individual local limits from growing
# without bound. Root artwork and active frame surfaces remain pinned.
DEFAULT_CACHE_BUDGET = CacheBudget(192 * 1024 * 1024)


class BoundedCache(Dict[Hashable, Any]):
    """dict comum (get, in, len) que guarda no máximo ``limit`` itens."""

    def __init__(self, limit: int, byte_limit: int = 0, budget: CacheBudget = DEFAULT_CACHE_BUDGET) -> None:
        super().__init__()
        self.limit = max(1, int(limit))
        self.byte_limit = max(0, int(byte_limit))
        self.bytes = 0
        self.budget = budget
        self.get_hits = 0
        self.get_misses = 0
        self.evictions = 0

    def get(self, key: Hashable, default: Any = None) -> Any:
        if key in self:
            self.get_hits += 1
            return super().__getitem__(key)
        self.get_misses += 1
        return default

    @classmethod
    def value_bytes(cls, value: Any, seen=None) -> int:
        """Estimativa de pixels retidos; não inclui objetos Python auxiliares."""
        if seen is None:
            seen = set()
        if isinstance(value, pygame.Surface):
            root = value
            while True:
                parent = root.get_parent()
                if parent is None or parent is root:
                    break
                root = parent
            root_id = id(root)
            if root_id in seen:
                return 0
            seen.add(root_id)
            return root.get_pitch() * root.get_height()
        identity = id(value)
        if identity in seen:
            return 0
        seen.add(identity)
        if isinstance(value, dict):
            return sum(cls.value_bytes(item, seen) for item in value.values())
        if isinstance(value, (list, tuple, set)):
            return sum(cls.value_bytes(item, seen) for item in value)
        return 0

    def __setitem__(self, key: Hashable, value: Any) -> None:
        value_size = self.value_bytes(value)
        if self.byte_limit and value_size > self.byte_limit:
            if key in self:
                self.__delitem__(key)
            return
        if key in self:
            self.__delitem__(key)
        if key not in self:
            while self and (len(self) >= self.limit or (self.byte_limit and self.bytes + value_size > self.byte_limit)):
                self._evict(next(iter(self)))
            if len(self) >= self.limit or (self.byte_limit and value_size > self.byte_limit):
                return
        super().__setitem__(key, value)
        self.bytes += value_size
        self.budget.touch(self, key, value)

    def __delitem__(self, key: Hashable) -> None:
        value = super().__getitem__(key)
        self.budget.forget(self, key)
        self.bytes = max(0, self.bytes - self.value_bytes(value))
        super().__delitem__(key)

    def _evict(self, key: Hashable) -> None:
        self.evictions += 1
        self.__delitem__(key)

    def clear(self) -> None:
        for key in tuple(self):
            self.budget.forget(self, key)
        super().clear()
        self.bytes = 0

    def pop(self, key: Hashable, *default: Any) -> Any:
        if len(default) > 1:
            raise TypeError(f"pop expected at most 2 arguments, got {len(default) + 1}")
        if key not in self:
            if default:
                return default[0]
            raise KeyError(key)
        value = super().__getitem__(key)
        self.__delitem__(key)
        return value

    def popitem(self):
        if not self:
            raise KeyError("popitem(): cache is empty")
        key = next(reversed(self))
        return key, self.pop(key)

    def setdefault(self, key: Hashable, default: Any = None) -> Any:
        if key not in self:
            self[key] = default
        return self.get(key, default)

    def update(self, other=(), **kwargs: Any) -> None:
        try:
            for key in other.keys():
                self[key] = other[key]
        except AttributeError:
            for key, value in other:
                self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def __ior__(self, other):
        self.update(other)
        return self

    def discard_where(self, predicate) -> int:
        """Remove itens que atendem ao predicado e devolve quantos saíram."""
        keys = [key for key in self if predicate(key)]
        for key in keys:
            self.__delitem__(key)
        return len(keys)

    def put(self, key: Hashable, value: Any) -> Any:
        """Guarda e devolve o valor (para usar numa expressão)."""
        self[key] = value
        return value
