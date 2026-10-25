"""Petrolina / Caatinga: flora sertaneja, casas, marcos e obstáculos do estágio industrial.

Medidas em "metros de modelo" (o jogo escala cada sprite pela altura do mundo).
Paleta: ocres e terracota da taipa, verde-acinzentado e azul-verde dos cactos,
concreto e ferrugem da cidade industrial, branco e azul-solar no estágio solarpunk.
"""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np

from .kit import (
    P,
    band_cylinder,
    canopy,
    chain,
    frond,
    gable_roof,
    hexcolor,
    lattice_tower,
    model,
    palm_crown,
    rotate_x,
    rotate_y,
    rotate_z,
    shade,
    solar_panel,
    translate,
    trunk,
)
from .mesh import Mesh, scatter

# ------------------------------------------------------------- paleta local
OCHRE = hexcolor("d7a262")
OCHRE_DARK = hexcolor("b5813f")
CACTUS = hexcolor("3f8a7f")
CACTUS_LIGHT = hexcolor("5fa08f")
XIQUE = hexcolor("6f9a5e")
JUAZEIRO = hexcolor("2e5e3a")
UMBU = hexcolor("8db04e")
CARNAUBA = hexcolor("4f7d58")
DRY = hexcolor("8c7650")
WHITE_WALL = hexcolor("f1ede4")
STEEL_GALV = hexcolor("7d8793")
SOOT = P["soot"]
SAND = hexcolor("e0c892")
BARK_TRUNK = hexcolor("7a5a40")


# ------------------------------------------------------------------ helpers
def _place(m: Mesh, part: Mesh, x: float = 0.0, z: float = 0.0, rot: np.ndarray = None) -> Mesh:
    """Anexa uma peça deslocada (e opcionalmente girada) ao modelo."""
    at = translate(x, 0.0, z) if rot is None else chain(translate(x, 0.0, z), rot)
    return m.extend(part, at=at)


def _ribs(
    m: Mesh,
    cx: float,
    cz: float,
    radius: float,
    height: float,
    color,
    count: int = 6,
    base_y: float = 0.0,
    width: float = 0.3,
) -> Mesh:
    """Costelas verticais: faixas coladas ao cilindro, dão a leitura de 'gomos' do cacto."""
    for k in range(count):
        a = 2 * math.pi * k / count
        at = chain(
            translate(cx + radius * math.cos(a), base_y, cz + radius * math.sin(a)), rotate_y(90 - math.degrees(a))
        )
        m.box((radius * width, height, radius * 0.22), shade(color, 0.8 if k % 2 else 0.92), at=at)
    return m


def _arm(
    m: Mesh, y_join: float, R: float, color, yaw: float, reach: float, y_top: float, arm_r: float
) -> Tuple[float, float]:
    """Braço de cacto: sai horizontal do tronco e sobe em candelabro. Devolve a ponta (x, z)."""
    a = math.radians(yaw)
    ex, ez = (R + reach) * math.cos(a), (R + reach) * math.sin(a)
    m.beam((0.4 * R * math.cos(a), y_join, 0.4 * R * math.sin(a)), (ex, y_join, ez), 2 * arm_r, color)
    m.cylinder(arm_r, y_top - y_join, color, 6, at=translate(ex, y_join, ez))
    m.sphere(arm_r, color, 2, 6, at=translate(ex, y_top, ez))
    return ex, ez


def _column(R: float, H: float, color, top_ratio: float = 0.9, segments: int = 7, ribs: int = 6) -> Mesh:
    """Tronco de cacto colunar (cilindro de poucas faces com costelas e topo arredondado)."""
    col = Mesh()
    col.cylinder(R, H, color, segments, R * top_ratio)
    _ribs(col, 0.0, 0.0, R, H * 0.96, color, ribs, 0.0, 0.3)
    col.sphere(R * top_ratio, shade(color, 1.04), 2, segments, at=translate(0, H, 0))
    return col


def _lying(m: Mesh, x: float, z: float, length: float, R: float, yaw: float, color) -> Mesh:
    """Cacto tombado no chão (cilindro deitado, com a ponta arredondada)."""
    m.cylinder(R, length, color, 7, R * 0.9, at=chain(translate(x, R, z), rotate_y(yaw), rotate_z(-90)))
    m.sphere(R * 0.9, shade(color, 1.04), 2, 6, at=chain(translate(x, R, z), rotate_y(yaw), translate(length, 0, 0)))
    return m


