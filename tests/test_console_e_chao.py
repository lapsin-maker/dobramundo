"""Módulos novos: orientação da projeção, calibração do chão, console T-TEA, perfil, cartucho e cena de projeção.

Tudo determinístico e sem webcam: as fontes de pontos são falsas (FakeSource de test_controle).
"""

from __future__ import annotations

import ast
import importlib.util
import math
from pathlib import Path

import pygame
import pytest
from helpers import FakeSource, landmarks

from dobramundo import __version__
from dobramundo import config as C
from dobramundo.engine.orientation import game_to_screen, orient, rotate_point, screen_to_game, unrotate_point
from dobramundo.input.console import TrackingSource, body_points, floor_indicator_position, floor_position
from dobramundo.input.floor import TARGETS, FloorMap, apply, expand_reach, feet_point, homography
from dobramundo.input.hub import RECENTER_S, InputHub
from dobramundo.input.pose import SEGMENTS, AxisMapper, BodyControl, FloorControl
from dobramundo.persistence import Profile
from dobramundo.scenes.projection import SHOW_TARGETS_S, ProjectionScene
from dobramundo.ui.widgets import Button, Menu

ROOT = Path(__file__).resolve().parent.parent
ROTACOES = (0, 90, 180, 270)
PONTOS = [(0.0, 0.0), (0.2, 0.7), (0.5, 0.5), (1.0, 1.0), (0.9, 0.1)]


# ----------------------------------------------------------- orientação
@pytest.mark.parametrize("rotacao", ROTACOES)
@pytest.mark.parametrize("espelho", (False, True))
def test_rotacao_e_desfeita_pelo_inverso(rotacao, espelho):
    for x, y in PONTOS:
        u, v = rotate_point(x, y, rotacao, espelho)
        assert unrotate_point(u, v, rotacao, espelho) == pytest.approx((x, y), abs=1e-9)


@pytest.mark.parametrize("rotacao", ROTACOES)
@pytest.mark.parametrize("espelho", (False, True))
def test_jogo_e_janela_sao_inversos(rotacao, espelho):
    for x, y in PONTOS:
        sx, sy = game_to_screen(x, y, rotacao, espelho)
        assert screen_to_game(sx, sy, rotacao, espelho) == pytest.approx((x, y), abs=1e-9)


@pytest.mark.parametrize("rotacao", ROTACOES)
@pytest.mark.parametrize("espelho", (False, True))
def test_orient_mantem_o_tamanho_do_canvas(rotacao, espelho):
    canvas = pygame.Surface((C.WIDTH, C.HEIGHT))
    assert orient(canvas, rotacao, espelho).get_size() == (C.WIDTH, C.HEIGHT)


def test_centro_da_janela_em_pe_e_o_centro_do_jogo():
    assert game_to_screen(0.5, 0.5, 90) == pytest.approx((0.5, 0.5))
    assert screen_to_game(0.5, 0.5, 90) == pytest.approx((0.5, 0.5))
    assert screen_to_game(0.5, 0.5, 270) == pytest.approx((0.5, 0.5))


# ------------------------------------------------------------------ chão
CAMERA_QUAD = ((0.1, 0.2), (0.9, 0.15), (0.85, 0.9), (0.12, 0.88))


def test_homografia_leva_a_origem_aos_alvos():
    matriz = homography(CAMERA_QUAD, TARGETS)
    for origem, alvo in zip(CAMERA_QUAD, TARGETS):
        x, y = apply(matriz, *origem)
        assert x == pytest.approx(alvo[0], abs=1e-6)
        assert y == pytest.approx(alvo[1], abs=1e-6)


@pytest.mark.parametrize(
    "pontos",
    [
        ((0.1, 0.1), (0.9, 0.9), (0.9, 0.1), (0.1, 0.9)),  # cruzados
        ((0.1, 0.1), (0.5, 0.5), (0.9, 0.9), (0.3, 0.3)),  # colineares
    ],
)
def test_floormap_recusa_pontos_cruzados_ou_colineares(pontos):
    assert FloorMap.maybe(pontos) is None


def test_floormap_recusa_menos_de_quatro_pontos():
    assert FloorMap.maybe([(0.1, 0.1), (0.9, 0.1), (0.9, 0.9)]) is None


