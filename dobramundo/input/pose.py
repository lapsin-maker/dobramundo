"""Controle corporal pela webcam (MediaPipe Pose), por qualquer segmento.

Adaptado da captura do T-TEA 2.0 (LARVA/UDESC): o MediaPipe Tasks
(PoseLandmarker em modo VIDEO) lê a imagem espelhada da webcam e encontra 33
pontos do corpo. O segmento escolhido (pés, tronco em pé ou sentado, uma das
mãos ou cabeça) vira um ponto; depois da calibração da postura neutra (cerca de
2 s parado), o deslocamento em relação a ela vira dois eixos de -1 a 1, que
movem o avião e o cursor dos menus.

O vídeo é processado localmente, quadro a quadro, e nunca é gravado. As
bibliotecas (mediapipe, opencv) são opcionais e só são importadas quando a
câmera é ligada; sem elas o jogo segue com teclado e mouse.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from ..log import log

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
    "mao_direita": Segment(
        "mao_direita",
        "Mão direita",
        (16,),
        1,
        0.10,
        0.08,
        0.015,
        "Deixe a mão direita parada, numa posição confortável",
    ),
    "mao_esquerda": Segment(
        "mao_esquerda",
        "Mão esquerda",
        (15,),
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

    def __init__(
        self, segment: Segment, sensitivity: float = 1.0, dead_scale: float = 1.0, invert_y: bool = False
    ) -> None:
        self.segment = segment
        self.sensitivity = sensitivity
        self.dead_scale = dead_scale
        self.invert_y = invert_y  # câmera vista de cima ou de cabeça para baixo: subir vira descer
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
                    # mediana: uma leitura ruim durante a calibração não desloca o repouso
                    self.base = (median([p[0] for p in self.samples]), median([p[1] for p in self.samples]))
            return
        if point is None:
            self.ax *= self.LOST_DECAY
            self.ay *= self.LOST_DECAY
            return
        seg = self.segment
        dead = seg.dead * self.dead_scale
        target_x = shape(point[0] - self.base[0], dead, max(dead * 2, seg.range_x / self.sensitivity))
        target_y = shape(self.base[1] - point[1], dead, max(dead * 2, seg.range_y / self.sensitivity))
        if self.invert_y:
            target_y = -target_y
        self.ax += (target_x - self.ax) * self.SMOOTHING
        self.ay += (target_y - self.ay) * self.SMOOTHING

    def axes(self) -> Tuple[float, float]:
        return (self.ax, self.ay) if self.calibrated else (0.0, 0.0)


# ----------------------------------------------------------------- MediaPipe
def create_landmarker(model_path: Path):
    """PoseLandmarker do MediaPipe Tasks em modo VIDEO (uma pessoa)."""
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.PoseLandmarker.create_from_options(options)


class PoseCameraSource:
    """Lê a webcam numa thread e guarda a leitura mais recente (pontos + miniatura).

    Erros (câmera ocupada, biblioteca faltando, modelo ausente) ficam em ``error``.
    """

    def __init__(self, model_path: Optional[Path], camera_index: int = 0) -> None:
        self.model_path = model_path
        self.camera_index = camera_index
        self.error: Optional[str] = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._seq = 0
        self._landmarks: Optional[List[Landmark]] = None
        self._preview: Optional[bytes] = None
        if model_path is None or not Path(model_path).is_file():
            self.fail("modelo de pose não encontrado")

    def fail(self, message: str) -> None:
        """Registra a falha da câmera (aparece nas opções e na calibração, e no log)."""
        self.error = message
        log.warning("câmera: %s", message)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.error is not None or self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="webcam-pose", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 1.5) -> None:
        """Pede para a thread parar; a referência só é solta quando ela termina de fato."""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=timeout)
            if thread.is_alive():
                return  # ainda liberando a câmera: running segue True e impede outra captura
        self._thread = None

    def snapshot(self) -> Tuple[int, Optional[List[Landmark]], Optional[bytes]]:
        with self._lock:
            return self._seq, self._landmarks, self._preview

    def _publish(self, landmarks: Optional[List[Landmark]], preview: Optional[bytes]) -> None:
        with self._lock:
            self._seq += 1
            self._landmarks = landmarks
            self._preview = preview

    def _run(self) -> None:
        try:
            import cv2
            import mediapipe as mp

            landmarker = create_landmarker(self.model_path)
        except ImportError:
            self.fail("instale mediapipe e opencv para usar a câmera")
            return
        except Exception as exc:  # modelo corrompido, runtime etc.
            self.fail(f"modelo de pose não carregou ({exc.__class__.__name__})")
            return
        capture = cv2.VideoCapture(self.camera_index)
        if not capture.isOpened():
            capture.release()
            landmarker.close()
            self.fail("não foi possível abrir a webcam")
            return
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_SIZE[0])
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_SIZE[1])
        last_ts = 0
        try:
            while not self._stop.is_set():
                ok, frame = capture.read()
                if not ok:
                    self.fail("a webcam não envia imagem")
                    break
                frame = cv2.flip(frame, 1)  # espelho: direita do jogador = direita da tela
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp = max(last_ts + 1, int(time.monotonic() * 1000))
                last_ts = timestamp
                result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
                points = None
                if result.pose_landmarks:
                    points = [(p.x, p.y, getattr(p, "visibility", 1.0) or 0.0) for p in result.pose_landmarks[0]]
                preview = cv2.resize(rgb, PREVIEW_SIZE, interpolation=cv2.INTER_AREA).tobytes()
                self._publish(points, preview)  # só a miniatura fica na memória; nada é gravado
        except Exception as exc:
            self.fail(f"erro na câmera ({exc.__class__.__name__})")
        finally:
            capture.release()
            landmarker.close()


class BodyControl:
    """Liga a fonte da câmera ao mapeador do segmento escolhido.

    ``source`` precisa ter snapshot() -> (seq, pontos, miniatura) e ``error``; quem a
    liga e desliga é o InputHub (os testes usam uma fonte falsa com essa forma).
    """

    def __init__(
        self, source, segment: Segment, sensitivity: float = 1.0, dead_scale: float = 1.0, invert_y: bool = False
    ) -> None:
        self.source = source
        self.segment = segment
        self.mapper = AxisMapper(segment, sensitivity, dead_scale, invert_y)
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
        self._since_reading += dt
        """Consome a leitura nova da câmera, se houver (chamado a cada quadro)."""
        seq, landmarks, preview = self.source.snapshot()
        if seq != 0 and seq != self._seq:
            self._seq = seq
            self._frames += 1
            self.landmarks = landmarks
            self.preview = preview
            point = segment_point(landmarks, self.segment)
            self.visible = point is not None
            self.mapper.feed(point, self._since_reading)
            self._since_reading = 0.0
        if self.receiving:
            if self.visible:
                self.seen_time += dt
                self.missing_time = 0.0
            else:
                self.missing_time += dt
                self.seen_time = 0.0

    def axes(self) -> Tuple[float, float]:
        return self.mapper.axes()
