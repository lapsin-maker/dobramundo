"""Manaus / Amazônia: flora, cidade ribeirinha, cidade solarpunk e obstáculos.

Medidas em "metros de modelo" (o jogo escala cada sprite pela altura do mundo).
"""

from __future__ import annotations

import math

from .kit import (
    P,
    band_cylinder,
    canopy,
    chain,
    flowers,
    gable_roof,
    hexcolor,
    lattice_tower,
    model,
    palm_crown,
    rotate_x,
    rotate_y,
    rotate_z,
    shade,
    smoke,
    solar_panel,
    stilts,
    translate,
    trunk,
    windows_row,
)
from .mesh import Mesh, scatter


# ------------------------------------------------------------------- flora
@model("AM_Samauma")
def samauma() -> Mesh:
    """Samaúma: raízes tabulares, tronco reto e altíssimo, copa larga em guarda-chuva."""
    m = Mesh()
    bark = P["bark_gray"]
    for i in range(6):  # sapopemas (raízes tabulares)
        yaw = 60 * i + 15
        m.slab(
            [(0, 0), (1.5, 0), (0.15, 2.4), (0, 2.6)],
            0.12,
            shade(bark, 0.9),
            at=chain(rotate_y(yaw), translate(0, 0, 0)),
        )
    m.cylinder(0.55, 7.5, bark, 9, 0.38)
    m.cylinder(0.38, 1.5, shade(bark, 0.95), 9, 0.3, at=translate(0, 7.4, 0))
    for yaw, length in ((20, 2.6), (140, 2.4), (260, 2.8)):  # galhos horizontais
        a = math.radians(yaw)
        m.beam((0, 8.4, 0), (length * math.cos(a), 9.2, length * math.sin(a)), 0.22, bark)
    canopy(m, (0, 9.4, 0), 3.4, P["leaf_dark"], blobs=8, seed=11, flat=0.42, spread=1.05)
    return m


@model("AM_Acaizeiro")
def acaizeiro() -> Mesh:
    """Touceira de açaí: vários estipes finos, folhas penadas e cachos roxos."""
    m = Mesh()
    stems = [(0.0, 0.0, 6.2, 0.0), (0.5, 0.3, 5.0, 0.06), (-0.45, 0.2, 5.6, -0.05), (0.15, -0.5, 4.3, 0.03)]
    for i, (x, z, h, lean) in enumerate(stems):
        trunk(m, h, 0.09, P["bark_light"], 0.8, 6, lean=lean, at=translate(x, 0, z), rings=3)
        top = (x + lean * h, h, z)
        palm_crown(m, top, 8, 1.7, 0.75, P["leaf"], seed=i * 5 + 1, width=0.12)
        for k in range(3):  # cachos de açaí
            a = 2 * math.pi * k / 3 + i
            m.sphere(
                0.16,
                P["purple"],
                3,
                6,
                at=translate(top[0] + 0.22 * math.cos(a), h - 0.35, z + 0.22 * math.sin(a)),
                squash=(1, 1.6, 1),
            )
    return m


@model("AM_Buriti")
def buriti() -> Mesh:
    """Buriti: estipe grosso e reto, coroa de folhas em leque e cachos de frutos."""
    m = Mesh()
    trunk(m, 6.8, 0.32, hexcolor("7a6650"), 0.85, 8, rings=4)
    top = (0.0, 6.8, 0.0)
    for i in range(10):  # folhas em leque: discos achatados
        yaw = 36 * i
        a = math.radians(yaw)
        tilt = 35 + 15 * (i % 2)
        m.beam(top, (1.3 * math.cos(a), 7.6 - 0.2 * (i % 2), 1.3 * math.sin(a)), 0.08, P["leaf_dark"])
        m.sphere(
            1.0,
            shade(P["leaf"], 0.9 + 0.1 * (i % 3)),
            2,
            9,
            at=chain(
                translate(2.0 * math.cos(a), 7.9 - 0.4 * (i % 2), 2.0 * math.sin(a)), rotate_y(-yaw), rotate_z(-tilt)
            ),
            squash=(1.0, 0.12, 0.9),
        )
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.4
        m.sphere(
            0.32,
            hexcolor("8a4a26"),
            3,
            6,
            at=translate(0.45 * math.cos(a), 6.3, 0.45 * math.sin(a)),
            squash=(1, 1.5, 1),
            jitter=0.15,
            seed=k,
        )
    return m


