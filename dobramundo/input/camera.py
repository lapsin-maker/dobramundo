"""Webcam do executável: MediaPipe Pose numa thread, com a leitura mais recente.

Adaptado da captura do T-TEA 2.0 (LARVA/UDESC): o MediaPipe Tasks
(PoseLandmarker em modo VIDEO) lê a imagem espelhada da webcam e encontra 33
pontos do corpo. O vídeo é processado localmente, quadro a quadro, e nunca é
gravado. As bibliotecas (mediapipe, opencv) são opcionais e só são importadas
quando a câmera é ligada; sem elas o jogo segue com teclado e mouse.

Só o executável usa este módulo: no console T-TEA a câmera é do próprio console.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import List, Optional, Tuple

from ..log import log
from .pose import CAMERA_SIZE, PREVIEW_SIZE, Landmark


def create_landmarker(model_path: Path):
    """PoseLandmarker do MediaPipe Tasks em modo VIDEO (uma pessoa)."""
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.4,
        min_pose_presence_confidence=0.4,
        min_tracking_confidence=0.4,
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
        self._want_still = False
        self._still: Optional[Tuple[bytes, Tuple[int, int]]] = None
        self.frame_size: Optional[Tuple[int, int]] = None  # resolução negociada, não a solicitada
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

    def request_still(self) -> None:
        """Pede uma imagem inteira da câmera (calibração do chão); chega em ``still()``."""
        with self._lock:
            self._still = None
            self._want_still = True

    def still(self) -> Optional[Tuple[bytes, Tuple[int, int]]]:
        """(RGB, (largura, altura)) da imagem pedida, ou None enquanto não chega.

        Fica só na memória, para o supervisor clicar nos alvos; nunca é gravada.
        """
        with self._lock:
            return self._still

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
                with self._lock:
                    self.frame_size = (int(frame.shape[1]), int(frame.shape[0]))
                frame = cv2.flip(frame, 1)  # espelho: direita do jogador = direita da tela
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp = max(last_ts + 1, int(time.monotonic() * 1000))
                last_ts = timestamp
                result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
                points = None
                if result.pose_landmarks:
                    points = [(p.x, p.y, getattr(p, "visibility", 1.0) or 0.0) for p in result.pose_landmarks[0]]
                preview = cv2.resize(rgb, PREVIEW_SIZE, interpolation=cv2.INTER_AREA).tobytes()
                if self._want_still:
                    with self._lock:
                        self._still = (rgb.tobytes(), (rgb.shape[1], rgb.shape[0]))
                        self._want_still = False
                self._publish(points, preview)  # só a miniatura fica na memória; nada é gravado
        except Exception as exc:
            self.fail(f"erro na câmera ({exc.__class__.__name__})")
        finally:
            capture.release()
            landmarker.close()