def _wheel(m: Mesh, x: float, z_center: float, radius: float, width: float, color, segments: int = 8) -> Mesh:
    """Roda com eixo no sentido z (centrada em z_center)."""
    m.cylinder(radius, width, color, segments, at=chain(translate(x, radius, z_center - width / 2), rotate_x(90)))
    return m


def _sun_cone(mesh: Mesh, x: float, y: float, z: float, a: float, length: float, radius: float, color) -> Mesh:
    """Cone que aponta para fora do centro no plano xy (espinhos da carranca)."""
    return mesh.cone(
        radius,
        length,
        color,
        5,
        at=chain(translate(x + math.cos(a) * 1.0, y + math.sin(a) * 1.0, z), rotate_z(math.degrees(a) - 90)),
    )


# ------------------------------------------------------------------- flora
def _mandacaru(H: float, R: float, arms, color, fruit: bool) -> Mesh:
    """Mandacaru: coluna com braços em candelabro; flores brancas nas pontas."""
    m = Mesh()
    m.extend(_column(R, H, color))
    for yaw, y_join, y_top, reach in arms:
        ex, ez = _arm(m, y_join, R, color, yaw, reach, y_top, R * 0.55)
        m.sphere(R * 0.42, P["white"], 2, 6, at=translate(ex, y_top + R * 0.35, ez), squash=(1.0, 0.7, 1.0))
        if fruit:
            m.sphere(R * 0.26, P["red"], 2, 5, at=translate(ex * 0.9, y_top - 0.25 * H * 0.1, ez * 0.9 + R * 0.2))
    m.sphere(R * 0.38, P["white"], 2, 6, at=translate(0, H + R * 0.55, 0), squash=(1.0, 0.7, 1.0))
    return m


@model("CA_Mandacaru")
def mandacaru() -> Mesh:
    """Mandacaru: cacto colunar de 4 braços em candelabro, verde-azulado, com flores brancas."""
    return _mandacaru(
        6.0,
        0.5,
        [(15, 2.2, 4.4, 1.1), (140, 2.9, 5.2, 1.2), (235, 2.5, 4.9, 1.1), (305, 3.5, 5.6, 1.0)],
        CACTUS,
        fruit=True,
    )


@model("CA_MandacaruGigante")
def mandacaru_gigante() -> Mesh:
    """Mandacaru gigante, esguio: tronco liso até ~55% da altura e braços só no alto (obstáculo: desvie)."""
    m = Mesh()
    m.extend(_column(0.36, 10.0, CACTUS_LIGHT, top_ratio=0.9, segments=6, ribs=5))
    for yaw, y_join, y_top, reach in ((-8, 6.2, 9.1, 1.0), (105, 7.2, 9.7, 1.1), (200, 6.6, 9.4, 1.0)):
        ex, ez = _arm(m, y_join, 0.36, CACTUS_LIGHT, yaw, reach, y_top, 0.2)
        m.sphere(0.16, P["white"], 2, 5, at=translate(ex, y_top + 0.12, ez), squash=(1.0, 0.7, 1.0))
    m.sphere(0.16, P["white"], 2, 5, at=translate(0, 10.2, 0), squash=(1.0, 0.7, 1.0))
    return m


@model("CA_XiqueXique")
def xiquexique() -> Mesh:
    """Xique-xique: touceira baixa e espalhada de cactos curtos, alguns tombados no chão."""
    m = Mesh()
    _place(m, _column(0.2, 1.5, XIQUE, segments=6, ribs=5), 0.0, 0.0)
    _place(m, _column(0.18, 1.05, shade(XIQUE, 1.04), segments=6, ribs=5), 0.45, 0.3)
    _place(m, _column(0.17, 0.85, XIQUE, segments=6, ribs=5), -0.42, 0.25)
    _lying(m, -0.1, -0.55, 1.1, 0.16, 35, XIQUE)
    _lying(m, 0.55, -0.35, 0.95, 0.15, -30, shade(XIQUE, 1.05))
    return m


