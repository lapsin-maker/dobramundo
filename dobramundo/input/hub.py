"""Junta as entradas: teclado e mouse (supervisor) e controle corporal (criança).

Não há botões para a criança: no voo, o segmento corporal move o avião; nos
menus, ele move um cursor e a seleção acontece pela permanência sobre o alvo.
O teclado (setas/WASD, ENTER, P/ESC) e o mouse continuam valendo para o
supervisor e para testes.
"""

from __future__ import annotations

from typing import Optional, Set, Tuple

import pygame

from .. import config as C
from ..paths import find_pose_model
from ..util import clamp
from .pose import SEGMENTS, BodyControl, PoseCameraSource

FLIGHT_KEYS = {
    pygame.K_LEFT: "left",
    pygame.K_a: "left",
    pygame.K_RIGHT: "right",
    pygame.K_d: "right",
    pygame.K_UP: "up",
    pygame.K_w: "up",
    pygame.K_SPACE: "up",
    pygame.K_DOWN: "down",
    pygame.K_s: "down",
}
POINTER_REACH = 0.46  # fração da tela que o cursor corporal alcança a partir do centro
AUTO_PAUSE_S = 1.0  # segundos fora da área de captura até pausar
RESUME_S = 1.2  # segundos de volta à área até liberar a retomada


class InputHub:
    def __init__(self) -> None:
        self.pressed: Set[int] = set()
        self.mouse_pos: Optional[Tuple[int, int]] = None
        self.mouse_moved = 0.0  # segundos desde o último movimento do mouse
        self.body: Optional[BodyControl] = None
        self.source = None  # fonte da câmera, compartilhada entre segmentos
        self.segment_key = "teclado"
        self.source_factory = lambda: PoseCameraSource(find_pose_model())

    # --------------------------------------------------------- corpo
    def set_segment(self, key: str, sensitivity: float = 1.0, dead_scale: float = 1.0) -> None:
        """Troca o segmento de controle (cada troca calibra de novo).

        A câmera é uma só e continua aberta entre trocas de segmento: só o mapeamento
        muda. Abrir e fechar a webcam a cada troca travava o quadro e, se a thread
        anterior demorasse a terminar, abria uma segunda captura do mesmo dispositivo.
        """
        if key == self.segment_key and self.body is not None:
            return
        self.segment_key = key
        self.body = None
        if key not in SEGMENTS:
            self.stop_camera()
            return
        if self.source is None:
            self.source = self.source_factory()
            self.source.start()
        self.body = BodyControl(self.source, SEGMENTS[key], sensitivity, dead_scale)

    def configure(self, sensitivity: float, dead_scale: float) -> None:
        if self.body is not None:
            self.body.mapper.sensitivity = sensitivity
            self.body.mapper.dead_scale = dead_scale

    def stop_camera(self) -> None:
        """Desliga a webcam (ao sair do jogo ou ao voltar para teclado e mouse)."""
        self.body = None
        if self.source is not None:
            self.source.stop()
            self.source = None

    @property
    def uses_body(self) -> bool:
        return self.body is not None

    @property
    def body_ready(self) -> bool:
        body = self.body
        return body is not None and body.error is None and body.calibrated

    def update(self, dt: float) -> None:
        self.mouse_moved += dt
        if self.body is not None:
            self.body.poll(dt)

    # ------------------------------------------------------------ eventos
    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in FLIGHT_KEYS:
            self.pressed.add(event.key)
        elif event.type == pygame.KEYUP:
            self.pressed.discard(event.key)
        elif event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            self.mouse_moved = 0.0
        elif event.type == getattr(pygame, "WINDOWFOCUSLOST", -1):
            self.pressed.clear()  # evita tecla "presa" ao trocar de janela

    def clear_keys(self) -> None:
        self.pressed.clear()

    def resync_keys(self) -> None:
        """Ao voltar da pausa, retoma as teclas que continuam pressionadas."""
        self.pressed.clear()
        try:
            state = pygame.key.get_pressed()
            self.pressed = {k for k in FLIGHT_KEYS if state[k]}
        except (pygame.error, IndexError):
            pass

    # -------------------------------------------------------------- leitura
    def held(self) -> Set[str]:
        return {FLIGHT_KEYS[k] for k in self.pressed}

    def flight_axes(self) -> Tuple[float, float]:
        held = self.held()
        ix = (1 if "right" in held else 0) - (1 if "left" in held else 0)
        iy = (1 if "up" in held else 0) - (1 if "down" in held else 0)
        if self.body is not None:
            ax, ay = self.body.axes()
            ix += ax
            iy += ay
        return clamp(ix, -1.0, 1.0), clamp(iy, -1.0, 1.0)

    def body_pointer(self) -> Optional[Tuple[int, int]]:
        """Cursor corporal nos menus (None antes da calibração ou sem câmera)."""
        if not self.body_ready:
            return None
        ax, ay = self.body.axes()
        return (int(C.WIDTH / 2 + ax * C.WIDTH * POINTER_REACH), int(C.HEIGHT / 2 - ay * C.HEIGHT * POINTER_REACH))

    def pointer(self) -> Optional[Tuple[int, int]]:
        """Cursor que seleciona por permanência: corpo; senão, o mouse parado na tela."""
        body = self.body_pointer()
        if body is not None and (self.mouse_pos is None or self.mouse_moved > 2.0):
            return body
        return self.mouse_pos

    def out_of_area(self) -> bool:
        """O segmento saiu da área de captura (para a pausa automática)."""
        body = self.body
        return body is not None and body.calibrated and body.error is None and body.missing_time >= AUTO_PAUSE_S

    def back_in_area(self) -> bool:
        body = self.body
        return body is None or body.error is not None or body.seen_time >= RESUME_S