def test_floormap_aceita_quadrilatero_valido():
    assert FloorMap.maybe(CAMERA_QUAD) is not None


def _pontos_corpo(pes: dict, visibilidade: float = 0.9):
    return landmarks(pes, visibility=visibilidade)


PES = {29: (0.4, 0.8), 31: (0.42, 0.82), 30: (0.6, 0.8), 32: (0.58, 0.82)}


def test_pes_no_meio_dos_dois_pes_visiveis():
    assert feet_point(_pontos_corpo(PES)) == pytest.approx((0.5, 0.81))


def test_pes_exige_os_dois_pes_visiveis():
    data = _pontos_corpo(PES)
    data[31] = (0.42, 0.82, 0.2)  # ponta do pé esquerdo escondida
    assert feet_point(data) is None
    assert feet_point(_pontos_corpo(PES)[:32]) is None


def test_locator_com_alvos_iguais_a_camera():
    locate = FloorMap(TARGETS).locator(0, False, 0.0)
    assert locate(_pontos_corpo({29: (0.5, 0.5), 31: (0.5, 0.5), 30: (0.5, 0.5), 32: (0.5, 0.5)})) == pytest.approx(
        (0.5, 0.5)
    )


@pytest.mark.parametrize(
    "point, expected",
    [
        ((0.15, 0.15), (0.0, 0.0)),
        ((0.85, 0.15), (1.0, 0.0)),
        ((0.85, 0.85), (1.0, 1.0)),
        ((0.15, 0.85), (0.0, 1.0)),
        ((0.5, 0.5), (0.5, 0.5)),
    ],
)
def test_alcance_expandido_mantem_centro_e_leva_marcadores_aos_cantos(point, expected):
    assert expand_reach(point) == pytest.approx(expected)
    locate = FloorMap(TARGETS).locator(0, False, 0.0)
    landmarks_at_point = _pontos_corpo({29: point, 31: point, 30: point, 32: point})
    assert locate(landmarks_at_point) == pytest.approx(expected)


@pytest.mark.parametrize("rotation", ROTACOES)
@pytest.mark.parametrize("mirrored", (False, True))
def test_quatro_cantos_com_offset_maximo_preservam_o_alcance(rotation, mirrored):
    locate = FloorMap(TARGETS).locator(rotation, mirrored, 0.35)
    corners = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    for marker, corner in zip(TARGETS, corners):
        camera_point = rotate_point(*marker, rotation, mirrored)
        points = _pontos_corpo({29: camera_point, 31: camera_point, 30: camera_point, 32: camera_point})
        assert locate(points) == pytest.approx(corner)


def test_alcance_do_console_admite_um_pe_na_borda_sem_perder_o_centro():
    left = type("Foot", (), {"x": 0.75, "y": 0.5, "visibility": 0.9})()
    right = type("Foot", (), {"x": 1.0, "y": 0.5, "visibility": 0.9})()
    tracking = type(
        "Frame",
        (),
        {
            "missing": False,
            "stale": False,
            "feet": {"left": left, "right": right},
            "out_of_area": {"left": False, "right": True},
            "control_target": None,
            "control_target_active": False,
        },
    )()
    assert floor_position(tracking) == pytest.approx((1.0, 0.5))
    tracking.feet = {
        "left": type("Foot", (), {"x": 0.49, "y": 0.49, "visibility": 0.9})(),
        "right": type("Foot", (), {"x": 0.51, "y": 0.51, "visibility": 0.9})(),
    }
    tracking.out_of_area = {"left": False, "right": False}
    assert floor_position(tracking) == pytest.approx((0.5, 0.5))


def test_alcance_do_console_preserva_alvo_offset_e_recusa_dois_pes_fora():
    foot = type("Foot", (), {"x": 0.5, "y": 0.5, "visibility": 0.9})()
    target = type("Target", (), {"x": 0.5, "y": 0.38})()
    tracking = type(
        "Frame",
        (),
        {
            "missing": False,
            "stale": False,
            "feet": {"left": foot, "right": foot},
            "out_of_area": {"left": False, "right": False},
            "control_target": target,
            "control_target_active": True,
        },
    )()
    assert floor_position(tracking) == pytest.approx((0.5, 0.38))
    foot.y = 0.85
    target.y = 0.73
    assert floor_position(tracking) == pytest.approx((0.5, 1.0))
    tracking.control_target = None
    assert floor_position(tracking) is None  # target inválido não reutiliza a média bruta
    tracking.out_of_area = {"left": True, "right": True}
    assert floor_position(tracking) is None


