"""Cenas: todas desenham sem erro, compras descontam recursos, pausa automática, fluxo de telas."""

from __future__ import annotations

import pygame
import pytest
from test_controle import CAL_READINGS, FakeSource

from dobramundo import config as C
from dobramundo.content.progress import VILLAGE_BY_KEY
from dobramundo.core import first_scene
from dobramundo.scenes.about import AboutScene
from dobramundo.scenes.calibration import CalibrationScene
from dobramundo.scenes.consent import ConsentScene
from dobramundo.scenes.flight import FlightScene
from dobramundo.scenes.hangar import HangarScene
from dobramundo.scenes.intro import IntroScene, fold_pose
from dobramundo.scenes.map import MapScene
from dobramundo.scenes.options import OptionsScene
from dobramundo.scenes.pilot import PilotScene
from dobramundo.scenes.result import ResultScene
from dobramundo.scenes.upgrades import UpgradesScene
from dobramundo.scenes.village import VillageScene


def show(app, scene, frames: int = 3):
    app.go(scene)
    for _ in range(frames):
        app.step(1 / 60, [])
    return app.scene


def key(app, code: int) -> None:
    app.step(1 / 60, [pygame.event.Event(pygame.KEYDOWN, key=code, mod=0, unicode="")])


@pytest.mark.parametrize(
    "factory",
    [
        VillageScene,
        MapScene,
        HangarScene,
        lambda a: HangarScene(a, "cor"),
        lambda a: HangarScene(a, "padrao"),
        PilotScene,
        UpgradesScene,
        lambda a: UpgradesScene(a, "aviao"),
        OptionsScene,
        AboutScene,
        lambda a: AboutScene(a, "ods"),
        lambda a: AboutScene(a, "creditos"),
        lambda a: AboutScene(a, "referencias"),
        IntroScene,
        lambda a: ConsentScene(a, VillageScene(a)),
        lambda a: FlightScene(a, "amazonia"),
        lambda a: FlightScene(a, "caatinga"),
    ],
)
def test_cenas_desenham(app, factory):
    show(app, factory(app))
    assert app.canvas.get_size() == (C.WIDTH, C.HEIGHT)


def test_alto_contraste_e_espelhamento_desenham(app):
    app.options.alto_contraste = True
    app.options.espelhar = True
    app.options.rotacao = 180
    app.apply_options()
    show(app, FlightScene(app, "amazonia"), 5)
    assert app.view.high_contrast
    assert app.to_logical((0, 0)) == (0, C.HEIGHT - 1)


def test_movimento_reduzido_aplica_no_view_e_fixa_o_fundo(app):
    app.options.reduzir_movimento = True
    app.apply_options()
    assert app.view.reduce_motion
    before = app.backdrop_time
    app.backdrop(app.canvas, 1 / 60)
    assert app.backdrop_time == before


def test_inicio_passa_pelo_aviso_na_primeira_vez(app):
    app.profile.consentimento = False
    app.profile.piloto_montado = True
    consent = first_scene(app)
    assert isinstance(consent, ConsentScene)
    assert isinstance(consent.next_scene, VillageScene)


def test_a_primeira_tela_e_montar_o_piloto(app):
    """Piloto (1ª vez) -> aviso -> vila; a história fica opcional nas opções."""
    from dobramundo.scenes.pilot import PilotScene

    app.profile.consentimento = False
    app.profile.piloto_montado = False
    app.profile.abertura_vista = False
    first = first_scene(app)
    assert isinstance(first, PilotScene) and first.first_time
    assert isinstance(first.return_to, ConsentScene)
    assert isinstance(first.return_to.next_scene, VillageScene)
    first.finish()
    assert app.profile.piloto_montado
    assert app.next_scene is first.return_to


def test_historia_nao_bloqueia_primeiro_uso(app):
    app.profile.piloto_montado = True
    app.profile.consentimento = True
    app.profile.abertura_vista = False
    assert isinstance(first_scene(app), VillageScene)


def test_comprar_melhoria_da_vila_desconta_recursos(app):
    scene = show(app, UpgradesScene(app))
    cost = VILLAGE_BY_KEY["ponto_troca"].cost
    app.profile.recursos.update({key: amount + 4 for key, amount in cost.items()})
    scene.buy_village(VILLAGE_BY_KEY["ponto_troca"])
    assert "ponto_troca" in app.profile.vila
    assert all(app.profile.recursos[key] == 4 for key in cost)


def test_compra_sem_recursos_nao_acontece(app):
    scene = show(app, UpgradesScene(app, "aviao"))
    from dobramundo.content.progress import PART_BY_KEY

    scene.buy_part(PART_BY_KEY["leme"])
    assert app.profile.pecas["leme"] == 0 and scene.toast.text


def test_comprar_padrao_usa_pontos(app):
    scene = show(app, HangarScene(app, "padrao"))
    app.profile.pontos = 400
    scene.choose_pattern("kraft")
    assert "kraft" in app.profile.owned_patterns and app.profile.pontos == 100
    scene.choose_pattern("galaxia")
    assert "galaxia" not in app.profile.owned_patterns


