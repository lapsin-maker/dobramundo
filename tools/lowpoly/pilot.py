"""Piloto em camadas: criança de traço redondo (cabeça grande, corpo curto, olhos
grandes), sem marcação de gênero, com itens opcionais.

Gera assets/pilot_layers/<vista>__<camada>.png para as vistas "flight" (de trás,
como no voo) e "menu" (3/4, olhando para a direita, como no hangar), mais
"segura" e "lanca" (em pé, na abertura), e anchors.json com a caixa do piloto em
cada avião e a caixa do corpo na tela. Pele, roupa, cabelo e os itens tingíveis
saem em branco; o jogo aplica a cor escolhida por multiplicação.
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
# Proporções "chibi": a cabeça tem quase o tamanho do tronco.
HEAD = (0.0, 1.0, 0.0)
HEAD_R = 0.42
TORSO = (0.0, 0.22, 0.0)
WHITE = (255, 255, 255)
HAIR_STYLES = ("curto", "cacheado", "crespo", "longo", "trancas", "coque", "franja", "chiquinhas", "moicano", "puffs")
# Camadas que o jogo tinge com a cor escolhida (saem brancas do rasterizador).
TINTED = ("skin", "shirt", "hijab") + tuple(f"hair_{style}" for style in HAIR_STYLES)
INK = hexcolor("1d2433")


# ------------------------------------------------------------------- corpo
def body(pose: str = "sentada") -> Mesh:
    """Criança de frente para -z: sentada acenando (voo), segurando o jornal ou lançando o avião."""
    m = Mesh()
    pants, shoe = hexcolor("2a3f6e"), hexcolor("e2483d")
    head_and_torso(m)
    if pose != "sentada":
        return standing(m, pose, pants, shoe)
    for side in (-1, 1):  # pernas curtas, sentadas, com tênis redondos
        m.beam((side * 0.15, 0.0, 0.0), (side * 0.17, -0.02, -0.34), 0.2, pants, part="base", segments=8)
        m.beam((side * 0.17, -0.02, -0.34), (side * 0.17, -0.3, -0.4), 0.18, pants, part="base", segments=8)
        m.sphere(0.13, shoe, 3, 8, at=translate(side * 0.17, -0.36, -0.46), squash=(1.0, 0.75, 1.25), part="base")
    # braço esquerdo para a frente (segurando o avião), braço direito acenando
    arm(m, (-0.3, 0.42, 0.0), (-0.38, 0.12, -0.26), (-0.3, 0.1, -0.5))
    arm(m, (0.3, 0.42, 0.0), (0.5, 0.72, -0.04), (0.6, 1.1, -0.08))
    return face(m)


def head_and_torso(m: Mesh) -> None:
    """Tronco arredondado (esfera achatada), pescoço curto e cabeça grande."""
    m.sphere(0.36, WHITE, 5, 12, at=translate(*TORSO), squash=(1.0, 1.05, 0.8), part="shirt")
    m.cylinder(0.12, 0.14, WHITE, 10, at=translate(0, 0.5, 0), part="skin")
    m.sphere(HEAD_R, WHITE, 6, 14, at=translate(*HEAD), squash=(1.0, 0.98, 0.96), part="skin")
    for side in (-1, 1):
        m.sphere(0.08, WHITE, 2, 6, at=translate(side * HEAD_R, HEAD[1] - 0.02, 0.02), part="skin")  # orelhas


def arm(m: Mesh, shoulder, elbow, hand) -> None:
    m.beam(shoulder, elbow, 0.15, WHITE, part="shirt", segments=8)
    m.beam(elbow, hand, 0.13, WHITE, part="skin", segments=8)
    m.sphere(0.1, WHITE, 3, 8, at=translate(*hand), part="skin")


def face(m: Mesh) -> Mesh:
    """Olhos grandes com brilho, bochechas e sorriso na frente da cabeça."""
    front = -HEAD_R
    for side in (-1, 1):
        x = side * 0.15
        m.sphere(0.085, (250, 250, 250), 3, 8, at=translate(x, HEAD[1] + 0.03, front + 0.05), part="base")
        m.sphere(0.052, INK, 3, 8, at=translate(x + side * 0.005, HEAD[1] + 0.03, front + 0.005), part="base")
        m.sphere(
            0.018, (255, 255, 255), 2, 6, at=translate(x - 0.02, HEAD[1] + 0.06, front - 0.03), part="base", emit=1.0
        )
        m.sphere(0.06, hexcolor("f0a0a0"), 2, 6, at=translate(side * 0.27, HEAD[1] - 0.1, front + 0.14), part="base")
    # sorriso: três segmentos num arco
    arc = [(-0.11, -0.16), (-0.04, -0.2), (0.04, -0.2), (0.11, -0.16)]
    for (x0, y0), (x1, y1) in zip(arc, arc[1:]):
        m.beam(
            (x0, HEAD[1] + y0, front + 0.02), (x1, HEAD[1] + y1, front + 0.02), 0.03, hexcolor("8a3a3a"), part="base"
        )
    return m


def standing(m: Mesh, pose: str, pants, shoe) -> Mesh:
    """Em pé: pernas curtas até y = -0,7; a cabeça fica onde está na pose sentada (os itens servem)."""
    for side in (-1, 1):
        m.beam((side * 0.15, 0.0, 0.0), (side * 0.16, -0.6, 0.0), 0.2, pants, part="base", segments=8)
        m.sphere(0.13, shoe, 3, 8, at=translate(side * 0.16, -0.66, -0.06), squash=(1.0, 0.7, 1.3), part="base")
    if pose == "segura":  # as duas mãos à frente do peito, segurando a folha de jornal
        for side in (-1, 1):
            arm(m, (side * 0.3, 0.42, 0.0), (side * 0.34, 0.14, -0.2), (side * 0.14, 0.24, -0.46))
    else:  # lança: braço direito esticado para a frente e para o alto, esquerdo para trás
        arm(m, (0.3, 0.42, 0.0), (0.44, 0.8, -0.28), (0.5, 1.2, -0.62))
        arm(m, (-0.3, 0.42, 0.0), (-0.42, 0.1, 0.16), (-0.46, -0.18, 0.24))
    return face(m)


# ---------------------------------------------------------------- cabelos
def cap(m: Mesh, part: str, grow: float = 1.06, drop: float = 0.0, squash_y: float = 0.84) -> Mesh:
    """Calota de cabelo: cobre o alto e a nuca, deixa o rosto livre."""
    m.sphere(
        HEAD_R * grow,
        WHITE,
        5,
        12,
        at=translate(0, HEAD[1] + 0.07 - drop, 0.06),
        squash=(1.0, squash_y, 1.0),
        part=part,
        jitter=0.03,
        seed=3,
    )
    return m


def curls(m: Mesh, part: str, count: int, radius: float, lift: float = 0.05) -> None:
    for i in range(count):
        a, b = np.radians(i * 137.5), np.radians(15 + (i * 53) % 75)
        x = HEAD_R * 1.05 * np.cos(a) * np.cos(b)
        z = HEAD_R * 1.05 * np.sin(a) * np.cos(b) + 0.05
        y = HEAD[1] + lift + HEAD_R * 0.95 * np.sin(b)
        if z < -0.22 and y < HEAD[1] + 0.22:
            continue  # não cobre o rosto
        m.sphere(radius, WHITE, 2, 6, at=translate(x, y, z), part=part)


def hair(style: str) -> Mesh:
    m = Mesh()
    part = f"hair_{style}"
    if style == "curto":
        cap(m, part)
    elif style == "cacheado":
        cap(m, part, 1.02)
        curls(m, part, 28, 0.11)
    elif style == "crespo":
        m.sphere(0.62, WHITE, 5, 12, at=translate(0, HEAD[1] + 0.18, 0.12), part=part, jitter=0.06, seed=5)
    elif style == "longo":
        cap(m, part)
        m.box((0.76, 0.8, 0.16), WHITE, at=translate(0, 0.5, 0.26), part=part)
        for side in (-1, 1):
            m.box((0.14, 0.6, 0.18), WHITE, at=translate(side * 0.42, 0.62, 0.02), part=part)
    elif style == "trancas":
        cap(m, part)
        for side in (-1, 1):
            for k in range(6):
                m.sphere(0.085, WHITE, 2, 6, at=translate(side * 0.4, HEAD[1] - 0.1 - 0.13 * k, 0.12), part=part)
    elif style == "coque":
        cap(m, part)
        m.sphere(0.2, WHITE, 3, 8, at=translate(0, HEAD[1] + 0.46, 0.14), part=part)
    elif style == "franja":  # calota com franja reta sobre a testa
        cap(m, part, 1.04)
        m.box((0.6, 0.16, 0.16), WHITE, at=translate(0, HEAD[1] + 0.26, -HEAD_R + 0.02), part=part)
    elif style == "chiquinhas":  # maria-chiquinha: duas mechas altas com laço
        cap(m, part, 1.04)
        for side in (-1, 1):
            m.sphere(0.13, WHITE, 3, 8, at=translate(side * 0.46, HEAD[1] + 0.3, 0.1), part=part)
            m.beam((side * 0.46, HEAD[1] + 0.3, 0.1), (side * 0.58, HEAD[1] - 0.1, 0.2), 0.16, WHITE, part=part)
            m.sphere(0.06, hexcolor("e2483d"), 2, 6, at=translate(side * 0.4, HEAD[1] + 0.34, 0.06), part="base")
    elif style == "moicano":  # crista no alto, laterais raspadas
        for k in range(7):
            z = -0.28 + k * 0.1
            m.sphere(0.11, WHITE, 2, 6, at=translate(0, HEAD[1] + HEAD_R + 0.02 - abs(k - 3) * 0.015, z), part=part)
    elif style == "puffs":  # afro puffs: dois coques crespos altos
        cap(m, part, 1.02)
        for side in (-1, 1):
            m.sphere(0.22, WHITE, 4, 9, at=translate(side * 0.4, HEAD[1] + 0.36, 0.1), part=part, jitter=0.06, seed=7)
    return m


def hijab() -> Mesh:
    """Lenço que cobre o cabelo e envolve o pescoço, deixando o rosto livre (tingível:
    a "cor do cabelo" vira a cor do lenço)."""
    m = Mesh()
    cap(m, "hijab", grow=1.14, drop=-0.02, squash_y=0.98)
    m.sphere(HEAD_R * 1.1, WHITE, 5, 12, at=translate(0, HEAD[1] - 0.16, 0.14), squash=(1.0, 0.9, 0.9), part="hijab")
    m.cylinder(0.3, 0.3, WHITE, 12, at=translate(0, 0.38, 0.04), part="hijab")
    m.box((0.5, 0.3, 0.22), WHITE, at=translate(0, 0.42, 0.18), part="hijab")
    return m


# ------------------------------------------------------------------- itens
def glasses(style: str) -> Mesh:
    m = Mesh()
    part = f"glasses_{style}"
    frame = INK if style != "redondo" else hexcolor("8a4a2a")
    lens = hexcolor("2a2f3a") if style == "sol" else hexcolor("cfefff")
    z = -HEAD_R - 0.02
    for side in (-1, 1):
        at = chain(translate(side * 0.15, HEAD[1] + 0.03, z), rotate_x(90))
        if style == "quadrado":
            m.box((0.2, 0.04, 0.15), frame, at=chain(at, translate(0, -0.02, 0)), part=part)
            m.box((0.16, 0.05, 0.11), lens, at=chain(at, translate(0, -0.03, 0)), part=part, emit=0.2)
        else:
            m.cylinder(0.1, 0.04, frame, 12, at=chain(at, translate(0, -0.02, 0)), part=part)
            m.cylinder(0.08, 0.05, lens, 12, at=chain(at, translate(0, -0.03, 0)), part=part, emit=0.2)
        m.beam((side * 0.24, HEAD[1] + 0.04, z + 0.02), (side * 0.42, HEAD[1] + 0.04, 0.05), 0.025, frame, part=part)
    m.beam((-0.05, HEAD[1] + 0.04, z - 0.01), (0.05, HEAD[1] + 0.04, z - 0.01), 0.025, frame, part=part)
    return m


def accessory(style: str) -> Mesh:
    m = Mesh()
    part = f"acc_{style}"
    top = HEAD[1] + HEAD_R
    if style == "bone":
        m.sphere(
            HEAD_R * 1.08,
            hexcolor("e2483d"),
            4,
            12,
            at=translate(0, HEAD[1] + 0.12, 0.03),
            squash=(1, 0.7, 1),
            part=part,
        )
        m.box((0.5, 0.04, 0.34), hexcolor("c23a30"), at=translate(0, HEAD[1] + 0.14, -0.42), part=part)
        m.sphere(0.05, hexcolor("c23a30"), 2, 6, at=translate(0, top + 0.08, 0.03), part=part)
    elif style == "lenco":
        m.sphere(
            HEAD_R * 1.07,
            hexcolor("f07c2a"),
            4,
            12,
            at=translate(0, HEAD[1] + 0.1, 0.04),
            squash=(1, 0.72, 1),
            part=part,
        )
        m.sphere(0.1, hexcolor("d9662a"), 2, 6, at=translate(0.0, HEAD[1] + 0.02, 0.46), part=part)
        m.slab(
            [(-0.07, 0), (0.07, 0), (0.0, -0.24)], 0.03, hexcolor("d9662a"), at=translate(0.0, HEAD[1], 0.48), part=part
        )
    elif style == "abafador":
        color, pad = hexcolor("2f7fd6"), INK
        for side in (-1, 1):
            at = chain(translate(side * (HEAD_R + 0.02), HEAD[1] - 0.02, 0.02), rotate_z(side * 90))
            m.cylinder(0.15, 0.13, color, 12, at=at, part=part)
            m.cylinder(
                0.11,
                0.04,
                pad,
                12,
                at=chain(translate(side * (HEAD_R - 0.01), HEAD[1] - 0.02, 0.02), rotate_z(side * 90)),
                part=part,
            )
        for k in range(8):
            a0, a1 = np.pi * k / 8, np.pi * (k + 1) / 8
            r = HEAD_R + 0.09
            m.beam(
                (-r * np.cos(a0), HEAD[1] - 0.02 + r * np.sin(a0), 0.02),
                (-r * np.cos(a1), HEAD[1] - 0.02 + r * np.sin(a1), 0.02),
                0.07,
                color,
                part=part,
            )
    elif style == "capacete":
        leather = hexcolor("7a4a2a")
        m.sphere(HEAD_R * 1.1, leather, 5, 12, at=translate(0, HEAD[1] + 0.05, 0.03), squash=(1, 0.85, 1), part=part)
        for side in (-1, 1):
            m.box((0.14, 0.36, 0.18), leather, at=translate(side * 0.4, HEAD[1] - 0.26, 0.02), part=part)
            at = chain(translate(side * 0.15, HEAD[1] + 0.26, -0.38), rotate_x(70))
            m.cylinder(0.1, 0.05, hexcolor("b8893a"), 12, at=at, part=part)
            m.cylinder(
                0.075,
                0.06,
                hexcolor("9fdcf0"),
                12,
                at=chain(translate(side * 0.15, HEAD[1] + 0.26, -0.39), rotate_x(70)),
                part=part,
                emit=0.3,
            )
    elif style == "flor":  # flor grande de lado, acima da orelha
        center = (0.34, HEAD[1] + 0.3, -0.1)
        m.sphere(0.07, hexcolor("f6c33b"), 2, 6, at=translate(*center), part=part)
        for k in range(6):
            a = np.radians(k * 60)
            at = translate(center[0] + 0.1 * np.cos(a), center[1] + 0.1 * np.sin(a), center[2])
            m.sphere(0.065, hexcolor("f06292"), 2, 6, at=at, squash=(1.0, 1.0, 0.55), part=part)
    elif style == "tiara":  # arco fino sobre a cabeça com um laço
        for k in range(10):
            a0, a1 = np.pi * k / 10, np.pi * (k + 1) / 10
            r = HEAD_R + 0.03
            m.beam(
                (-r * np.cos(a0), HEAD[1] + 0.04 + r * np.sin(a0), 0.0),
                (-r * np.cos(a1), HEAD[1] + 0.04 + r * np.sin(a1), 0.0),
                0.05,
                hexcolor("2f7fd6"),
                part=part,
            )
        for side in (-1, 1):
            m.sphere(
                0.07,
                hexcolor("f06292"),
                2,
                6,
                at=translate(0.3 + side * 0.06, top + 0.02, 0.0),
                squash=(1.0, 0.8, 0.6),
                part=part,
            )
        m.sphere(0.04, hexcolor("c2185b"), 2, 6, at=translate(0.3, top + 0.02, -0.02), part=part)
    elif style == "coroa":  # coroa de papel dourado com cinco pontas
        gold = hexcolor("f6c33b")
        m.cylinder(HEAD_R * 0.78, 0.1, gold, 10, at=translate(0, top - 0.1, 0.04), part=part)
        for k in range(5):
            a = np.radians(90 + k * 72)
            x, z = HEAD_R * 0.76 * np.cos(a), HEAD_R * 0.76 * np.sin(a) + 0.04
            m.cone(0.08, 0.16, gold, 6, at=translate(x, top - 0.02, z), part=part)
            m.sphere(0.035, hexcolor("e2483d"), 2, 6, at=translate(x, top - 0.02, z), part=part, emit=0.3)
    return m


def hearing_aid() -> Mesh:
    """Aparelho auditivo atrás da orelha (colorido, para ficar visível como acessório comum)."""
    m = Mesh()
    color = hexcolor("1fb0a8")
    for side in (-1, 1):
        m.box((0.06, 0.18, 0.11), color, at=translate(side * (HEAD_R + 0.05), HEAD[1] - 0.08, 0.1), part="hearing")
        m.sphere(0.045, color, 2, 6, at=translate(side * (HEAD_R + 0.06), HEAD[1] + 0.0, 0.0), part="hearing")
    return m


def wheelchair() -> Mesh:
    """Cadeira de rodas com rodas grandes, encosto e empunhaduras."""
    m = Mesh()
    frame, seat, tyre = hexcolor("b8c2cc"), hexcolor("2f6fc0"), hexcolor("2a2a2a")
    m.box((0.7, 0.08, 0.6), seat, at=translate(0, -0.12, -0.08), part="chair")
    m.box((0.66, 0.66, 0.06), seat, at=translate(0, 0.08, 0.28), part="chair")
    for side in (-1, 1):
        wheel = chain(translate(side * 0.44, 0.02, 0.05), rotate_z(90))
        m.cylinder(0.44, 0.06, tyre, 16, at=chain(wheel, translate(0, -0.03, 0)), part="chair")
        m.cylinder(0.36, 0.07, frame, 16, at=chain(wheel, translate(0, -0.035, 0)), part="chair")
        m.cylinder(0.09, 0.09, seat, 8, at=chain(wheel, translate(0, -0.045, 0)), part="chair")
        m.beam((side * 0.34, 0.66, 0.3), (side * 0.34, 0.72, 0.46), 0.05, frame, part="chair")  # empunhadura
        m.beam((side * 0.32, -0.12, -0.36), (side * 0.32, -0.46, -0.42), 0.04, frame, part="chair")
        m.cylinder(0.08, 0.04, tyre, 8, at=chain(translate(side * 0.32, -0.46, -0.44), rotate_z(90)), part="chair")
    return m


OPTIONS: Dict[str, Mesh] = {}


def options() -> Dict[str, Mesh]:
    if not OPTIONS:
        for style in HAIR_STYLES:
            OPTIONS[f"hair_{style}"] = hair(style)
        OPTIONS["hijab"] = hijab()
        for style in ("redondo", "quadrado", "sol"):
            OPTIONS[f"glasses_{style}"] = glasses(style)
        for style in ("bone", "lenco", "abafador", "capacete", "flor", "tiara", "coroa"):
            OPTIONS[f"acc_{style}"] = accessory(style)
        OPTIONS["hearing"] = hearing_aid()
        OPTIONS["chair"] = wheelchair()
    return OPTIONS


# ------------------------------------------------------------------- build
def build_pilot(assets: Path) -> None:
    folder = assets / "pilot_layers"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.png"):
        old.unlink()
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
            rendered = render_layers(scene, cam["yaw"], cam["pitch"], frame, white_parts=TINTED)
            image = rendered.get(name)
            if image is not None:
                image.save(folder / f"{view}__{name}.png", optimize=True)
            if name == "hijab" and "skin" in rendered:  # o lenço muda o recorte da pele
                rendered["skin"].save(folder / f"{view}__skin_hijab.png", optimize=True)
        print(view, "camadas:", len(list(folder.glob(f"{view}__*.png"))), "corpo:", layout[view])
    anchors = measure_all(assets)
    anchors["body"] = layout
    (folder / "anchors.json").write_text(json.dumps(anchors, indent=1), encoding="utf-8")
    print("anchors.json gravado")


__all__ = ["build_pilot", "P"]
