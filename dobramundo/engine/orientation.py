"""Orientação da imagem projetada: espelhar e girar 0°, 90°, 180° ou 270°.

O jogo desenha sempre na tela lógica de 1100x650. Para projetar no chão, na mesa
ou por trás de uma parede, a imagem é espelhada (primeiro) e girada no sentido
horário (depois). Girada 90° ou 270°, a imagem fica em pé e é reduzida para
caber na janela, com faixas pretas dos lados.

As funções de coordenadas usam valores normalizados (0..1, x para a direita e y
para baixo): ``game_to_screen`` leva um ponto do jogo para a janela e
``screen_to_game`` desfaz o caminho (para o mouse e para a calibração do chão).
"""

from __future__ import annotations

from typing import Dict, Tuple

import pygame

from .. import config as C

ROTATIONS = (0, 90, 180, 270)
Point = Tuple[float, float]
_cache: Dict[tuple, pygame.Surface] = {}


def check_rotation(rotation: int) -> int:
    return rotation if rotation in ROTATIONS else 0


def standing(rotation: int) -> bool:
    """Girada 90° ou 270°: a imagem fica em pé dentro da janela deitada."""
    return check_rotation(rotation) in (90, 270)


def letterbox() -> Tuple[float, float]:
    """(largura, deslocamento x) normalizados da imagem em pé dentro da janela."""
    width = (C.HEIGHT / C.WIDTH) * (C.HEIGHT / C.WIDTH)
    return width, (1.0 - width) / 2


def rotate_point(x: float, y: float, rotation: int, mirrored: bool) -> Point:
    """Ponto da imagem do jogo -> ponto da imagem projetada (sem faixas pretas)."""
    if mirrored:
        x = 1.0 - x
    rotation = check_rotation(rotation)
    if rotation == 90:
        return 1.0 - y, x
    if rotation == 180:
        return 1.0 - x, 1.0 - y
    if rotation == 270:
        return y, 1.0 - x
    return x, y


def unrotate_point(x: float, y: float, rotation: int, mirrored: bool) -> Point:
    """Inverso de ``rotate_point``."""
    rotation = check_rotation(rotation)
    if rotation == 90:
        x, y = y, 1.0 - x
    elif rotation == 180:
        x, y = 1.0 - x, 1.0 - y
    elif rotation == 270:
        x, y = 1.0 - y, x
    if mirrored:
        x = 1.0 - x
    return x, y


def game_to_screen(x: float, y: float, rotation: int = 0, mirrored: bool = False) -> Point:
    """Ponto do jogo -> ponto da janela, contando as faixas pretas da imagem em pé."""
    u, v = rotate_point(x, y, rotation, mirrored)
    if standing(rotation):
        width, left = letterbox()
        u = left + u * width
    return u, v


def screen_to_game(x: float, y: float, rotation: int = 0, mirrored: bool = False) -> Point:
    """Ponto da janela -> ponto do jogo (pode sair de 0..1 nas faixas pretas)."""
    if standing(rotation):
        width, left = letterbox()
        x = (x - left) / width
    return unrotate_point(x, y, rotation, mirrored)


def orient(canvas: pygame.Surface, rotation: int = 0, mirrored: bool = False) -> pygame.Surface:
    """A tela lógica pronta para a janela (espelhada, girada e reduzida se em pé)."""
    rotation = check_rotation(rotation)
    if not mirrored and rotation == 0:
        return canvas
    image = pygame.transform.flip(canvas, True, False) if mirrored else canvas
    if rotation:
        image = pygame.transform.rotate(image, -rotation)  # rotate() gira no sentido anti-horário
    if not standing(rotation):
        return image
    size = canvas.get_size()
    frame = _cache.get(size)
    if frame is None:
        frame = _cache[size] = pygame.Surface(size)
    frame.fill((0, 0, 0))
    width = round(size[0] * letterbox()[0])
    fitted = pygame.transform.scale(image, (width, size[1]))
    frame.blit(fitted, ((size[0] - width) // 2, 0))
    return frame
