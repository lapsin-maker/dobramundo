"""Integração dos atlas de aviões em aquarela com a API PlaneSkin."""

from __future__ import annotations

import pygame

from dobramundo.content.planes import PLANE_COLOR_KEYS, PLANE_KEYS, PLANE_PATTERN_KEYS


def test_atlas_flight_expoe_os_11_modelos_e_recorta_alpha(app):
    skin = app.view.skin
    models = skin.models()
    assert models == PLANE_KEYS
    for key in PLANE_KEYS:
        surface = skin.base(key, "flight")
        assert isinstance(surface, pygame.Surface)
        assert surface.get_width() <= 640
        assert surface.get_bounding_rect(min_alpha=20).size == surface.get_size()


def test_menu_resolve_atlas_ou_fallback_sem_perder_modelos(app):
    skin = app.view.skin
    for key in PLANE_KEYS:
        menu = skin.base(key, "menu")
        assert menu is not None and menu.get_bounding_rect(min_alpha=20).size == menu.get_size()


def test_pintura_muda_papel_e_preserva_dobras_e_contorno(app):
    skin = app.view.skin
    base = skin.base("dart", "flight")
    painted = skin.painted("dart", "flight", "azul", "liso")
    assert base is not None and painted is not None
    mask = skin.painted_planes._paper_mask(base)
    changed_paper = False
    preserved_ink = False
    for y in range(base.get_height()):
        for x in range(base.get_width()):
            before, after = base.get_at((x, y)), painted.get_at((x, y))
            if mask.get_at((x, y)).a:
                changed_paper |= before[:3] != after[:3]
            elif before.a >= 20:
                preserved_ink |= before == after
    assert changed_paper and preserved_ink


def test_cor_e_estampa_sao_combinadas_sem_pintar_dobras(app):
    skin = app.view.skin
    base = skin.base("dart", "flight")
    blue = skin.painted("dart", "flight", "azul", "bolinhas")
    red = skin.painted("dart", "flight", "vermelho", "bolinhas")
    assert base is not None and blue is not None and red is not None
    mask = skin.painted_planes._paper_mask(base)
    changed_inside = False
    for y in range(base.get_height()):
        for x in range(base.get_width()):
            paper_pixel = bool(mask.get_at((x, y)).a)
            if not paper_pixel and base.get_at((x, y)).a >= 20:
                assert blue.get_at((x, y)) == red.get_at((x, y)) == base.get_at((x, y))
            changed_inside |= paper_pixel and blue.get_at((x, y)) != red.get_at((x, y))
    assert changed_inside


def test_cores_padroes_e_modelos_legados_continuam_catalogados(app):
    assert len(PLANE_KEYS) == 11
    assert len(PLANE_COLOR_KEYS) == 15
    assert len(PLANE_PATTERN_KEYS) == 26
    skin = app.view.skin
    for color in PLANE_COLOR_KEYS:
        surface = skin.painted("glider", "flight", color, "liso")
        assert surface is not None
    for pattern in PLANE_PATTERN_KEYS:
        surface = skin.painted("dart", "flight", "original", pattern)
        assert surface is not None


def test_piloto_montado_e_cacheado_nas_duas_vistas(app):
    skin = app.view.skin
    look = dict(app.profile.piloto, pele="pele4", cabelo="crespo", olhos="castanhos")
    assert look.get("cadeira") != "sim"
    for plane in PLANE_KEYS:
        for view in ("flight", "menu"):
            surface = skin.surface(plane, view, "original", "liso", look)
            assert surface is not None
            assert surface.get_size() == skin.base(plane, view).get_size()
            assert skin.surface(plane, view, "original", "liso", look) is surface
    for view, pose in (("flight", "back_seated"), ("menu", "front_seated")):
        seated = skin.pilots.compose(view, look, pose=pose)
        standing = skin.pilots.compose(view, look)
        assert seated is not None and standing is not None
        assert pygame.image.tobytes(seated, "RGBA") != pygame.image.tobytes(standing, "RGBA")
        assert look.get("cadeira") != "sim"  # pose de cockpit não altera mobilidade salva


def test_piloto_em_voo_fica_no_cockpit_sem_pernas_penduradas(app):
    skin = app.view.skin
    look = dict(app.profile.piloto, pele="pele4", cabelo="crespo")
    plane = skin.base("dart", "flight")
    mounted = skin.surface("dart", "flight", "original", "liso", look)
    assert plane is not None and mounted is not None
    changed = [
        (x, y)
        for y in range(plane.get_height())
        for x in range(plane.get_width())
        if plane.get_at((x, y)) != mounted.get_at((x, y))
    ]
    assert changed
    # A pose sentada maior continua dentro do cockpit, sem pernas fora da fuselagem.
    assert max(y for _x, y in changed) < plane.get_height() * 0.55
    assert max(y for _x, y in changed) - min(y for _x, y in changed) > plane.get_height() * 0.20
