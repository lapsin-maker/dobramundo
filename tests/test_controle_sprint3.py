"""Regressões do controle robusto de cabeça e calibração da Sprint 3."""

from __future__ import annotations

import pytest

from dobramundo import config as C
from dobramundo.input.hub import InputHub
from dobramundo.input.pose import SEGMENTS, AxisMapper, BodyControl, segment_point
from dobramundo.persistence import Profile


def frame(points, visibility=0.9):
    values = [(0.5, 0.5, 0.0)] * 33
    for index, (x, y) in points.items():
        values[index] = (x, y, visibility)
    return values


class Source:
    error = None
    frame_size = (1280, 720)

    def __init__(self):
        self.seq = 0
        self.points = None

    def start(self):
        pass

    def stop(self):
        pass

    def show(self, points):
        self.seq += 1
        self.points = points

    def snapshot(self):
        return self.seq, self.points, None


def test_cabeca_continua_com_orelha_oculta_e_compensa_troca_de_ancora():
    body = BodyControl(Source(), SEGMENTS["cabeca"])
    baseline = frame({0: (0.50, 0.50), 7: (0.46, 0.50), 8: (0.54, 0.50)})
    nose_only = frame({0: (0.50, 0.50), 7: (0.46, 0.50)}, visibility=0.6)
    ears_only = frame({7: (0.46, 0.50), 8: (0.54, 0.50)})
    one_ear = frame({7: (0.46, 0.50)})
    assert segment_point(baseline, SEGMENTS["cabeca"]) == pytest.approx((0.50, 0.50))
    p0 = body.locate(baseline)
    p1 = body.locate(nose_only)
    p2 = body.locate(ears_only)
    p3 = body.locate(one_ear)
    assert p1 == pytest.approx(p0)
    assert p2 == pytest.approx(p0)
    assert p3 == pytest.approx(p0)


def test_cabeca_usa_nariz_com_visibilidade_reduzida_ao_virar():
    points = frame({0: (0.61, 0.49), 7: (0.54, 0.50)}, visibility=0.4)
    assert segment_point(points, SEGMENTS["cabeca"]) == pytest.approx((0.61, 0.49))


def test_extremos_confortaveis_sao_assimetricos_e_saturam():
    mapper = AxisMapper(SEGMENTS["cabeca"])
    for _ in range(70):
        mapper.feed((0.5, 0.5))
    assert mapper.set_comfortable_extent("right", [(0.57, 0.5)] * 5)
    assert mapper.set_comfortable_extent("left", [(0.46, 0.5)] * 5)
    for _ in range(60):
        mapper.feed((0.57, 0.5))
    assert mapper.axes()[0] == pytest.approx(1.0, abs=1e-3)
    mapper.ax = 0.0
    for _ in range(60):
        mapper.feed((0.46, 0.5))
    assert mapper.axes()[0] == pytest.approx(-1.0, abs=1e-3)


def test_extremo_guiado_significa_cem_porcento_na_sensibilidade_de_captura():
    mapper = AxisMapper(SEGMENTS["cabeca"], sensitivity=1.8)
    for _ in range(70):
        mapper.feed((0.5, 0.5))
    assert mapper.set_comfortable_extent("right", [(0.57, 0.5)] * 5)
    for _ in range(70):
        mapper.feed((0.57, 0.5))
    assert mapper.axes()[0] == pytest.approx(1.0, abs=1e-3)
    mapper.sensitivity = 0.9
    mapper.ax = 0.0
    for _ in range(70):
        mapper.feed((0.57, 0.5))
    assert 0.45 < mapper.axes()[0] < 0.55


def test_cursor_corporal_alcanca_os_limites_uteis():
    hub = InputHub()
    source = Source()
    hub.source_factory = lambda: source
    hub.set_segment("cabeca")
    for _ in range(70):
        source.show(frame({0: (0.5, 0.5), 7: (0.46, 0.5), 8: (0.54, 0.5)}))
        hub.update(1 / 30)
    for x, y, expected in ((0.75, 0.5, (C.WIDTH - 1, C.HEIGHT // 2)), (0.25, 0.5, (0, C.HEIGHT // 2)),
                           (0.5, 0.75, (C.WIDTH // 2, C.HEIGHT - 1)), (0.5, 0.25, (C.WIDTH // 2, 0))):
        for _ in range(70):
            source.show(frame({0: (x, y), 7: (x - 0.04, y), 8: (x + 0.04, y)}))
            hub.update(1 / 30)
        assert hub.body_pointer() == expected


def test_leitura_antiga_invalida_cursor_e_nao_reusa_quadro():
    hub = InputHub()
    source = Source()
    hub.source_factory = lambda: source
    hub.set_segment("cabeca")
    for _ in range(70):
        source.show(frame({0: (0.5, 0.5), 7: (0.46, 0.5), 8: (0.54, 0.5)}))
        hub.update(1 / 30)
    assert hub.body_pointer() is not None
    for _ in range(70):
        source.show(frame({0: (0.7, 0.5), 7: (0.66, 0.5), 8: (0.74, 0.5)}))
        hub.update(1 / 30)
    assert hub.body.axes()[0] > 0.9
    hub.update(0.4)  # sem novo seq: o último quadro envelheceu
    assert not hub.body.visible
    assert hub.body_pointer() is None
    assert hub.pointer() is None
    assert hub.flight_command() == (0.0, 0.0, None)


def test_perfil_migra_pedidos_e_normaliza_novas_opcoes():
    profile = Profile.from_dict({
        "opcoes": {"permanencia_editor": 9.0, "escala_contraste": 9.0},
        "pedidos_vila": {"horta": "solicitada", "desconhecida": "concluida", "escola": "errada"},
    })
    assert profile.opcoes.permanencia_editor == 5.0
    assert profile.opcoes.escala_contraste == 1.6
    assert profile.pedidos_vila == {"horta": "solicitada"}
    round_trip = Profile.from_dict(profile.to_dict())
    assert round_trip.pedidos_vila == profile.pedidos_vila
    assert round_trip.opcoes.permanencia_editor == profile.opcoes.permanencia_editor
    old = Profile.from_dict({})
    assert old.opcoes.permanencia_editor == 3.0
    assert old.opcoes.escala_contraste == 1.3
    assert old.pedidos_vila == {}

