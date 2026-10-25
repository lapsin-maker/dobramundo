"""Contratos dos atlas opcionais e da projeção física dos itens do voo."""

from __future__ import annotations

import pygame

import dobramundo.engine.paper_items as paper_items
from dobramundo import config as C
from dobramundo.content.items import ObstacleSpec
from dobramundo.engine.paper_items import PaperItems
from dobramundo.engine.sprites import project
from dobramundo.game.entities import Entity


def _atlas(path, columns: int, rows: int, *, blank_last: bool = False) -> pygame.Surface:
    """Grade propositalmente não divisível por número inteiro de pixels."""
    width, height = columns * 25 + 1, rows * 25 + 1
    atlas = pygame.Surface((width, height), pygame.SRCALPHA)
    colors = ((209, 72, 64), (55, 147, 191), (230, 176, 56), (74, 154, 94),
              (161, 95, 176), (69, 168, 161), (203, 116, 57), (238, 238, 238))
    for index in range(columns * rows):
        if blank_last and index == columns * rows - 1:
            continue
        row, col = divmod(index, columns)
        left, right = col * width // columns, (col + 1) * width // columns
        top, bottom = row * height // rows, (row + 1) * height // rows
        color = colors[index % len(colors)]
        pygame.draw.circle(atlas, color, ((left + right) // 2, (top + bottom) // 2), 7)
    pygame.image.save(atlas, str(path))
    return atlas


def _obstacle_atlas(path) -> pygame.Surface:
    atlas = pygame.Surface((1536, 1024), pygame.SRCALPHA)
    crops = ((56, 297, 512, 472), (548, 174, 1078, 270), (1258, 23, 1412, 480),
             (31, 655, 512, 953), (548, 646, 1145, 742), (1223, 513, 1455, 977))
    for index, (x0, y0, x1, y1) in enumerate(crops):
        color = (30 + index * 20, 100 + index * 10, 180, 255)
        pygame.draw.ellipse(atlas, color, (x0 + 3, y0 + 3, x1 - x0 - 6, y1 - y0 - 6))
    pygame.image.save(atlas, str(path))
    return atlas


def test_atlas_itens_4x2_transparente_com_sobra_de_pixels_e_celula_vazia(tmp_path, monkeypatch):
    path = tmp_path / "items_refined.png"
    _atlas(path, 4, 2, blank_last=True)
    monkeypatch.setattr(paper_items, "find_asset_file", lambda folder, name: path if name == path.name else None)

    items = PaperItems()

    assert items.canonical[("waste", "papel")].get_size() == (96, 96)
    assert items.canonical[("powerup", "repair")].get_at((48, 48)).a > 0
    assert items.canonical[("waste", "papel")].get_bounding_rect(min_alpha=1).size == (92, 92)
    # Benefícios recebem moldura hexagonal, diferente da ficha circular do resíduo.
    assert pygame.image.tobytes(items.canonical[("waste", "papel")], "RGBA") != pygame.image.tobytes(
        items.canonical[("powerup", "shield")], "RGBA"
    )


def test_atlas_obstaculos_recorta_celulas_sem_pixelar_forma(tmp_path, monkeypatch):
    path = tmp_path / "obstacles_refined.png"
    _obstacle_atlas(path)
    monkeypatch.setattr(paper_items, "find_asset_file", lambda folder, name: path if name == path.name else None)
    items = PaperItems()
    screen = pygame.Surface((1100, 650), pygame.SRCALPHA)
    spec = ObstacleSpec("gate", "unused", 90.0, 100.0, 60.0, 400.0)
    items.draw(screen, Entity(z=360, lane=0, kind="gate", spec=spec), cam=0.0)

    assert screen.get_bounding_rect(min_alpha=1).width <= 100
    gate_art = items.canonical[("obstacle", "gate", False)]
    assert gate_art.get_size() == (530, 96)
    assert gate_art.get_bounding_rect(min_alpha=1).size != (0, 0)


def test_atlas_real_trava_folhagem_do_portal_fora_do_vano():
    items = PaperItems()
    industrial = items.canonical[("obstacle", "gate", False)]
    solar = items.canonical[("obstacle", "gate", True)]
    assert industrial.get_height() == 96 and solar.get_height() == 96
    # A fileira inferior de cada recorte é a própria borda da travessa; as cordas
    # e folhas abaixo dela não entram na projeção da clearance do jogo.
    assert pygame.mask.from_surface(industrial.subsurface((0, 95, industrial.get_width(), 1)), 1).count() > 0
    assert pygame.mask.from_surface(solar.subsurface((0, 95, solar.get_width(), 1)), 1).count() > 0
    for era in (False, True):
        screen = pygame.Surface((1100, 650), pygame.SRCALPHA)
        spec = ObstacleSpec("gate", "unused", 175.0, 230.0, 100.0, 400.0)
        items.draw(screen, Entity(z=360, lane=0, kind="gate", spec=spec, solar=era), cam=0.0)
        assert screen.get_at((550, 230)).a > 0
        assert screen.get_at((550, 280)).a == 0


def test_desenho_em_cache_nao_reabre_o_arquivo_ou_depende_de_path_no_quadro(monkeypatch):
    items = PaperItems()
    screen = pygame.Surface((1100, 650), pygame.SRCALPHA)
    entity = Entity(z=360, lane=0, kind="waste", y=100, sprite="plastico")

    def no_frame_io(*args, **kwargs):
        raise AssertionError("o desenho do quadro não deve reabrir arquivos")

    monkeypatch.setattr(pygame.image, "load", no_frame_io)
    items.draw(screen, entity, cam=0.0)
    items.draw(screen, entity, cam=0.0)
    assert screen.get_bounding_rect(min_alpha=1).size != (0, 0)


def test_contorno_de_alto_contraste_usa_mascara_precalculada(monkeypatch):
    items = PaperItems()
    screen = pygame.Surface((1100, 650), pygame.SRCALPHA)
    spec = ObstacleSpec("gate", "unused", 175.0, 230.0, 100.0, 400.0)
    entity = Entity(z=360, lane=0, kind="gate", spec=spec)

    def no_frame_mask(*args, **kwargs):
        raise AssertionError("a máscara deve ser preparada fora do desenho por quadro")

    monkeypatch.setattr(pygame.mask, "from_surface", no_frame_mask)
    items.draw(screen, entity, cam=0.0, high_contrast=True)
    items.draw(screen, entity, cam=0.0, high_contrast=True)
    assert screen.get_bounding_rect(min_alpha=1).size != (0, 0)


def test_silhuetas_de_obstaculo_ficam_dentro_das_faixas_de_colisao():
    items = PaperItems()
    cases = (
        ("low", ObstacleSpec("low", "", 100.0, 165.0, 0.0, 90.0), (0.0, 90.0)),
        ("gate", ObstacleSpec("gate", "", 175.0, 230.0, 100.0, 400.0), (100.0, 200.0)),
        ("tower", ObstacleSpec("tower", "", 330.0, 100.0, 0.0, 400.0), (0.0, 200.0)),
    )
    for kind, spec, (y_low, y_high) in cases:
        screen = pygame.Surface((1100, 650), pygame.SRCALPHA)
        items.draw(screen, Entity(z=360, lane=0, kind=kind, spec=spec), cam=0.0)
        actual = screen.get_bounding_rect(min_alpha=16)
        left, _, _ = project(-spec.width / 2, 0.0, 360.0, 0.0)
        right, _, _ = project(spec.width / 2, 0.0, 360.0, 0.0)
        top = project(0.0, y_high, 360.0, 0.0)[1]
        bottom = project(0.0, y_low, 360.0, 0.0)[1]
        expected = pygame.Rect(round(left), round(top), round(right - left), round(bottom - top)).inflate(2, 2)
        assert actual.left >= expected.left and actual.right <= expected.right
        assert actual.top >= expected.top and actual.bottom <= expected.bottom
        assert actual.width >= expected.width * 0.75
        if kind != "gate":
            assert actual.height >= expected.height * 0.9


def test_limites_fisicos_low_gate_tower_coincidem_com_a_manobra(run):
    low = Entity(
        z=C.PLAYER_Z,
        lane=0,
        kind="low",
        spec=ObstacleSpec("low", "", 100.0, 165.0, 0.0, 90.0),
    )
    run.player.x, run.player.y = 0.0, 120.0
    run.world.entities = [low]
    run.check_collisions()
    assert not low.hit  # acima da borda superior da barreira
    run.player.y = 95.0
    run.check_collisions()
    assert low.hit

    gate = Entity(
        z=C.PLAYER_Z,
        lane=0,
        kind="gate",
        spec=ObstacleSpec("gate", "", 175.0, 230.0, 100.0, 400.0),
    )
    run.lives = C.MAX_LIVES
    run.invulnerable_timer = 0.0
    run.world.entities = [gate]
    run.player.x, run.player.y = 0.0, 65.0
    run.check_collisions()
    assert not gate.hit  # abaixo da travessa, no vão livre
    run.player.y = 95.0
    run.check_collisions()
    assert gate.hit

    tower = Entity(
        z=C.PLAYER_Z,
        lane=0,
        kind="tower",
        spec=ObstacleSpec("tower", "", 330.0, 100.0, 0.0, 400.0),
    )
    run.lives = C.MAX_LIVES
    run.invulnerable_timer = 0.0
    run.world.entities = [tower]
    run.player.x, run.player.y = 120.0, 100.0
    run.check_collisions()
    assert not tower.hit  # fora da silhueta lateral da torre
    run.player.x = 95.0  # intersecta a torre mesmo com a tolerância comum de colisão
    run.check_collisions()
    assert tower.hit


def test_fallbacks_sao_silhuetas_vazadas_e_alvos_de_texto_cabem(monkeypatch):
    monkeypatch.setattr(paper_items, "find_asset_file", lambda folder, name: None)
    items = PaperItems()
    low = items.canonical[("obstacle", "low", False)]
    gate = items.canonical[("obstacle", "gate", False)]
    assert low.get_at((80, 80)).a == 0
    assert gate.get_at((80, 90)).a == 0

    from dobramundo.scenes.flight import FlightScene

    assert FlightScene._fit_banner_text(
        "Instrução extremamente longa para testar o limite sem ultrapassar a faixa superior do voo",
        pygame.font.Font(None, 24),
        210,
    )


def test_banner_longo_fica_na_faixa_e_movimento_reduzido_remove_fade(app):
    from dobramundo.config import HEIGHT, WIDTH
    from dobramundo.scenes.flight import Banner, FlightScene

    scene = FlightScene(app, "amazonia")
    scene.banners = [Banner("Título de missão longo " * 8, "Ajuda complementar muito extensa " * 8, action="up")]
    scene.app.options.reduzir_movimento = True
    screen = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    scene.draw_banners(screen)
    bounds = screen.get_bounding_rect(min_alpha=1)
    assert bounds.left >= 0 and bounds.right <= WIDTH
    assert bounds.top >= 150 and bounds.bottom < 240

    first = pygame.image.tobytes(screen, "RGBA")
    scene.banners[0].ttl = 0.1
    screen.fill((0, 0, 0, 0))
    scene.draw_banners(screen)
    assert pygame.image.tobytes(screen, "RGBA") == first
