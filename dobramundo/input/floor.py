"""Calibração do chão no executável: da imagem da webcam para a imagem projetada.

Quatro alvos numerados são projetados a 15% das bordas da imagem (1 superior
esquerdo, 2 superior direito, 3 inferior direito, 4 inferior esquerdo). Com a
webcam vendo o chão, o supervisor clica no centro de cada alvo na imagem
congelada da câmera; os quatro pares de pontos definem uma homografia (uma
transformação de perspectiva) da câmera para a imagem projetada.

A calibração vale para a imagem projetada já orientada, então espelhar ou girar
180° depois não a invalida; girar 90° ou 270°, mover a câmera ou o projetor
exige calibrar de novo. A posição estimada é a do pé na imagem da câmera: ela
não detecta o contato com o chão. Confira no local, pisando sobre os alvos.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from ..engine.orientation import unrotate_point
from .pose import MIN_VISIBILITY, Landmark, Point

TARGETS: Tuple[Point, ...] = ((0.15, 0.15), (0.85, 0.15), (0.85, 0.85), (0.15, 0.85))
HEEL_TOE = ((29, 31), (30, 32))  # (calcanhar, ponta) do pé esquerdo e do direito no MediaPipe Pose
Matrix = Tuple[Tuple[float, float, float], ...]


def is_convex(points: Sequence[Point]) -> bool:
    """Quadrilátero convexo, sem cruzar, e com área que não seja minúscula."""
    if len(points) != 4:
        return False
    turns = []
    for i in range(4):
        (ax, ay), (bx, by), (cx, cy) = points[i], points[(i + 1) % 4], points[(i + 2) % 4]
        turns.append((bx - ax) * (cy - by) - (by - ay) * (cx - bx))
    same_side = all(t > 1e-6 for t in turns) or all(t < -1e-6 for t in turns)
    area = abs(sum(points[i][0] * points[(i + 1) % 4][1] - points[(i + 1) % 4][0] * points[i][1] for i in range(4)))
    return same_side and area / 2 >= 0.01


def solve(rows: List[List[float]], values: List[float]) -> List[float]:
    """Sistema linear quadrado por eliminação de Gauss com pivô parcial (sem numpy)."""
    m = [row[:] + [value] for row, value in zip(rows, values)]
    n = len(m)
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-12:
            raise ValueError("os pontos não definem uma perspectiva estável")
        m[col], m[pivot] = m[pivot], m[col]
        head = m[col][col]
        m[col] = [v / head for v in m[col]]
        for r in range(n):
            if r != col and m[r][col]:
                factor = m[r][col]
                m[r] = [a - factor * b for a, b in zip(m[r], m[col])]
    return [row[-1] for row in m]


def homography(source: Sequence[Point], target: Sequence[Point]) -> Matrix:
    """Matriz 3x3 que leva os 4 pontos de ``source`` aos 4 de ``target``."""
    rows, values = [], []
    for (x, y), (u, v) in zip(source, target):
        rows.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y])
        rows.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y])
        values += [u, v]
    h = solve(rows, values)
    return ((h[0], h[1], h[2]), (h[3], h[4], h[5]), (h[6], h[7], 1.0))


def apply(matrix: Matrix, x: float, y: float) -> Optional[Point]:
    a, b, c = matrix
    w = c[0] * x + c[1] * y + c[2]
    if abs(w) < 1e-12:
        return None
    return (a[0] * x + a[1] * y + a[2]) / w, (b[0] * x + b[1] * y + b[2]) / w


def feet_point(landmarks: Optional[Sequence[Landmark]]) -> Optional[Point]:
    """Meio dos dois pés na imagem da câmera (cada pé: meio do calcanhar e da ponta)."""
    if not landmarks or len(landmarks) < 33:
        return None
    feet = []
    for heel, toe in HEEL_TOE:
        a, b = landmarks[heel], landmarks[toe]
        if a[2] < MIN_VISIBILITY or b[2] < MIN_VISIBILITY:
            return None
        feet.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
    return (feet[0][0] + feet[1][0]) / 2, (feet[0][1] + feet[1][1]) / 2


class FloorMap:
    """Câmera -> imagem projetada -> imagem do jogo, com o alvo um pouco à frente dos pés."""

    def __init__(self, camera_points: Sequence[Sequence[float]]) -> None:
        points: List[Point] = [(float(p[0]), float(p[1])) for p in camera_points]
        if not is_convex(points):
            raise ValueError("os quatro pontos precisam formar um quadrilátero convexo")
        self.camera_points = points
        self.matrix = homography(points, TARGETS)

    @classmethod
    def maybe(cls, camera_points: Sequence[Sequence[float]]) -> Optional[FloorMap]:
        """A calibração salva, ou None se não houver ou não servir."""
        try:
            return cls(camera_points) if len(camera_points) == 4 else None
        except ValueError:
            return None

    def to_image(self, x: float, y: float) -> Optional[Point]:
        """Ponto da câmera -> ponto da imagem projetada (0..1 dentro dela)."""
        return apply(self.matrix, x, y)

    def locator(self, rotation: int, mirrored: bool, lead: float):
        """Função dos pontos do corpo -> posição dos pés na imagem do jogo (ou None)."""

        def locate(landmarks: Optional[Sequence[Landmark]]) -> Optional[Point]:
            feet = feet_point(landmarks)
            image = None if feet is None else self.to_image(*feet)
            if image is None:
                return None
            x, y = unrotate_point(image[0], image[1], rotation, mirrored)
            y -= lead  # o cursor fica à frente dos dedos, visível, e não sob o corpo
            if not (-0.05 <= x <= 1.05 and -0.05 <= y <= 1.05):
                return None  # fora da projeção
            return min(1.0, max(0.0, x)), min(1.0, max(0.0, y))

        return locate