@model("CA_Macambira")
def macambira() -> Mesh:
    """Macambira: bromélia em roseta de folhas pontudas, baixa, com haste laranja de flores."""
    m = Mesh()
    base = hexcolor("7e9a6a")
    for i in range(11):
        yaw = 360 * i / 11 + (i % 2) * 6
        length = 0.9 + 0.25 * ((i * 3) % 4) / 3
        frond(m, (0.0, 0.12, 0.0), yaw, length, 0.55, base, width=0.2, segments=3)
    m.cone(0.13, 0.85, hexcolor("e0633a"), 5, at=chain(translate(0, 0.1, 0), rotate_z(8)))
    return m


@model("CA_Juazeiro")
def juazeiro() -> Mesh:
    """Juazeiro: tronco retorcido de dois troncos entrelaçados e copa densa verde-escura."""
    m = Mesh()
    trunk(m, 2.9, 0.26, BARK_TRUNK, 0.7, 7, lean=0.3, rings=4)
    trunk(m, 2.4, 0.18, hexcolor("9a7a58"), 0.6, 6, lean=-0.25, at=translate(0.25, 0, 0.12), rings=3)
    canopy(m, (0.55, 3.45, 0.0), 1.75, JUAZEIRO, blobs=9, seed=7, flat=0.72, spread=0.95)
    return m


@model("CA_Umbuzeiro")
def umbuzeiro() -> Mesh:
    """Umbuzeiro: árvore baixa e larga, copa em guarda-chuva, tronco curto e grosso, frutinhos amarelos."""
    m = Mesh()
    m.cylinder(0.36, 1.2, hexcolor("8d8577"), 8, 0.3)
    for yaw in (20, 110, 200, 290):
        a = math.radians(yaw)
        m.beam(
            (0.1 * math.cos(a), 1.0, 0.1 * math.sin(a)),
            (1.1 * math.cos(a), 1.8, 1.1 * math.sin(a)),
            0.22,
            hexcolor("8d8577"),
        )
    canopy(m, (0, 2.0, 0), 1.7, UMBU, blobs=7, seed=12, flat=0.42, spread=1.1)
    for k, (x, z) in enumerate(scatter(9, 1.5, 5)):
        m.sphere(0.09, hexcolor("d4d65e"), 2, 5, at=translate(x, 1.4 + 0.1 * (k % 2), z), squash=(1, 0.9, 1))
    return m


@model("CA_Carnauba")
def carnauba() -> Mesh:
    """Carnaúba: palmeira alta, folhas em leque e uma saia de folhas secas pendentes abaixo da copa."""
    m = Mesh()
    trunk(m, 6.0, 0.2, hexcolor("a89670"), 0.85, 8, rings=6)
    palm_crown(m, (0, 6.0, 0), 10, 2.4, 0.7, CARNAUBA, seed=3, width=0.2)
    for k in range(7):
        frond(m, (0, 5.4, 0), 360 * k / 7 + 10, 1.5, 1.8, DRY, width=0.12)
    return m


@model("CA_Mangueira")
def mangueira() -> Mesh:
    """Mangueira: copa muito densa e arredondada, com mangas penduradas (amarelas, laranjas e vermelhas)."""
    m = Mesh()
    trunk(m, 2.0, 0.28, P["bark"], 0.7, 7, rings=2)
    canopy(m, (0, 3.2, 0), 2.0, hexcolor("2f6b30"), blobs=10, seed=21, flat=0.8, spread=0.85, rings=3, segments=8)
    mango_colors = [P["yellow"], P["orange"], P["red"]]
    for k, (x, z) in enumerate(scatter(12, 1.9, 9)):
        m.sphere(0.17, mango_colors[k % 3], 2, 5, at=translate(x, 1.9 + 0.3 * (k % 3), z), squash=(0.9, 1.25, 0.9))
    return m


