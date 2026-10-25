"""Assets: tudo o que o conteúdo referencia existe (sprites, sons, camadas do piloto)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dobramundo.content.biomes import BIOMES, biome_sprite_names
from dobramundo.content.items import POWERUP_KINDS, WASTE_TYPES
from dobramundo.content.pilot import ACCESSORIES, GLASSES, HAIR_STYLES
from dobramundo.content.planes import PLANE_KEYS, PLANE_PATTERN_KEYS
from dobramundo.content.progress import VILLAGE_UPGRADES
from dobramundo.engine.assets import SCENERY_FOLDERS

ASSETS = Path(__file__).resolve().parent.parent / "assets"


def scenery_exists(name: str) -> bool:
    return any((ASSETS / folder / f"{name}.png").is_file() for folder in SCENERY_FOLDERS)


@pytest.mark.parametrize("biome", sorted(BIOMES))
def test_sprites_das_fases(biome):
    missing = [n for n in biome_sprite_names(BIOMES[biome]) if not scenery_exists(n)]
    assert missing == []


def test_sprites_da_vila_residuos_e_power_ups():
    assert all(scenery_exists(u.sprite) for u in VILLAGE_UPGRADES)
    assert all((ASSETS / "waste_sprites" / f"{w.sprite}.png").is_file() for w in WASTE_TYPES)
    assert all((ASSETS / "powerup_sprites" / f"{k}.png").is_file() for k in ("shield", "magnet", "repair"))
    assert len(POWERUP_KINDS) == 3


def test_avioes_tem_todas_as_camadas():
    for folder in ("plane_sprites", "plane_menu", "plane_paint", "plane_menu_paint", "plane_uv", "plane_menu_uv"):
        assert all((ASSETS / folder / f"{p}__none.png").is_file() for p in PLANE_KEYS), folder
    assert all((ASSETS / "plane_patterns" / f"{k}.png").is_file() for k in PLANE_PATTERN_KEYS if k != "liso")


def test_camadas_do_piloto():
    layers = ASSETS / "pilot_layers"
    names = ["skin", "shirt", "base", "hearing", "chair"]
    names += [f"hair_{o.key}" for o in HAIR_STYLES if o.key != "raspado"]
    names += [f"glasses_{o.key}" for o in GLASSES if o.key != "nenhum"]
    names += [f"acc_{o.key}" for o in ACCESSORIES if o.key != "nenhum"]
    for view in ("flight", "menu"):
        missing = [n for n in names if not (layers / f"{view}__{n}.png").is_file()]
        assert missing == [], view
    anchors = json.loads((layers / "anchors.json").read_text(encoding="utf-8"))
    assert set(anchors["flight"]) == set(PLANE_KEYS) and set(anchors["menu"]) == set(PLANE_KEYS)
    assert len(anchors["body"]["flight"]) == 4


def test_trilhas_e_efeitos():
    audio = ASSETS / "audio"
    tracks = ["musica_vila"] + [f"musica_{b.music}_{i}" for b in BIOMES.values() for i in (1, 2, 3)]
    effects = [
        "sfx_coleta_papel",
        "sfx_coleta_plastico",
        "sfx_coleta_metal",
        "sfx_coleta_vidro",
        "sfx_colisao",
        "sfx_powerup",
        "sfx_escudo_fim",
        "sfx_estrela",
        "sfx_estagio",
        "sfx_selecao",
        "sfx_foco",
        "sfx_compra",
        "sfx_fim_fase",
        "sfx_game_over",
        "sfx_decolagem",
    ]
    assert [n for n in tracks + effects if not (audio / f"{n}.ogg").is_file()] == []


def test_identidade_e_texturas():
    assert (ASSETS / "ui" / "logo.png").is_file() and (ASSETS / "ui" / "icone.png").is_file()
    assert (ASSETS / "icon.ico").is_file()
    for biome in BIOMES.values():
        for texture in (biome.green_ground, biome.solar_ground, biome.solar_road):
            assert texture is None or (ASSETS / "ground" / f"{texture}.png").is_file()


def test_obstaculos_de_portal_tem_vao_livre():
    """Portais (passe por baixo) precisam de vão acima da altitude mínima do avião."""
    for biome in BIOMES.values():
        for table in (biome.industrial_obstacles, biome.solar_obstacles):
            for spec in table["gate"]:
                assert spec.y_min >= 100.0, spec.sprite
            for spec in table["tower"]:
                assert spec.width <= 160.0, spec.sprite
