"""Controle corporal por qualquer segmento, a partir dos 33 pontos do corpo.

Os pontos vêm de uma fonte (a webcam do executável, em input/camera.py, ou o
rastreamento do console T-TEA, em input/console.py). O segmento escolhido (pés,
tronco em pé ou sentado, uma das mãos ou cabeça) vira um ponto; depois da
calibração da postura neutra (cerca de 2 s parado), o deslocamento em relação a
ela vira dois eixos de -1 a 1, que movem o avião e o cursor dos menus.

Este módulo não usa câmera nem bibliotecas de visão computacional.
"""

from __future__ import annotations

from typing import Callable, Dict, List, NamedTuple, Optional, Sequence, Tuple

Point = Tuple[float, float]  # posição normalizada (0..1 na imagem)
Landmark = Tuple[float, float, float]  # x, y, visibilidade
MIN_VISIBILITY = 0.5
PREVIEW_SIZE = (160, 120)  # miniatura mostrada ao supervisor
CAMERA_SIZE = (640, 480)


class Segment(NamedTuple):
    """Segmento corporal de controle e o alcance de movimento que vale o máximo."""

    key: str
    label: str
    landmarks: Tuple[int, ...]  # índices do MediaPipe Pose usados no ponto (média dos visíveis)
    min_points: int
    range_x: float  # deslocamento (fração da imagem) que vale o eixo máximo
    range_y: float
    dead: float  # tremor abaixo disso é ignorado
    hint: str  # instrução de calibração


SEGMENTS: Dict[str, Segment] = {
    "pes": Segment(
        "pes", "Pés", (27, 28, 29, 30, 31, 32), 2, 0.12, 0.07, 0.015, "Fique em pé, parado no centro da área"
    ),
    "tronco_pe": Segment(
        "tronco_pe", "Tronco (em pé)", (11, 12, 23, 24), 2, 0.06, 0.05, 0.012, "Fique em pé, de frente para a câmera"
    ),
    "tronco_sentado": Segment(
        "tronco_sentado",
        "Tronco (sentado)",
        (11, 12),
        2,
        0.05,
        0.035,
        0.010,
        "Sente-se confortável, de frente para a câmera",
    ),
    # mãos: centro da palma (punho, mínimo e indicador), mais estável que o punho sozinho
    "mao_direita": Segment(
        "mao_direita",
        "Mão direita",
        (16, 18, 20),
        1,
        0.10,
        0.08,
        0.015,
        "Deixe a mão direita parada, numa posição confortável",
    ),
    "mao_esquerda": Segment(
        "mao_esquerda",
        "Mão esquerda",
        (15, 17, 19),
        1,
        0.10,
        0.08,
        0.015,
        "Deixe a mão esquerda parada, numa posição confortável",
    ),
    "cabeca": Segment("cabeca", "Cabeça", (0, 7, 8), 2, 0.045, 0.035, 0.008, "Olhe para a tela com a cabeça parada"),
}


def segment_point(landmarks: Optional[Sequence[Landmark]], segment: Segment) -> Optional[Point]:
    """Ponto do segmento (média dos pontos visíveis), ou None se não estiver visível."""
    if not landmarks:
        return None
    visible = [landmarks[i] for i in segment.landmarks if i < len(landmarks) and landmarks[i][2] >= MIN_VISIBILITY]
    if len(visible) < segment.min_points:
        return None
    return (sum(p[0] for p in visible) / len(visible), sum(p[1] for p in visible) / len(visible))


def shape(delta: float, dead: float, full: float) -> float:
    """Zona morta em torno do repouso e saturação em ±1 depois de ``full``."""
    size = abs(delta)
    if size <= dead:
        return 0.0
    value = min(1.0, (size - dead) / max(1e-6, full - dead))
    return value if delta > 0 else -value


