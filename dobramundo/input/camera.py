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
from .pose import CAMERA_SIZE, MAX_READING_AGE_S, PREVIEW_SIZE, Landmark

MAX_RESULT_AGE_S = MAX_READING_AGE_S


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
        self._captured_at: Optional[float] = None
        self._published_at: Optional[float] = None
        self._inference_ms = 0.0
        self._want_still = False
        self._still: Optional[Tuple[bytes, Tuple[int, int]]] = None
        self.frame_size: Optional[Tuple[int, int]] = None  # resolução negociada, não a solicitada
        self._started_at: Optional[float] = None
        self._frames_read = 0
        self._inferences = 0
        self._published = 0
        self._stale_dropped = 0
        self._read_failures = 0
        self._errors = 0
        self._first_capture_at: Optional[float] = None
        self._first_inference_at: Optional[float] = None
        self._last_capture_at: Optional[float] = None
        self._last_capture_interval_ms = 0.0
        self._last_inference_started_at: Optional[float] = None
        self._last_inference_interval_ms = 0.0
        self._last_inference_ms = 0.0
        self._last_result_age_ms: Optional[float] = None
        self._stop_complete = threading.Event()
        self._stop_complete.set()
        if model_path is None or not Path(model_path).is_file():
            self.fail("modelo de pose não encontrado")

    def fail(self, message: str) -> None:
        """Registra a falha da câmera (aparece nas opções e na calibração, e no log)."""
        self.error = message
        with self._lock:
            self._errors += 1
        log.warning("câmera: %s", message)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def stopping(self) -> bool:
        return self._stop.is_set()

    def start(self) -> None:
        if self.error is not None or self.running:
            return
        self._stop.clear()
        self._stop_complete.clear()
        self._started_at = time.monotonic()
        self._thread = threading.Thread(target=self._run, name="webcam-pose", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 0.0) -> None:
        """Pede encerramento sem bloquear a interface; timeout só é usado em ferramentas."""
        self._stop.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            if timeout > 0:
                thread.join(timeout=timeout)
            if thread.is_alive():
                return  # mantém a referência enquanto read()/detector ainda liberam o dispositivo
        self._thread = None
        self._stop_complete.set()

    def snapshot(self) -> Tuple[int, Optional[List[Landmark]], Optional[bytes]]:
        with self._lock:
            return self._seq, self._landmarks, self._preview

    def snapshot_with_metadata(self) -> tuple:
        """Leitura atômica e metadados; mantém ``snapshot()`` compatível com fontes antigas."""
        with self._lock:
            return (
                self._seq,
                self._landmarks,
                self._preview,
                self._captured_at,
                self._published_at,
                self._inference_ms,
            )

    def diagnostics(self) -> dict:
        """Contadores sem imagem nem pontos, próprios para a tela do supervisor/benchmark."""
        now = time.monotonic()
        with self._lock:
            capture_elapsed = max(0.001, now - self._first_capture_at) if self._first_capture_at is not None else 0.0
            inference_elapsed = (
                max(0.001, now - self._first_inference_at) if self._first_inference_at is not None else 0.0
            )
            age = None if self._captured_at is None else max(0.0, (now - self._captured_at) * 1000.0)
            return {
                "frames_read": self._frames_read,
                "inferences": self._inferences,
                "published": self._published,
                "stale_dropped": self._stale_dropped,
                "read_failures": self._read_failures,
                "errors": self._errors,
                "startup_ms": (
                    max(0.0, (self._first_capture_at - self._started_at) * 1000.0)
                    if self._first_capture_at is not None and self._started_at is not None
                    else None
                ),
                "capture_fps": self._frames_read / capture_elapsed if capture_elapsed else 0.0,
                "inference_fps": self._inferences / inference_elapsed if inference_elapsed else 0.0,
                "capture_interval_ms": self._last_capture_interval_ms,
                "inference_interval_ms": self._last_inference_interval_ms,
                "inference_ms": self._last_inference_ms,
                "result_age_ms": age,
                "last_result_age_ms": self._last_result_age_ms,
                "resolution": self.frame_size,
                "error": self.error,
                "stopping": self.stopping,
            }

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

    def _publish(
        self,
        landmarks: Optional[List[Landmark]],
        preview: Optional[bytes],
        captured_at: Optional[float] = None,
        inference_ms: float = 0.0,
        published_at: Optional[float] = None,
    ) -> bool:
        published_at = time.monotonic() if published_at is None else published_at
        age_s = max(0.0, published_at - captured_at) if captured_at is not None else 0.0
        with self._lock:
            self._inferences += 1
            self._last_inference_ms = max(0.0, inference_ms)
            self._last_result_age_ms = age_s * 1000.0
            if captured_at is not None and age_s > MAX_RESULT_AGE_S:
                self._stale_dropped += 1
                return False
            self._seq += 1
            self._landmarks = landmarks
            self._preview = preview
            self._captured_at = captured_at
            self._published_at = published_at
            self._inference_ms = max(0.0, inference_ms)
            self._published += 1
        return True

    def _run(self) -> None:
        capture = None
        landmarker = None
        try:
            import cv2
            import mediapipe as mp

            landmarker = create_landmarker(self.model_path)
            capture = cv2.VideoCapture(self.camera_index)
            if not capture.isOpened():
                self.fail("não foi possível abrir a webcam")
                return
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_SIZE[0])
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_SIZE[1])
            last_ts = 0
            while not self._stop.is_set():
                ok, frame = capture.read()
                if not ok:
                    with self._lock:
                        self._read_failures += 1
                    self.fail("a webcam não envia imagem")
                    break
                captured_at = time.monotonic()
                with self._lock:
                    self.frame_size = (int(frame.shape[1]), int(frame.shape[0]))
                    self._frames_read += 1
                    if self._first_capture_at is None:
                        self._first_capture_at = captured_at
                    if self._last_capture_at is not None:
                        self._last_capture_interval_ms = max(0.0, (captured_at - self._last_capture_at) * 1000.0)
                    self._last_capture_at = captured_at
                if self._stop.is_set():
                    break
                if time.monotonic() - captured_at > MAX_RESULT_AGE_S:
                    with self._lock:
                        self._stale_dropped += 1
                        self._last_result_age_ms = (time.monotonic() - captured_at) * 1000.0
                    continue
                frame = cv2.flip(frame, 1)  # espelho: direita do jogador = direita da tela
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp = max(last_ts + 1, int(time.monotonic() * 1000))
                last_ts = timestamp
                inference_started = time.monotonic()
                with self._lock:
                    if self._first_inference_at is None:
                        self._first_inference_at = inference_started
                    if self._last_inference_started_at is not None:
                        self._last_inference_interval_ms = max(
                            0.0, (inference_started - self._last_inference_started_at) * 1000.0
                        )
                    self._last_inference_started_at = inference_started
                result = landmarker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), timestamp)
                inference_finished = time.monotonic()
                inference_ms = max(0.0, (inference_finished - inference_started) * 1000.0)
                points = None
                if result.pose_landmarks:
                    points = [(p.x, p.y, getattr(p, "visibility", 1.0) or 0.0) for p in result.pose_landmarks[0]]
                preview = cv2.resize(rgb, PREVIEW_SIZE, interpolation=cv2.INTER_AREA).tobytes()
                with self._lock:
                    want_still = self._want_still
                if want_still:
                    with self._lock:
                        self._still = (rgb.tobytes(), (rgb.shape[1], rgb.shape[0]))
                        self._want_still = False
                self._publish(points, preview, captured_at, inference_ms, time.monotonic())
        except ImportError:
            self.fail("instale mediapipe e opencv para usar a câmera")
        except Exception as exc:
            category = "modelo de pose não carregou" if landmarker is None else "erro na câmera"
            self.fail(f"{category} ({exc.__class__.__name__})")
        finally:
            try:
                if capture is not None:
                    try:
                        capture.release()
                    except Exception as exc:
                        self.fail(f"erro ao liberar a webcam ({exc.__class__.__name__})")
            finally:
                try:
                    if landmarker is not None:
                        landmarker.close()
                except Exception as exc:
                    self.fail(f"erro ao fechar o detector ({exc.__class__.__name__})")
                finally:
                    self._stop_complete.set()
