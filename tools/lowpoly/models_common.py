"""Resíduos coletáveis (coleta seletiva, cores da CONAMA 275/2001) e melhorias da vila.

Resíduos: objetos que flutuam sobre uma "aura" (disco na cor da lixeira).
Vila: ponto de troca, horta, casa com painéis e sobrado com telhado verde.
"""

from __future__ import annotations

import math

from .kit import (
    P,
    chain,
    flowers,
    gable_roof,
    hexcolor,
    model,
    rotate_x,
    rotate_z,
    scale,
    shade,
    solar_panel,
    translate,
    windows_row,
)
from .mesh import Mesh, mix, scatter

# cores da coleta seletiva (CONAMA 275/2001)
BIN_BLUE = hexcolor("1e6fd9")
BIN_RED = hexcolor("e53935")
BIN_YELLOW = hexcolor("fbc02d")
BIN_GREEN = hexcolor("2e9e44")
WHITE = hexcolor("f7f4ec")
SILVER = hexcolor("c9ced6")
TWINE = hexcolor("b8935a")
GLASS_BLUE = hexcolor("a6dcef")

LIFT = 0.3  # altura do objeto sobre a aura


# ------------------------------------------------------------------ auras
def aura(mesh: Mesh, color, radius: float = 0.36) -> Mesh:
    """Disco achatado no chão, na cor da lixeira, com um miolo mais claro."""
    mesh.cylinder(radius, 0.03, color, 16)
    mesh.cylinder(radius * 0.62, 0.02, mix(color, WHITE, 0.35), 16, at=translate(0, 0.03, 0))
    return mesh


# ---------------------------------------------------------------- resíduos
def _paper_bundle(m: Mesh) -> Mesh:
    """Bola de jornal amassado (facetas claras e cinzentas) com uma cinta azul."""
    paper = hexcolor("f0ebdc")
    m.sphere(0.34, paper, 5, 9, at=translate(0, LIFT + 0.32, 0), jitter=0.22, seed=12)
    for i, (dx, dz) in enumerate(scatter(5, 0.2, 7)):  # "manchas" de texto impresso
        m.sphere(
            0.12,
            hexcolor("8a8a86") if i % 2 else hexcolor("b9b6ad"),
            2,
            5,
            at=translate(dx, LIFT + 0.42 + 0.05 * (i % 3), dz + 0.12),
            squash=(1, 0.5, 1),
        )
    m.cylinder(0.345, 0.1, BIN_BLUE, 12, at=chain(translate(0, LIFT + 0.27, 0), rotate_z(12)), caps=False)
    return m


@model("papel", "waste_sprites", yaw=-30, pitch=28, sprite_max=256)
def papel() -> Mesh:
    """Maço de papel/jornal amarrado: faixa e etiqueta azuis."""
    m = aura(Mesh(), BIN_BLUE)
    return _paper_bundle(m)


def _pet_bottle(m: Mesh) -> Mesh:
    """Garrafa PET translúcida (azul-claro) com rótulo e tampa vermelhos."""
    profile = [
        (0.0, 0.0),
        (0.2, 0.0),
        (0.24, 0.06),
        (0.25, 0.2),
        (0.25, 0.5),
        (0.22, 0.6),
        (0.13, 0.72),
        (0.1, 0.78),
        (0.1, 0.82),
        (0.0, 0.82),
    ]
    body = [GLASS_BLUE] * (len(profile) - 1)
    m.lathe(profile, GLASS_BLUE, 12, at=translate(0, LIFT, 0), colors=body)
    m.cylinder(0.255, 0.22, BIN_RED, 12, at=translate(0, LIFT + 0.2, 0), caps=False)  # rótulo
    m.cylinder(0.105, 0.1, BIN_RED, 10, at=translate(0, LIFT + 0.78, 0))  # tampa
    return m


@model("plastico", "waste_sprites", yaw=-30, pitch=28, sprite_max=256)
def plastico() -> Mesh:
    """Garrafa PET com rótulo e tampa vermelhos sobre aura vermelha."""
    m = aura(Mesh(), BIN_RED)
    return _pet_bottle(m)


def _alu_can(m: Mesh) -> Mesh:
    """Lata de alumínio amassada: prateada, faixa amarela e tampa."""
    squash = (1.0, 1.0, 0.8)
    m.cylinder(0.18, 0.5, SILVER, 12, at=chain(translate(0, LIFT, 0), scale(*squash)))
    m.cylinder(0.186, 0.12, BIN_YELLOW, 12, at=chain(translate(0, LIFT + 0.19, 0), scale(*squash)), caps=False)
    m.cylinder(0.15, 0.04, shade(SILVER, 0.8), 12, at=chain(translate(0, LIFT + 0.5, 0), scale(*squash)))
    m.sphere(0.14, SILVER, 3, 8, at=translate(0.16, LIFT + 0.28, 0.05), squash=(0.6, 1.2, 0.6), jitter=0.2, seed=3)
    m.box((0.08, 0.02, 0.05), shade(SILVER, 0.7), at=translate(0.02, LIFT + 0.53, 0.05))  # argola
    return m


