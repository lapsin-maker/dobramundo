"""Fluxo do primeiro voo e tutorial pictográfico sem penalidade."""

from __future__ import annotations

from types import SimpleNamespace

import pygame
import pytest

from dobramundo import config as C
from dobramundo.core import first_scene
from dobramundo.persistence import Profile
from dobramundo.scenes.calibration import CalibrationScene
from dobramundo.scenes.flight import FlightScene
from dobramundo.scenes.map import MapScene
from dobramundo.scenes.options import OptionsScene
from dobramundo.scenes.tutorial import MOVE_DISTANCE, OBSTACLE_APPROACH_Z, PRACTICE_STEPS, TutorialScene
from dobramundo.scenes.village import VillageScene


def test_save_anterior_migra_tutorial_pendente():
    profile = Profile.from_dict({"piloto_montado": True, "opcoes": {"abertura_automatica": True}})
    assert profile.tutorial_visto is False
    profile.tutorial_visto = True
    assert Profile.from_dict(profile.to_dict()).tutorial_visto is True


def test_tutorial_abre_no_primeiro_bioma_escolhido_e_pular_inicia_voo(app):
    app.profile.tutorial_visto = False
    map_scene = MapScene(app)
    map_scene.start("caatinga")
    tutorial = app.next_scene
    assert isinstance(tutorial, TutorialScene)
    assert isinstance(tutorial.next_scene, FlightScene)
    assert tutorial.next_scene.biome.key == "caatinga"
    assert isinstance(tutorial.return_to, MapScene)

    tutorial.skip()
    assert app.profile.tutorial_visto is True
    assert app.next_scene is tutorial.next_scene


def test_calibracao_pendiente_rodeia_tutorial_antes_do_voo(app):
    app.profile.tutorial_visto = False
    app.input.body = SimpleNamespace(error=None, calibrated=False)
    MapScene(app).start("amazonia")
    calibration = app.next_scene
    assert isinstance(calibration, CalibrationScene)
    assert isinstance(calibration.return_to, TutorialScene)
    assert isinstance(calibration.return_to.next_scene, FlightScene)


def test_voltar_ao_mapa_nao_marca_tutorial_visto(app):
    app.profile.tutorial_visto = False
    map_scene = MapScene(app)
    map_scene.start("amazonia")
    tutorial = app.next_scene
    assert isinstance(tutorial, TutorialScene)
    tutorial.back()
    assert app.profile.tutorial_visto is False
    assert isinstance(app.next_scene, MapScene)


def test_botao_segurar_avanca_etapa_sem_exigir_sucesso(app):
    scene = TutorialScene(app, next_scene=FlightScene(app, "amazonia"), return_to=MapScene(app))
    scene.build()
    button = next(button for button in scene.menu.buttons if button.key == "avancar")
    center = button.rect.center
    assert not scene.menu.update(1.0, center, 2.0)
    assert scene.menu.update(1.0, center, 2.0)
    assert scene.step_index == 1


def test_avanco_por_movimento_e_coleta_real_sem_perder_vidas(app):
    scene = TutorialScene(app, next_scene=FlightScene(app, "amazonia"), return_to=MapScene(app))
    scene.run.player.x = MOVE_DISTANCE + 5
    scene.update(0.7)
    assert scene.step_index == 1
    assert PRACTICE_STEPS[scene.step_index][0] == "collect"

    assert scene.trial is not None
    scene.run.player.x = C.LANE_WIDTH
    scene.trial.entity.z = C.PLAYER_Z + 1.0
    lives = scene.run.lives
    scene.update(0.05)
    assert scene.trial is not None and scene.trial.entity.collected
    assert scene.run.lives == lives == C.MAX_LIVES
    scene.update(0.7)
    assert scene.step_index == 2


def test_obstaculo_bate_sem_punir_e_pausa_congela_treino(app):
    scene = TutorialScene(app, next_scene=FlightScene(app, "amazonia"), return_to=MapScene(app))
    scene.step_index = 2
    scene._start_step()
    assert scene.trial is not None
    scene.trial.entity.z = C.PLAYER_Z
    lives = scene.run.lives
    scene.update(0.05)
    assert scene.run.lives == lives == C.MAX_LIVES

    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0, unicode="p"))
    assert scene.paused
    distance = scene.run.world.distance
    scene.update(0.5)
    assert scene.run.world.distance == distance
    scene.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p, mod=0, unicode="p"))
    assert not scene.paused


