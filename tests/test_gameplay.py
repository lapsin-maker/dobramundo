"""Regras do voo: colisão por tipo de obstáculo, coleta, combo, power-ups, vidas, estrelas."""

from __future__ import annotations

import pytest
from conftest import advance, make_run

from dobramundo import config as C
from dobramundo.content.biomes import BIOMES
from dobramundo.content.items import WASTE_KEYS
from dobramundo.content.progress import RESOURCES_PER_WASTE
from dobramundo.game.entities import Entity


def obstacle(run, kind: str, z: float = C.PLAYER_Z, lane: int = 0, solar: bool = False) -> Entity:
    table = BIOMES[run.biome.key].solar_obstacles if solar else run.biome.industrial_obstacles
    spec = table[kind][0]
    entity = Entity(z, lane, kind, 0.0, spec.sprite, spec, solar)
    run.world.entities.append(entity)
    return entity


def place(run, x: float = 0.0, y: float = 60.0) -> None:
    run.player.x, run.player.y = x, y
    run.player.vx = run.player.vy = 0.0


# ----------------------------------------------------------------- colisões
@pytest.mark.parametrize("altitude, hits", [(60.0, True), (112.0, True), (117.0, False), (150.0, False)])
def test_obstaculo_baixo_pede_passar_por_cima(run, altitude, hits):
    place(run, y=altitude)
    obstacle(run, "low")
    run.check_collisions()
    assert (run.lives < C.MAX_LIVES) is hits


@pytest.mark.parametrize("altitude, hits", [(30.0, False), (80.0, False), (88.0, False), (100.0, True), (140.0, True)])
def test_portal_pede_passar_por_baixo(run, altitude, hits):
    place(run, y=altitude)
    obstacle(run, "gate")
    run.check_collisions()
    assert (run.lives < C.MAX_LIVES) is hits


@pytest.mark.parametrize("x, hits", [(0.0, True), (C.LANE_WIDTH, False), (-C.LANE_WIDTH, False)])
def test_torre_pede_desviar_para_o_lado(run, x, hits):
    place(run, x=x, y=150.0)
    obstacle(run, "tower")
    run.check_collisions()
    assert (run.lives < C.MAX_LIVES) is hits


def test_obstaculo_longe_nao_colide(run):
    place(run)
    obstacle(run, "low", z=C.PLAYER_Z + 120)
    run.check_collisions()
    assert run.lives == C.MAX_LIVES


def test_invulnerabilidade_depois_da_colisao(run):
    place(run)
    obstacle(run, "low")
    run.check_collisions()
    obstacle(run, "low")
    run.check_collisions()
    assert run.lives == C.MAX_LIVES - 1


def test_tres_colisoes_terminam_o_voo(run):
    place(run)
    for _ in range(C.MAX_LIVES):
        run.invulnerable_timer = 0.0
        obstacle(run, "low")
        run.check_collisions()
    assert run.lives == 0 and run.game_over and run.finished
    assert ("game_over", 0) in run.take_events()


def test_escudo_e_demonstracao_evitam_dano(run):
    place(run)
    run.shield_timer = 3.0
    obstacle(run, "low")
    run.check_collisions()
    run.shield_timer = 0.0
    run.invincible = True
    obstacle(run, "low")
    run.check_collisions()
    assert run.lives == C.MAX_LIVES


def test_pecas_mantem_a_mesma_tolerancia_de_colisao():
    plain = make_run().player.hitbox()
    tuned = make_run(parts={"estabilizador": 2}).player.hitbox()
    assert tuned == plain


# ------------------------------------------------------------------- coleta
def waste(run, kind: str = "papel", y: float = 60.0, lane: int = 0, z: float = C.PLAYER_Z) -> Entity:
    entity = Entity(z, lane, "waste", y, kind)
    run.world.entities.append(entity)
    return entity


@pytest.mark.parametrize("height", C.TRASH_HEIGHTS)
def test_coleta_nas_tres_altitudes(run, height):
    place(run, y=min(C.MAX_ALTITUDE, height))
    waste(run, y=height)
    run.check_collisions()
    assert run.resources["papel"] == RESOURCES_PER_WASTE["dificil"]


def test_cada_tipo_vira_o_recurso_certo(run):
    place(run)
    for kind in WASTE_KEYS:
        waste(run, kind)
    run.check_collisions()
    assert all(run.resources[k] == 1 for k in WASTE_KEYS)
    assert [d for n, d in run.take_events() if n == "collect"] == list(WASTE_KEYS)