# ------------------------------------------------------------- construções
@model("CA_CasaTaipa")
def casa_taipa() -> Mesh:
    """Casa de taipa sertaneja: paredes ocres, telha cerâmica, porta azul e alpendre com dois esteios."""
    m = Mesh()
    W, H, D = 2.6, 1.5, 2.0
    m.box((W + 0.12, 0.12, D + 0.12), P["concrete"], at=translate(0, 0, 0))
    m.box((W, H, D), OCHRE, at=translate(0, 0.12, 0))
    # porta e janelas na fachada (+z)
    m.box((0.45, 0.95, 0.04), P["blue"], at=translate(-0.45, 0.12, D / 2 + 0.01))
    m.box((0.6, 0.5, 0.05), WHITE_WALL, at=translate(0.55, 0.7, D / 2 + 0.005))
    m.box((0.48, 0.38, 0.06), hexcolor("3f8f5a"), at=translate(0.55, 0.76, D / 2 + 0.02))
    m.box((0.04, 0.42, 0.5), hexcolor("3f8f5a"), at=translate(W / 2 + 0.01, 0.8, -0.4))
    # alpendre com dois esteios
    m.box((W * 0.95, 0.1, 0.75), P["concrete"], at=translate(0, 0.0, D / 2 + 0.4))
    for x in (-W / 2 + 0.25, W / 2 - 0.25):
        m.cylinder(0.08, 1.3, P["wood"], 6, at=translate(x, 0.1, D / 2 + 0.7))
    m.box((W * 0.95, 0.08, 0.95), P["tile"], at=chain(translate(0, 1.4, D / 2 + 0.5), rotate_x(12)))
    # telhado de duas águas com cumeeira ao longo de x (as águas caem para frente e para trás)
    roof = Mesh()
    gable_roof(roof, D, W, 0.7, H + 0.12, P["tile"], overhang=0.2, gable=OCHRE_DARK)
    m.extend(roof, at=rotate_y(90))
    return m


@model("CA_CisternaPlacas")
def cisterna_placas() -> Mesh:
    """Cisterna de placas: cilindro largo e baixo de concreto branco, tampa cônica rasa e cano lateral.
    Obstáculo baixo: o topo é a parte mais alta do modelo."""
    m = Mesh()
    m.cylinder(1.4, 1.0, P["white"], 12)
    m.cylinder(1.44, 0.12, shade(P["white"], 0.86), 12, at=translate(0, 0.42, 0), caps=False)
    m.cylinder(1.46, 0.35, shade(P["white"], 0.94), 12, 0.3, at=translate(0, 1.0, 0), top_color=P["concrete"])
    m.cylinder(0.12, 0.06, P["steel"], 6, at=translate(0, 1.33, 0))
    m.beam((1.35, 0.8, 0.0), (2.2, 0.8, 0.0), 0.12, P["steel"])
    m.beam((2.2, 0.8, 0.0), (2.2, 0.05, 0.0), 0.12, P["steel"])
    return m


@model("CA_Galpao")
def galpao() -> Mesh:
    """Galpão de embalagem de frutas: cobertura em arco enferrujada, paredes sujas, caixas no pátio."""
    m = Mesh()
    W, H, L = 6.0, 2.8, 9.0
    wall = hexcolor("b49a78")
    roof = hexcolor("8f6a4c")
    m.box((W, H, L), wall, at=translate(0, 0, 0))
    arch = [(W / 2 * math.cos(t), H + 1.6 * math.sin(t)) for t in np.linspace(0, math.pi, 13)]
    m.slab(arch, L, roof, side=shade(roof, 0.8))
    m.box((W * 0.5, H * 0.7, 0.06), P["rust_dark"], at=translate(0, 0, L / 2 + 0.01))  # portão enrolável
    for x in (-2.2, 0.9, 2.1):  # escorridos de ferrugem
        m.box((0.12, H * 0.9, 0.04), P["rust"], at=translate(x, 0.2, L / 2 + 0.02))
    for x in (-2.0, 2.0):  # janelas sujas
        m.box((0.7, 0.5, 0.05), hexcolor("7d8a7f"), at=translate(x, 1.9, L / 2 + 0.01))
    for k, (x, y, z) in enumerate(((-2.2, 0, 5.1), (-1.2, 0, 5.1), (-1.7, 0.5, 5.1), (2.0, 0, 5.2))):
        m.box((0.9, 0.5, 0.7), SAND if k % 2 else hexcolor("e0a050"), at=translate(x, y, z))
    return m


