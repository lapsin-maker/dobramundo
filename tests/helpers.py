"""Fontes sintéticas e calibração compartilhadas pelos testes de entrada.

Nenhuma imagem ou câmera real é usada. Fora destes helpers, prefira comandos e
resultados públicos; detalhes internos só para injeção de falhas/invariantes.
"""

from dobramundo.input.pose import SEGMENTS, AxisMapper

CAL_READINGS = 70


def landmarks(points: dict, visibility: float = 0.9):
    data = [(0.5, 0.5, 0.0)] * 33
    for index, (x, y) in points.items():
        data[index] = (x, y, visibility)
    return data


class FakeSource:
    """Fonte de câmera falsa: devolve os pontos que o teste definir."""

    def __init__(self) -> None:
        self.error = None
        self.seq = 0
        self.points = None

    def start(self):
        pass

    def stop(self):
        pass

    def show(self, points) -> None:
        self.seq += 1
        self.points = points

    def snapshot(self):
        return self.seq, self.points, None


def calibrated(segment: str = "tronco_pe") -> AxisMapper:
    mapper = AxisMapper(SEGMENTS[segment])
    for _ in range(CAL_READINGS):
        mapper.feed((0.5, 0.5))
    return mapper
