"""Liquidação segura de recompensa parcial e resultado reapresentado."""

from __future__ import annotations

from types import SimpleNamespace

from conftest import make_run

from dobramundo.config import ERA_SPAN
from dobramundo.scenes.calibration import CalibrationScene
from dobramundo.scenes.flight import FlightScene
from dobramundo.scenes.options import OptionsScene
from dobramundo.scenes.result import ResultScene, apply_run


def _start_interactive_flight(app, scene):
    app.go(scene)
    app.step(1 / 60, [])
    while app.view.warmup_pending:
        app.view.step_warm_up(100.0)
    app.step(1 / 60, [])
    assert scene.started


def test_interromper_voo_credita_parcial_uma_vez_e_abre_resultado(app):
    scene = FlightScene(app, "amazonia")
    scene.started = True
    scene.run.resources["papel"] = 3
    scene.run.score = 120
    scene.run.add_restoration(2 * ERA_SPAN)

    scene.quit_to_village()

    assert isinstance(app.next_scene, ResultScene)
    assert scene.run.interrupted and scene.run.finished
    app.step(1 / 60, [])
    assert app.profile.recursos["papel"] == 3
    assert app.profile.pontos == 120
    assert app.profile.estrelas["amazonia"] == 2  # parcial não concede a terceira estrela
    assert app.profile.historico[-1]["concluida"] == 0
    assert app.profile.historico[-1]["interrompida"] == 1
    assert app.profile.voos == 1

    ResultScene(app, scene.run)  # reentrada no resultado não aplica outra vez
    assert app.profile.recursos["papel"] == 3
    assert app.profile.pontos == 120
    assert app.profile.voos == 1
    assert len(app.profile.historico) == 1


def test_conclusao_normal_e_colisao_final_nao_viram_interrupcao(app):
    complete = make_run()
    complete.add_restoration(100)
    apply_run(app.profile, complete)
    assert app.profile.historico[-1]["concluida"] == 1
    assert app.profile.historico[-1]["interrompida"] == 0

    collided = make_run()
    for _ in range(3):
        collided.invulnerable_timer = 0
        collided.take_hit()
    assert collided.game_over and collided.finished
    apply_run(app.profile, collided)
    assert app.profile.historico[-1]["concluida"] == 0
    assert app.profile.historico[-1]["interrompida"] == 0
    assert app.profile.voos == 2


def test_repetir_settlement_e_notificacao_nao_duplica(app, monkeypatch):
    notices = []
    monkeypatch.setattr(app, "on_flight", notices.append)
    run = make_run()
    run.resources["vidro"] = 4
    scene = FlightScene(app, "amazonia")
    scene.run = run
    scene.started = True

    scene.settle_on_close()
    apply_run(app.profile, run)
    ResultScene(app, run)

    assert app.profile.recursos["vidro"] == 4
    assert app.profile.voos == 1
    assert len(app.profile.historico) == 1
    assert len(notices) == 1


def test_fechamento_normal_liquida_voo_em_andamento(app):
    scene = FlightScene(app, "amazonia")
    _start_interactive_flight(app, scene)
    scene.run.resources["vidro"] = 2
    scene.run.score = 80

    app.shutdown()

    assert app.profile.recursos["vidro"] == 2
    assert app.profile.pontos == 80
    assert app.profile.historico[-1]["interrompida"] == 1
    assert app.profile.historico[-1]["concluida"] == 0
    assert app.profile.voos == 1


def test_fechamento_com_voo_pendente_antes_de_entrar_nao_registra_partida(app):
    scene = FlightScene(app, "amazonia")
    app.go(scene)  # ainda não houve _switch() nem FlightScene.enter()

    app.shutdown()

    assert not scene.started
    assert app.profile.voos == 0
    assert app.profile.historico == []
    assert app.profile.recursos["papel"] == 0


def test_fechamento_durante_warmup_nao_registra_voo_ou_recursos(app):
    scene = FlightScene(app, "amazonia")
    scene.run.resources["papel"] = 3
    app.go(scene)
    app.step(1 / 60, [])  # cena entrou, mas ainda não processou quadro interativo
    assert not scene.started

    app.shutdown()

    assert app.profile.voos == 0
    assert app.profile.historico == []
    assert app.profile.recursos["papel"] == 0