@model("CA_CaixaDagua")
def caixa_dagua() -> Mesh:
    """Caixa d'água elevada sobre quatro pernas de concreto, com tampa cônica e manchas de umidade."""
    m = Mesh()
    concrete = P["concrete"]
    m.box((2.2, 0.2, 2.2), shade(concrete, 0.9), at=translate(0, 0, 0))
    for x in (-0.9, 0.9):
        for z in (-0.9, 0.9):
            m.box((0.3, 3.0, 0.3), concrete, at=translate(x, 0.2, z))
    for y in (1.2, 2.4):
        for side in (-0.9, 0.9):
            m.beam((-0.9, y, side), (0.9, y, side), 0.14, concrete)
            m.beam((side, y, -0.9), (side, y, 0.9), 0.14, concrete)
    m.cylinder(1.2, 1.5, concrete, 12, at=translate(0, 3.0, 0))
    m.cylinder(1.25, 0.45, shade(concrete, 0.85), 12, 0.2, at=translate(0, 4.5, 0))
    _ribs(m, 0, 0, 1.22, 1.0, hexcolor("6b5a48"), count=5, base_y=3.3, width=0.3)
    return m


@model("CA_TorreTransmissao", yaw=-30)
def torre_transmissao() -> Mesh:
    """Torre treliçada de linha de transmissão: esguia, com braços dos cabos e isoladores.
    Obstáculo 'desvie para o lado'."""
    m = Mesh()
    lattice_tower(m, 1.0, 0.45, 8.0, 5, STEEL_GALV, thickness=0.14)
    for y in (6.6, 7.5):
        m.beam((-0.95, y, 0), (0.95, y, 0), 0.14, STEEL_GALV)
        for x in (-0.95, 0.95):
            m.cylinder(0.1, 0.45, WHITE_WALL, 6, at=translate(x, y - 0.45, 0))
            m.beam((x, y - 0.02, 0.0), (x, y - 0.5, 0.0), 0.04, SOOT)
    m.beam((0, 8.0, 0), (0, 8.0, 0.0), 0.1, STEEL_GALV)
    return m


@model("CA_UsinaSolar")
def usina_solar() -> Mesh:
    """Usina solar: quatro fileiras de painéis inclinados sobre suportes, baixa e larga."""
    m = Mesh()
    m.box((7.2, 0.04, 7.0), hexcolor("c9b48a"), at=translate(0, 0, 0))
    for row in range(4):
        z = -2.4 + row * 1.6
        for x in (-2.6, 2.6):
            m.box((0.14, 0.62, 0.14), P["steel"], at=translate(x, 0.04, z))
        # inclinação negativa: a face das placas olha para a câmera (com 28° elas ficavam de perfil)
        solar_panel(m, translate(0, 0.95, z), (6.0, 1.1), -22, (8, 2))
    return m


@model("CA_Aerogerador")
def aerogerador() -> Mesh:
    """Aerogerador branco: torre cônica fina e alta, nacele e três pás longas no alto.
    Obstáculo 'desvie': só o mastro fica na faixa baixa."""
    m = Mesh()
    H, R = 10.5, 4.2
    m.cylinder(0.5, 0.35, P["concrete"], 10, 0.4)
    band_cylinder(m, 0.3, H - 0.3, [WHITE_WALL, hexcolor("e4e8ee")], 6, 0.1, segments=8, at=translate(0, 0.35, 0))
    m.box((0.7, 0.55, 1.6), WHITE_WALL, at=translate(0, H, -0.6))
    hub_y = H + 0.27
    m.cone(0.3, 0.4, WHITE_WALL, 8, at=chain(translate(0, hub_y, 0.2), rotate_x(90)))
    m.sphere(0.32, WHITE_WALL, 2, 7, at=translate(0, hub_y, 0.6))
    for k in range(3):
        at = chain(translate(0, hub_y, 0.6), rotate_z(120 * k))
        m.slab([(-0.3, 0.0), (0.3, 0.0), (0.08, R), (-0.04, R)], 0.14, WHITE_WALL, at=at, side=shade(WHITE_WALL, 0.8))
    return m


