"""Piloto em camadas: corpo neutro (sem marcação de gênero) e itens opcionais.

Gera assets/pilot_layers/<vista>__<camada>.png para as vistas "flight" (de trás,
como no voo) e "menu" (3/4, olhando para a direita, como no hangar), e
anchors.json com a caixa do piloto em cada avião e a caixa do corpo na tela.
Pele, roupa e cabelo saem em tons de cinza; o jogo aplica a cor escolhida.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np

from .anchors import measure_all
from .kit import P, chain, hexcolor, rotate_x, rotate_z, translate
from .mesh import Mesh
from .raster import make_frame, render_layers

# Vista -> pose e câmera. "segura" e "lanca" são a criança em pé da abertura (GDD, seção 2).
VIEWS = {
    "flight": {"pose": "sentada", "yaw": 0.0, "pitch": 28.0},
    "menu": {"pose": "sentada", "yaw": -120.0, "pitch": 18.0},
    "segura": {"pose": "segura", "yaw": -150.0, "pitch": 8.0},
    "lanca": {"pose": "lanca", "yaw": -150.0, "pitch": 8.0},
}
SPRITE_MAX = 256
HEAD = (0.0, 1.08, 0.0)
HEAD_R = 0.32
TINTED = ("skin", "shirt", "hair_curto", "hair_cacheado", "hair_crespo", "hair_longo", "hair_trancas", "hair_coque")


# ------------------------------------------------------------------- corpo
def body(pose: str = "sentada") -> Mesh:
    """Criança de frente para -z: sentada acenando (voo), segurando o jornal ou lançando o avião."""
    m = Mesh()
    pants, shoe = hexcolor("2a3f6e"), hexcolor("e2483d")
    if pose != "sentada":
        return standing(m, pose, pants, shoe)
    m.box((0.5, 0.62, 0.32), (255, 255, 255), at=translate(0, 0.05, 0), part="shirt")  # tronco
    m.box((0.18, 0.1, 0.18), (255, 255, 255), at=translate(0, 0.66, 0), part="skin")  # pescoço
    m.sphere(HEAD_R, (255, 255, 255), 5, 10, at=translate(*HEAD), part="skin")  # cabeça
    for side in (-1, 1):
        m.sphere(0.07, (255, 255, 255), 2, 6, at=translate(side * HEAD_R, HEAD[1], 0.02), part="skin")  # orelhas
    for side in (-1, 1):  # pernas sentadas
        m.box((0.2, 0.18, 0.5), pants, at=translate(side * 0.13, 0.0, -0.2), part="base")
        m.box((0.18, 0.4, 0.18), pants, at=translate(side * 0.13, -0.32, -0.42), part="base")
        m.box((0.2, 0.12, 0.3), shoe, at=translate(side * 0.13, -0.42, -0.5), part="base")
    # braço esquerdo para a frente (segurando o avião), braço direito acenando
    m.beam((-0.3, 0.6, 0.0), (-0.36, 0.3, -0.25), 0.14, (255, 255, 255), part="shirt")
    m.beam((-0.36, 0.3, -0.25), (-0.28, 0.25, -0.5), 0.12, (255, 255, 255), part="skin")
    m.beam((0.3, 0.6, 0.0), (0.5, 0.85, -0.05), 0.14, (255, 255, 255), part="shirt")
    m.beam((0.5, 0.85, -0.05), (0.6, 1.22, -0.1), 0.12, (255, 255, 255), part="skin")
    m.sphere(0.09, (255, 255, 255), 2, 6, at=translate(0.61, 1.27, -0.1), part="skin")
    return face(m)


def face(m: Mesh) -> Mesh:
    """Olhos e sorriso na frente da cabeça."""
    for side in (-1, 1):
        m.sphere(
            0.045, hexcolor("1d2433"), 2, 6, at=translate(side * 0.11, HEAD[1] + 0.04, -HEAD_R + 0.03), part="base"
        )
    m.box((0.12, 0.03, 0.02), hexcolor("8a3a3a"), at=translate(0, HEAD[1] - 0.12, -HEAD_R + 0.04), part="base")
    return m


def standing(m: Mesh, pose: str, pants, shoe) -> Mesh:
    """Em pé: pernas retas até y = -0,95; a cabeça fica onde está na pose sentada (os itens servem)."""
    white = (255, 255, 255)
    m.box((0.5, 0.62, 0.32), white, at=translate(0, 0.05, 0), part="shirt")
    m.box((0.18, 0.1, 0.18), white, at=translate(0, 0.66, 0), part="skin")
    m.sphere(HEAD_R, white, 5, 10, at=translate(*HEAD), part="skin")
    for side in (-1, 1):
        m.sphere(0.07, white, 2, 6, at=translate(side * HEAD_R, HEAD[1], 0.02), part="skin")
        m.box((0.2, 0.92, 0.22), pants, at=translate(side * 0.13, -0.87, 0), part="base")
        m.box((0.22, 0.12, 0.34), shoe, at=translate(side * 0.13, -0.95, -0.06), part="base")
    if pose == "segura":  # as duas mãos à frente do peito, segurando a folha de jornal
        for side in (-1, 1):
            m.beam((side * 0.3, 0.6, 0.0), (side * 0.32, 0.35, -0.22), 0.14, white, part="shirt")
            m.beam((side * 0.32, 0.35, -0.22), (side * 0.16, 0.42, -0.45), 0.12, white, part="skin")
            m.sphere(0.09, white, 2, 6, at=translate(side * 0.14, 0.44, -0.5), part="skin")
    else:  # lança: braço direito esticado para a frente e para o alto, esquerdo para trás
        m.beam((0.3, 0.6, 0.0), (0.42, 0.95, -0.3), 0.14, white, part="shirt")
        m.beam((0.42, 0.95, -0.3), (0.48, 1.3, -0.62), 0.12, white, part="skin")
        m.sphere(0.09, white, 2, 6, at=translate(0.49, 1.35, -0.68), part="skin")
        m.beam((-0.3, 0.6, 0.0), (-0.42, 0.25, 0.18), 0.14, white, part="shirt")
        m.beam((-0.42, 0.25, 0.18), (-0.45, -0.05, 0.25), 0.12, white, part="skin")
    return face(m)


# ---------------------------------------------------------------- cabelos
def cap(m: Mesh, part: str, grow: float = 1.06, drop: float = 0.0) -> Mesh:
    """Calota de cabelo: cobre o alto e a nuca, deixa o rosto livre."""
    m.sphere(
        HEAD_R * grow,
        (255, 255, 255),
        5,
        10,
        at=translate(0, HEAD[1] + 0.06 - drop, 0.05),
        squash=(1.0, 0.82, 1.0),
        part=part,
        jitter=0.04,
        seed=3,
    )
    return m


def hair(style: str) -> Mesh:
    m = Mesh()
    part = f"hair_{style}"
    if style == "curto":
        cap(m, part)
    elif style == "cacheado":
        cap(m, part, 1.02)
        for i in range(26):
            a, b = np.radians(i * 137.5), np.radians(15 + (i * 53) % 75)
            x = HEAD_R * 1.05 * np.cos(a) * np.cos(b)
            z = HEAD_R * 1.05 * np.sin(a) * np.cos(b) + 0.05
            y = HEAD[1] + 0.05 + HEAD_R * 0.95 * np.sin(b)
            if z < -0.18 and y < HEAD[1] + 0.2:
                continue  # não cobre o rosto
            m.sphere(0.1, (255, 255, 255), 2, 6, at=translate(x, y, z), part=part)
    elif style == "crespo":
        m.sphere(0.5, (255, 255, 255), 5, 11, at=translate(0, HEAD[1] + 0.16, 0.12), part=part, jitter=0.06, seed=5)
    elif style == "longo":
        cap(m, part)
        m.box((0.6, 0.62, 0.14), (255, 255, 255), at=translate(0, 0.62, 0.22), part=part)
        for side in (-1, 1):
            m.box((0.12, 0.45, 0.16), (255, 255, 255), at=translate(side * 0.32, 0.75, 0.02), part=part)
    elif style == "trancas":
        cap(m, part)
        for side in (-1, 1):
            for k in range(5):
                m.sphere(
                    0.075, (255, 255, 255), 2, 6, at=translate(side * 0.3, HEAD[1] - 0.12 - 0.12 * k, 0.12), part=part
                )
    elif style == "coque":
        cap(m, part)
        m.sphere(0.16, (255, 255, 255), 3, 8, at=translate(0, HEAD[1] + 0.34, 0.16), part=part)
    return m


# ------------------------------------------------------------------- itens
def glasses(style: str) -> Mesh:
    m = Mesh()
    part = f"glasses_{style}"
    frame = hexcolor("1d2433") if style != "redondo" else hexcolor("8a4a2a")
    lens = hexcolor("2a2f3a") if style == "sol" else hexcolor("cfefff")
    z = -HEAD_R - 0.01
    for side in (-1, 1):
        at = chain(translate(side * 0.12, HEAD[1] + 0.02, z), rotate_x(90))
        if style == "quadrado":
            m.box((0.17, 0.04, 0.13), frame, at=chain(at, translate(0, -0.02, 0)), part=part)
            m.box((0.13, 0.05, 0.09), lens, at=chain(at, translate(0, -0.03, 0)), part=part, emit=0.2)
        else:
            m.cylinder(0.085, 0.04, frame, 10, at=chain(at, translate(0, -0.02, 0)), part=part)
            m.cylinder(0.065, 0.05, lens, 10, at=chain(at, translate(0, -0.03, 0)), part=part, emit=0.2)
        m.beam((side * 0.2, HEAD[1] + 0.03, z + 0.02), (side * 0.31, HEAD[1] + 0.03, 0.05), 0.025, frame, part=part)
    m.beam((-0.04, HEAD[1] + 0.03, z - 0.01), (0.04, HEAD[1] + 0.03, z - 0.01), 0.025, frame, part=part)
    return m


def accessory(style: str) -> Mesh:
    m = Mesh()
    part = f"acc_{style}"
    if style == "bone":
        m.sphere(
            HEAD_R * 1.08,
            hexcolor("e2483d"),
            4,
            10,
            at=translate(0, HEAD[1] + 0.1, 0.03),
            squash=(1, 0.7, 1),
            part=part,
        )
        m.box((0.42, 0.04, 0.3), hexcolor("c23a30"), at=translate(0, HEAD[1] + 0.12, -0.33), part=part)
    elif style == "lenco":
        m.sphere(
            HEAD_R * 1.07,
            hexcolor("f07c2a"),
            4,
            10,
            at=translate(0, HEAD[1] + 0.09, 0.04),
            squash=(1, 0.72, 1),
            part=part,
        )
        m.sphere(0.09, hexcolor("d9662a"), 2, 6, at=translate(0.0, HEAD[1] + 0.02, 0.36), part=part)
        m.slab(
            [(-0.06, 0), (0.06, 0), (0.0, -0.2)], 0.03, hexcolor("d9662a"), at=translate(0.0, HEAD[1], 0.38), part=part
        )
    elif style == "abafador":
        color, pad = hexcolor("2f7fd6"), hexcolor("1d2433")
        for side in (-1, 1):
            m.cylinder(
                0.13,
                0.12,
                color,
                10,
                at=chain(translate(side * (HEAD_R + 0.02), HEAD[1], 0.02), rotate_z(side * 90)),
                part=part,
            )
            m.cylinder(
                0.1,
                0.04,
                pad,
                10,
                at=chain(translate(side * (HEAD_R - 0.01), HEAD[1], 0.02), rotate_z(side * 90)),
                part=part,
            )
        for k in range(8):
            a0, a1 = np.pi * k / 8, np.pi * (k + 1) / 8
            m.beam(
                (-(HEAD_R + 0.08) * np.cos(a0), HEAD[1] + (HEAD_R + 0.08) * np.sin(a0), 0.02),
                (-(HEAD_R + 0.08) * np.cos(a1), HEAD[1] + (HEAD_R + 0.08) * np.sin(a1), 0.02),
                0.06,
                color,
                part=part,
            )
    elif style == "capacete":
        leather = hexcolor("7a4a2a")
        m.sphere(HEAD_R * 1.1, leather, 5, 10, at=translate(0, HEAD[1] + 0.05, 0.03), squash=(1, 0.85, 1), part=part)
        for side in (-1, 1):
            m.box((0.12, 0.3, 0.16), leather, at=translate(side * 0.3, HEAD[1] - 0.25, 0.02), part=part)
            m.cylinder(
                0.08,
                0.05,
                hexcolor("b8893a"),
                10,
                at=chain(translate(side * 0.12, HEAD[1] + 0.2, -0.3), rotate_x(70)),
                part=part,
            )
            m.cylinder(
                0.06,
                0.06,
                hexcolor("9fdcf0"),
                10,
                at=chain(translate(side * 0.12, HEAD[1] + 0.2, -0.31), rotate_x(70)),
                part=part,
                emit=0.3,
            )
    return m


def hearing_aid() -> Mesh:
    """Aparelho auditivo atrás da orelha (colorido, para ficar visível como acessório comum)."""
    m = Mesh()
    color = hexcolor("1fb0a8")
    for side in (-1, 1):
        m.box((0.06, 0.16, 0.1), color, at=translate(side * (HEAD_R + 0.04), HEAD[1] - 0.06, 0.1), part="hearing")
        m.sphere(0.04, color, 2, 6, at=translate(side * (HEAD_R + 0.05), HEAD[1] + 0.02, 0.0), part="hearing")
    return m


def wheelchair() -> Mesh:
    """Cadeira de rodas com rodas grandes, encosto e empunhaduras."""
    m = Mesh()
    frame, seat, tyre = hexcolor("b8c2cc"), hexcolor("2f6fc0"), hexcolor("2a2a2a")
    m.box((0.62, 0.08, 0.55), seat, at=translate(0, -0.1, -0.08), part="chair")
    m.box((0.6, 0.62, 0.06), seat, at=translate(0, -0.05, 0.24), part="chair")
    for side in (-1, 1):
        wheel = chain(translate(side * 0.4, 0.05, 0.05), rotate_z(90))
        m.cylinder(0.42, 0.06, tyre, 14, at=chain(wheel, translate(0, -0.03, 0)), part="chair")
        m.cylinder(0.34, 0.07, frame, 14, at=chain(wheel, translate(0, -0.035, 0)), part="chair")
        m.cylinder(0.08, 0.09, seat, 8, at=chain(wheel, translate(0, -0.045, 0)), part="chair")
        m.beam((side * 0.32, 0.55, 0.27), (side * 0.32, 0.6, 0.42), 0.05, frame, part="chair")  # empunhadura
        m.beam((side * 0.3, -0.1, -0.34), (side * 0.3, -0.42, -0.4), 0.04, frame, part="chair")
        m.cylinder(0.07, 0.04, tyre, 8, at=chain(translate(side * 0.3, -0.42, -0.42), rotate_z(90)), part="chair")
    return m


OPTIONS: Dict[str, Mesh] = {}


def options() -> Dict[str, Mesh]:
    if not OPTIONS:
        for style in ("curto", "cacheado", "crespo", "longo", "trancas", "coque"):
            OPTIONS[f"hair_{style}"] = hair(style)
        for style in ("redondo", "quadrado", "sol"):
            OPTIONS[f"glasses_{style}"] = glasses(style)
        for style in ("bone", "lenco", "abafador", "capacete"):
            OPTIONS[f"acc_{style}"] = accessory(style)
        OPTIONS["hearing"] = hearing_aid()
        OPTIONS["chair"] = wheelchair()
    return OPTIONS


# ------------------------------------------------------------------- build
def build_pilot(assets: Path) -> None:
    folder = assets / "pilot_layers"
    folder.mkdir(parents=True, exist_ok=True)
    layout: Dict[str, Dict[str, List[int]]] = {}
    for view, cam in VIEWS.items():
        base = body(cam["pose"])
        everything = Mesh().extend(base)
        for name, mesh in options().items():
            if name != "chair" or cam["pose"] == "sentada":
                everything.extend(mesh)
        frame = make_frame(everything, cam["yaw"], cam["pitch"], SPRITE_MAX)
        layers = render_layers(base, cam["yaw"], cam["pitch"], frame, white_parts=TINTED)
        for name, image in layers.items():
            image.save(folder / f"{view}__{name}.png", optimize=True)
        alpha = np.maximum.reduce([np.asarray(img)[..., 3] for img in layers.values()])
        ys, xs = np.nonzero(alpha > 40)
        layout[view] = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        for name, mesh in options().items():
            if name == "chair" and cam["pose"] != "sentada":
                continue  # em pé não há cadeira: com cadeira, a abertura usa a pose sentada
            scene = Mesh().extend(base).extend(mesh)
            image = render_layers(scene, cam["yaw"], cam["pitch"], frame, white_parts=TINTED).get(name)
            if image is not None:
                image.save(folder / f"{view}__{name}.png", optimize=True)
        print(view, "camadas:", len(list(folder.glob(f"{view}__*.png"))), "corpo:", layout[view])
    anchors = measure_all(assets)
    anchors["body"] = layout
    (folder / "anchors.json").write_text(json.dumps(anchors, indent=1), encoding="utf-8")
    print("anchors.json gravado")


__all__ = ["build_pilot", "P"]