@model("AM_Seringueira")
def seringueira() -> Mesh:
    """Seringueira: tronco claro (com a tigelinha do látex) e copa arredondada."""
    m = Mesh()
    m.cylinder(0.34, 4.2, P["bark_light"], 8, 0.26)
    m.cylinder(0.12, 0.12, P["white"], 6, 0.16, at=translate(0.0, 1.2, 0.34))  # tigela do látex
    for yaw in (30, 150, 270):
        a = math.radians(yaw)
        m.beam((0, 3.6, 0), (1.3 * math.cos(a), 4.9, 1.3 * math.sin(a)), 0.16, P["bark_light"])
    canopy(m, (0, 5.4, 0), 2.4, P["leaf"], blobs=7, seed=23, flat=0.78)
    return m


@model("AM_Heliconia")
def heliconia() -> Mesh:
    """Helicônia: folhas grandes em remo e brácteas vermelhas e amarelas."""
    m = Mesh()
    for i in range(7):
        yaw = 360 * i / 7
        a = math.radians(yaw)
        h = 1.4 + 0.3 * (i % 3)
        m.beam((0, 0, 0), (0.25 * math.cos(a), h, 0.25 * math.sin(a)), 0.05, P["leaf_dark"])
        m.sphere(
            0.5,
            shade(P["leaf"], 0.9 + 0.08 * (i % 2)),
            2,
            6,
            at=chain(translate(0.45 * math.cos(a), h + 0.2, 0.45 * math.sin(a)), rotate_y(-yaw), rotate_z(-55)),
            squash=(0.35, 1.0, 0.12),
        )
    for k in range(3):
        a = math.radians(120 * k + 40)
        x, z = 0.3 * math.cos(a), 0.3 * math.sin(a)
        for j in range(4):
            m.cone(
                0.12,
                0.28,
                P["red"] if j % 2 == 0 else P["yellow"],
                4,
                at=chain(translate(x + (0.08 if j % 2 else -0.08), 1.0 + 0.22 * j, z), rotate_z(70 if j % 2 else -70)),
            )
    return m


@model("AM_VitoriaRegia")
def vitoria_regia() -> Mesh:
    """Vitória-régia: folhas redondas com borda virada e uma flor rosa."""
    m = Mesh()
    for i, (x, z, r) in enumerate(((0, 0, 1.2), (1.6, 0.6, 0.8), (-1.4, 0.7, 0.9), (0.5, -1.4, 0.7))):
        m.cylinder(r, 0.06, P["leaf"], 14, at=translate(x, 0, z), top_color=shade(P["leaf_light"], 1.0 - 0.05 * i))
        m.cylinder(r, 0.14, hexcolor("a8423a"), 14, r * 1.02, at=translate(x, 0.04, z), caps=False)
    for k in range(8):  # flor
        a = 2 * math.pi * k / 8
        m.sphere(
            0.18,
            P["pink"] if k % 2 else P["white"],
            2,
            5,
            at=translate(0.18 * math.cos(a), 0.25, 0.18 * math.sin(a)),
            squash=(1, 0.6, 1),
        )
    m.sphere(0.12, P["yellow"], 2, 5, at=translate(0, 0.33, 0))
    return m


# --------------------------------------------------------------- moradias
def house_box(m: Mesh, w: float, h: float, d: float, wall, roof, y: float = 0.0, door=None) -> Mesh:
    m.box((w, h, d), wall, at=translate(0, y, 0))
    windows_row(m, w, y + h * 0.4, d / 2, 2, (w * 0.18, h * 0.3), P["glass"], P["white"], 0.2)
    if door is not None:
        m.box((w * 0.16, h * 0.62, 0.03), door, at=translate(w * 0.32, y, d / 2 + 0.01))
    gable_roof(m, w, d, h * 0.55, y + h, roof)
    return m


@model("AM_Palafita")
def palafita() -> Mesh:
    """Casa de palafita colorida, com escadinha e varanda."""
    m = Mesh()
    stilts(m, 2.6, 1.8, 1.4, P["wood_dark"], (4, 3), 0.12)
    m.box((3.2, 0.12, 2.4), P["plank"], at=translate(0, 1.35, 0))
    house_box(m, 2.4, 1.6, 1.8, hexcolor("3f8fb5"), hexcolor("c8c1b0"), 1.47, P["wood"])
    m.box((0.08, 0.6, 2.4), P["wood"], at=translate(1.55, 1.47, 0))  # guarda-corpo da varanda
    for i in range(5):  # escada
        m.box((0.5, 0.08, 0.25), P["plank"], at=translate(1.9 + 0.14 * i, 1.25 - 0.27 * i, 0.9))
    return m