@model("CA_Videira")
def videira() -> Mesh:
    """Parreiral em latada: postes de madeira, arames, folhagem em teto e cachos de uva roxos."""
    m = Mesh()
    m.box((7.6, 0.05, 4.6), hexcolor("b08a5f"), at=translate(0, 0, 0))
    for x in (-3.0, 0.0, 3.0):
        for z in (-1.6, 1.6):
            m.box((0.22, 1.9, 0.22), P["wood"], at=translate(x, 0, z))
    for z in (-1.6, 1.6):
        m.beam((-3.3, 1.8, z), (3.3, 1.8, z), 0.1, STEEL_GALV)
    for x in (-3.0, 0.0, 3.0):
        m.beam((x, 1.8, -1.8), (x, 1.8, 1.8), 0.08, STEEL_GALV)
    leaf = [hexcolor("5f9a4a"), hexcolor("4f8a3e"), hexcolor("6fae55")]
    for k, (dx, dz) in enumerate(scatter(16, 1.0, 4)):
        m.sphere(
            0.62,
            leaf[k % 3],
            2,
            7,
            at=translate(dx * 3.4, 1.9 + 0.04 * (k % 3), dz * 2.2),
            squash=(1.0, 0.28, 1.0),
            jitter=0.15,
            seed=k,
        )
    for _k, (dx, dz) in enumerate(scatter(7, 1.0, 11)):
        cx, cz = dx * 2.6, dz * 1.5
        for j in range(3):
            m.sphere(0.15, P["purple"], 2, 5, at=translate(cx + 0.12 * (j - 1), 1.25 - 0.14 * j, cz + 0.08 * j))
    return m


@model("CA_Carranca")
def carranca() -> Mesh:
    """Carranca do Rio São Francisco: cabeça entalhada, meio leão, meio gente, com juba
    em mechas coloridas, olhos arregalados e boca aberta, na proa de uma barca. Marco da cidade."""
    m = Mesh()
    wood = hexcolor("8a5a32")
    m.prism([(-2.6, -0.9), (1.4, -0.9), (2.6, 0.0), (1.4, 0.9), (-2.6, 0.9)], 1.0, wood, top=hexcolor("a8744a"))
    m.box((5.4, 0.14, 1.95), P["blue"], at=translate(-0.4, 0.55, 0))  # faixa da barca
    m.beam((1.6, 1.0, 0.0), (2.4, 2.6, 0.0), 0.7, wood)  # pescoço na proa
    hx, hy, hz = 2.55, 3.55, 0.0
    face = hexcolor("c8402a")
    mane = [hexcolor("f2c037"), hexcolor("2e9e44"), hexcolor("e07a2a"), hexcolor("1f6fc0")]
    for k in range(16):  # juba em mechas
        a = 2 * math.pi * k / 16
        dy, dz = 1.05 * math.sin(a), 1.05 * math.cos(a)
        m.sphere(0.45, mane[k % 4], 2, 6, at=chain(translate(hx - 0.35, hy + dy, hz + dz)), squash=(0.7, 1.3, 1.0))
    m.sphere(0.95, face, 4, 10, at=translate(hx, hy, hz), squash=(1.15, 1.25, 0.9), jitter=0.04, seed=8)
    m.box((0.9, 0.6, 0.9), shade(face, 0.9), at=translate(hx + 0.75, hy - 0.55, hz))  # focinho
    m.box((0.85, 0.35, 0.95), hexcolor("5a1a14"), at=translate(hx + 0.9, hy - 1.05, hz))  # boca aberta
    m.box((0.9, 0.22, 0.95), shade(face, 0.85), at=translate(hx + 0.85, hy - 1.4, hz))  # queixo
    for z in (-0.3, -0.1, 0.1, 0.3):  # dentes
        m.cone(0.07, 0.2, P["white"], 4, at=chain(translate(hx + 1.25, hy - 0.72, hz + z), rotate_z(180)))
        m.cone(0.07, 0.18, P["white"], 4, at=translate(hx + 1.25, hy - 1.18, hz + z))
    for side in (-1, 1):
        m.sphere(0.28, P["white"], 3, 8, at=translate(hx + 0.7, hy + 0.3, hz + 0.42 * side))  # olhos
        m.sphere(0.13, hexcolor("1d2433"), 2, 6, at=translate(hx + 0.94, hy + 0.3, hz + 0.42 * side))
        m.box(
            (0.2, 0.12, 0.45),
            hexcolor("1d2433"),
            at=chain(translate(hx + 0.72, hy + 0.62, hz + 0.42 * side), rotate_x(-15 * side)),
        )  # sobrancelhas
        m.cone(
            0.25, 0.6, mane[0], 5, at=chain(translate(hx - 0.2, hy + 0.95, hz + 0.7 * side), rotate_x(-25 * side))
        )  # orelhas
    m.sphere(0.16, hexcolor("2a1a14"), 2, 6, at=translate(hx + 1.2, hy - 0.4, hz))  # nariz
    return m


