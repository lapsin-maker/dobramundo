"""Metas curtas dentro do voo."""

from __future__ import annotations

import random

from conftest import advance, make_run

from dobramundo import config as C
from dobramundo.content.items import WASTE_KEYS
from dobramundo.game.entities import Entity
from dobramundo.game.missions import FIRST_DELAY_S, Mission, MissionTracker


def test_meta_aparece_depois_da_decolagem():
    tracker = MissionTracker("normal", random.Random(1))
    tracker.update(FIRST_DELAY_S - 0.1)
    assert tracker.current is None
    tracker.update(0.2)
    assert tracker.current is not None and tracker.text


def test_meta_de_coleta_conta_so_o_tipo_pedido():
    tracker = MissionTracker("normal")
    tracker.current = Mission("coletar", 2, "vidro")
    assert tracker.record("coletar", "papel") is None
    assert tracker.record("coletar", "vidro") is None
    assert tracker.record("coletar", "vidro") is not None
    assert tracker.current is None and tracker.completed == 1


def test_meta_cumprida_recompensa_o_voo(run):
    run.missions.current = Mission("powerup", 1)
    before = run.restoration
    run.world.entities.append(Entity(C.PLAYER_Z, 0, "shield", run.player.y))
    run.player.x = 0.0
    run.check_collisions()
    events = [n for n, _ in run.take_events()]
    assert "mission" in events and run.restoration > before
    assert sum(run.resources.values()) > 0


def test_desviar_conta_obstaculos_que_passam_sem_bater(run):
    run.missions.current = Mission("desviar", 1)
    spec = run.biome.industrial_obstacles["tower"][0]
    run.player.x = C.LANE_WIDTH  # faixa ao lado da torre, mas perto o bastante para valer
    run.world.entities.append(Entity(C.PLAYER_Z - 40.0, 1, "tower", 0.0, spec.sprite, spec))
    run.count_passes()
    assert run.missions.completed == 1


def test_metas_nao_repetem_o_tipo_seguido():
    tracker = MissionTracker("dificil", random.Random(4))
    kinds = []
    for _ in range(12):
        mission = tracker.pick()
        kinds.append(mission.kind)
        assert mission.kind != "coletar" or mission.waste in WASTE_KEYS
    assert all(a != b for a, b in zip(kinds, kinds[1:]))


def test_voo_real_cumpre_metas():
    run = make_run(mode="normal", clear=False)
    run.invincible = True
    advance(run, 60.0)
    assert run.missions.current is not None or run.missions.completed > 0