@model("AM_CasaFlutuante")
def casa_flutuante() -> Mesh:
    """Casa flutuante sobre toras, com telhado de zinco."""
    m = Mesh()
    for i in range(5):
        m.cylinder(0.22, 3.4, P["bark"], 7, at=chain(translate(-1.7, 0.22, -1.0 + 0.5 * i), rotate_z(-90)))
    m.box((3.4, 0.1, 2.5), P["plank"], at=translate(0, 0.42, 0))
    house_box(m, 2.4, 1.5, 1.7, hexcolor("e6c45a"), hexcolor("9aa3a8"), 0.52, P["wood_dark"])
    return m


@model("AM_PalafitaSolar")
def palafita_solar() -> Mesh:
    """Palafita solarpunk: painéis no telhado, horta suspensa e caixa d'água de chuva."""
    m = Mesh()
    stilts(m, 2.8, 2.0, 1.4, P["wood"], (4, 3), 0.12)
    m.box((3.4, 0.12, 2.6), P["plank"], at=translate(0, 1.35, 0))
    m.box((2.6, 1.7, 2.0), hexcolor("e9dcc0"), at=translate(0, 1.47, 0))
    windows_row(m, 2.6, 2.0, 1.0, 3, (0.42, 0.55), P["glass"], P["gold"], 0.35)
    m.box((2.9, 0.12, 2.3), P["green_roof"], at=translate(0, 3.17, 0))
    for i in range(2):
        solar_panel(m, translate(-0.65 + 1.3 * i, 3.35, 0.2), (1.1, 0.8), 22)
    m.cylinder(0.35, 0.8, hexcolor("4f9fb0"), 9, at=translate(-1.1, 3.29, -0.75))  # cisterna de chuva
    for i in range(4):  # horta na varanda
        m.box((0.4, 0.25, 0.4), P["wood"], at=translate(1.45, 1.47, -0.9 + 0.6 * i))
        m.sphere(0.22, P["leaf_light"], 2, 6, at=translate(1.45, 1.85, -0.9 + 0.6 * i), jitter=0.2, seed=i)
    return m


# -------------------------------------------------------------- marcos
@model("AM_TeatroAmazonas", sprite_max=420)
def teatro_amazonas() -> Mesh:
    """Inspirado no Teatro Amazonas: fachada rosada com colunas brancas e a cúpula colorida."""
    m = Mesh()
    wall, trim = hexcolor("e9a7a0"), P["white"]
    m.box((7.0, 0.5, 4.6), P["concrete"], at=translate(0, 0, 0))  # escadaria
    m.box((6.4, 3.4, 4.0), wall, at=translate(0, 0.5, 0))
    m.box((6.6, 0.3, 4.2), trim, at=translate(0, 3.9, 0))
    m.box((6.6, 0.25, 4.2), trim, at=translate(0, 2.2, 0))
    for i in range(6):  # colunata
        x = -2.5 + i
        m.cylinder(0.14, 2.6, trim, 8, at=translate(x, 0.5, 2.15))
    windows_row(m, 6.0, 2.6, 2.0, 5, (0.45, 0.8), P["glass"], trim, 0.3)
    m.slab([(-3.2, 0), (3.2, 0), (0, 1.1)], 0.3, wall, at=translate(0, 4.2, 2.0), side=trim)  # frontão
    # cúpula de ladrilhos em faixas (verde, amarelo e azul, como as cores da bandeira)
    colors = [hexcolor("2e8b57"), hexcolor("f2c037"), hexcolor("2f6fc0")]
    m.cylinder(1.6, 0.9, trim, 14, at=translate(0, 4.2, -0.4))
    profile = [(1.6, 0.0), (1.55, 0.55), (1.35, 1.1), (1.0, 1.55), (0.55, 1.85), (0.0, 1.98)]
    m.lathe(profile, colors[0], 14, at=translate(0, 5.1, -0.4), colors=[colors[k % 3] for k in range(5)])
    m.cylinder(0.12, 0.6, P["gold"], 6, at=translate(0, 7.05, -0.4))
    return m


