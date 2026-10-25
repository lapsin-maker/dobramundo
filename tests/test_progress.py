"""Progressão (estrelas, custos, peças) e perfil salvo (validação, migração do protótipo)."""

from __future__ import annotations

import json

import pytest
from conftest import advance, make_run

from dobramundo import config as C
from dobramundo.content.progress import PLANE_PARTS, VILLAGE_UPGRADES, can_afford, missing, plane_stats, stars_for
from dobramundo.persistence import Profile, load_profile, profile_path, save_profile


@pytest.mark.parametrize("value, stars", [(10, 0), (33.4, 1), (70, 2), (100, 2)])
def test_estrelas_sem_pecas(value, stars):
    assert stars_for(value, {"leme": 1}, {}) == stars


def test_terceira_estrela_com_pecas():
    assert stars_for(100.0, {"leme": 1, "quilha": 1}, {"leme": 2, "quilha": 1}) == 3


def test_custos():
    assert can_afford({"papel": 5}, {"papel": 5})
    assert not can_afford({"papel": 4}, {"papel": 5})
    assert missing({"papel": 1}, {"papel": 5, "vidro": 2}) == {"papel": 4, "vidro": 2}


def test_pecas_melhoram_o_voo():
    stats = plane_stats({"estabilizador": 2, "leme": 2, "quilha": 2})
    assert stats.response > 1 and stats.max_speed > 1 and stats.hitbox < 1 and stats.dead_zone < 1
    quick = make_run(parts={"leme": 2})
    slow = make_run()
    advance(quick, 0.1, ix=1.0)
    advance(slow, 0.1, ix=1.0)
    assert quick.player.x > slow.player.x


def test_catalogo_de_melhorias_coerente():
    assert len(VILLAGE_UPGRADES) == 8 and len({u.key for u in VILLAGE_UPGRADES}) == 8
    assert all(len(p.level_costs) == 2 for p in PLANE_PARTS)


def test_perfil_ida_e_volta(data_dir):
    profile = Profile()
    profile.recursos["metal"] = 7
    profile.vila = ["horta"]
    profile.estrelas = {"amazonia": 2}
    profile.opcoes.alto_contraste = True
    assert save_profile(profile)
    loaded = load_profile()
    assert loaded.recursos["metal"] == 7 and loaded.vila == ["horta"]
    assert loaded.estrelas == {"amazonia": 2} and loaded.opcoes.alto_contraste


def test_opcoes_novas_migram_e_persistem(data_dir):
    # Saves anteriores não têm essas chaves; os defaults mantêm o comportamento atual.
    old = Profile.from_dict({"opcoes": {"alto_contraste": True}})
    assert not old.opcoes.reduzir_movimento
    assert not old.opcoes.abertura_automatica

    old.opcoes.reduzir_movimento = True
    old.opcoes.abertura_automatica = True
    loaded = Profile.from_dict(old.to_dict())
    assert loaded.opcoes.reduzir_movimento
    assert loaded.opcoes.abertura_automatica


def test_perfil_corrompido_ou_invalido_vira_padrao(data_dir):
    profile_path().write_text("{nao e json", encoding="utf-8")
    assert load_profile().recursos == Profile().recursos
    profile_path().write_text(
        json.dumps(
            {
                "modo": "turbo",
                "aviao": "foguete",
                "estrelas": {"amazonia": 9},
                "vila": ["horta", "nada"],
                "opcoes": {"volume_geral": 5},
            }
        ),
        encoding="utf-8",
    )
    loaded = load_profile()
    assert loaded.modo == "normal" and loaded.aviao == "dart"
    assert loaded.estrelas == {"amazonia": 3} and loaded.vila == ["horta"]
    assert loaded.opcoes.volume_geral == 1.0


def test_importa_o_save_do_prototipo(tmp_path):
    legacy = tmp_path / "legado"
    legacy.mkdir()
    (legacy / "eco_runner_recorde.json").write_text(
        json.dumps({"pontos": 900, "padroes_comprados": ["kraft"]}), encoding="utf-8"
    )
    (legacy / "eco_runner_config.json").write_text(
        json.dumps({"aviao": "crane", "cores": {"crane": "azul"}}), encoding="utf-8"
    )
    profile = load_profile()
    assert profile.pontos == 900 and "kraft" in profile.owned_patterns
    assert profile.aviao == "crane" and profile.plane_color("crane") == "azul"


def test_caatinga_abre_com_uma_estrela_em_manaus():
    profile = Profile()
    assert profile.unlocked("amazonia") and not profile.unlocked("caatinga")
    profile.estrelas["amazonia"] = 1
    assert profile.unlocked("caatinga")


def test_resultado_leva_o_voo_para_o_perfil():
    from dobramundo.scenes.result import apply_run

    profile = Profile()
    run = make_run(mode="normal")
    run.resources["vidro"] = 12
    run.score = 300
    run.add_restoration(C.ERA_SPAN)
    summary = apply_run(profile, run)
    assert profile.recursos["vidro"] == 12 and profile.pontos == 300 and profile.voos == 1
    assert profile.estrelas["amazonia"] == 1 and summary["new_record"]
    run.stars = 0
    apply_run(profile, run)
    assert profile.estrelas["amazonia"] == 1  # guarda a melhor marca


def test_perfil_corrompido_ganha_copia_de_seguranca(data_dir):
    profile_path().write_text("{quebrado", encoding="utf-8")
    load_profile()
    assert (data_dir / "dobramundo_perfil.corrompido.json").is_file()


def test_perfil_invalido_tambem_ganha_copia(data_dir):
    profile_path().write_text(json.dumps({"recursos": "muitos", "estrelas": {"amazonia": "x"}}), encoding="utf-8")
    load_profile()
    assert (data_dir / "dobramundo_perfil.corrompido.json").is_file()


def test_booleanos_em_texto_no_perfil(data_dir):
    profile_path().write_text(json.dumps({"opcoes": {"silencio": "false", "alto_contraste": "sim"}}), encoding="utf-8")
    loaded = load_profile()
    assert loaded.opcoes.silencio is False and loaded.opcoes.alto_contraste is True