@model("CA_PonteSaoFrancisco", sprite_max=420, yaw=-20, pitch=14)
def ponte_sao_francisco() -> Mesh:
    """Ponte de concreto sobre o Rio São Francisco (Petrolina-Juazeiro): tabuleiro reto sobre muitos pilares."""
    m = Mesh()
    m.box((18.0, 0.4, 1.4), P["concrete"], at=translate(0, 2.2, 0))
    for x in np.linspace(-8.0, 8.0, 9):
        m.box((0.5, 2.2, 0.9), shade(P["concrete"], 0.95), at=translate(float(x), 0, 0))
    for side in (-0.68, 0.68):
        m.box((18.0, 0.35, 0.06), P["white"], at=translate(0, 2.6, side))
        for x in np.linspace(-8.5, 8.5, 18):
            m.box((0.06, 0.35, 0.06), P["white"], at=translate(float(x), 2.6, side))
    return m


# ------------------------------------------------------ obstáculos industriais
@model("CA_CaminhaoPipa")
def caminhao_pipa() -> Mesh:
    """Caminhão-pipa velho e enferrujado: cabine e tanque cilíndrico deitado. Obstáculo baixo."""
    m = Mesh()
    steel = hexcolor("7a7f86")
    m.box((4.0, 0.3, 1.1), P["steel_dark"], at=translate(0, 0.45, 0))
    m.box((1.1, 0.9, 1.2), hexcolor("c26a3a"), at=translate(-1.7, 0.75, 0))
    m.box((0.04, 0.4, 0.9), SOOT, at=translate(-1.15, 1.0, 0))
    m.cylinder(0.6, 3.0, steel, 10, at=chain(translate(-0.4, 1.15, 0), rotate_z(-90)))
    m.cylinder(0.61, 0.5, P["rust"], 10, at=chain(translate(0.6, 1.15, 0), rotate_z(-90)))
    m.cylinder(0.61, 0.4, P["rust_dark"], 10, at=chain(translate(-0.7, 1.15, 0), rotate_z(-90)))
    for x in (-1.6, 1.2):
        for z in (-0.6, 0.6):
            _wheel(m, x, z, 0.35, 0.25, SOOT)
    return m


@model("CA_Carroca")
def carroca() -> Mesh:
    """Carroça de madeira carregada de sacas, puxada por um jegue low-poly. Obstáculo baixo."""
    m = Mesh()
    wood = P["wood"]
    m.box((2.4, 0.12, 1.3), wood, at=translate(0, 0.55, 0))
    m.box((2.4, 0.35, 0.08), P["wood_dark"], at=translate(0, 0.67, 0.6))
    m.box((2.4, 0.35, 0.08), P["wood_dark"], at=translate(0, 0.67, -0.6))
    m.box((0.08, 0.35, 1.3), P["wood_dark"], at=translate(1.2, 0.67, 0))
    for z in (-0.7, 0.7):
        _wheel(m, 0.0, z, 0.6, 0.12, P["wood_dark"], segments=10)
    for x, z, y in ((-0.6, -0.3, 0.67), (0.1, -0.3, 0.67), (-0.25, 0.3, 0.67), (0.45, 0.3, 0.67), (-0.25, 0.0, 1.12)):
        m.box((0.7, 0.45, 0.5), SAND, at=translate(x, y, z))
    for z in (-0.35, 0.35):  # varas
        m.beam((1.2, 0.7, z), (2.6, 0.55, z), 0.1, P["wood_dark"])
    gray, dark = hexcolor("8a8580"), hexcolor("4f4a46")  # jegue
    m.box((1.0, 0.6, 0.42), gray, at=translate(3.1, 0.55, 0))
    for x in (2.7, 3.5):
        for z in (-0.13, 0.13):
            m.box((0.11, 0.55, 0.11), dark, at=translate(x, 0.0, z))
    m.box((0.26, 0.6, 0.26), gray, at=chain(translate(3.7, 1.0, 0), rotate_z(-28)))
    m.box((0.42, 0.3, 0.26), dark, at=chain(translate(3.95, 1.25, 0), rotate_z(-28)))
    for z in (-0.1, 0.1):
        m.cone(0.05, 0.25, dark, 4, at=chain(translate(3.9 - 0.12, 1.45, z), rotate_z(-10)))
    m.beam((2.5, 0.9, 0), (2.25, 0.8, 0), 0.06, dark)  # rabo
    return m