@model("AM_PonteEstaiada", sprite_max=420, yaw=-20, pitch=14)
def ponte_estaiada() -> Mesh:
    """Ponte estaiada sobre o Rio Negro (silhueta para o horizonte)."""
    m = Mesh()
    m.box((16.0, 0.35, 1.2), P["concrete"], at=translate(0, 1.8, 0))
    for x in (-6.0, -2.0, 2.0, 6.0):
        m.box((0.4, 1.8, 0.6), P["concrete"], at=translate(x, 0, 0))
    m.box((0.5, 6.5, 0.7), P["white"], at=translate(0, 1.8, 0))
    for i in range(1, 7):
        for side in (-1, 1):
            m.beam((0, 7.8 - 0.35 * i, 0), (side * 1.15 * i, 2.15, 0), 0.05, P["white"])
    return m


# ------------------------------------------------------------------ barcos
def boat_hull(m: Mesh, length: float, width: float, height: float, color, stripe) -> Mesh:
    half = length / 2
    m.prism(
        [(-half, -width / 2), (half - 0.8, -width / 2), (half, 0), (half - 0.8, width / 2), (-half, width / 2)],
        height,
        color,
    )
    m.prism(
        [
            (-half, -width / 2 - 0.01),
            (half - 0.8, -width / 2 - 0.01),
            (half + 0.01, 0),
            (half - 0.8, width / 2 + 0.01),
            (-half, width / 2 + 0.01),
        ],
        height * 0.18,
        stripe,
        base=height * 0.55,
    )
    return m


@model("AM_BarcoRegional", yaw=-25, pitch=12)
def barco_regional() -> Mesh:
    """Barco regional de dois andares (recreio), visto de longe no horizonte."""
    m = Mesh()
    boat_hull(m, 6.0, 1.6, 0.6, P["white"], hexcolor("2f6fc0"))
    m.box((4.6, 0.9, 1.4), P["white"], at=translate(-0.4, 0.6, 0))
    windows_row(m, 4.4, 0.9, 0.7, 6, (0.45, 0.35), hexcolor("2f4f6f"), None, 0.0)
    m.box((3.6, 0.8, 1.3), hexcolor("f2c037"), at=translate(-0.7, 1.5, 0))
    m.box((3.9, 0.1, 1.5), hexcolor("2f6fc0"), at=translate(-0.7, 2.3, 0))
    return m


@model("AM_BarcoSolar")
def barco_solar() -> Mesh:
    """Barco regional elétrico, com teto de painéis solares."""
    m = Mesh()
    boat_hull(m, 4.4, 1.5, 0.55, P["white"], hexcolor("2e9e44"))
    m.box((3.0, 0.8, 1.3), hexcolor("f4efe2"), at=translate(-0.3, 0.55, 0))
    windows_row(m, 2.8, 0.75, 0.65, 4, (0.45, 0.35), P["glass"], None, 0.3)
    for i in range(3):
        solar_panel(m, translate(-1.2 + 0.95 * i, 1.45, 0), (0.85, 1.3), 8, (2, 3))
    return m


# -------------------------------------------------------- estágio industrial
@model("AM_Termeletrica")
def termeletrica() -> Mesh:
    """Usina termelétrica a óleo: galpão, tanques e duas chaminés fumegantes."""
    m = Mesh()
    m.box((5.0, 2.6, 3.0), hexcolor("6a625a"), at=translate(0, 0, 0))
    m.box((5.2, 0.25, 3.2), P["rust_dark"], at=translate(0, 2.6, 0))
    windows_row(m, 4.6, 1.4, 1.5, 4, (0.6, 0.5), hexcolor("e0a050"), P["rust_dark"], 0.5)
    for x in (-1.4, 0.4):
        band_cylinder(m, 0.38, 6.5, [P["concrete"], P["rust"]], 6, 0.3, at=translate(x, 2.6, -0.6))
        smoke(m, (x, 9.1, -0.6), 0.5, 3, seed=int(x * 10) + 5)
    for z in (-0.8, 0.8):
        m.cylinder(0.7, 1.6, P["steel"], 10, at=translate(3.4, 0, z), top_color=P["steel_dark"])
    m.beam((2.5, 1.2, 0.8), (3.0, 1.2, 0.8), 0.18, P["rust"])
    return m