def test_normal_rende_mais_por_coleta():
    normal, hard = make_run(mode="normal"), make_run(mode="dificil")
    for r in (normal, hard):
        place(r)
        waste(r)
        r.check_collisions()
    assert normal.resources["papel"] == 4 * hard.resources["papel"]
    assert normal.restoration - C.START_RESTORATION == pytest.approx(C.NORMAL_RESTORATION_PER_TRASH)
    assert hard.restoration - C.START_RESTORATION == pytest.approx(C.RESTORATION_PER_TRASH)
    assert normal.score == C.NORMAL_TRASH_POINTS and hard.score == C.HARD_TRASH_POINTS


def test_combo_sobe_a_cada_quatro_coletas_no_dificil(run):
    place(run)
    for _ in range(8):
        waste(run)
        run.check_collisions()
    assert run.combo == 3


def test_normal_nao_tem_combo():
    run = make_run(mode="normal")
    place(run)
    for _ in range(8):
        waste(run)
        run.check_collisions()
    assert run.combo == 1


def test_sequencia_zera_quando_o_tempo_do_combo_acaba(run):
    place(run)
    for _ in range(3):
        waste(run)
        run.check_collisions()
    advance(run, C.COMBO_WINDOW_S + 0.1)
    assert run.streak == 0 and run.combo == 1


def test_ima_alcanca_a_faixa_vizinha(run):
    place(run)
    run.magnet_timer = 5.0
    waste(run, lane=1)
    run.check_collisions()
    assert run.resources["papel"] == 1


def test_colisao_zera_o_combo(run):
    place(run)
    run.combo, run.streak = 4, 9
    obstacle(run, "low")
    run.check_collisions()
    assert run.combo == 1 and run.streak == 0


# ---------------------------------------------------------------- power-ups
def powerup(run, kind: str) -> None:
    run.world.entities.append(Entity(C.PLAYER_Z, 0, kind, 60.0))


def test_escudo_e_ima_duram_o_tempo_certo(run):
    place(run)
    powerup(run, "shield")
    powerup(run, "magnet")
    run.check_collisions()
    assert run.shield_timer == C.SHIELD_S and run.magnet_timer == C.MAGNET_S


def test_reparo_devolve_vida_ou_transforma(run):
    place(run)
    run.lives = 1
    powerup(run, "repair")
    run.check_collisions()
    assert run.lives == 2
    before = run.restoration
    run.lives = C.MAX_LIVES
    powerup(run, "repair")
    run.check_collisions()
    assert run.restoration == pytest.approx(before + C.REPAIR_RESTORATION)


# ------------------------------------------------------- estágios e estrelas
def test_estrelas_e_estagios_seguem_os_limiares(run):
    run.add_restoration(30.0)  # 35%
    events = run.take_events()
    assert run.stage == 1 and run.stars == 1
    assert ("stage", 1) in events and ("star", 1) in events
    run.add_restoration(35.0)  # 70%
    assert run.stage == 2 and run.stars == 2


def test_terceira_estrela_exige_as_pecas_da_fase():
    without = make_run("amazonia")
    without.add_restoration(100.0)
    assert without.complete and without.stars == 2
    with_parts = make_run("amazonia", parts=BIOMES["amazonia"].required_parts)
    with_parts.add_restoration(100.0)
    assert with_parts.stars == 3


def test_fase_termina_depois_do_voo_final(run):
    run.add_restoration(100.0)
    assert run.complete and not run.finished
    advance(run, 3.2)
    assert run.finished


@pytest.mark.parametrize("mode", ["normal", "dificil"])
def test_fase_dura_alguns_minutos(mode):
    """Equilíbrio: pegando 4 de cada 10 resíduos, a fase leva de 2,5 a 6 minutos."""
    import random

    run = make_run(mode=mode, clear=False)
    run.invincible = True
    rng, t = random.Random(2), 0.0
    while not run.complete and t < 600:
        for entity in run.world.entities:
            # a marca fica no objeto: id() se repete quando objetos antigos são liberados
            if entity.kind == "waste" and not hasattr(entity, "decided") and entity.z <= C.PLAYER_Z + 60:
                entity.decided = True
                if rng.random() < 0.4:
                    run.player.x, run.player.y = entity.x, min(C.MAX_ALTITUDE, entity.y)
        run.update(1 / 30)
        t += 1 / 30
    assert 150 <= t <= 360, f"{mode}: {t / 60:.1f} min"