@model("metal", "waste_sprites", yaw=-30, pitch=28, sprite_max=256)
def metal() -> Mesh:
    """Lata de alumínio amassada, prateada com faixa amarela, sobre aura amarela."""
    m = aura(Mesh(), BIN_YELLOW)
    return _alu_can(m)


def _glass_bottle(m: Mesh) -> Mesh:
    """Garrafa de vidro verde com rótulo claro e brilho."""
    green = BIN_GREEN
    profile = [(0.0, 0.0), (0.2, 0.0), (0.21, 0.05), (0.21, 0.42), (0.17, 0.55), (0.08, 0.66), (0.07, 0.7), (0.0, 0.7)]
    m.lathe(profile, green, 12, at=translate(0, LIFT, 0))
    m.cylinder(0.095, 0.05, shade(green, 0.7), 10, at=translate(0, LIFT + 0.68, 0))  # tampa
    m.cylinder(0.212, 0.2, WHITE, 12, at=translate(0, LIFT + 0.14, 0), caps=False)  # rótulo
    m.box((0.04, 0.3, 0.02), shade(green, 1.45), at=translate(-0.1, LIFT + 0.04, 0.19))  # brilho
    return m


@model("vidro", "waste_sprites", yaw=-30, pitch=28, sprite_max=256)
def vidro() -> Mesh:
    """Garrafa de vidro verde com rótulo claro sobre aura verde."""
    m = aura(Mesh(), BIN_GREEN)
    return _glass_bottle(m)


# ------------------------------------------------------------ vila: ponto de troca
def _recycle_bin(m: Mesh, x: float, color) -> Mesh:
    """Contêiner de coleta: corpo colorido, tampa clara e boca escura."""
    m.box((0.9, 1.0, 0.72), color, at=translate(x, 0, 0))
    m.box((0.96, 0.08, 0.78), shade(color, 1.12), at=translate(x, 1.0, 0))
    m.box((0.5, 0.12, 0.03), shade(color, 0.4), at=translate(x, 0.68, 0.37))
    return m


@model("VL_PontoTroca", "biome_sprites", sprite_max=320)
def ponto_troca() -> Mesh:
    """Ecoponto: quatro contêineres azul, vermelho, amarelo e verde sob cobertura de madeira."""
    m = Mesh()
    for x, color in zip((-1.5, -0.5, 0.5, 1.5), (BIN_BLUE, BIN_RED, BIN_YELLOW, BIN_GREEN)):
        _recycle_bin(m, x, color)
    for x in (-2.2, 2.2):
        for z in (-0.6, 0.6):
            m.box((0.12, 2.0, 0.12), P["wood"], at=translate(x, 0, z))
    m.box((5.0, 0.14, 2.0), P["plank"], at=translate(0, 2.0, 0))
    m.box((5.1, 0.04, 2.1), P["wood_dark"], at=translate(0, 1.94, 0))
    return m


# ------------------------------------------------------------ vila: horta
def _lettuce(m: Mesh, x: float, z: float) -> Mesh:
    for dx, dz in ((-0.25, 0.0), (0.25, 0.0), (0.0, 0.2), (0.0, -0.2)):
        m.sphere(0.2, shade(P["leaf_light"], 0.95), 2, 6, at=translate(x + dx, 0.5, z + dz), squash=(1, 0.6, 1))
    return m


def _tomato(m: Mesh, x: float, z: float) -> Mesh:
    for dx in (-0.3, 0.0, 0.3):
        m.beam((x + dx, 0.42, z), (x + dx, 0.95, z), 0.05, P["leaf_dark"])
        m.sphere(0.2, P["leaf"], 2, 6, at=translate(x + dx, 0.98, z), squash=(1, 0.7, 1))
        m.sphere(0.1, P["red"], 2, 6, at=translate(x + dx + 0.12, 0.8, z + 0.1))
    return m


def _carrots(m: Mesh, x: float, z: float) -> Mesh:
    for dz in (-0.25, 0.0, 0.25):
        m.cone(0.07, 0.22, P["orange"], 6, at=chain(translate(x, 0.47, z + dz), rotate_x(180)))
        m.sphere(0.07, P["leaf_light"], 2, 5, at=translate(x, 0.56, z + dz))
    return m