def test_alcance_do_console_tem_fallback_para_tracking_frame_antigo():
    foot = type("Foot", (), {"x": 0.5, "y": 0.5, "visibility": 0.9})()
    legacy = type(
        "LegacyFrame",
        (),
        {
            "missing": False,
            "stale": False,
            "feet": {"left": foot, "right": foot},
            "out_of_area": {"left": False, "right": False},
        },
    )()
    assert floor_position(legacy) == pytest.approx((0.5, 0.5))


def test_floorcontrol_filtra_jitter_e_reverte_da_borda_oposta():
    control = FloorControl(FakeSource(), lambda _landmarks: None)
    edge = expand_reach((0.875, 0.5))
    for _ in range(16):
        control.feed(edge, 1 / 30)
    assert control.position()[0] > 0.99
    for point in ((0.49, 0.5), (0.51, 0.5)) * 8:
        control.feed(point, 1 / 30)
    assert control.position()[0] == pytest.approx(0.5, abs=0.03)
    for _ in range(16):
        control.feed(expand_reach((0.125, 0.5)), 1 / 30)
    assert control.axes()[0] < -0.99


@pytest.mark.parametrize(
    "x, expected_x, key",
    [(0.0, 0, "left"), (1.0, C.WIDTH - 1, "right")],
)
def test_cursor_de_pes_alcanca_e_aciona_botoes_nas_duas_bordas(x, expected_x, key):
    source = FakeSource()
    hub = InputHub()
    hub.source_factory = lambda: source
    point = [x, 0.5]
    hub.set_floor(lambda _landmarks: tuple(point), "edge")
    hub.set_segment("pes")
    for _ in range(3):
        source.show(_pontos_corpo(PES))
        hub.update(1 / 30)
    pointer = hub.body_pointer()
    assert pointer is not None and pointer[0] == expected_x

    hits = []
    menu = Menu(
        [
            Button(pygame.Rect(0, 0, 150, C.HEIGHT), "left", lambda: hits.append("left"), key="left"),
            Button(
                pygame.Rect(C.WIDTH - 150, 0, 150, C.HEIGHT),
                "right",
                lambda: hits.append("right"),
                key="right",
            ),
        ]
    )
    assert menu.update(0.1, pointer, 0.1)
    assert hits == [key]


def test_perda_dos_pes_nao_completa_permanencia_do_cursor():
    source = FakeSource()
    hub = InputHub()
    hub.source_factory = lambda: source
    hub.set_floor(lambda points: (0.5, 0.5) if points is not None else None, "loss")
    hub.set_segment("pes")
    hits = []
    menu = Menu([Button(pygame.Rect(0, 0, C.WIDTH, C.HEIGHT), "alvo", lambda: hits.append("alvo"))])

    source.show(_pontos_corpo(PES))
    hub.update(1 / 30)
    pointer = hub.body_pointer()
    assert pointer is not None
    menu.update(0.2, pointer, 0.5)

    source.show(None)
    hub.update(1 / 30)
    assert hub.body_pointer() is None
    menu.update(0.4, hub.body_pointer(), 0.5)
    assert hits == []


def test_marcador_de_voo_some_quando_os_dois_pes_estao_fora():
    body = FloorControl(FakeSource(), lambda _points: None)
    body.point = (0.92, 0.5)  # posição anterior continua guardada no controle
    body.visible = False  # o quadro atual informou ambos os pés fora da área
    assert floor_indicator_position(body) is None

    body.visible = True
    assert floor_indicator_position(body) == pytest.approx((0.92, 0.5))


def test_locator_sobe_com_o_cursor_a_frente():
    locate = FloorMap(TARGETS).locator(0, False, 0.1)
    pes = {29: (0.5, 0.5), 31: (0.5, 0.5), 30: (0.5, 0.5), 32: (0.5, 0.5)}
    x, y = locate(_pontos_corpo(pes))
    assert (x, y) == pytest.approx((0.5, 0.4))


