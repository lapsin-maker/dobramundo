"""Uma instância desktop por pasta de dados; o SO libera o lock após queda.

O arquivo permanece no disco: removê-lo permitiria dois locks em inodes distintos.
Este módulo não faz parte do cartucho, cujo armazenamento é gerido pelo console.
"""

from __future__ import annotations

import os
from pathlib import Path


class InstanceBusyError(RuntimeError):
    """Outra instância já está usando estes pilotos."""


class InstanceLock:
    def __init__(self, directory: Path) -> None:
        self.path = directory / ".dobramundo.lock"
        self.stream = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        try:
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            stream.close()
            raise InstanceBusyError("O Dobramundo já está aberto com estes pilotos. Use a janela existente.") from exc
        self.stream = stream
        return self

    def __exit__(self, *_):
        if self.stream is not None:
            # Fechar o handle libera o lock também em KeyboardInterrupt e erros.
            self.stream.close()
            self.stream = None
