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
from .pose import SEGMENTS, BodyControl, FloorControl

FlightCommand = Tuple[float, float, Optional[Tuple[float, float]]]  # (ix, iy, alvo de posição)
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
POINTER_REACH = 0.50  # alcança os limites úteis; os pixels finais são limitados abaixo
AUTO_PAUSE_S = 1.0  # segundos fora da área de captura até pausar
RESUME_S = 1.2  # segundos de volta à área até liberar a retomada
RECENTER_S = 3.0  # ausência que apaga o repouso de cabeça, mãos e tronco (calibra de novo sozinho)


def webcam_source():
    """Webcam do executável (importada só aqui: o cartucho do T-TEA não leva a câmera)."""
    from .camera import PoseCameraSource

    return PoseCameraSource(find_pose_model())


class InputHub:
    def __init__(self) -> None:
        self.pressed: Set[int] = set()
        self.mouse_pos: Optional[Tuple[int, int]] = None
        self.mouse_moved = 0.0  # segundos desde o último movimento do mouse
        self.body: Optional[BodyControl] = None
        self.source = None  # fonte da câmera, compartilhada entre segmentos
        self.segment_key = "teclado"
        self.position_control = True  # o corpo indica onde o avião fica (senão, a velocidade)
        self.auto_center = False  # recalibração automática é opt-in para evitar saltos
        self.invert_x = False
        # Pés sobre a projeção: função dos pontos do corpo -> posição na imagem do jogo.
        # Definida pela plataforma (calibração do chão no executável; o próprio console no T-TEA).
        self.floor_locate = None
        self.floor_token: object = None
        self.settings = (1.0, 1.0, False)  # sensibilidade, zona morta e inverter subir/descer
        self.source_factory = webcam_source  # o console T-TEA troca pela fonte dele
        self._pending_segment: Optional[str] = None

    # --------------------------------------------------------- corpo
    def set_segment(self, key: str, sensitivity: float = 1.0, dead_scale: float = 1.0, invert_y: bool = False) -> None:
        """Troca o segmento de controle (cada troca calibra de novo).

        A câmera é uma só e continua aberta entre trocas de segmento: só o mapeamento
        muda. Abrir e fechar a webcam a cada troca travava o quadro e, se a thread
        anterior demorasse a terminar, abria uma segunda captura do mesmo dispositivo.
        """
        self.settings = (sensitivity, dead_scale, invert_y)
        if key == self.segment_key and self.body is not None and self.body.error is None:
            return
        self.segment_key = key
        self.body = None
        if key not in SEGMENTS:
            self.stop_camera()
            return
        if self.source is not None:
            error = self.source.error
            stopping = False
            running = False
            try:
                running = self.source.running
                stopping = self.source.stopping
            except AttributeError:
                # Fontes antigas (incluindo mocks e o cartucho) não têm thread desktop.
                pass
            if error is not None or stopping:
                self.source.stop()
                if running:
                    self._pending_segment = key
                    self.body = self.make_control(key)
                    return
                self.source = None
            elif running:
                self.body = self.make_control(key)
                return
        self._open_segment(key)

    def _open_segment(self, key: str) -> None:
        self._pending_segment = None
        if self.source is None:
            self.source = self.source_factory()
            self.source.start()
        self.body = self.make_control(key)

    def retry_camera(self) -> None:
        """Reabre a fonte após falha, sem esperar a thread/captura na interface."""
        key = self.segment_key
        if key not in SEGMENTS:
            return
        source = self.source
        if source is not None:
            source.stop()
            running = False
            try:
                running = source.running
            except AttributeError:
                pass
            if running:
                self._pending_segment = key
                return
            self.source = None
        self.body = None
        self._open_segment(key)

    def make_control(self, key: str) -> BodyControl:
        """Pés sobre a projeção calibrada viram posição absoluta; o resto, relativo ao repouso."""
        if key == "pes" and self.floor_locate is not None:
            return FloorControl(self.source, self.floor_locate)
        sensitivity, dead_scale, invert_y = self.settings
        body = BodyControl(self.source, SEGMENTS[key], sensitivity, dead_scale, invert_y, self.invert_x)
        body.mapper.hold_when_lost = self.position_control
        body.recenter_after = RECENTER_S if self.auto_center and key != "pes" else None
        return body

    def set_floor(self, locate, token: object) -> None:
        """Troca a localização dos pés sobre a projeção (token muda quando a calibração muda)."""
        if token == self.floor_token:
            return
        self.floor_locate, self.floor_token = locate, token
        if self.body is not None and self.segment_key == "pes":
            self.body = self.make_control("pes")

    def configure(
        self, sensitivity: float, dead_scale: float, invert_y: bool = False, position: Optional[bool] = None
    ) -> None:
        if position is not None:
            self.position_control = position
        self.settings = (sensitivity, dead_scale, invert_y)
        if self.body is not None:
            mapper = self.body.mapper
            mapper.sensitivity = sensitivity
            mapper.dead_scale = dead_scale
            mapper.invert_y = invert_y
            mapper.invert_x = self.invert_x
            mapper.hold_when_lost = self.position_control
            if not self.body.absolute:
                self.body.recenter_after = RECENTER_S if self.auto_center and self.segment_key != "pes" else None

    def stop_camera(self) -> None:
        """Desliga a webcam (ao sair do jogo ou ao voltar para teclado e mouse)."""
        self.body = None
        self._pending_segment = None
        if self.source is not None:
            source = self.source
            source.stop()
            running = False
            try:
                running = source.running
            except AttributeError:
                pass
            if not running:
                self.source = None

    @property
    def uses_body(self) -> bool:
        return self.body is not None

    @property
    def body_ready(self) -> bool:
        body = self.body
        return body is not None and body.error is None and body.calibrated and body.visible

    def note_rendered(self) -> Optional[float]:
        """Marca o fim da composição para a leitura corporal consumida."""
        if self.body is None:
            return None
        try:
            return self.body.note_rendered()
        except AttributeError:
            # Compatibilidade com controles simples usados por hosts/fixtures antigos.
            return None

    def update(self, dt: float) -> None:
        self.mouse_moved += dt
        if self._pending_segment is not None:
            source = self.source
            running = False
            if source is not None:
                try:
                    running = source.running
                except AttributeError:
                    pass
            if not running:
                key = self._pending_segment
                self.source = None
                self._open_segment(key)
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
        elif event.type == pygame.WINDOWFOCUSLOST:
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

    def flight_command(self) -> FlightCommand:
        """(ix, iy, alvo) para o voo.

        Teclado: velocidade. Corpo calibrado com controle por posição: alvo (-1..1 nos dois
        eixos, 0 na postura calibrada) e velocidade zero; uma tecla apertada pelo supervisor
        tem prioridade enquanto estiver pressionada. Corpo com controle por velocidade: soma
        aos eixos do teclado, como antes.
        """
        held = self.held()
        ix = (1 if "right" in held else 0) - (1 if "left" in held else 0)
        iy = (1 if "up" in held else 0) - (1 if "down" in held else 0)
        if self.body is not None and self.position_control and not (ix or iy) and self.body.calibrated:
            if self.body.visible:
                return 0.0, 0.0, self.body.axes()
            return 0.0, 0.0, None  # quadro perdido: não reaproveita o último eixo como velocidade
        return self.flight_axes() + (None,)

    def body_pointer(self) -> Optional[Tuple[int, int]]:
        """Cursor corporal nos menus (None antes da calibração ou sem câmera)."""
        if not self.body_ready:
            return None
        if not self.body.visible:
            return None
        position = self.body.position()
        if position is not None:  # pés sobre a projeção: o cursor fica onde a criança pisa
            return int(position[0] * (C.WIDTH - 1)), int(position[1] * (C.HEIGHT - 1))
        ax, ay = self.body.axes()
        x = round(C.WIDTH / 2 + ax * C.WIDTH * POINTER_REACH)
        y = round(C.HEIGHT / 2 - ay * C.HEIGHT * POINTER_REACH)
        return max(0, min(C.WIDTH - 1, x)), max(0, min(C.HEIGHT - 1, y))

    def pointer(self) -> Optional[Tuple[int, int]]:
        """Cursor que seleciona por permanência: corpo; senão, o mouse parado na tela."""
        body = self.body_pointer()
        if self.body is not None:
            if self.mouse_pos is not None and self.mouse_moved <= 2.0:
                return self.mouse_pos
            return body  # None suspende permanência durante perda/atraso de quadro
        return self.mouse_pos

    def out_of_area(self) -> bool:
        """Falha da câmera pausa já; perda de pose usa a tolerância normal."""
        body = self.body
        return body is not None and (body.error is not None or (body.calibrated and body.missing_time >= AUTO_PAUSE_S))

    def back_in_area(self) -> bool:
        # Teclado é uma escolha explícita feita em calibração; falha de câmera não
        # pode ser confundida com retorno de pose válida.
        if self.segment_key == "teclado" and self.body is None:
            return True
        body = self.body
        return (
            body is not None
            and body.error is None
            and body.calibrated
            and body.visible
            and body.seen_time >= RESUME_S
        )
