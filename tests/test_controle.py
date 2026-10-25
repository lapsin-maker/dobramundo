"""Controle corporal (sem webcam): pontos por segmento, calibração, presença e permanência."""

from __future__ import annotations

import pygame
import pytest
from helpers import CAL_READINGS, FakeSource, calibrated, landmarks

from dobramundo import config as C
from dobramundo.input.hub import AUTO_PAUSE_S, InputHub
from dobramundo.input.pose import SEGMENTS, AxisMapper, BodyControl, segment_point
from dobramundo.ui.widgets import Button, Menu

# leituras suficientes para calibrar (2 s a 30 leituras por segundo, com folga)






@pytest.mark.parametrize("key", sorted(SEGMENTS))
def test_cada_segmento_vira_um_ponto(key):
    segment = SEGMENTS[key]
    points = {i: (0.4, 0.6) for i in segment.landmarks}
    assert segment_point(landmarks(points), segment) == pytest.approx((0.4, 0.6))
    assert segment_point(landmarks(points, visibility=0.1), segment) is None


def test_tronco_precisa_de_dois_pontos():
    segment = SEGMENTS["tronco_pe"]
    assert segment_point(landmarks({11: (0.5, 0.5)}), segment) is None




def test_calibracao_usa_a_mediana():
    mapper = AxisMapper(SEGMENTS["cabeca"])
    for i in range(CAL_READINGS):
        mapper.feed((0.9, 0.9) if i == 3 else (0.5, 0.4))
    assert mapper.base == (0.5, 0.4) and mapper.progress == 1.0


def test_eixos_com_zona_morta_e_saturacao():
    mapper = calibrated()
    mapper.feed((0.505, 0.5))
    assert mapper.axes() == (0.0, 0.0)
    for _ in range(40):
        mapper.feed((0.7, 0.3))  # direita e para cima (y da imagem diminui)
    ax, ay = mapper.axes()
    assert ax == pytest.approx(1.0, abs=1e-3) and ay == pytest.approx(1.0, abs=1e-3)


def test_sensibilidade_reduz_o_movimento_necessario():
    low, high = calibrated(), calibrated()
    high.sensitivity = 2.0
    for mapper in (low, high):
        for _ in range(40):
            mapper.feed((0.53, 0.5))
    assert high.axes()[0] > low.axes()[0]


def test_presenca_e_pausa_automatica():
    hub = InputHub()
    source = FakeSource()
    hub.source_factory = lambda: source
    hub.set_segment("mao_direita")
    for _ in range(CAL_READINGS):
        source.show(landmarks({16: (0.5, 0.5)}))
        hub.update(1 / 30)
    assert hub.body_ready and not hub.out_of_area()
    for _ in range(int(AUTO_PAUSE_S * 30) + 2):
        source.show(landmarks({}))
        hub.update(1 / 30)
    assert hub.out_of_area() and not hub.back_in_area()
    for _ in range(60):
        source.show(landmarks({16: (0.5, 0.5)}))
        hub.update(1 / 30)
    assert hub.back_in_area()


def test_erro_de_camera_pausa_imediatamente_e_retry_exige_novos_dados():
    hub = InputHub()
    sources = [FakeSource(), FakeSource()]
    hub.source_factory = lambda: sources.pop(0)
    first = sources[0]
    hub.set_segment("mao_direita")
    for _ in range(CAL_READINGS):
        first.show(landmarks({16: (0.5, 0.5)}))
        hub.update(1 / 30)
    assert hub.body_ready

    first.error = "webcam desconectada"
    assert hub.out_of_area()
    assert not hub.back_in_area()

    replacement = sources[0]
    hub.retry_camera()
    assert hub.source is replacement
    assert not hub.out_of_area()
    assert not hub.back_in_area()
    for _ in range(CAL_READINGS):
        replacement.show(landmarks({16: (0.5, 0.5)}))
        hub.update(1 / 30)
    assert hub.body_ready
    assert hub.back_in_area()


