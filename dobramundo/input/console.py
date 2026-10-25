"""Fonte de pontos do console T-TEA: o rastreamento é do console, não do jogo.

A cada quadro o cartucho entrega o que o console mediu: os 33 pontos do corpo
na imagem da câmera (para tronco, mãos e cabeça) e a posição dos pés já
projetada na imagem do jogo (para os pés sobre o chão interativo). Esta fonte
tem a mesma forma da webcam do executável (snapshot, error, start, stop), então
o resto da entrada não muda.

A câmera do console não espelha a imagem: com a criança de frente para ela, a
direita da criança aparece à esquerda. Por isso o x dos pontos é espelhado, como
na webcam do executável; a opção "Trocar lados" desfaz isso se a câmera estiver
atrás da criança.
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

from .pose import Landmark, Point

RawPoint = Tuple[float, float, Optional[float]]  # x, y e visibilidade (None: o modelo não informa)


def body_points(raw: Optional[Sequence[RawPoint]], mirror: bool = True) -> Optional[List[Landmark]]:
    """Pontos do console -> pontos do jogo (x espelhado; inválidos com visibilidade 0)."""
    if not raw or len(raw) < 33:
        return None
    points = []
    for x, y, visibility in raw:
        if not (math.isfinite(x) and math.isfinite(y)):
            points.append((0.0, 0.0, 0.0))
            continue
        seen = 1.0 if visibility is None else (visibility if math.isfinite(visibility) else 0.0)
        points.append((1.0 - x if mirror else x, y, seen))
    return points


class TrackingSource:
    """Última leitura do console; ``push`` é chamado pelo cartucho a cada quadro."""

    error: Optional[str] = None  # o console cuida da câmera; aqui não há falha de abertura

    def __init__(self) -> None:
        self._seq = 0
        self._landmarks: Optional[List[Landmark]] = None
        self.floor: Optional[Point] = None  # pés na imagem do jogo (0..1), ou None

    def start(self) -> None:
        """Nada a abrir: o console já está rastreando."""

    def stop(self) -> None:
        """Nada a fechar."""

    def push(self, landmarks: Optional[List[Landmark]], floor: Optional[Point]) -> None:
        self._seq += 1
        self._landmarks = landmarks
        self.floor = floor

    def snapshot(self) -> Tuple[int, Optional[List[Landmark]], Optional[bytes]]:
        return self._seq, self._landmarks, None

    def locate_floor(self, landmarks: Optional[Sequence[Landmark]] = None) -> Optional[Point]:
        """Localizador dos pés para o FloorControl: a posição que o console projetou."""
        return self.floor
