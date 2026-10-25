"""Renderização determinística dos itens nativos de papel e obstáculos."""

from __future__ import annotations

import pygame

from dobramundo.content.items import ObstacleSpec
from dobramundo.engine.paper_items import PaperItems
from dobramundo.game.entities import Entity


def _waste(z: float = 360.0, y: float = 100.0) -> Entity:
    return Entity(z=z, lane=0, kind="waste", y=y, sprite="papel")


def _obstacle(kind: str, *, width: float = 100.0, y_min: float = 0.0, y_max: float = 70.0,
              solar: bool = False) -> Entity:
    spec = ObstacleSpec(kind, "unused", 90.0, width, y_min, y_max)
    return Entity(z=360.0, lane=0, kind=kind, spec=spec, solar=solar)


def test_tokens_nativos_distintos_estaticos_e_sem_assets():
    items = PaperItems()
    kinds = ["papel", "plastico", "metal", "vidro", "shield", "magnet", "repair"]
    canonical = [items.canonical[("waste", key)] if key in ("papel", "plastico", "metal", "vidro")
                 else items.canonical[("powerup", key)] for key in kinds]
    assert len({pygame.image.tobytes(surface, "RGBA") for surface in canonical}) == len(kinds)

    screen = pygame.Surface((1100, 650), pygame.SRCALPHA)
    entity = _waste()
    items.draw(screen, entity, cam=0.0)
    first = pygame.image.tobytes(screen, "RGBA")
    screen.fill((0, 0, 0, 0))
    items.draw(screen, entity, cam=0.0)
    assert pygame.image.tobytes(screen, "RGBA") == first
    assert entity.kind == "waste" and entity.spec is None


def test_powerup_e_residuo_respeitam_raio_mundo_e_alto_contraste():
    items = PaperItems()
    screen = pygame.Surface((1100, 650), pygame.SRCALPHA)
    items.draw(screen, _waste(), cam=0.0)
    regular = pygame.image.tobytes(screen, "RGBA")
    screen.fill((0, 0, 0, 0))
    items.draw(screen, Entity(z=360, lane=0, kind="shield", y=100), cam=0.0)
    powerup = pygame.image.tobytes(screen, "RGBA")
    assert powerup != regular  # raio do escudo é 28; resíduo é 30

    screen.fill((0, 0, 0, 0))
    items.draw(screen, _waste(), cam=0.0, high_contrast=True)
    assert pygame.image.tobytes(screen, "RGBA") != regular


def test_low_respeita_largura_e_topo_da_hitbox():
    items = PaperItems()
    screen = pygame.Surface((1100, 650), pygame.SRCALPHA)
    items.draw(screen, _obstacle("low", width=100, y_max=70), cam=0.0)
    box = screen.get_bounding_rect(min_alpha=1)
    assert box == pygame.Rect(500, 300, 100, 70)


def test_gate_deixa_vazio_o_vano_e_tower_cobre_a_altura_util():
    items = PaperItems()
    gate_screen = pygame.Surface((1100, 650), pygame.SRCALPHA)
    items.draw(gate_screen, _obstacle("gate", width=100, y_min=60, y_max=400), cam=0.0)
    assert gate_screen.get_at((510, 280)).a > 0  # parte bloqueada, acima do vão
    assert gate_screen.get_at((510, 330)).a == 0  # vão livre abaixo da clearance

    tower_screen = pygame.Surface((1100, 650), pygame.SRCALPHA)
    items.draw(tower_screen, _obstacle("tower", width=100), cam=0.0)
    assert tower_screen.get_at((550, 280)).a > 0
    assert tower_screen.get_at((550, 330)).a > 0


def test_era_solar_usa_palette_diferente_e_cache_de_escala_tem_limite():
    items = PaperItems(cache_limit=5)
    industrial = pygame.Surface((1100, 650), pygame.SRCALPHA)
    solar = pygame.Surface((1100, 650), pygame.SRCALPHA)
    items.draw(industrial, _obstacle("low", solar=False), cam=0.0)
    items.draw(solar, _obstacle("low", solar=True), cam=0.0)
    assert pygame.image.tobytes(industrial, "RGBA") != pygame.image.tobytes(solar, "RGBA")

    for z in range(300, 900, 7):
        items.draw(solar, Entity(z=float(z), lane=0, kind="waste", y=32, sprite="metal"), cam=0.0)
    assert len(items._scaled) <= items._scaled.limit