@model("AM_GuindastePorto")
def guindaste_porto() -> Mesh:
    """Guindaste de pórtico do porto, enferrujado."""
    m = Mesh()
    color = hexcolor("c0622e")
    for x in (-1.4, 1.4):
        for z in (-1.0, 1.0):
            m.box((0.25, 5.0, 0.25), color, at=translate(x, 0, z))
    m.box((3.2, 0.5, 2.4), color, at=translate(0, 5.0, 0))
    m.box((1.0, 0.9, 1.0), P["steel_dark"], at=translate(0, 5.5, 0))
    m.box((0.4, 0.4, 6.0), color, at=translate(0, 5.9, 1.8))  # lança
    m.beam((0, 6.4, 0), (0, 6.3, 4.6), 0.05, P["steel_dark"])
    m.beam((0, 6.2, 4.4), (0, 3.6, 4.4), 0.04, P["steel_dark"])
    m.box((0.6, 0.4, 0.4), P["yellow"], at=translate(0, 3.2, 4.4))
    for x in (-1.4, 1.4):
        m.beam((x, 0.3, -1.0), (x, 4.8, 1.0), 0.1, shade(color, 0.85))
    return m


def container(m: Mesh, at, color) -> Mesh:
    m.box((2.4, 1.0, 1.0), color, at=at)
    for k in range(6):
        m.box((0.05, 0.95, 1.02), shade(color, 0.8), at=chain(at, translate(-1.0 + 0.4 * k, 0.02, 0)))
    return m


@model("AM_Containers")
def containers() -> Mesh:
    """Pilha de contêineres enferrujados do porto."""
    m = Mesh()
    colors = [hexcolor("a8442e"), hexcolor("2f5f8a"), hexcolor("c08a2e"), hexcolor("5a6e3a"), hexcolor("8a4a2a")]
    slots = [(0, 0, 0), (0, 0, 1.1), (0.2, 1.0, 0.55), (2.6, 0, 0.3), (2.5, 1.0, 0.3)]
    for (x, y, z), color in zip(slots, colors):
        container(m, translate(x, y, z), color)
    return m


@model("AM_ChamineTermeletrica")
def chamine_termeletrica() -> Mesh:
    """Chaminé alta listrada da termelétrica (obstáculo: desvie para o lado)."""
    m = Mesh()
    m.box((1.4, 0.8, 1.4), P["concrete"])
    band_cylinder(m, 0.55, 8.0, [hexcolor("c9c3b8"), hexcolor("b8452e")], 8, 0.42, at=translate(0, 0.8, 0))
    m.cylinder(0.5, 0.25, P["soot"], 10, 0.5, at=translate(0, 8.8, 0))
    smoke(m, (0.0, 9.0, 0.0), 0.55, 3, seed=9)
    return m


@model("AM_Balsa")
def balsa() -> Mesh:
    """Balsa de carga enferrujada com sacas e tambores (obstáculo: passe por cima)."""
    m = Mesh()
    m.prism(
        [(-2.0, -1.1), (1.6, -1.1), (2.1, -0.6), (2.1, 0.6), (1.6, 1.1), (-2.0, 1.1)],
        0.55,
        P["rust"],
        top=P["rust_dark"],
    )
    for i, (x, z) in enumerate(((-1.2, -0.4), (-1.2, 0.45), (-0.4, 0.0), (0.5, -0.45), (0.5, 0.4))):
        m.cylinder(0.32, 0.8, [P["steel"], hexcolor("3a6e8a"), P["rust"]][i % 3], 9, at=translate(x, 0.55, z))
    for k in range(3):
        m.sphere(0.4, P["sand"], 2, 6, at=translate(1.3, 0.85 + 0.0 * k, -0.6 + 0.6 * k), squash=(1.2, 0.6, 0.8))
    return m


@model("AM_PassarelaPalafita")
def passarela_palafita() -> Mesh:
    """Passarela alta de madeira sobre o rio (obstáculo: passe por baixo)."""
    m = Mesh()
    for x in (-2.6, 2.6):
        for z in (-0.5, 0.5):
            m.box((0.2, 3.9, 0.2), P["wood_dark"], at=translate(x, 0, z))
        m.beam((x, 0.2, -0.5), (x, 3.6, 0.5), 0.08, P["wood_dark"])
    m.box((5.6, 0.25, 1.3), P["plank"], at=translate(0, 3.7, 0))
    for z in (-0.6, 0.6):
        m.box((5.6, 0.08, 0.08), P["wood"], at=translate(0, 4.5, z))
        for k in range(8):
            m.box((0.07, 0.6, 0.07), P["wood"], at=translate(-2.6 + 0.74 * k, 3.95, z))
    for k in range(5):  # roupas no varal: cor e vida
        m.box((0.3, 0.4, 0.02), [P["red"], P["yellow"], P["blue"]][k % 3], at=translate(-1.6 + 0.8 * k, 3.95, 0.66))
    return m