def median(values: List[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


class AxisMapper:
    """Ponto do segmento -> eixos (ax: direita, ay: subir), com calibração do repouso.

    Não usa câmera nem MediaPipe: recebe os pontos já detectados (testável sem webcam).
    """

    CALIBRATION_SECONDS = 2.0  # tempo parado e visível para definir o repouso
    MIN_SAMPLES = 15  # e pelo menos estas leituras (câmeras lentas levam mais tempo)
    DEFAULT_READING_S = 0.05  # intervalo suposto quando a leitura não informa o tempo
    SMOOTHING = 0.35  # 0..1: quanto maior, mais rápido responde
    LOST_DECAY = 0.85  # sem o ponto, os eixos voltam ao centro aos poucos
    STILL_SHARE = 0.5  # parado = metade do alcance do segmento (desvio mediano das leituras)

    def __init__(
        self,
        segment: Segment,
        sensitivity: float = 1.0,
        dead_scale: float = 1.0,
        invert_y: bool = False,
        invert_x: bool = False,
    ) -> None:
        self.segment = segment
        self.sensitivity = sensitivity
        self.dead_scale = dead_scale
        self.invert_y = invert_y  # câmera vista de cima ou de cabeça para baixo: subir vira descer
        self.invert_x = invert_x  # imagem da câmera sem espelho: esquerda e direita trocadas
        # Controle por posição: sem o ponto, o comando fica onde estava (o avião mantém o
        # rumo). No controle por velocidade, volta ao centro aos poucos (o avião para).
        self.hold_when_lost = False
        self.reset()

    def reset(self) -> None:
        self.samples: List[Point] = []
        self.sampled_time = 0.0
        self.base: Optional[Point] = None
        self.ax = 0.0
        self.ay = 0.0

    @property
    def calibrated(self) -> bool:
        return self.base is not None

    @property
    def progress(self) -> float:
        if self.calibrated:
            return 1.0
        return min(len(self.samples) / self.MIN_SAMPLES, self.sampled_time / self.CALIBRATION_SECONDS, 1.0)

    def feed(self, point: Optional[Point], elapsed: Optional[float] = None) -> None:
        """Uma leitura da câmera; elapsed = segundos desde a leitura anterior."""
        if not self.calibrated:
            if point is not None:
                self.samples.append(point)
                self.sampled_time += self.DEFAULT_READING_S if elapsed is None else elapsed
                if self.progress >= 1.0:
                    self.settle()
            return
        if point is None:
            if self.hold_when_lost:
                return
            self.ax *= self.LOST_DECAY
            self.ay *= self.LOST_DECAY
            return
        seg = self.segment
        dead = seg.dead * self.dead_scale
        target_x = shape(point[0] - self.base[0], dead, max(dead * 2, seg.range_x / self.sensitivity))
        target_y = shape(self.base[1] - point[1], dead, max(dead * 2, seg.range_y / self.sensitivity))
        if self.invert_y:
            target_y = -target_y
        if self.invert_x:
            target_x = -target_x
        self.ax += (target_x - self.ax) * self.SMOOTHING
        self.ay += (target_y - self.ay) * self.SMOOTHING

    def settle(self) -> None:
        """Fim da janela de calibração: aceita o repouso só se o segmento ficou parado.

        Mediana, para que uma leitura ruim não desloque o repouso; e o desvio mediano
        das leituras, para que um segmento em movimento não vire o repouso (recomeça).
        """
        base = (median([p[0] for p in self.samples]), median([p[1] for p in self.samples]))
        spread = max(
            median([abs(p[0] - base[0]) for p in self.samples]), median([abs(p[1] - base[1]) for p in self.samples])
        )
        if spread > self.STILL_SHARE * min(self.segment.range_x, self.segment.range_y):
            self.samples, self.sampled_time = [], 0.0
            return
        self.base = base

    def axes(self) -> Tuple[float, float]:
        return (self.ax, self.ay) if self.calibrated else (0.0, 0.0)


class BodyControl:
    """Liga a fonte dos pontos ao mapeador do segmento escolhido.

    ``source`` precisa ter snapshot() -> (seq, pontos, miniatura) e ``error``; quem a
    liga e desliga é o InputHub (os testes usam uma fonte falsa com essa forma).
    Com ``recenter_after`` (segundos), uma ausência longa apaga o repouso: quando o
    segmento volta e fica parado, a calibração se refaz sozinha.
    """

    absolute = False  # o comando é relativo ao repouso calibrado

    def __init__(
        self,
        source,
        segment: Segment,
        sensitivity: float = 1.0,
        dead_scale: float = 1.0,
        invert_y: bool = False,
        invert_x: bool = False,
    ) -> None:
        self.source = source
        self.segment = segment
        self.mapper = AxisMapper(segment, sensitivity, dead_scale, invert_y, invert_x)
        self.recenter_after: Optional[float] = None
        self.preview: Optional[bytes] = None
        self.visible = False
        self.missing_time = 0.0  # segundos sem ver o segmento (pausa automática)
        self.seen_time = 0.0  # segundos seguidos vendo o segmento (retomada)
        self.landmarks: Optional[List[Landmark]] = None
        self._seq = -1
        self._since_reading = 0.0
        self._frames = 0

    @property
    def error(self) -> Optional[str]:
        return self.source.error

    @property
    def receiving(self) -> bool:
        return self._frames > 0

    @property
    def calibrated(self) -> bool:
        return self.mapper.calibrated

    @property
    def progress(self) -> float:
        return self.mapper.progress

    def recalibrate(self) -> None:
        self.mapper.reset()

    def poll(self, dt: float) -> None:
        """Consome a leitura nova da fonte, se houver (chamado a cada quadro)."""
        self._since_reading += dt
        seq, landmarks, preview = self.source.snapshot()
        if seq != 0 and seq != self._seq:
            self._seq = seq
            self._frames += 1
            self.landmarks = landmarks
            self.preview = preview
            point = self.locate(landmarks)
            self.visible = point is not None
            self.feed(point, self._since_reading)
            self._since_reading = 0.0
        if self.receiving:
            if self.visible:
                self.seen_time += dt
                self.missing_time = 0.0
            else:
                self.missing_time += dt
                self.seen_time = 0.0
                if self.recenter_after is not None and self.calibrated and self.missing_time >= self.recenter_after:
                    self.recalibrate()

    def locate(self, landmarks: Optional[Sequence[Landmark]]) -> Optional[Point]:
        return segment_point(landmarks, self.segment)

    def feed(self, point: Optional[Point], elapsed: float) -> None:
        self.mapper.feed(point, elapsed)

    def axes(self) -> Tuple[float, float]:
        return self.mapper.axes()

    def position(self) -> Optional[Point]:
        """Ponto da tela lógica (0..1) apontado diretamente; só no controle absoluto."""
        return None


class FloorControl(BodyControl):
    """Pés sobre a projeção: onde a criança pisa na imagem do jogo vira o comando.

    ``locate`` recebe os pontos da fonte e devolve a posição dos pés na imagem do
    jogo (0..1, x para a direita e y para baixo), ou None. No executável ela vem da
    calibração do chão (input/floor.py); no console T-TEA, do próprio console. Não
    há repouso a calibrar: o meio da imagem é o centro da pista; pisar mais à frente
    (para o alto da imagem) sobe o avião, mais atrás desce.
    """

    absolute = True

    def __init__(self, source, locate: Callable[[Optional[Sequence[Landmark]]], Optional[Point]]) -> None:
        super().__init__(source, SEGMENTS["pes"])
        self.locator = locate
        self.point: Optional[Point] = None

    @property
    def calibrated(self) -> bool:
        return True

    @property
    def progress(self) -> float:
        return 1.0

    def recalibrate(self) -> None:
        """Nada a refazer: a calibração do chão é feita na tela de projeção."""

    def locate(self, landmarks: Optional[Sequence[Landmark]]) -> Optional[Point]:
        return self.locator(landmarks)

    def feed(self, point: Optional[Point], elapsed: float) -> None:
        if point is None:
            return  # mantém o último ponto: o avião segue o rumo
        if self.point is None:
            self.point = point
        else:
            k = AxisMapper.SMOOTHING
            (x, y), (tx, ty) = self.point, point
            self.point = (x + (tx - x) * k, y + (ty - y) * k)

    def axes(self) -> Tuple[float, float]:
        if self.point is None:
            return 0.0, 0.0
        x, y = self.point
        return max(-1.0, min(1.0, 2.0 * x - 1.0)), max(-1.0, min(1.0, 1.0 - 2.0 * y))

    def position(self) -> Optional[Point]:
        return self.point
