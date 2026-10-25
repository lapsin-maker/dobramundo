"""Estilo "papel e aquarela": filtro dos sprites, formas de papel, fontes, piloto novo,
vila-diorama e abertura em páginas."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pygame
import pytest

from dobramundo import config as C
from dobramundo.content.pilot import ACCESSORIES, HAIR_STYLES, SKIN_TONES, option_keys
from dobramundo.engine import paper
from dobramundo.scenes.intro import PAGES, IntroScene, fold_pose
from dobramundo.scenes.pilot import PilotScene
from dobramundo.scenes.village import HOUSES, SLOTS, VillageScene, draw_village, village_progress
from dobramundo.ui import theme as T

ROOT = Path(__file__).resolve().parents[1]


def load_stylize():
    """O filtro é ferramenta de build: precisa de numpy e Pillow, que o jogo não exige."""
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")
    spec = importlib.util.spec_from_file_location("stylize", ROOT / "tools" / "stylize.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["stylize"] = module
    spec.loader.exec_module(module)
    return module


# ------------------------------------------------------------ filtro
def test_filtro_mantem_tamanho_e_poe_contorno_de_tinta():
    stylize = load_stylize()
    from PIL import Image

    image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
    for y in range(10, 30):
        for x in range(10, 30):
            image.putpixel((x, y), (200, 90, 60, 255))
    out = stylize.stylize_image(image, "teste", outline=2)
    assert out.size == image.size
    assert out.getpixel((20, 20))[3] == 255
    rim = out.getpixel((8, 20))  # 2 px fora da forma: tinta
    assert rim[3] > 200 and rim[2] > rim[0]  # azulada (tinta), não a cor do objeto
    assert out.getpixel((2, 2))[3] == 0


def test_filtro_tem_parametros_proprios_para_avioes():
    stylize = load_stylize()
    assert stylize.params_for("plane_sprites")["outline"] == 1
    assert stylize.params_for("biome_sprites") == {}


# ------------------------------------------------------------- papel
def test_formas_de_papel_desenham_sem_erro():
    screen = pygame.Surface((400, 300))
    paper.ink_polygon(screen, paper.hill_points(0, 400, 200, 80, 3, 1), (100, 160, 100))
    line = paper.bezier((0, 100), (100, 150), (300, 50), (400, 120), 20)
    paper.ink_polygon(screen, paper.ribbon(line, [20] * len(line)), (60, 160, 200))
    paper.tree(screen, (200, 250), 60, (60, 160, 80), (120, 80, 40), 2)
    paper.person(screen, (100, 280), 40, (240, 120, 50), (230, 180, 140), 1.0)
    paper.shadow(screen, (200, 280), 60, 14)
    paper.smoke(screen, (300, 100), 1.0, 1.0)
    paper.sparkles(screen, screen.get_rect(), 1.0, 1.0, (250, 200, 60))
    assert screen.get_at((200, 250))[:3] != (0, 0, 0)


def test_bezier_passa_pelas_pontas():
    line = paper.bezier((0, 0), (10, 10), (20, 10), (30, 0), 10)
    assert line[0] == (0, 0) and line[-1] == (30, 0) and len(line) == 11


# ------------------------------------------------------------ fontes
def test_fontes_embutidas_carregam():
    text = T.Text()
    assert text.font(24, bold=True) is not None
    hand = text.font(24, hand=True)
    assert hand.size("Dobra")[0] > 0
    assert (ROOT / "assets" / "fonts" / "OFL-Fredoka.txt").is_file()


def test_painel_com_sombra_nao_cresce_o_retangulo():
    screen = pygame.Surface((200, 100), pygame.SRCALPHA)
    T.panel(screen, pygame.Rect(10, 10, 100, 50))
    assert screen.get_at((50, 30))[3] > 200  # dentro do cartão
    assert screen.get_at((112, 40))[3] > 0  # sombra à direita
    assert screen.get_at((150, 80))[3] == 0


# ------------------------------------------------------------- piloto
def test_piloto_tem_tons_de_fantasia_e_cabelos_variados():
    keys = option_keys(SKIN_TONES)
    assert {"roxo", "azul", "verde", "rosa"} <= set(keys)
    hair = option_keys(HAIR_STYLES)
    assert {"franja", "chiquinhas", "puffs", "moicano", "hijab", "raspado"} <= set(hair)
    assert {"flor", "tiara", "coroa"} <= set(option_keys(ACCESSORIES))


def test_piloto_com_hijab_e_tons_de_fantasia_compoe(app):
    look = dict(app.profile.piloto)
    look.update(pele="roxo", cabelo="hijab", cor_cabelo="azul", acessorio="coroa")
    for view in ("menu", "flight", "segura"):
        surface = app.view.skin.pilots.compose(view, look)
        assert surface is not None and surface.get_width() > 0


def test_surpresa_nao_sorteia_itens_assistivos(app):
    scene = PilotScene(app)
    app.go(scene)
    app.step(1 / 60, [])
    app.profile.piloto["cadeira"] = "sim"
    scene.shuffle()
    assert app.profile.piloto["cadeira"] == "sim"


def test_pronto_marca_o_piloto_e_segue(app):
    target = VillageScene(app)
    scene = PilotScene(app, first_time=True, return_to=target)
    scene.finish()
    assert app.profile.piloto_montado and app.next_scene is target


# ---------------------------------------------------------------- vila
def test_vila_cada_melhoria_tem_lugar_e_as_casas_mudam_aos_poucos(app):
    from dobramundo.content.progress import VILLAGE_UPGRADES

    assert {u.key for u in VILLAGE_UPGRADES} == set(SLOTS)
    assert len(HOUSES) == 5
    scene = VillageScene(app)
    app.go(scene)
    app.step(1 / 60, [])
    for owned in (0, 3, len(VILLAGE_UPGRADES)):
        app.profile.vila = [u.key for u in VILLAGE_UPGRADES][:owned]
        draw_village(scene, app.canvas, highlight="horta")
    assert village_progress(app.profile) == 1.0


# ------------------------------------------------------------ abertura
def test_abertura_tem_quatro_paginas_e_vira_no_fim_de_cada_uma(app):
    scene = IntroScene(app)
    app.go(scene)
    app.step(1 / 60, [])
    assert scene.page()[0] == 0
    scene.time = PAGES[0] + 0.1
    assert scene.page()[0] == 1
    scene.time = PAGES[0] - 0.1  # no fim da página 1, a virada já começou
    assert 0.0 < scene.page()[2] < 1.0
    scene.time = sum(PAGES) - 0.5
    assert scene.page()[0] == 3
    for t in (0.5, PAGES[0] + 1.0, sum(PAGES[:2]) + 2.0, sum(PAGES[:3]) + 2.0):
        scene.time = t
        scene.draw(app.canvas)
    assert app.canvas.get_size() == (C.WIDTH, C.HEIGHT)


def test_dobradura_vai_da_folha_ao_aviao():
    start, end = fold_pose(0.0), fold_pose(1.0)
    assert start["body"][0] == (-1, -0.7)
    assert end["body"][1] == (0, -0.85)
    middle = fold_pose(0.5)
    assert len(middle["body"]) == 6


@pytest.mark.parametrize("pattern", ["liso", "jornal"])
def test_pintura_padrao_e_lisa_e_jornal_continua_disponivel(pattern):
    from dobramundo.content.planes import DEFAULT_PATTERN, FREE_PATTERNS

    assert DEFAULT_PATTERN == "liso"
    assert pattern in FREE_PATTERNS
