"""Momento de foco, controle por posição, abertura didática, medida de movimento e histórico.

Cobre as mecânicas recentes do voo: o avião indo a um ponto da pista pelo corpo, a
seta que desacelera o mundo perto de uma batida, a abertura que ensina um obstáculo
por vez e a medida de movimento que entra no resultado e no histórico do perfil.
"""

from __future__ import annotations

import json
import random
from datetime import datetime

import pygame
import pytest
from conftest import DT, make_run

from dobramundo import config as C
from dobramundo.content.biomes import BIOMES
from dobramundo.game.entities import Entity
from dobramundo.game.focus import choose_escape
from dobramundo.game.player import Player
from dobramundo.game.run import FlightRun
from dobramundo.input.hub import InputHub
from dobramundo.input.pose import SEGMENTS, AxisMapper
from dobramundo.persistence import Profile
from dobramundo.scenes.result import apply_run

SEED = 7
# leituras suficientes para calibrar (2 s a 30 leituras por segundo, com folga)
CAL_READINGS = 70


def landmarks(points: dict, visibility: float = 0.9):
    data = [(0.5, 0.5, 0.0)] * 33
    for index, (x, y) in points.items():
        data[index] = (x, y, visibility)
    return data


class FakeSource:
    """Fonte de câmera falsa: devolve os pontos que o teste definir."""

    def __init__(self) -> None:
        self.error = None
        self.seq = 0
        self.points = None

    def start(self):
        pass

    def stop(self):
        pass

    def show(self, points) -> None:
        self.seq += 1
        self.points = points

    def snapshot(self):
        return self.seq, self.points, None


def calibrated(segment: str = "tronco_pe") -> AxisMapper:
    mapper = AxisMapper(SEGMENTS[segment])
    for _ in range(CAL_READINGS):
        mapper.feed((0.5, 0.5))
    return mapper


def threat_run(top: float | None = None, focus: bool = True) -> tuple:
    """Voo da Amazônia (normal) com um único obstáculo baixo na faixa 0, a 0,5 s de batida.

    top: altura do topo do obstáculo (None usa o da fase). Sem resíduos nem outros obstáculos.
    """
    run = FlightRun(BIOMES["amazonia"], "normal", rng=random.Random(SEED), focus=focus)
    run.world.entities.clear()
    run.world.spawn_pattern = lambda z: None
    run.focus.cooldown = 0.0
    spec = BIOMES["amazonia"].industrial_obstacles["low"][0]
    if top is not None:
        spec = spec._replace(y_max=top)
    # tempo até a frente do obstáculo tocar a caixa do avião = (z - 16 - (PLAYER_Z + 27)) / speed
    z = C.PLAYER_Z + 27.0 + 16.0 + 0.5 * run.speed
    entity = Entity(z, 0, "low", 0.0, spec.sprite, spec)
    run.world.entities.append(entity)
    return run, entity


# ------------------------------------------------------- alvo do corpo
@pytest.mark.parametrize(
    "ax, ay, esperado",
    [
        (0, 0, (0, C.REST_ALTITUDE)),
        (1, 1, (C.MAX_PLAYER_X, C.MAX_ALTITUDE)),
        (-1, -1, (-C.MAX_PLAYER_X, C.MIN_ALTITUDE)),
    ],
)
def test_comando_do_corpo_vira_ponto_da_pista(ax, ay, esperado):
    assert Player.command_target(ax, ay) == pytest.approx(esperado)


# -------------------------------------------------- controle por posição
def test_controle_por_posicao_chega_ao_alvo_sem_ultrapassar():
    player = Player()
    player.x, player.y = 0.0, C.START_ALTITUDE
    target = (120.0, 120.0)
    max_x = C.MAX_LATERAL_SPEED * player.stats.max_speed * DT + 1e-9
    max_y = C.MAX_VERTICAL_SPEED * player.stats.max_speed * DT + 1e-9
    for _ in range(3 * C.FPS):
        x0, y0 = player.x, player.y
        player.update(DT, 0.0, 0.0, target)
        assert abs(player.x - x0) <= max_x and abs(player.y - y0) <= max_y
        assert player.x <= target[0] + 1e-9 and player.y <= target[1] + 1e-9
    assert abs(player.x - target[0]) < 1.0 and abs(player.y - target[1]) < 1.0


