"""Regressões da interface em papel: ícones cacheados, dwell e telas redesenhadas."""

from __future__ import annotations

import pygame

from dobramundo.content.planes import PLANE_COLORS, PLANE_MODELS, PLANE_PATTERNS
from dobramundo.game.missions import Mission
from dobramundo.scenes.flight import FlightScene
from dobramundo.scenes.hangar import HangarScene
from dobramundo.scenes.intro import PAGES, IntroScene
from dobramundo.scenes.result import ResultScene
from dobramundo.ui import theme as T
from dobramundo.ui.widgets import Button, Menu


def test_pictogramas_sao_superficies_cacheadas():
    first = T.icon_surface("portal", 48, T.TEAL)
    second = T.icon_surface("portal", 48, T.TEAL)
    assert first is second
    assert first.get_size() == (48, 48)


def test_botao_com_icone_preserva_ativacao_por_dwell():
    hits = []
    button = Button(
        pygame.Rect(0, 0, 180, 80),
        "Próxima",
        lambda: hits.append("next"),
        icon=T.icon_surface("next", 32),
    )
    menu = Menu([button])
    assert not menu.update(0.4, (30, 30), 1.0)
    assert menu.update(0.6, (30, 30), 1.0)
    assert hits == ["next"]
    menu.update(0.2, (30, 30), 1.0)
    assert hits == ["next"]


def test_alvo_sob_ponteiro_exato_vence_margem_do_cartao_vizinho():
    first = Button(pygame.Rect(0, 0, 100, 100), "1", lambda: None)
    second = Button(pygame.Rect(110, 0, 100, 100), "2", lambda: None)
    menu = Menu([first, second])
    menu.update(0.4, (50, 50), 1.0)
    assert menu.hover is first
    menu.update(0.1, (115, 50), 1.0)
    assert menu.hover is second
    assert menu.dwell == 0.1


def test_intro_manual_pode_avancar_voltar_e_pular_sem_auto(app):
    app.options.abertura_automatica = False
    scene = IntroScene(app)
    scene.build()
    scene.update(PAGES[0] + 1.0)
    assert scene.page()[0] == 0
    assert scene.page()[2] == 0.0
    scene.advance_page()
    assert scene.page()[0] == 1
    scene.previous_page()
    assert scene.page()[0] == 0
    scene.finish()
    assert app.profile.abertura_vista


def test_hangar_preserva_todas_as_opcoes_em_cards_legiveis(app):
    scene = HangarScene(app)
    scene.build()
    assert len([b for b in scene.menu.buttons if b.key.startswith("aviao_")]) == len(PLANE_MODELS) == 11
    scene.tab = "cor"
    scene.build()
    assert len([b for b in scene.menu.buttons if b.key.startswith("cor_")]) == len(PLANE_COLORS)
    scene.tab = "padrao"
    scene.build()
    assert len([b for b in scene.menu.buttons if b.key.startswith("padrao_")]) == len(PLANE_PATTERNS)
    scene.draw(app.canvas)
    assert app.canvas.get_size() == (1100, 650)


def test_hud_missao_pictografica_e_resultado_desempenham(app, run):
    flight = FlightScene(app, "amazonia")
    flight.run.missions.current = Mission("coletar", 5, "papel")
    flight.run.missions.progress = 2
    flight.run.resources["papel"] = 3
    flight.draw_hud(app.canvas)
    flight.draw_pause_rewards(app.canvas, pygame.Rect(130, 80, 840, 520))

    run.complete = True
    run.world.set_restoration(100.0)
    run.stars = 2
    run.score = 250
    run.resources["papel"] = 4
    result = ResultScene(app, run)
    result.draw(app.canvas)
    assert app.profile.recursos["papel"] >= 4
    assert app.canvas.get_size() == (1100, 650)
