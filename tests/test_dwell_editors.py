"""Regressões do treino de permanência e das escolhas visuais paginadas."""

from __future__ import annotations

import pygame

from dobramundo.scenes.hangar import MODELS_PER_PAGE, PATTERNS_PER_PAGE, HangarScene
from dobramundo.scenes.pilot import PilotScene
from dobramundo.scenes.tutorial import DWELL_TARGET, DwellPracticeScene, TutorialScene
from dobramundo.ui.widgets import Button, Menu


def test_menu_trava_a_mesma_chave_apos_rebuild_e_exige_saida():
    activated = []
    menu = None
    target = pygame.Rect(100, 100, 180, 90)

    def action():
        activated.append("ok")
        menu.set_buttons([Button(target, "Escolha", action, key="escolha")])

    menu = Menu([Button(target, "Escolha", action, key="escolha")])
    pointer = target.center
    assert not menu.update(2.9, pointer, 3.0)
    assert menu.update(0.2, pointer, 3.0)
    assert activated == ["ok"]
    assert not menu.update(3.5, pointer, 3.0)
    assert activated == ["ok"]

    # Sair do retângulo reabilita a chave; só uma nova permanência a aciona.
    menu.update(0.2, (20, 20), 3.0)
    menu.update(0.2, (20, 20), 3.0)
    assert not menu.update(2.9, pointer, 3.0)
    assert menu.update(0.2, pointer, 3.0)
    assert activated == ["ok", "ok"]


def test_editor_usa_permanencia_lenta_configuravel(app):
    app.options.permanencia = 1.0
    app.options.permanencia_editor = 4.0
    scene = PilotScene(app)
    scene.build()
    assert scene.dwell_time == 4.0


def test_tutorial_ancora_indicadores_no_viewport_de_alto_contraste(app):
    app.options.alto_contraste = True
    app.options.escala_contraste = 1.4
    app.apply_options()
    scene = TutorialScene(app)
    scene.draw(app.canvas)
    assert app.view.viewport.width < app.canvas.get_width()


def test_treino_mostra_saida_e_termina_sem_alterar_perfil(app):
    target = PilotScene(app, first_time=True)
    scene = DwellPracticeScene(app, next_scene=target)
    scene.build()
    app.options.permanencia_editor = 0.1
    before = app.profile.to_dict()
    pointer = DWELL_TARGET.center
    app.input.pointer = lambda: pointer
    scene.update(0.11)
    assert scene.phase == "leave"
    assert app.next_scene is None
    pointer = (100, 100)
    scene.update(0.36)
    assert app.next_scene is target
    assert app.profile.to_dict() == before


def test_hangar_mostra_tres_avioes_e_padroes_em_paginas_grandes(app):
    scene = HangarScene(app, "modelo")
    scene.build()
    models = [button for button in scene.menu.buttons if button.key.startswith("aviao_")]
    assert len(models) == MODELS_PER_PAGE
    assert len({button.rect.width for button in models}) == 1
    assert models[0].rect.width > 500
    scene.change_page("modelo", 1)
    assert scene.model_page == 1
    assert len([b for b in scene.menu.buttons if b.key.startswith("aviao_")]) == MODELS_PER_PAGE

    scene.set_tab("padrao")
    patterns = [button for button in scene.menu.buttons if button.key.startswith("padrao_")]
    assert len(patterns) == PATTERNS_PER_PAGE
    scene.change_page("padrao", 1)
    assert scene.pattern_page == 1
    assert len([b for b in scene.menu.buttons if b.key.startswith("padrao_")]) == PATTERNS_PER_PAGE


def test_compra_de_padrao_por_permanencia_nao_gasta_duas_vezes(app):
    scene = HangarScene(app, "padrao")
    app.profile.pontos = 700
    scene.build()
    button = next(b for b in scene.menu.buttons if b.key == "padrao_papel_reciclado")
    pointer = button.rect.center
    dwell = app.options.permanencia_editor
    assert scene.menu.update(dwell + 0.05, pointer, dwell)
    assert app.profile.pontos == 400
    assert "papel_reciclado" in app.profile.owned_patterns
    assert not scene.menu.update(dwell + 0.05, pointer, dwell)
    assert app.profile.pontos == 400