def test_controle_por_posicao_parado_quando_ja_no_alvo():
    player = Player()
    player.x, player.y = 40.0, 90.0
    for _ in range(60):
        player.update(DT, 0.0, 0.0, (40.0, 90.0))
    assert player.x == pytest.approx(40.0) and player.y == pytest.approx(90.0)


# ----------------------------------------------------- eixos com mão parada
def test_eixos_mantidos_quando_o_ponto_some():
    mapper = calibrated()
    mapper.hold_when_lost = True
    for _ in range(40):
        mapper.feed((0.7, 0.3))
    before = mapper.axes()
    assert before[0] > 0.9 and before[1] > 0.9
    for _ in range(20):
        mapper.feed(None)
    assert mapper.axes() == before


def test_eixos_voltam_ao_centro_quando_o_ponto_some_sem_manter():
    mapper = calibrated()
    mapper.hold_when_lost = False
    for _ in range(40):
        mapper.feed((0.7, 0.3))
    before = mapper.axes()
    for _ in range(20):
        mapper.feed(None)
    after = mapper.axes()
    assert abs(after[0]) < 0.1 * before[0] and abs(after[1]) < 0.1 * before[1]


# ------------------------------------------------------ comando de voo
class TestFlightCommand:
    @staticmethod
    def body_hub(position: bool = True) -> tuple:
        hub = InputHub()
        source = FakeSource()
        hub.source_factory = lambda: source
        hub.set_segment("mao_direita")
        for _ in range(CAL_READINGS):
            source.show(landmarks({16: (0.5, 0.5)}))
            hub.update(1 / 30)
        if not position:
            hub.configure(1.0, 1.0, False, position=False)
        return hub, source

    def test_so_teclado_nao_tem_alvo(self):
        hub = InputHub()
        assert hub.flight_command() == (0.0, 0.0, None)
        hub.pressed.add(pygame.K_UP)
        ix, iy, target = hub.flight_command()
        assert (ix, iy) == (0.0, 1.0) and target is None

    def test_corpo_calibrado_com_controle_por_posicao_manda_alvo(self):
        hub, source = self.body_hub()
        assert hub.body_ready and hub.position_control
        ix, iy, target = hub.flight_command()
        assert (ix, iy) == (0.0, 0.0) and target == hub.body.axes()
        for _ in range(40):
            source.show(landmarks({16: (0.6, 0.4)}))
            hub.update(1 / 30)
        ix, iy, target = hub.flight_command()
        assert (ix, iy) == (0.0, 0.0)
        assert target == hub.body.axes() and target != (0.0, 0.0)

    def test_tecla_segurada_tem_prioridade_sobre_o_corpo(self):
        hub, source = self.body_hub()
        for _ in range(40):
            source.show(landmarks({16: (0.6, 0.4)}))
            hub.update(1 / 30)
        hub.pressed.add(pygame.K_RIGHT)
        ix, _iy, target = hub.flight_command()
        assert ix == 1.0 and target is None

    def test_sem_controle_por_posicao_nao_manda_alvo(self):
        hub, source = self.body_hub(position=False)
        for _ in range(40):
            source.show(landmarks({16: (0.6, 0.4)}))
            hub.update(1 / 30)
        assert hub.flight_command()[2] is None


# ------------------------------------------------------- momento de foco
def test_momento_de_foco_abre_com_seta_e_tempo_lento():
    run, _ = threat_run()
    run.update(DT, target=(0.0, 0.0))
    assert run.focus.state == "pending"
    assert run.focus.time_scale == C.FOCUS_SLOW
    assert ("foco", "up") in run.take_events()