def test_locator_devolve_none_fora_da_projecao():
    locate = FloorMap(TARGETS).locator(0, False, 0.0)
    pes = {29: (1.2, 0.5), 31: (1.2, 0.5), 30: (1.2, 0.5), 32: (1.2, 0.5)}
    assert locate(_pontos_corpo(pes)) is None
    assert locate(None) is None


def test_locator_com_rotacao_180_inverte_a_posicao():
    locate = FloorMap(TARGETS).locator(180, False, 0.0)
    pes = {29: (0.3, 0.4), 31: (0.3, 0.4), 30: (0.3, 0.4), 32: (0.3, 0.4)}
    assert locate(_pontos_corpo(pes)) == pytest.approx((0.7857142857, 0.6428571429))


# ------------------------------------------------------------------ pose
def test_eixo_nao_calibra_com_leituras_muito_variadas():
    mapper = AxisMapper(SEGMENTS["tronco_pe"])
    for i in range(60):  # 3 s alternando pontos distantes
        mapper.feed((0.2, 0.2) if i % 2 else (0.8, 0.8), 0.05)
    assert not mapper.calibrated


def test_eixo_calibra_quando_parado():
    mapper = AxisMapper(SEGMENTS["tronco_pe"])
    for _ in range(100):  # 5 s parado
        mapper.feed((0.5, 0.5), 0.05)
    assert mapper.calibrated
    assert mapper.base == pytest.approx((0.5, 0.5))


def test_invert_x_inverte_o_eixo_horizontal():
    normal = AxisMapper(SEGMENTS["tronco_pe"])
    invertido = AxisMapper(SEGMENTS["tronco_pe"], invert_x=True)
    for mapper in (normal, invertido):
        for _ in range(100):
            mapper.feed((0.5, 0.5), 0.05)
        for _ in range(40):
            mapper.feed((0.6, 0.5))
    assert normal.axes()[0] > 0.5
    assert invertido.axes()[0] == pytest.approx(-normal.axes()[0])


def test_recenter_apaga_o_repouso_depois_de_uma_ausencia_longa():
    source = FakeSource()
    body = BodyControl(source, SEGMENTS["cabeca"])
    body.recenter_after = 1.0
    centro = landmarks({0: (0.5, 0.5), 7: (0.5, 0.5), 8: (0.5, 0.5)})
    for _ in range(80):
        source.show(centro)
        body.poll(1 / 30)
    assert body.calibrated
    for _ in range(27):  # 0,9 s sem ver o segmento
        source.show(landmarks({}))
        body.poll(1 / 30)
    assert body.calibrated
    for _ in range(9):  # mais 0,3 s: passa de 1 s
        source.show(landmarks({}))
        body.poll(1 / 30)
    assert not body.calibrated


def test_floorcontrol_axes_a_partir_do_ponto_do_chao():
    source = FakeSource()
    control = FloorControl(source, lambda lm: (0.75, 0.25))
    for _ in range(5):
        source.show(landmarks({}))
        control.poll(1 / 30)
    ax, ay = control.axes()
    assert ax == pytest.approx(0.5, abs=1e-2)
    assert ay == pytest.approx(0.5, abs=1e-2)
    assert control.calibrated


def test_floorcontrol_mantem_o_ultimo_ponto_quando_perde_os_pes():
    source = FakeSource()
    leituras = iter([(0.75, 0.25), None, None])
    control = FloorControl(source, lambda lm: next(leituras))
    for _ in range(3):
        source.show(landmarks({}))
        control.poll(1 / 30)
    assert control.axes() == pytest.approx((0.5, 0.5), abs=1e-2)


# ------------------------------------------------------------------ hub
def test_hub_com_chao_cria_controle_absoluto_no_centro():
    hub = InputHub()
    hub.source_factory = lambda: FakeSource()
    hub.set_floor(lambda lm: (0.5, 0.5), "t1")
    hub.set_segment("pes")
    assert isinstance(hub.body, FloorControl)
    assert hub.body_pointer() is None  # não posiciona o cursor até chegar uma leitura válida