def test_recalibrar_trocar_segmento_para_opcoes_liquida_parcial_uma_vez(app):
    flight = FlightScene(app, "amazonia")
    _start_interactive_flight(app, flight)
    flight.run.resources["papel"] = 2
    flight.run.score = 40
    calibration = CalibrationScene(app, return_to=flight)

    calibration.options()
    assert isinstance(app.next_scene, OptionsScene)
    assert calibration.return_to is None
    assert app.profile.recursos["papel"] == 2
    assert app.profile.pontos == 40
    assert app.profile.voos == 1
    assert app.profile.historico[-1]["interrompida"] == 1

    flight.settle_on_close()  # um fechamento posterior não repete a recompensa
    assert app.profile.recursos["papel"] == 2
    assert app.profile.voos == 1
    assert len(app.profile.historico) == 1


def test_fechar_jogo_enquanto_calibra_liquida_voo_de_retorno(app):
    flight = FlightScene(app, "amazonia")
    _start_interactive_flight(app, flight)
    flight.run.resources["vidro"] = 3
    flight.run.score = 75
    app.scene = CalibrationScene(app, return_to=flight)
    app.next_scene = None

    app.shutdown()

    assert app.profile.recursos["vidro"] == 3
    assert app.profile.pontos == 75
    assert app.profile.voos == 1
    assert len(app.profile.historico) == 1
    assert app.profile.historico[-1]["interrompida"] == 1


def test_resultado_oferece_retry_quando_save_falha(app, monkeypatch):
    outcomes = iter((False, True))
    monkeypatch.setattr(app, "writer", lambda profile: next(outcomes))
    run = make_run()
    run.resources["papel"] = 5
    result = ResultScene(app, run)
    result.enter()
    assert app.save_failed
    assert any(button.key == "retry_save" for button in result.menu.buttons)
    for index, button in enumerate(result.menu.buttons):
        assert all(not button.rect.colliderect(other.rect) for other in result.menu.buttons[index + 1 :])

    result.retry_save()
    assert not app.save_failed
    assert all(button.key != "retry_save" for button in result.menu.buttons)
    assert app.profile.recursos["papel"] == 5
    assert app.profile.voos == 1


def test_result_preview_is_read_only_until_enter(app, monkeypatch):
    notices = []
    monkeypatch.setattr(app, "on_flight", notices.append)
    run = make_run()
    run.resources["papel"] = 4
    run.score = 75
    result = ResultScene(app, run)

    result.build()
    result.draw(app.canvas)

    assert app.profile.recursos["papel"] == 0
    assert app.profile.pontos == 0 and app.profile.voos == 0
    assert app.profile.historico == []
    assert run.settlement is None
    assert notices == []


def test_result_pending_on_close_settles_once(app, monkeypatch):
    notices = []
    monkeypatch.setattr(app, "on_flight", notices.append)
    run = make_run()
    run.finished = True
    run.interrupted = True
    run.resources["vidro"] = 2
    result = ResultScene(app, run)
    app.go(result)

    app.shutdown()

    assert app.profile.recursos["vidro"] == 2
    assert app.profile.voos == 1 and len(app.profile.historico) == 1
    assert app.profile.historico[0]["interrompida"] == 1
    assert len(notices) == 1


def test_historico_antigo_sem_marcador_de_interrupcao_continua_valido(app, data_dir):
    from dobramundo.persistence import load_profile, profile_path

    app.profile.historico = [{"fase": "amazonia", "concluida": 1, "pontos": 50}]
    app.save()
    loaded = load_profile()
    assert loaded.historico == [{"fase": "amazonia", "concluida": 1, "pontos": 50}]
    assert profile_path().exists()


def test_tracking_loss_bloqueia_colisao_durante_tolerancia(app, monkeypatch):
    scene = FlightScene(app, "amazonia")
    app.profile.controle = "pes"
    app.input.body = SimpleNamespace(calibrated=True, error=None, visible=False, missing_time=0.2)
    calls = []
    monkeypatch.setattr(scene.run, "update", lambda *args, **kwargs: calls.append((args, kwargs)))

    scene.update(1 / 60)

    assert calls == []
    assert not scene.run.game_over


def test_controle_teclado_nao_fica_bloqueado_por_camera_sem_tracking(app, monkeypatch):
    scene = FlightScene(app, "amazonia")
    app.profile.controle = "teclado"
    app.input.body = SimpleNamespace(calibrated=True, error=None, visible=False, missing_time=0.2)
    calls = []
    monkeypatch.setattr(scene.run, "update", lambda *args, **kwargs: calls.append((args, kwargs)))

    scene.update(1 / 60)

    assert len(calls) == 1