@model("CA_PorticoIrrigacao")
def portico_irrigacao() -> Mesh:
    """Pórtico de irrigação sobre a pista: duas torres laterais e barra treliçada com aspersores no alto.
    Obstáculo 'passe por baixo': entre as torres nada abaixo de 66% da altura."""
    m = Mesh()
    steel = STEEL_GALV
    for x in (-6.8, 6.8):
        tower = Mesh()
        lattice_tower(tower, 0.9, 0.6, 5.5, 4, steel, thickness=0.14)
        m.extend(tower, at=translate(x, 0.0, 0.0))
        m.box((0.7, 0.25, 0.7), P["concrete"], at=translate(x, 0.0, 0.0))
    for z in (-0.4, 0.4):
        m.beam((-7.2, 5.8, z), (7.2, 5.8, z), 0.15, steel)
        m.beam((-7.2, 5.2, z), (7.2, 5.2, z), 0.12, steel)
    for i in range(14):
        x0, x1 = -7.2 + i, -6.2 + i
        y0, y1 = (5.8, 5.2) if i % 2 == 0 else (5.2, 5.8)
        m.beam((x0, y0, -0.4), (x1, y1, -0.4), 0.09, steel)
        m.beam((x0, y0, 0.4), (x1, y1, 0.4), 0.09, steel)
    m.beam((-7.2, 5.5, 0.0), (7.2, 5.5, 0.0), 0.12, hexcolor("c8a46a"))  # tubulação de água
    for x in (-5.6, -2.8, 0.0, 2.8, 5.6):
        m.beam((x, 5.2, 0.0), (x, 4.6, 0.0), 0.1, hexcolor("5a8ac0"))
        m.cone(0.16, 0.3, P["steel_dark"], 6, at=chain(translate(x, 4.6, 0.0), rotate_x(180)))
    return m


@model("CA_PorticoSolar")
def portico_solar() -> Mesh:
    """Pérgola solarpunk sobre a pista: painéis solares no topo e trepadeiras floridas penduradas.
    Mesma regra de passagem: vão livre até 66% da altura."""
    m = Mesh()
    white = hexcolor("e9e4d6")
    for x in (-6.8, 6.8):
        m.box((0.32, 5.4, 0.32), white, at=translate(x, 0.12, 0.0))
        m.box((0.6, 0.2, 0.6), P["steel"], at=translate(x, 0.0, 0.0))
    for z in (-1.1, 1.1):
        m.box((13.4, 0.3, 0.3), white, at=translate(0, 5.4, z))
    for x in (-5.4, -1.8, 1.8, 5.4):  # inclinação negativa: placas voltadas para a câmera
        solar_panel(m, translate(x, 5.75, 0.0), (3.2, 2.1), -14, (4, 3))
    for x in np.linspace(-6.2, 6.2, 11):
        for z in (-1.1, 1.1):
            m.sphere(
                0.4,
                P["leaf"],
                2,
                6,
                at=translate(float(x), 4.95, z),
                squash=(1, 0.6, 1),
                jitter=0.15,
                seed=int(x * 10) + 3,
            )
            m.sphere(0.12, P["pink"], 2, 5, at=translate(float(x) + 0.2, 4.6, z + 0.15))
    return m
