"""Contratos pequenos das páginas de opções, mapa e encaixe do piloto."""

from __future__ import annotations

import pygame

from dobramundo import config as C
from dobramundo.engine.painted_planes import PaintedPlanes
from dobramundo.scenes.map import brazil_map
from dobramundo.scenes.options import OPTION_PAGES, OptionsScene


def test_opcoes_em_paginas_grandes_sem_perder_acoes_ou_sair_da_tela(app):
    scene = OptionsScene(app)
    scene.build()
    all_keys = set()
    for section, _label, _icon in OPTION_PAGES:
        scene.select_section(section)
        buttons = scene.menu.buttons
        assert all(button.icon is not None for button in buttons if button.key.startswith("section:"))
        assert all(button.rect.left >= 0 and button.rect.top >= 0 for button in buttons)
        assert all(button.rect.right <= C.WIDTH and button.rect.bottom <= C.HEIGHT for button in buttons)
        for index, button in enumerate(buttons):
            assert all(not button.rect.colliderect(other.rect) for other in buttons[index + 1 :])
        visible = {button.key for button in buttons}
        assert f"section:{section}" in visible
        all_keys.update(visible)
    assert {"seg=", "sens=", "perm=", "sup=", "volume_geral=", "contraste", "movimento", "auto_abertura"} <= all_keys
    assert {"voltar", "abertura", "treino", "dwell_treino", "preparar"} <= all_keys


def test_mapa_geografico_texturizado_e_cacheado():
    texture = pygame.Surface((48, 48))
    texture.fill((205, 148, 82))
    pygame.draw.ellipse(texture, (64, 128, 174), (4, 6, 35, 32))
    first = brazil_map(texture)
    second = brazil_map(texture)
    assert first is second
    assert first.get_size() == (C.WIDTH, C.HEIGHT)
    assert first.get_at((0, 0)).a == 0
    assert len(set(pygame.image.tobytes(first, "RGBA")[::4])) > 1


class _PilotStub:
    def __init__(self):
        self.calls = []

    def compose(self, view, look, pose=None):
        self.calls.append((view, pose))
        surface = pygame.Surface((60, 120), pygame.SRCALPHA)
        surface.fill((220, 140, 80, 255))
        return surface


def test_piloto_montado_no_voo_aparece_maior_e_de_costas():
    plane = pygame.Surface((140, 220), pygame.SRCALPHA)
    renderer = _PilotStub()
    bis = PaintedPlanes.mount_pilot(plane, renderer, "bis14", "flight", {})
    crane = PaintedPlanes.mount_pilot(plane, renderer, "crane", "flight", {})
    assert renderer.calls == [("flight", "back_seated"), ("flight", "back_seated")]
    bis_bounds = bis.get_bounding_rect(min_alpha=1)
    crane_bounds = crane.get_bounding_rect(min_alpha=1)
    assert bis_bounds.height == round(220 * 0.32)
    assert bis_bounds.width > 25 and bis_bounds.top == round(220 * 0.12)
    assert crane_bounds.height == round(220 * 0.36)
    assert crane_bounds.width > 25 and crane_bounds.top == round(220 * 0.24)
