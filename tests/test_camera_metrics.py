"""Métricas de captura/idade e rejeição do resultado atrasado."""

from __future__ import annotations

import time

import pytest

from dobramundo.input.camera import PoseCameraSource
from dobramundo.input.pose import SEGMENTS, BodyControl


class TimestampSource:
    error = None
    frame_size = (640, 480)

    def __init__(self, captured_at):
        self.seq = 0
        self.captured_at = captured_at
        self.published_at = captured_at + 0.03
        self.points = [(0.5, 0.5, 0.9)] * 33

    def snapshot(self):
        return self.seq, self.points, b"preview"

    def snapshot_with_metadata(self):
        return self.seq, self.points, b"preview", self.captured_at, self.published_at, 12.0

    def diagnostics(self):
        return {
            "capture_fps": 24.0,
            "inference_fps": 22.0,
            "inference_ms": 12.0,
            "stale_dropped": 3,
            "read_failures": 1,
            "errors": 1,
        }


def test_body_control_rejeita_leitura_velha_desde_retorno_de_capture_read():
    source = TimestampSource(time.monotonic() - 0.8)
    source.seq = 1
    body = BodyControl(source, SEGMENTS["cabeca"])
    body.mapper.base = (0.5, 0.5)
    body.mapper.ax = 0.4
    body.mapper.hold_when_lost = True
    body.poll(1 / 60)

    assert not body.visible
    assert body.reading_age >= 0.8
    assert body.mapper.ax == 0.4
    assert body.capture_fps == 24.0 and body.inference_fps == 22.0
    assert body.inference_ms == 12.0 and body.capture_to_publish_ms == pytest.approx(30.0)
    assert body.stale_dropped == 3 and body.read_failures == 1 and body.camera_errors == 1


def test_idade_monotonica_avanca_mesmo_sem_nova_sequencia(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("dobramundo.input.pose.time.monotonic", lambda: clock[0])
    source = TimestampSource(100.0)
    source.seq = 1
    body = BodyControl(source, SEGMENTS["cabeca"])
    body.poll(1 / 60)
    assert body.visible

    clock[0] += 1.0  # simula pausa/travamento sem atualizar o seq publicado
    body.poll(1 / 60)
    assert not body.visible
    assert body.reading_age == 1.0


def test_captura_ate_quadro_mede_a_leitura_consumida(monkeypatch):
    clock = [200.0]
    monkeypatch.setattr("dobramundo.input.pose.time.monotonic", lambda: clock[0])
    source = TimestampSource(199.95)
    source.seq = 1
    body = BodyControl(source, SEGMENTS["cabeca"])
    body.poll(1 / 60)
    clock[0] = 200.02  # composição ocorreu depois da captura, sem nova sequência

    assert body.note_rendered() == pytest.approx(70.0)
    assert body.capture_to_render_ms == pytest.approx(70.0)

    source.seq = 2
    source.captured_at = 200.08  # publicado, mas ainda não consumido por poll
    clock[0] = 200.10
    assert body.note_rendered() == pytest.approx(150.0)

    clock[0] = 200.11
    body.poll(1 / 60)
    assert body.note_rendered() == pytest.approx(30.0)


def test_camera_publica_contadores_sem_expor_imagem_nem_pontos():
    source = PoseCameraSource(None)
    assert source._publish(None, None, captured_at=10.0, inference_ms=40.0, published_at=10.1)
    report = source.diagnostics()
    assert report["inferences"] == 1
    assert report["published"] == 1
    assert report["last_result_age_ms"] == pytest.approx(100.0)
    assert "landmarks" not in report and "preview" not in report and "image" not in report


def test_camera_descarta_resultado_que_envelheceu_durante_inferencia():
    source = PoseCameraSource(None)
    assert not source._publish(None, None, captured_at=10.0, inference_ms=500.0, published_at=10.5)
    assert source.snapshot()[0] == 0
    report = source.diagnostics()
    assert report["stale_dropped"] == 1
    assert report["published"] == 0
    assert report["last_result_age_ms"] == 500.0