@pytest.mark.parametrize(
    "step_index,position",
    [(2, (0.0, 150.0)), (3, (0.0, 30.0)), (4, (180.0, C.REST_ALTITUDE))],
)
def test_manobras_corretas_passam_obstaculos_e_avancam(app, step_index, position):
    scene = TutorialScene(app, next_scene=FlightScene(app, "amazonia"), return_to=MapScene(app))
    scene.step_index = step_index
    scene._start_step()
    assert scene.trial is not None
    assert scene.trial.entity.z == C.PLAYER_Z + OBSTACLE_APPROACH_Z
    scene.run.player.x, scene.run.player.y = position
    scene.trial.entity.z = C.PLAYER_Z - 29.0
    scene.update(0.05)
    assert scene.feedback > 0.0
    assert scene.run.lives == C.MAX_LIVES
    if scene.trial is not None and scene.trial.kind != "collect":
        assert scene.trial.entity.passed
        assert scene.trial.entity not in scene.run.world.entities
    scene.update(0.7)
    if step_index + 1 == len(PRACTICE_STEPS):
        assert app.profile.tutorial_visto is True
        assert app.next_scene is scene.next_scene
    else:
        assert scene.step_index == step_index + 1


def test_tentativa_de_obstaculo_reaparece_com_tempo_de_aproximacao(app):
    scene = TutorialScene(app, next_scene=FlightScene(app, "amazonia"), return_to=MapScene(app))
    scene.step_index = 2
    scene._start_step()
    assert scene.trial is not None
    scene.trial.entity.z = C.PLAYER_Z - 31.0
    scene._check_trial()
    assert scene.trial is not None
    assert scene.trial.entity.z == C.PLAYER_Z + OBSTACLE_APPROACH_Z


def test_opcoes_reabre_tutorial_e_tutorial_desenha(app):
    options = OptionsScene(app)
    options.build()
    assert any(button.key == "treino" for button in options.menu.buttons)
    options.replay_tutorial()
    tutorial = app.next_scene
    assert isinstance(tutorial, TutorialScene)
    assert isinstance(tutorial.next_scene, OptionsScene)

    tutorial.build()
    tutorial.draw(app.canvas)
    assert {button.key for button in tutorial.menu.buttons} == {"mapa", "avancar", "pular"}
    assert app.canvas.get_size() == (C.WIDTH, C.HEIGHT)
    assert app.canvas.get_at((C.WIDTH // 2, C.HEIGHT // 2)) != (0, 0, 0, 255)


def test_pictogramas_indicam_direcao_e_coleta_sem_depender_da_legenda(app):
    scene = TutorialScene(app, next_scene=FlightScene(app, "amazonia"), return_to=MapScene(app))
    kinds = ("move", "collect", "up", "down", "side")
    icons = {kind: pygame.image.tobytes(scene._step_icon(kind), "RGBA") for kind in kinds}
    assert len(set(icons.values())) == len(icons)

    cues = {}
    for kind in ("move", "collect", "up", "down", "side"):
        scene.step_index = next(index for index, step in enumerate(PRACTICE_STEPS) if step[0] == kind)
        if kind == "collect":
            scene._start_step()
        surface = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        scene._draw_action_cue(surface, kind, 550.0, 320.0)
        cues[kind] = pygame.image.tobytes(surface, "RGBA")
        assert surface.get_bounding_rect(min_alpha=1).size != (0, 0)
    assert len(set(cues.values())) == len(cues)


def test_tecla_mantida_na_licao_nao_pilota_a_proxima(app):
    scene = TutorialScene(app, next_scene=FlightScene(app, "amazonia"), return_to=MapScene(app))
    app.input.pressed.add(pygame.K_RIGHT)
    scene.advance_step()
    assert scene.step_index == 1
    assert pygame.K_RIGHT not in app.input.pressed
    assert scene.run.player.x == 0.0


def test_setas_verticais_ficam_fora_dos_paineis_de_titulo_e_botoes(app):
    scene = TutorialScene(app, next_scene=FlightScene(app, "amazonia"), return_to=MapScene(app))
    up = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
    scene._draw_action_cue(up, "up", 550.0, 180.0)
    assert up.get_bounding_rect(min_alpha=1).top > 128

    down = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
    scene._draw_action_cue(down, "down", 550.0, 470.0)
    assert down.get_bounding_rect(min_alpha=1).bottom < 570


def test_fluxo_de_inicializacao_nao_injeta_tutorial_antes_da_vila(app):
    app.profile.consentimento = True
    app.profile.piloto_montado = True
    app.profile.tutorial_visto = False
    assert isinstance(first_scene(app), VillageScene)