def _watering_can(m: Mesh, x: float, z: float) -> Mesh:
    blue = hexcolor("3f8fd0")
    m.cylinder(0.2, 0.36, blue, 10, at=translate(x, 0, z))
    m.beam((x + 0.18, 0.08, z), (x + 0.5, 0.4, z), 0.07, blue)
    m.cylinder(0.05, 0.1, shade(blue, 0.7), 6, at=translate(x + 0.5, 0.4, z))
    m.beam((x - 0.2, 0.32, z), (x, 0.62, z), 0.05, shade(blue, 0.8))
    m.beam((x, 0.62, z), (x + 0.2, 0.32, z), 0.05, shade(blue, 0.8))
    return m


@model("VL_Horta", "biome_sprites", sprite_max=320)
def horta() -> Mesh:
    """Horta urbana: três canteiros de madeira (alface, tomate e cenoura) e um regador."""
    m = Mesh()
    for x in (-1.7, 0.0, 1.7):
        m.box((1.2, 0.45, 0.8), P["wood"], at=translate(x, 0, 0))
        m.box((1.1, 0.05, 0.7), hexcolor("4a3224"), at=translate(x, 0.4, 0))
    _lettuce(m, -1.7, 0.0)
    _tomato(m, 0.0, 0.0)
    _carrots(m, 1.7, 0.0)
    _watering_can(m, 2.8, 0.4)
    return m


# ------------------------------------------------------------ vila: painéis
@model("VL_PaineisSolares", "biome_sprites", sprite_max=320)
def paineis_solares() -> Mesh:
    """Casinha com telhado coberto de painéis solares e um inversor na parede."""
    m = Mesh()
    cream = hexcolor("f1e3c2")
    m.box((2.4, 1.4, 2.0), cream, at=translate(0, 0, 0))
    windows_row(m, 2.4, 0.85, 1.0, 1, (0.45, 0.45), P["glass"], P["white"], 0.25, x0=0.6)
    m.box((0.4, 0.85, 0.03), P["wood"], at=translate(-0.5, 0, 1.01))
    gable_roof(m, 2.4, 2.0, 0.9, 1.4, hexcolor("8a5a48"), overhang=0.1)
    slope = math.degrees(math.atan2(0.94, 1.3))
    for side in (-1, 1):
        cx = side * 0.65
        cy = 1.83 + 0.05
        solar_panel(m, chain(translate(cx, cy, 0), rotate_z(-side * slope)), (1.5, 1.7), 0, (3, 2))
    m.box((0.05, 0.4, 0.28), P["steel"], at=translate(1.22, 0.4, 0))  # inversor
    m.box((0.01, 0.05, 0.05), hexcolor("7dff9a"), at=translate(1.25, 0.6, 0), emit=0.9)  # LED
    return m


# ------------------------------------------------------------ vila: telhado verde
@model("VL_TelhadoVerde", "biome_sprites", sprite_max=320)
def telhado_verde() -> Mesh:
    """Sobrado de dois andares com telhado plano coberto de plantas e flores."""
    m = Mesh()
    m.box((2.6, 1.3, 2.2), hexcolor("f6e7c1"), at=translate(0, 0, 0))
    m.box((2.4, 1.2, 2.0), hexcolor("e8a07a"), at=translate(0, 1.3, 0))
    m.box((2.8, 0.14, 2.4), P["wood_dark"], at=translate(0, 2.5, 0))  # laje
    m.box((2.7, 0.18, 2.3), hexcolor("5a4632"), at=translate(0, 2.64, 0))  # terra
    windows_row(m, 2.6, 0.35, 1.1, 2, (0.7, 0.7), P["glass"], P["white"], 0.35)
    windows_row(m, 2.4, 1.65, 1.0, 2, (0.6, 0.55), P["glass"], P["white"], 0.35)
    for k, (dx, dz) in enumerate(scatter(22, 1.05, 9)):
        tone = shade(P["leaf"], 0.9 + 0.2 * (k % 3))
        m.sphere(0.18, tone, 2, 6, at=translate(dx, 2.82, dz), squash=(1, 0.7, 1), jitter=0.15, seed=k)
    flowers(m, (0, 2.8, 0), 1.0, P["pink"], 6, 4, 0.1)
    flowers(m, (0, 2.8, 0), 1.0, P["yellow"], 5, 8, 0.1)
    for k, (dx, _dz) in enumerate(scatter(5, 1.0, 12)):  # vasos e folhas na borda
        m.sphere(0.12, P["leaf_light"], 2, 5, at=translate(dx * 1.1, 1.85 - 0.3 * (k % 2), 1.14))
    return m
