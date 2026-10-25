"""Cache com limite de itens: ao lotar, descarta os mais antigos, um a um.

Esvaziar o cache inteiro de uma vez obrigava a refazer dezenas de imagens no
mesmo quadro (engasgo visível); descartar aos poucos espalha esse custo.
"""

from __future__ import annotations

from typing import Any, Dict, Hashable


class BoundedCache(Dict[Hashable, Any]):
    """dict comum (get, in, len) que guarda no máximo ``limit`` itens."""

    def __init__(self, limit: int) -> None:
        super().__init__()
        self.limit = max(1, int(limit))

    def __setitem__(self, key: Hashable, value: Any) -> None:
        if key not in self:
            while len(self) >= self.limit:
                del self[next(iter(self))]
        super().__setitem__(key, value)

    def put(self, key: Hashable, value: Any) -> Any:
        """Guarda e devolve o valor (para usar numa expressão)."""
        self[key] = value
        return value
