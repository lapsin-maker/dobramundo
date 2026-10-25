"""Testes direcionados para aparência, migração e escolhas do piloto 2D."""

from __future__ import annotations

import pygame

from dobramundo.content.pilot import DEFAULT_PILOT, SKIN_TONES, UNSELECTED, normalize_pilot
from dobramundo.persistence import Profile
from dobramundo.scenes.pilot import PAGE_BY_FIELD, PilotScene, mobility


def test_primeiro_piloto_neutro_sem_tom_ou_cabelo_preselecionados():
    assert DEFAULT_PILOT["pele"] == UNSELECTED
    assert DEFAULT_PILOT["cabelo"] == UNSELECTED
    assert DEFAULT_PILOT["cor_cabelo"] == UNSELECTED
    assert DEFAULT_PILOT["olhos"] == UNSELECTED
    assert normalize_pilot({})["pele"] == normalize_pilot({})["cabelo"] == UNSELECTED


def test_save_antigo_preserva_aparencia_e_completa_olhos_andador():
    old = Profile.from_dict({"piloto": {"pele": "pele5", "cabelo": "trancas", "cadeira": "sim"}})
    assert old.piloto["pele"] == "pele5" and old.piloto["cabelo"] == "trancas"
    assert old.piloto["olhos"] == UNSELECTED and old.piloto["andador"] == "nao"


def test_normalizacao_resolve_cadeira_e_andador_mutuamente_exclusivos():
    look = normalize_pilot({"cadeira": "sim", "andador": "sim"})
    assert look["cadeira"] == "sim" and look["andador"] == "nao"


def test_piloto_aquarela_renderiza_todas_as_vistas_e_dispositivos(app):
    renderer = app.view.skin.pilots
    for view in ("menu", "flight", "segura", "lanca"):
        for device in ({"cadeira": "nao", "andador": "nao"}, {"cadeira": "sim"}, {"andador": "sim"}):
            look = {**DEFAULT_PILOT, **device, "pele": "pele4", "cabelo": "crespo", "olhos": "verdes",
                    "aparelho": "sim", "oculos": "redondo"}
            image = renderer.compose(view, look)
            assert image is not None and image.get_size() == (190, 240)
            assert image.get_bounding_rect(min_alpha=1).width > 120


def test_cabelos_longos_nao_cobrem_o_rosto_em_nenhuma_vista(app):
    skin = next(option.color for option in SKIN_TONES if option.key == "pele4")
    for hair in ("longo", "trancas", "hijab"):
        # Em flight a nuca fica voltada para a camera; nao ha rosto a expor.
        for view in ("menu", "segura", "lanca"):
            image = app.view.skin.pilots.compose(view, {**DEFAULT_PILOT, "pele": "pele4", "cabelo": hair})
            assert image.get_at((95, 116))[:3] == skin


def test_vista_de_voo_mostra_nuca_sem_tracos_faciais(app):
    skin = next(option.color for option in SKIN_TONES if option.key == "pele4")
    image = app.view.skin.pilots.compose("flight", {**DEFAULT_PILOT, "pele": "pele4"})
    # Os pontos onde ficam as pupilas e o sorriso nas vistas frontais sao nuca.
    assert image.get_at((76, 72))[:3] == skin
    assert image.get_at((114, 72))[:3] == skin
    assert image.get_at((95, 103))[:3] == skin


def test_dispositivos_assistivos_afetam_as_quatro_vistas_e_montagens(app):
    renderer = app.view.skin.pilots
    base = dict(DEFAULT_PILOT, pele="pele4", cabelo="cacheado")
    for view in ("menu", "flight", "segura", "lanca"):
        neutral = renderer.compose(view, base)
        wheelchair = renderer.compose(view, dict(base, cadeira="sim"))
        walker = renderer.compose(view, dict(base, andador="sim"))
        assert pygame.image.tobytes(neutral, "RGBA") != pygame.image.tobytes(wheelchair, "RGBA")
        assert pygame.image.tobytes(neutral, "RGBA") != pygame.image.tobytes(walker, "RGBA")
    plane = app.view.skin.base("dart", "flight")
    mounted = [renderer.mount(plane, "dart", "flight", dict(base, **device))
               for device in ({}, {"cadeira": "sim"}, {"andador": "sim"})]
    assert pygame.image.tobytes(mounted[0], "RGBA") != pygame.image.tobytes(mounted[1], "RGBA")
    assert pygame.image.tobytes(mounted[0], "RGBA") != pygame.image.tobytes(mounted[2], "RGBA")


def test_montagem_no_aviao_preserva_api_ancoras(app):
    renderer = app.view.skin.pilots
    plane = app.view.skin.base("dart", "flight")
    assert plane is not None
    mounted = renderer.mount(plane, "dart", "flight", {**DEFAULT_PILOT, "andador": "sim"})
    assert isinstance(mounted, pygame.Surface)
    assert mounted.get_width() >= plane.get_width() and mounted.get_height() >= plane.get_height()


def test_categorias_de_personalizacao_e_mobilidade_mutua(app):
    scene = PilotScene(app, first_time=True)
    scene.build()
    assert set(PAGE_BY_FIELD) >= {"pele", "cabelo", "olhos", "oculos", "aparelho", "mobilidade"}
    scene.choose("mobilidade", "andador")
    assert mobility(app.profile.piloto) == "andador"
    scene.choose("mobilidade", "cadeira")
    assert mobility(app.profile.piloto) == "cadeira" and app.profile.piloto["andador"] == "nao"


def test_surpresa_preserva_todos_os_dispositivos_assistivos(app):
    scene = PilotScene(app)
    app.profile.piloto.update({"aparelho": "sim", "andador": "sim", "cadeira": "nao",
                              "oculos": "redondo", "acessorio": "abafador"})
    scene.shuffle()
    assert app.profile.piloto["aparelho"] == "sim"
    assert app.profile.piloto["andador"] == "sim" and app.profile.piloto["cadeira"] == "nao"
    assert app.profile.piloto["oculos"] == "redondo"
    assert app.profile.piloto["acessorio"] == "abafador"