def test_movimento_para_cima_acerta_e_o_obstaculo_nao_bate():
    run, entity = threat_run()
    run.update(DT, target=(0.0, 0.0))
    score = run.score
    run.update(DT, target=(0.0, 0.5))
    assert run.focus.state == "success" and entity.dodged
    assert run.score == score + C.FOCUS_POINTS
    assert ("foco_ok", "up") in run.take_events()
    for _ in range(6 * C.FPS):  # o obstáculo passa pelo avião no desvio guiado
        run.update(DT, target=(0.0, 0.5))
        if all(e is not entity for e in run.world.entities):
            break
    assert all(e is not entity for e in run.world.entities)
    assert run.lives == C.MAX_LIVES and not entity.hit


def test_sem_movimento_a_janela_acaba_em_tempo_real():
    run, _ = threat_run()
    run.update(DT, target=(0.0, 0.0))
    frames = 0
    while run.focus.state == "pending" and frames < 10 * C.FPS:
        run.update(DT, target=(0.0, 0.0))
        frames += 1
    assert abs(frames - C.FOCUS_WINDOW_S["normal"] * C.FPS) <= 2
    assert ("foco_quase", "up") in run.take_events()
    assert run.focus.misses == 1 and run.focus.successes == 0


def test_inclinacao_antes_do_momento_nao_conta():
    # topo em 115: com o comando em (0, 0,5) o corpo já cruza a caixa do obstáculo, então
    # o momento abre, mas a posição parada não é movimento novo
    run, _ = threat_run(top=115.0)
    run.update(DT, target=(0.0, 0.5))
    assert run.focus.state == "pending" and run.focus.direction == "up"
    for _ in range(10 * C.FPS):
        if run.focus.state != "pending":
            break
        run.update(DT, target=(0.0, 0.5))
    assert run.focus.state == "miss" and run.focus.successes == 0


def test_voo_sem_foco_nunca_abre_o_momento():
    run, _ = threat_run(focus=False)
    assert run.focus.enabled is False
    for _ in range(2 * C.FPS):
        run.update(DT, target=(0.0, 0.0))
    assert run.focus.state is None and run.focus.total == 0
    assert not any(name.startswith("foco") for name, _ in run.take_events())


# ----------------------------------------------------------- escape
def tower_at(lane: int, width: float | None = None):
    spec = BIOMES["amazonia"].industrial_obstacles["tower"][2]  # AM_ChamineTermeletrica, largura 62
    if width is not None:
        spec = spec._replace(width=width)
    return Entity(300.0, lane, "tower", 0.0, spec.sprite, spec), spec


@pytest.mark.parametrize("start_x, direction", [(-50.0, "left"), (50.0, "right")])
def test_torre_escapa_para_o_lado_em_que_o_aviao_esta(start_x, direction):
    entity, _ = tower_at(0)
    box = Player().hitbox()
    chosen = choose_escape(entity, box, (start_x, 60.0))
    assert chosen is not None and chosen[0] == direction


def test_torre_perto_da_borda_escolhe_o_outro_lado():
    # obstáculo na faixa da borda direita: pelo lado direito já não cabe, vai pela esquerda
    entity, _ = tower_at(1)
    chosen = choose_escape(entity, Player().hitbox(), (200.0, 60.0))
    assert chosen is not None and chosen[0] == "left"
    assert -C.MAX_PLAYER_X <= chosen[1][0] <= C.MAX_PLAYER_X


def test_torre_larga_sem_lado_livre_devolve_none():
    entity, _ = tower_at(0, width=2 * C.MAX_PLAYER_X)  # bloqueia a largura útil inteira
    assert choose_escape(entity, Player().hitbox(), (200.0, 60.0)) is None