# ----------------------------------------------------------- estágio solar
@model("AM_VitoriaRegiaSolar")
def vitoria_regia_solar() -> Mesh:
    """Ilha de vitórias-régias com células solares (obstáculo baixo: passe por cima)."""
    m = Mesh()
    m.cylinder(1.9, 0.35, hexcolor("2f7f6a"), 16, at=translate(0, 0, 0), top_color=hexcolor("3f8f5a"))
    m.cylinder(1.95, 0.4, hexcolor("a8423a"), 16, 2.0, at=translate(0, 0.2, 0), caps=False)
    for _i, (dx, dz) in enumerate(scatter(6, 1.2, 4)):
        solar_panel(m, translate(dx, 0.62, dz), (0.6, 0.45), 15, (2, 2))
    m.cylinder(0.08, 1.4, P["leaf_dark"], 5, at=translate(0, 0.35, 0))
    for k in range(8):
        a = 2 * math.pi * k / 8
        m.sphere(
            0.2,
            P["pink"] if k % 2 else P["white"],
            2,
            5,
            at=translate(0.22 * math.cos(a), 1.75, 0.22 * math.sin(a)),
            squash=(1, 0.6, 1),
        )
    m.sphere(0.14, P["yellow"], 2, 5, at=translate(0, 1.85, 0), emit=0.5)
    return m


@model("AM_PassarelaCopa")
def passarela_copa() -> Mesh:
    """Passarela suspensa entre copas (obstáculo: passe por baixo)."""
    m = Mesh()
    for x in (-2.7, 2.7):
        m.cylinder(0.3, 4.6, P["bark"], 8, 0.24, at=translate(x, 0, 0))
        canopy(m, (x, 5.0, 0), 1.2, P["leaf"], blobs=5, seed=int(x * 10) + 40, flat=0.7)
    for k in range(12):  # deck curvo de madeira
        t = k / 11
        x = -2.4 + 4.8 * t
        y = 3.7 - 0.25 * math.sin(math.pi * t)
        m.box((0.42, 0.08, 1.0), P["plank"], at=translate(x, y, 0))
    for z in (-0.5, 0.5):
        for k in range(11):
            t0, t1 = k / 11, (k + 1) / 11
            m.beam(
                (-2.4 + 4.8 * t0, 4.5 - 0.3 * math.sin(math.pi * t0), z),
                (-2.4 + 4.8 * t1, 4.5 - 0.3 * math.sin(math.pi * t1), z),
                0.05,
                hexcolor("c8a46a"),
            )
    flowers(m, (0, 3.75, 0.45), 2.2, P["pink"], 8, 3, 0.07)
    return m


@model("AM_TorreBioenergia")
def torre_bioenergia() -> Mesh:
    """Torre de bioenergia: tubos de algas verdes e aletas solares (obstáculo: desvie)."""
    m = Mesh()
    m.cylinder(0.75, 0.5, P["concrete"], 10)
    m.cylinder(0.2, 8.2, P["white"], 8, 0.16, at=translate(0, 0.5, 0))
    for k in range(4):
        a = 2 * math.pi * k / 4
        m.cylinder(
            0.13,
            5.6,
            hexcolor("5fd08a"),
            7,
            at=translate(0.42 * math.cos(a), 1.0, 0.42 * math.sin(a)),
            emit=0.35,
            top_color=P["white"],
        )
    for j in range(3):
        y = 6.8 + 0.5 * j
        for side in (-1, 1):
            solar_panel(m, chain(translate(side * 0.75, y, 0), rotate_z(side * 20)), (1.0, 0.5), 0, (2, 1))
    m.sphere(0.3, P["gold"], 3, 8, at=translate(0, 8.8, 0), emit=0.4)
    return m


__all__ = ["rotate_x", "lattice_tower", "rotate_z"]