def test_hub_recria_o_controle_quando_o_token_muda():
    hub = InputHub()
    hub.source_factory = lambda: FakeSource()
    hub.set_floor(lambda lm: (0.5, 0.5), "t1")
    hub.set_segment("pes")
    antigo = hub.body
    hub.set_floor(lambda lm: (0.2, 0.2), "t1")  # mesmo token: nada muda
    assert hub.body is antigo
    hub.set_floor(lambda lm: (0.2, 0.2), "t2")
    assert hub.body is not antigo and isinstance(hub.body, FloorControl)


def test_hub_cabeca_recentra_so_com_conforto():
    hub = InputHub()
    hub.source_factory = lambda: FakeSource()
    hub.auto_center = True
    hub.set_segment("cabeca")
    assert hub.body.recenter_after == RECENTER_S

    outro = InputHub()
    outro.source_factory = lambda: FakeSource()
    outro.auto_center = False
    outro.set_segment("cabeca")
    assert outro.body.recenter_after is None


# -------------------------------------------------------------- console
def _cru(n: int = 33, x: float = 0.2, y: float = 0.3, vis: float = 0.9):
    return [(x, y, vis)] * n


def test_body_points_espelha_x():
    pontos = body_points(_cru())
    assert pontos[0] == pytest.approx((0.8, 0.3, 0.9))
    assert body_points(_cru(), mirror=False)[0] == pytest.approx((0.2, 0.3, 0.9))


def test_body_points_nan_vira_visibilidade_zero():
    raw = _cru()
    raw[5] = (float("nan"), 0.4, 0.9)
    assert body_points(raw)[5] == (0.0, 0.0, 0.0)


def test_body_points_visibilidade_none_vira_um():
    raw = _cru()
    raw[7] = (0.5, 0.5, None)
    assert body_points(raw)[7] == pytest.approx((0.5, 0.5, 1.0))


def test_body_points_com_menos_de_33_pontos_e_none():
    assert body_points(_cru(32)) is None
    assert body_points(None) is None


def test_tracking_source_push_avanca_o_seq_e_localiza_o_chao():
    source = TrackingSource()
    seq_inicial = source.snapshot()[0]
    source.push(None, (0.4, 0.6))
    assert source.snapshot()[0] == seq_inicial + 1
    assert source.locate_floor() == (0.4, 0.6)


# ------------------------------------------------------------ persistência
def test_girar_antigo_vira_rotacao_180():
    assert Profile.from_dict({"opcoes": {"girar": True}}).opcoes.rotacao == 180


def test_rotacao_invalida_vira_zero():
    assert Profile.from_dict({"opcoes": {"rotacao": 45}}).opcoes.rotacao == 0


@pytest.mark.parametrize(
    "pontos",
    [
        [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9]],  # três pontos
        [[0.1, 0.1], [0.9, 0.1], [0.9, 0.9], [1.5, 0.9]],  # valor acima de 1
    ],
)
def test_chao_pontos_invalido_vira_lista_vazia(pontos):
    assert Profile.from_dict({"opcoes": {"chao_pontos": pontos}}).opcoes.chao_pontos == []


def test_alvo_frente_e_limitado_a_35_por_cento():
    assert Profile.from_dict({"opcoes": {"alvo_frente": 0.9}}).opcoes.alvo_frente == pytest.approx(0.35)


def test_inverter_horizontal_sobrevive_ao_json():
    perfil = Profile()
    perfil.opcoes.inverter_horizontal = True
    assert Profile.from_dict(perfil.to_dict()).opcoes.inverter_horizontal is True


