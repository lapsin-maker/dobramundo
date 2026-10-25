"""Cache com limite de itens: ao lotar, descarta os mais antigos, um a um.

Esvaziar o cache inteiro de uma vez obrigava a refazer dezenas de imagens no
mesmo quadro (engasgo visível); descartar aos poucos espalha esse custo.
"""

from __future__ import annotations

from typing import Any, Dict, Hashable

import pygame


class BoundedCache(Dict[Hashable, Any]):
    """dict comum (get, in, len) que guarda no máximo ``limit`` itens."""

    def __init__(self, limit: int, byte_limit: int = 0) -> None:
        super().__init__()
        self.limit = max(1, int(limit))
        self.byte_limit = max(0, int(byte_limit))
        self.bytes = 0

    @classmethod
    def value_bytes(cls, value: Any, seen=None) -> int:
        """Estimativa de pixels retidos; não inclui objetos Python auxiliares."""
        if seen is None:
            seen = set()
        identity = id(value)
        if identity in seen:
            return 0
        seen.add(identity)
        if isinstance(value, pygame.Surface):
            return value.get_pitch() * value.get_height()
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
            while len(self) >= self.limit or (
                self.byte_limit and self.bytes + value_size > self.byte_limit
            ):
                self.__delitem__(next(iter(self)))
        super().__setitem__(key, value)
        self.bytes += value_size

    def __delitem__(self, key: Hashable) -> None:
        value = super().__getitem__(key)
        self.bytes = max(0, self.bytes - self.value_bytes(value))
        super().__delitem__(key)

    def clear(self) -> None:
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