def test_mapa_bloqueia_a_caatinga_sem_estrela(app):
    scene = show(app, MapScene(app))
    caatinga = next(b for b in scene.menu.buttons if b.key == "caatinga")
    assert not caatinga.enabled
    app.profile.estrelas["amazonia"] = 1
    scene.build()
    assert next(b for b in scene.menu.buttons if b.key == "caatinga").enabled


def test_pausa_do_supervisor(app):
    scene = show(app, FlightScene(app, "amazonia"))
    key(app, pygame.K_p)
    assert scene.paused
    distance = scene.run.world.distance
    app.step(1 / 60, [])
    assert scene.run.world.distance == distance
    key(app, pygame.K_p)
    assert not scene.paused


def test_pausa_automatica_e_retomada(app):
    source = FakeSource()
    app.input.source_factory = lambda: source
    app.profile.controle = "mao_direita"
    app.apply_options()
    from test_controle import landmarks

    for _ in range(CAL_READINGS):
        source.show(landmarks({16: (0.5, 0.5)}))
        app.input.update(1 / 30)
    scene = show(app, FlightScene(app, "amazonia"))
    for _ in range(80):
        source.show(landmarks({}))
        app.step(1 / 60, [])
    assert scene.paused and scene.auto_paused
    for _ in range(60 * 5):
        source.show(landmarks({16: (0.5, 0.5)}))
        app.step(1 / 60, [])
    assert not scene.paused


def test_controle_corporal_sem_calibrar_pede_calibracao(app):
    source = FakeSource()
    app.input.source_factory = lambda: source
    app.profile.controle = "tronco_sentado"
    app.apply_options()
    show(app, MapScene(app)).fly("amazonia")
    app.step(1 / 60, [])
    assert isinstance(app.scene, CalibrationScene)


def test_fim_do_voo_vai_para_o_resultado(app):
    scene = show(app, FlightScene(app, "caatinga"))
    scene.run.add_restoration(100.0)
    for _ in range(60 * 4):
        app.step(1 / 60, [])
    assert isinstance(app.scene, ResultScene)
    assert app.profile.estrelas["caatinga"] == 2  # sem leme e quilha: duas estrelas


def test_opcoes_mudam_o_perfil(app):
    scene = show(app, OptionsScene(app))
    scene.flip("silencio")
    scene.adjust("volume_geral", -0.3, 0.0, 1.0)
    scene.set_segment(1)
    assert app.options.silencio and app.options.volume_geral == pytest.approx(0.5)
    assert app.profile.controle == "pes"


def test_piloto_alterna_opcoes(app):
    scene = show(app, PilotScene(app))
    scene.cycle("cadeira", 1)
    scene.cycle("aparelho", 1)
    assert app.profile.piloto["cadeira"] == "sim" and app.profile.piloto["aparelho"] == "sim"


def test_dobradura_interpola_as_poses():
    start, end = fold_pose(0.0), fold_pose(1.0)
    assert start["body"][0] == (-1, -0.7) and end["body"][1] == (0, -0.85)


def test_self_test_completo(data_dir):
    from dobramundo.selftest import run_self_test

    assert run_self_test(45) == 0
    assert (data_dir / "self_test.json").is_file()


def test_abertura_so_na_primeira_vez(app):
    app.profile.abertura_vista = True
    app.profile.piloto_montado = True
    assert isinstance(first_scene(app), VillageScene)


def test_voltar_da_recalibracao_nao_reinicia_o_voo(app):
    scene = show(app, FlightScene(app, "amazonia"))
    scene.run.add_restoration(70.0)
    scene.run.take_events()
    banners = len(scene.banners)
    app.go(CalibrationScene(app, return_to=scene))
    app.step(1 / 60, [])
    app.go(scene)
    app.step(1 / 60, [])
    assert scene.music == "musica_amazonia_3"
    assert len(scene.banners) <= banners


def test_esc_na_vila_pergunta_antes_de_sair(app):
    scene = show(app, VillageScene(app))
    key(app, pygame.K_ESCAPE)
    assert scene.confirm_exit and app.running and isinstance(app.scene, VillageScene)
    key(app, pygame.K_ESCAPE)
    assert not scene.confirm_exit


def test_falha_ao_salvar_aparece_na_vila(app, monkeypatch):
    monkeypatch.setattr(app, "writer", lambda profile: False)
    app.save()
    show(app, VillageScene(app))
    assert app.save_failed


def test_superficie_aplica_o_segmento_sugerido(app):
    source = FakeSource()
    app.input.source_factory = lambda: source
    app.profile.controle = "tronco_pe"
    app.apply_options()
    scene = show(app, OptionsScene(app))
    from dobramundo.persistence import SURFACES

    scene.set_surface(SURFACES.index("chao"))
    assert app.profile.controle == "pes" and scene.toast.text
