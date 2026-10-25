"""Pista: trechos, sorteio de objetos por estágio, transformação do horizonte para o avião."""

from __future__ import annotations

import random

import pytest
from conftest import advance, make_run

from dobramundo import config as C
from dobramundo.content.biomes import BIOMES
from dobramundo.content.items import WASTE_KEYS
from dobramundo.game.world import World


def world(mode: str = "dificil", biome: str = "caatinga") -> World:
    return World(BIOMES[biome], mode, random.Random(5))


def test_pista_comeca_cheia_e_recicla_trechos():
    w = world()
    count = len(w.segments)
    assert w.segments[0] == C.SEGMENT_LENGTH and w.segments[-1] == C.TRACK_LENGTH
    w.advance(1.0, 500.0)
    assert len(w.segments) == count and w.segment_base > 0
    assert all(b - a == pytest.approx(C.SEGMENT_LENGTH) for a, b in zip(w.segments, w.segments[1:]))


def test_normal_mostra_um_quarto_dos_residuos():
    hard, normal = world("dificil"), world("normal")
    for w in (hard, normal):
        for i in range(400):
            w.spawn_pattern(3000.0 + i)
    count = {w.mode: sum(e.kind == "waste" for e in w.entities) for w in (hard, normal)}
    assert count["normal"] == pytest.approx(count["dificil"] / C.NORMAL_TRASH_EVERY, rel=0.1)


def test_residuos_alternam_os_quatro_tipos():
    w = world()
    w.waste_counter = 0
    kinds = [w.next_waste() for _ in range(8)]
    assert kinds == list(WASTE_KEYS) * 2


def test_obstaculos_seguem_a_tabela_do_bioma_e_do_estagio():
    w = world()
    industrial = {s.sprite for t in w.biome.industrial_obstacles.values() for s in t}
    solar = {s.sprite for t in w.biome.solar_obstacles.values() for s in t}
    assert all(e.sprite in industrial for e in w.entities if e.spec is not None)
    w.set_restoration(95.0)
    w.entities.clear()
    for i in range(200):
        w.spawn_pattern(C.TRACK_LENGTH + 100 + i)
    spawned = [e for e in w.entities if e.spec is not None]
    assert spawned and all(e.sprite in solar and e.solar for e in spawned)


def test_obstaculos_aparecem_em_ordem_fixa():
    w = world()
    sprites = [w.next_obstacle("low", False).sprite for _ in range(len(w.biome.industrial_obstacles["low"]) * 2)]
    first = sprites[: len(sprites) // 2]
    assert sprites == first * 2


def test_transformacao_chega_do_horizonte():
    w = world()
    w.set_restoration(C.GRASS_START_RESTORATION + 15.0)
    w.green_since.clear()
    w.visual = w.restoration
    w.advance(0.016, 1.0)
    assert w.green_since
    near = [i for i, z in enumerate(w.segments) if z < C.GREEN_CONVERT_Z]
    assert not any(w.segment_base + i in w.green_since for i in near)


def test_visual_alcanca_a_transformacao_aos_poucos():
    w = world()
    w.add_restoration(30.0)
    w.ease_visual(0.1)
    assert C.START_RESTORATION < w.visual < w.restoration
    for _ in range(600):
        w.ease_visual(0.1)
    assert w.visual == w.restoration


def test_estagio_visual_mistura_paletas():
    w = world()
    w.set_restoration(C.ERA_SPAN * 1.5)
    a, b, t = w.visual_stage_pair()
    assert a is w.biome.stages[1] and b is w.biome.stages[2] and t == pytest.approx(0.5)


def test_velocidade_normal_e_metade():
    assert make_run(mode="normal").speed == pytest.approx(make_run(mode="dificil").speed * C.NORMAL_SPEED_FACTOR)


def test_objetos_que_passaram_saem_da_pista():
    run = make_run(clear=False)
    advance(run, 3.0)
    assert all(e.z > C.PLAYER_Z - 70.0 for e in run.world.entities)
