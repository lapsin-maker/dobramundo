"""Sprint 3 art integration: expressions, story plates, and village requests."""

from __future__ import annotations

import pygame

from dobramundo.content.pilot import DEFAULT_PILOT
from dobramundo.content.progress import VILLAGE_UPGRADES
from dobramundo.engine.village_art import village_resident
from dobramundo.persistence import Profile
from dobramundo.scenes.intro import PAGES, IntroScene
from dobramundo.scenes.upgrades import PLANE_CARD_TOPS, PLANE_STATS_Y, UpgradesScene
from dobramundo.scenes.village import SQUARE, VILLAGE_NEIGHBOR_POSITIONS, VillageScene, ensure_village_requests
from dobramundo.ui import theme as T


def _pixels(surface: pygame.Surface) -> bytes:
    return pygame.image.tostring(surface, "RGBA")


def test_pilot_expressions_are_distinct_cached_and_hidden_from_back(app):
    look = {
        **DEFAULT_PILOT,
        "pele": "pele3",
        "cabelo": "cacheado",
        "cor_cabelo": "castanho",
        "roupa": "azul",
    }
    renderer = app.view.skin.pilots
    moods = ("curious", "focused", "happy", "recover")
    surfaces = [renderer.compose("menu", look, expression=mood) for mood in moods]
    assert all(surface is not None for surface in surfaces)
    assert len({_pixels(surface) for surface in surfaces}) == len(moods)
    assert renderer.compose("menu", look, expression="happy") is surfaces[2]
    base = renderer.compose("flight", look)
    back_mood = renderer.compose("flight", look, expression="happy")
    assert base is not None and back_mood is not None
    assert base.get_size() == back_mood.get_size()
    assert pygame.mask.from_surface(base, 16).to_surface().get_bounding_rect() == (
        pygame.mask.from_surface(back_mood, 16).to_surface().get_bounding_rect()
    )


def test_village_requests_follow_build_state_and_survive_profile_roundtrip():
    profile = Profile()
    profile.vila = ["ponto_troca", "horta"]
    profile.pedidos_vila = {"ponto_troca": "solicitada", "obsolete": "x"}
    assert ensure_village_requests(profile)
    assert profile.pedidos_vila["ponto_troca"] == "concluida"
    assert profile.pedidos_vila["horta"] == "concluida"
    assert profile.pedidos_vila["paineis"] == "solicitada"
    assert set(profile.pedidos_vila) == {upgrade.key for upgrade in VILLAGE_UPGRADES}
    assert not ensure_village_requests(profile)
    restored = Profile.from_dict(profile.to_dict())
    assert restored.pedidos_vila == profile.pedidos_vila


def test_villager_atlas_cells_are_cropped_transparent_and_pose_specific(app):
    atlas = app.assets.sprite("watercolor", "villagers_sprint3")
    assert atlas is not None and atlas.get_size() == (1536, 1024)
    calm = village_resident(atlas, 0, "calmo")
    request = village_resident(atlas, 0, "pedido")
    happy = village_resident(atlas, 0, "feliz")
    wheelchair = village_resident(atlas, 1, "calmo")
    assert all(surface is not None for surface in (calm, request, happy, wheelchair))
    assert calm.get_at((0, 0)).a == 0
    assert len({_pixels(surface) for surface in (calm, request, happy)}) == 3


def test_story_uses_four_separate_backgrounds_and_draws_reduced_motion(app):
    scene = IntroScene(app)
    app.go(scene)
    for start in (0.0, PAGES[0], sum(PAGES[:2]), sum(PAGES[:3])):
        scene.time = start + 0.2
        scene.draw(app.canvas)
    assert set(scene.story_backgrounds) == {"story_city", "story_newspaper", "story_fold", "story_launch"}
    assert all(surface is not None for surface in scene.story_backgrounds.values())
    app.options.reduzir_movimento = True
    scene.time = sum(PAGES[:2]) + 0.2
    scene.draw(app.canvas)
    scene.time = sum(PAGES[:3]) + 0.2
    scene.draw(app.canvas)


def test_village_draw_persists_eight_requests_and_residents(app):
    scene = VillageScene(app)
    app.go(scene)
    app.step(1 / 60, [])
    assert set(app.profile.pedidos_vila) == {upgrade.key for upgrade in VILLAGE_UPGRADES}
    assert sum(state == "solicitada" for state in app.profile.pedidos_vila.values()) == 8


def test_village_requests_stay_clear_of_the_centered_paper_plane():
    plane = pygame.Rect(0, 0, 225, 150)
    plane.center = (SQUARE[0], 340)
    for x, feet_y in VILLAGE_NEIGHBOR_POSITIONS:
        person = pygame.Rect(0, 0, 68, 90)
        person.midbottom = (x, feet_y)
        bubble = pygame.Rect(x - 24, feet_y - 132, 48, 42)
        assert not person.colliderect(plane)
        assert not bubble.colliderect(plane)


def test_plane_upgrade_stats_do_not_cover_third_card_or_toast(app):
    last_card_bottom = PLANE_CARD_TOPS[-1] + 110
    toast_top = 630 - 54 // 2
    assert last_card_bottom <= PLANE_STATS_Y
    assert PLANE_STATS_Y + T.SIZES["body"] <= toast_top
    scene = UpgradesScene(app, "aviao")
    scene.build()
    third_card = next(button.rect for button in scene.menu.buttons if button.key == "quilha")
    assert third_card.bottom <= PLANE_STATS_Y
