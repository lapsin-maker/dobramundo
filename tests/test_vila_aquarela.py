"""Fluxos críticos das escolhas de vila, compra confirmada e cartões de destino."""

from __future__ import annotations

from dobramundo.content.progress import VILLAGE_BY_KEY
from dobramundo.scenes.map import BIOME_ORDER, MapScene
from dobramundo.scenes.upgrades import UpgradesScene
from dobramundo.scenes.village import VillageScene


def _dwell(scene, key: str) -> None:
    button = next(button for button in scene.menu.buttons if button.key == key)
    point = button.rect.center
    # Primeiro quadro mira o alvo; o seguinte completa a permanência.
    scene.menu.update(0.1, point, 0.1)
    scene.menu.update(0.1, point, 0.1)


def _assert_no_dwell_overlap(scene, keys: list[str]) -> None:
    buttons = [next(button for button in scene.menu.buttons if button.key == key) for key in keys]
    for i, first in enumerate(buttons):
        for second in buttons[i + 1:]:
            assert not first.rect.inflate(60, 60).colliderect(second.rect.inflate(60, 60))


def test_vila_oferece_destinos_grandes_e_alvos_separados(app):
    scene = VillageScene(app)
    scene.build()
    _assert_no_dwell_overlap(scene, ["voar", "hangar", "piloto", "cuidar"])
    assert all(next(b for b in scene.menu.buttons if b.key == key).rect.size == (210, 86)
               for key in ("voar", "hangar", "piloto", "cuidar"))


def test_compra_exige_confirmacao_e_nao_desconta_duas_vezes(app):
    scene = UpgradesScene(app)
    scene.build()
    upgrade = VILLAGE_BY_KEY["ponto_troca"]
    app.profile.recursos.update({key: amount + 5 for key, amount in upgrade.cost.items()})
    before = dict(app.profile.recursos)

    _dwell(scene, upgrade.key)
    assert scene.selected_key == upgrade.key
    assert app.profile.recursos == before
    assert upgrade.key not in app.profile.vila
    _assert_no_dwell_overlap(scene, ["confirmar", "cancelar"])

    _dwell(scene, "confirmar")
    assert upgrade.key in app.profile.vila
    assert all(app.profile.recursos[key] == before[key] - amount
               for key, amount in upgrade.cost.items())
    after_purchase = dict(app.profile.recursos)
    # O antigo alvo de confirmação desaparece após a compra e não pode repetir o gasto.
    scene.menu.update(0.1, (380, 593), 0.1)
    scene.menu.update(0.1, (380, 593), 0.1)
    assert app.profile.recursos == after_purchase
    assert app.profile.vila.count(upgrade.key) == 1


def test_mapa_mantem_destinos_geograficos_e_modos_separados(app):
    scene = MapScene(app)
    scene.build()
    _assert_no_dwell_overlap(scene, ["modo_normal", "modo_dificil"])
    assert tuple(key for key in BIOME_ORDER if any(button.key == key for button in scene.menu.buttons)) == BIOME_ORDER
    assert next(button for button in scene.menu.buttons if button.key == "amazonia").rect.size == (440, 100)
    assert next(button for button in scene.menu.buttons if button.key == "caatinga").rect.size == (440, 100)
