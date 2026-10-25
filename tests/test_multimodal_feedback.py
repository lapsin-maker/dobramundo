"""Retorno multimodal: sons concorrentes e relógios visuais dos benefícios."""

import pygame

from dobramundo.audio import Audio
from dobramundo.persistence import Options
from dobramundo.scenes.flight import FlightScene


def test_fanfarras_nao_somam_e_prioridade_nao_regride():
    audio = Audio()
    try:
        audio.play("sfx_coleta_papel")
        audio.play("sfx_compra")
        audio.play("sfx_estrela")
        audio.play("sfx_estagio")
        assert audio.effects[1].get_sound() is audio.sound("sfx_estagio")
        audio.play("sfx_compra")
        assert audio.effects[1].get_sound() is audio.sound("sfx_estagio")
        audio.play("sfx_fim_fase")
        assert audio.effects[1].get_sound() is audio.sound("sfx_fim_fase")
        assert not any(pygame.mixer.Channel(i).get_busy() for i in range(4, 16))
        audio.apply(Options(silencio=True))
        assert not any(channel.get_busy() for channel in audio.effects)
    finally:
        audio.stop()


def test_dois_beneficios_tem_relogios_visuais_independentes(app):
    scene = FlightScene(app, "amazonia")
    scene.run.shield_timer = 6.0
    scene.run.magnet_timer = 7.0
    screen = app.canvas
    scene.draw_hud(screen)
    first = screen.subsurface((940, 90, 140, 62)).copy()
    scene.run.shield_timer = 2.0
    scene.draw_hud(screen)
    second = screen.subsurface((940, 90, 140, 62)).copy()
    assert pygame.image.tobytes(first, "RGB") != pygame.image.tobytes(second, "RGB")
    # Só o relógio do escudo mudou; o ímã à direita conserva a informação.
    assert pygame.image.tobytes(first.subsurface((80, 0, 60, 62)), "RGB") == pygame.image.tobytes(
        second.subsurface((80, 0, 60, 62)), "RGB"
    )


def test_comemoracao_reduzida_nao_modifica_fisica_e_pausa_preserva_selo(app):
    scene = FlightScene(app, "amazonia")
    app.go(scene)
    app.step(1 / 60, [])
    app.options.reduzir_movimento = True
    app.apply_options()
    scene.celebration = 1.8
    scene.pause()
    before = (scene.run.player.x, scene.run.player.y, scene.run.world.distance)
    app.step(1 / 60, [])
    assert scene.celebration == 1.8
    assert before == (scene.run.player.x, scene.run.player.y, scene.run.world.distance)