# ----------------------------------------------------------- cartucho
@pytest.fixture
def cartucho(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("build_cartridge", ROOT / "tools" / "build_cartridge.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "STAGE_ROOT", tmp_path)
    monkeypatch.setattr(module, "STAGE", tmp_path / "cartucho")
    return module


def test_stage_deixa_de_fora_o_que_so_o_executavel_usa(cartucho):
    assert (ROOT / "assets" / "pose_model").is_dir()  # pré-condição: o modelo existe no projeto
    pasta = cartucho.stage()
    for relativo in cartucho.DESKTOP_ONLY:
        assert not (pasta / "dobramundo" / relativo).exists(), relativo
    assert not (pasta / "assets" / "pose_model").exists()
    manifesto = (pasta / "ttea.toml").read_text(encoding="utf-8")
    assert f'version = "{__version__}"' in manifesto


PROIBIDOS_IMPORT = {"cv2", "mediapipe", "importlib", "subprocess", "ctypes"}
PROIBIDOS_PREFIXO = ("pygame.display.", "pygame.event.")
PROIBIDOS_EXATOS = {"pygame.init", "pygame.mixer.init", "pygame.time.Clock", "getattr", "eval", "exec", "__import__"}


def _nome(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _nome(node.value)
        return f"{base}.{node.attr}" if base else None
    return None


def _problemas(arquivo: Path):
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    achados = []
    for node in ast.walk(arvore):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in PROIBIDOS_IMPORT:
                    achados.append(f"import {alias.name} (linha {node.lineno})")
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] in PROIBIDOS_IMPORT:
                achados.append(f"from {node.module} (linha {node.lineno})")
        elif isinstance(node, ast.Call):
            nome = _nome(node.func)
            if nome and (nome in PROIBIDOS_EXATOS or nome.startswith(PROIBIDOS_PREFIXO)):
                achados.append(f"{nome}() (linha {node.lineno})")
    return achados


def test_codigo_montado_nao_chama_o_que_o_console_proibe(cartucho):
    pasta = cartucho.stage()
    arquivos = sorted(pasta.rglob("*.py"))
    assert arquivos, "nenhum .py montado"
    erros = {}
    for arquivo in arquivos:
        achados = _problemas(arquivo)
        if achados:
            erros[str(arquivo.relative_to(pasta))] = achados
    assert erros == {}


# ------------------------------------------------------- cena de projeção
class FakeCamera(FakeSource):
    """Fonte falsa com foto: a cena pede e recebe um quadro RGB de 64x48."""

    def __init__(self) -> None:
        super().__init__()
        self.pedidos = 0

    def request_still(self) -> None:
        self.pedidos += 1

    def still(self):
        return bytes(64 * 48 * 3), (64, 48)


@pytest.mark.parametrize("estado", ["menu", "alvos", "foto"])
def test_projecao_desenha_em_todos_os_estados(app, estado):
    scene = ProjectionScene(app)
    scene.state = estado
    scene.build()
    scene.draw(pygame.Surface((C.WIDTH, C.HEIGHT)))


def _leva_a_foto(scene: ProjectionScene) -> None:
    scene.calibrate()
    for _ in range(int(SHOW_TARGETS_S / 0.1) + 5):
        scene.update(0.1)
        if scene.state == "foto":
            return


def test_calibrar_passa_dos_alvos_para_a_foto(app):
    app.input.source = FakeCamera()
    scene = ProjectionScene(app)
    scene.calibrate()
    assert scene.state == "alvos"
    _leva_a_foto(scene)
    assert scene.state == "foto"
    assert app.input.source.pedidos == 1


CANTOS = ((0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9))


def test_quatro_cliques_gravam_o_chao(app):
    app.input.source = FakeCamera()
    scene = ProjectionScene(app)
    _leva_a_foto(scene)
    rect = scene.photo_rect()
    for fx, fy in CANTOS:
        scene.click((round(rect.left + fx * rect.width), round(rect.top + fy * rect.height)))
    assert len(app.options.chao_pontos) == 4
    assert app.options.superficie == "chao"
    assert app.profile.controle == "pes"


def test_cliques_cruzados_nao_gravam(app):
    app.input.source = FakeCamera()
    scene = ProjectionScene(app)
    _leva_a_foto(scene)
    rect = scene.photo_rect()
    cruzados = ((0.1, 0.1), (0.9, 0.9), (0.9, 0.1), (0.1, 0.9))
    for fx, fy in cruzados:
        scene.click((round(rect.left + fx * rect.width), round(rect.top + fy * rect.height)))
    assert app.options.chao_pontos == []
    assert app.options.superficie == "monitor"


# -------------------------------------------------------- to_logical
def test_to_logical_com_rotacao_90_leva_o_centro_ao_centro(app):
    app.options.rotacao = 90
    app.options.espelhar = False
    x, y = app.to_logical((C.WIDTH // 2, C.HEIGHT // 2))
    assert math.hypot(x - C.WIDTH / 2, y - C.HEIGHT / 2) <= 5
