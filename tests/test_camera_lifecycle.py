"""Ciclo de vida da captura sem depender de uma webcam física."""

from __future__ import annotations

from dobramundo.input.camera import PoseCameraSource
from dobramundo.input.hub import InputHub


class DeferredSource:
    error = None

    def __init__(self):
        self.open = False
        self.closing = False
        self.started = 0
        self.stopped = 0

    @property
    def running(self):
        return self.open

    @property
    def stopping(self):
        return self.closing

    def start(self):
        self.started += 1
        self.open = True
        self.closing = False

    def stop(self):
        self.stopped += 1
        self.closing = True

    def finish_close(self):
        self.open = False

    def snapshot(self):
        return 0, None, None


def test_fonte_em_encerramento_fica_retida_ate_liberar_a_camera():
    hub = InputHub()
    sources = []

    def create_source():
        source = DeferredSource()
        sources.append(source)
        return source

    hub.source_factory = create_source
    hub.set_segment("cabeca")
    old = sources[0]
    hub.set_segment("teclado")
    assert hub.source is old and old.stopping

    hub.set_segment("mao_direita")
    assert len(sources) == 1
    assert hub.source is old and hub._pending_segment == "mao_direita"

    old.finish_close()
    hub.update(1 / 60)
    assert len(sources) == 2
    assert hub.source is sources[1] and sources[1].running
    assert hub.body.source is sources[1]


def test_fonte_ja_encerrada_nao_e_reutilizada_na_selecao_seguinte():
    hub = InputHub()
    sources = []

    def create_source():
        source = DeferredSource()
        sources.append(source)
        return source

    hub.source_factory = create_source
    hub.set_segment("cabeca")
    old = sources[0]
    hub.set_segment("teclado")
    old.finish_close()
    hub.set_segment("cabeca")

    assert len(sources) == 2
    assert hub.source is sources[1] and hub.body.source is sources[1]


def test_fonte_com_erro_e_retentida_ate_thread_encerrar_antes_do_retry():
    hub = InputHub()
    sources = []

    def create_source():
        source = DeferredSource()
        sources.append(source)
        return source

    hub.source_factory = create_source
    hub.set_segment("cabeca")
    old = sources[0]
    old.error = "webcam desconectada"
    hub.retry_camera()
    assert hub.source is old and hub.body.source is old
    assert hub._pending_segment == "cabeca"
    assert len(sources) == 1

    old.finish_close()
    hub.update(1 / 60)
    assert len(sources) == 2 and hub.body.source is sources[1]


def test_stop_real_nao_espera_thread_de_captura_bloqueada():
    class BlockedThread:
        def __init__(self):
            self.alive = True
            self.join_calls = []

        def is_alive(self):
            return self.alive

        def join(self, timeout=None):
            self.join_calls.append(timeout)

    source = PoseCameraSource(None)
    thread = BlockedThread()
    source._thread = thread
    source.stop()
    assert source.running
    assert source._thread is thread
    assert thread.join_calls == []
    assert source.stopping

    thread.alive = False
    source.stop()
    assert source._thread is None
