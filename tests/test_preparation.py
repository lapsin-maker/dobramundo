"""Atalhos de preparação e seus efeitos persistidos."""

from __future__ import annotations

from dobramundo import config as C
from dobramundo.persistence import load_profile
from dobramundo.scenes.calibration import CalibrationScene
from dobramundo.scenes.options import OptionsScene
from dobramundo.scenes.preparation import PreparationScene


def test_preset_calmo_persiste_valores_sem_trocar_segmento(app):
    app.profile.controle = "teclado"
    scene = PreparationScene(app)
    scene.apply_calm()
    saved = load_profile()
    assert app.profile.controle == "teclado"
    assert app.options.reduzir_movimento and not app.options.efeitos_fortes
    assert (app.options.volume_geral, app.options.volume_musica, app.options.volume_efeitos) == (0.35, 0.35, 0.4)
    assert app.options.permanencia_editor == 3.5
    assert saved.opcoes.reduzir_movimento and saved.opcoes.permanencia_editor == 3.5
    assert saved.controle == "teclado"


def test_preset_visivel_aplica_zoom_com_alto_contraste(app):
    scene = PreparationScene(app)
    scene.apply_visible()
    assert app.options.alto_contraste
    assert app.options.escala_contraste == 1.3
    assert app.view.contrast_scale == 1.3
    assert load_profile().opcoes.alto_contraste


def test_preparar_sem_camera_leva_a_escolha_de_controle(app):
    scene = PreparationScene(app)
    scene.build()
    card = next(button for button in scene.menu.buttons if button.key == "calibrar")
    assert card.label == "Escolher controle"
    scene.calibrate()
    assert isinstance(app.next_scene, OptionsScene)


def test_calibrar_com_camera_inicia_extremos_depois_do_centro(app):
    class Source:
        error = None

        def __init__(self):
            self.seq = 0
            self.points = None

        def start(self):
            pass

        def stop(self):
            pass

        def snapshot(self):
            return self.seq, self.points, None

        def show(self):
            self.seq += 1
            self.points = [(0.5, 0.5, 0.9)] * 33

    source = Source()
    app.input.source_factory = lambda: source
    app.profile.controle = "cabeca"
    app.apply_options()
    scene = PreparationScene(app)
    scene.calibrate()
    assert isinstance(app.next_scene, CalibrationScene)
    assert app.next_scene.guided_after_center
    app.go(app.next_scene)
    app.step(1 / 30, [])
    for _ in range(70):
        source.show()
        app.step(1 / 30, [])
    assert isinstance(app.scene, CalibrationScene)
    assert app.scene.guided_index == 0
    app.input.stop_camera()


def test_opcoes_distribui_botoes_sem_sobreposicao(app):
    scene = OptionsScene(app)
    scene.build()
    buttons = scene.menu.buttons
    assert all(0 <= b.rect.left and b.rect.right <= C.WIDTH for b in buttons)
    assert all(0 <= b.rect.top and b.rect.bottom <= C.HEIGHT for b in buttons)
    for index, first in enumerate(buttons):
        for second in buttons[index + 1 :]:
            assert not first.rect.colliderect(second.rect), (first.key, second.key)
    assert any(button.key == "preparar" for button in buttons)