def test_cursor_corporal_cobre_a_tela():
    hub = InputHub()
    source = FakeSource()
    hub.source_factory = lambda: source
    hub.set_segment("cabeca")
    for _ in range(CAL_READINGS):
        source.show(landmarks({0: (0.5, 0.5), 7: (0.5, 0.5), 8: (0.5, 0.5)}))
        hub.update(1 / 30)
    for _ in range(40):
        source.show(landmarks({0: (0.6, 0.6), 7: (0.6, 0.6), 8: (0.6, 0.6)}))
        hub.update(1 / 30)
    x, y = hub.body_pointer()
    assert x > C.WIDTH * 0.9 and y > C.HEIGHT * 0.9
    ix, iy = hub.flight_axes()
    assert ix > 0.9 and iy < -0.9


def test_body_control_ignora_leituras_repetidas():
    source = FakeSource()
    body = BodyControl(source, SEGMENTS["mao_esquerda"])
    source.show(landmarks({15: (0.5, 0.5)}))
    body.poll(0.03)
    body.poll(0.03)
    assert len(body.mapper.samples) == 1


# ----------------------------------------------------------- permanência
def test_permanencia_aciona_uma_vez_por_entrada():
    hits = []
    menu = Menu([Button(pygame.Rect(0, 0, 100, 60), "A", lambda: hits.append("a"))])
    for _ in range(30):
        menu.update(0.05, (50, 30), 1.2)
    assert hits == ["a"]  # 1,5 s parado: um acionamento só
    for _ in range(12):  # sai por 0,6 s (mais que a tolerância): rearma
        menu.update(0.05, (500, 500), 1.2)
    for _ in range(30):
        menu.update(0.05, (50, 30), 1.2)
    assert hits == ["a", "a"]


def test_permanencia_tolera_tremor_e_saida_breve():
    """Tremor perto da borda e uma saída curta não zeram a contagem."""
    hits = []
    menu = Menu([Button(pygame.Rect(0, 0, 100, 60), "A", lambda: hits.append("a"))])
    for _ in range(12):
        menu.update(0.05, (50, 30), 1.2)  # 0,6 s dentro
    for _ in range(6):
        menu.update(0.05, (120, 30), 1.2)  # 20 px fora da borda: ainda vale (margem do botão em seleção)
    for _ in range(4):
        menu.update(0.05, (500, 500), 1.2)  # 0,2 s fora: a contagem espera
    for _ in range(6):
        menu.update(0.05, (50, 30), 1.2)
    assert hits == ["a"]  # 0,6 + 0,3 + 0,3 = 1,2 s de permanência


def test_teclado_move_o_foco_e_confirma():
    hits = []
    menu = Menu(
        [
            Button(pygame.Rect(0, 0, 100, 60), "A", lambda: hits.append("a")),
            Button(pygame.Rect(200, 0, 100, 60), "B", lambda: hits.append("b")),
        ]
    )
    menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
    assert hits == ["b"]


def test_botao_desabilitado_nao_aciona():
    hits = []
    menu = Menu([Button(pygame.Rect(0, 0, 100, 60), "A", lambda: hits.append("a"), enabled=False)])
    for _ in range(40):
        menu.update(0.05, (50, 30), 1.0)
    menu.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(50, 30)))
    assert hits == []


def test_calibracao_espera_dois_segundos_reais():
    mapper = AxisMapper(SEGMENTS["tronco_pe"])
    for _ in range(30):
        mapper.feed((0.5, 0.5), 0.02)  # câmera rápida: 30 leituras em 0,6 s
    assert not mapper.calibrated
    for _ in range(80):
        mapper.feed((0.5, 0.5), 0.02)
    assert mapper.calibrated


def test_inverter_subir_e_descer():
    mapper = calibrated()
    mapper.invert_y = True
    for _ in range(40):
        mapper.feed((0.5, 0.3))
    assert mapper.axes()[1] < -0.9