# ---------------------------------------------------- abertura didática
def test_abertura_apresenta_uma_coisa_por_vez_e_nada_antes_da_hora():
    run = FlightRun(BIOMES["amazonia"], "normal", rng=random.Random(SEED), intro=True, focus=False)
    run.invincible = True
    lessons = []
    for _ in range(30 * C.FPS):
        run.update(DT, target=(0.0, 0.0))
        lessons += [data for name, data in run.take_events() if name == "lesson"]
        for entity in run.world.entities:
            if entity.spec is not None and not entity.lesson:
                assert run.world.distance + entity.z >= run.world.intro_until
    assert lessons == ["waste", "low", "gate", "tower"]


def test_sem_abertura_nao_ha_legendas_de_licao():
    run = FlightRun(BIOMES["amazonia"], "normal", rng=random.Random(SEED), intro=False, focus=False)
    run.invincible = True
    lessons = []
    for _ in range(30 * C.FPS):
        run.update(DT, target=(0.0, 0.0))
        lessons += [name for name, _ in run.take_events() if name == "lesson"]
    assert lessons == []


# ------------------------------------------------------ medida de movimento
def test_medida_de_movimento_soma_alcance_e_tempo_em_acao():
    run = make_run("amazonia", "normal")
    run.record_movement(DT, (-1.0, 0.0))
    for i in range(1, 61):
        run.record_movement(DT, (-1.0 + 2.0 * i / 60, 0.0))
    assert run.travel == pytest.approx(1.0)
    assert run.active_time == pytest.approx(1.0)


def test_resumo_do_voo_tem_as_chaves_do_historico():
    run = make_run("amazonia", "normal")
    summary = run.summary()
    expected = {"fase", "modo", "foco_acertos", "foco_total", "movimento_s", "alcances"}
    assert expected <= set(summary)
    assert summary["fase"] == "amazonia" and summary["modo"] == "normal"


# ------------------------------------------------------------ persistência
def test_historico_descarta_entradas_que_nao_sao_objetos_ou_textos_numeros():
    raw = {"historico": ["texto", 5, None, [1], {"a": 1, "b": True, "c": [1], "d": "ok", "e": 2.5, "f": None}]}
    profile = Profile.from_dict(raw)
    assert profile.historico == [{"a": 1, "d": "ok", "e": 2.5}]
    assert Profile.from_dict({"historico": ["x", 5, None]}).historico == []


def test_historico_fica_limitado_aos_voos_mais_recentes():
    entries = [{"n": i} for i in range(C.HISTORY_LIMIT + 20)]
    profile = Profile.from_dict({"historico": entries})
    assert len(profile.historico) == C.HISTORY_LIMIT
    assert profile.historico[-1] == {"n": C.HISTORY_LIMIT + 19}


def test_voos_por_fase_ignora_biomas_desconhecidos():
    profile = Profile.from_dict({"voos_fase": {"amazonia": 2, "marte": 5, "caatinga": 3}})
    assert profile.voos_fase == {"amazonia": 2, "caatinga": 3}


def test_opcoes_novas_sobrevivem_ao_json():
    profile = Profile()
    assert profile.opcoes.controle_posicao is True and profile.opcoes.momento_foco is True
    profile.opcoes.controle_posicao = False
    profile.opcoes.momento_foco = False
    profile.opcoes.efeitos_fortes = False
    again = Profile.from_dict(json.loads(json.dumps(profile.to_dict())))
    assert again.opcoes.controle_posicao is False
    assert again.opcoes.momento_foco is False
    assert again.opcoes.efeitos_fortes is False


def test_aplicar_voo_conta_a_fase_e_grava_o_historico():
    profile = Profile()
    profile.controle = "tronco_pe"
    run = make_run("amazonia", "normal")
    apply_run(profile, run)
    assert profile.voos_fase == {"amazonia": 1}
    assert len(profile.historico) == 1
    entry = profile.historico[0]
    assert entry["fase"] == "amazonia" and entry["controle"] == "tronco_pe"
    datetime.fromisoformat(entry["data"])
    apply_run(profile, make_run("amazonia", "normal"))
    assert profile.voos_fase == {"amazonia": 2} and len(profile.historico) == 2
