"""Recuperação e slots locais sem tocar em dados reais do usuário."""

from __future__ import annotations

import json

import pygame
import pytest
from helpers import FakeSource

from dobramundo import persistence as P
from dobramundo.input.pose import SEGMENTS, BodyControl


def _profile(points: int, consent: bool = False) -> P.Profile:
    profile = P.Profile()
    profile.pontos = points
    profile.consentimento = consent
    profile.piloto["chapeu"] = "coroa" if points else "nenhum"
    profile.opcoes.volume_geral = points / 100
    return profile


def test_backup_valido_recupera_perfil_corrompido_e_preserva_copia(data_dir):
    assert P.save_profile(_profile(10))
    assert P.save_profile(_profile(25, True))
    path = P.profile_path()
    path.write_bytes(b"{arquivo interrompido")

    profile, notice = P.load_profile_with_notice()

    assert profile.pontos == 10
    assert profile.consentimento is False
    assert notice and "salvamento íntegro" in notice
    assert P._profile_from_bytes(path.read_bytes()).pontos == 10
    assert list(data_dir.glob("dobramundo_perfil.corrompido*.json"))


@pytest.mark.parametrize("invalid_raw", [b"", b"{perfil interrompido"])
def test_perfil_corrompido_sem_backup_valido_avisa_e_preserva_original(data_dir, invalid_raw):
    path = P.profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(invalid_raw)
    path.with_name(path.name + ".bak").write_bytes(b"not-json")
    path.with_name(path.name + ".bak.1").write_bytes(b"")

    profile, notice = P.load_profile_with_notice()

    assert profile.pontos == 0
    assert notice and "estava danificado" in notice
    archived = list(data_dir.glob("dobramundo_perfil.corrompido*.json"))
    assert len(archived) == 1
    assert archived[0].read_bytes() == invalid_raw
    assert not path.exists()


def test_arquivo_vazio_tambem_tenta_backup(data_dir):
    assert P.save_profile(_profile(7))
    assert P.save_profile(_profile(12))
    P.profile_path().write_bytes(b"")

    profile, notice = P.load_profile_with_notice()

    assert profile.pontos == 7
    assert notice
    assert list(data_dir.glob("dobramundo_perfil.corrompido*.json"))


def test_backup_recupera_quando_arquivo_principal_sumiu(data_dir):
    assert P.save_profile(_profile(8))
    assert P.save_profile(_profile(13))
    P.profile_path().unlink()

    profile, notice = P.load_profile_with_notice()

    assert profile.pontos == 8
    assert notice
    assert P.profile_path().is_file()


def test_leitura_bloqueada_impede_salvar_perfil_vazio(data_dir, monkeypatch):
    path = P.profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("conteúdo preservado", encoding="utf-8")
    original_read_bytes = type(path).read_bytes

    def blocked_read(candidate):
        if candidate == path:
            raise PermissionError("bloqueado no teste")
        return original_read_bytes(candidate)

    monkeypatch.setattr(type(path), "read_bytes", blocked_read)
    profile, notice = P.load_profile_with_notice()

    assert notice and "Não foi possível ler" in notice
    assert not P.save_profile(profile)
    monkeypatch.setattr(type(path), "read_bytes", original_read_bytes)
    assert path.read_text(encoding="utf-8") == "conteúdo preservado"
    P._READ_BLOCKED_SLOT_IDS.discard(P.DEFAULT_PROFILE_SLOT)


def test_slots_independentes_e_indice_nao_guarda_nomes(data_dir):
    assert P.save_profile(_profile(31, True))
    slot = P.create_profile_slot()
    assert slot is not None
    assert P.set_active_profile_slot(slot.id)
    assert P.save_profile(_profile(4), slot.id)

    principal = P.load_profile_with_notice(P.DEFAULT_PROFILE_SLOT)[0]
    extra = P.load_profile_with_notice(slot.id)[0]
    index = json.loads(P.profiles_index_path().read_text(encoding="utf-8"))

    assert principal.pontos == 31 and principal.consentimento is True
    assert extra.pontos == 4 and extra.consentimento is False
    assert index["active"] == slot.id
    assert all("nome" not in key.lower() for key in index)
    assert [entry.label for entry in P.list_profile_slots()] == ["Piloto 1", "Piloto 2"]


def test_indice_ausente_recupera_backup_valido(data_dir):
    slot = P.create_profile_slot()
    assert slot is not None
    path = P.profiles_index_path()
    registry = {"version": P.PROFILE_INDEX_VERSION, "active": slot.id, "slots": ["principal", slot.id]}
    path.with_name(path.name + ".bak").write_text(json.dumps(registry), encoding="utf-8")
    path.unlink()

    recovered, notice = P._registry_with_notice()

    assert recovered["active"] == slot.id
    assert slot.id in recovered["slots"]
    assert notice and path.is_file()


def test_indice_corrompido_com_falha_de_restauro_mantem_slots_em_memoria(data_dir, monkeypatch):
    slot = P.create_profile_slot()
    assert slot is not None
    path = P.profiles_index_path()
    registry = {"version": P.PROFILE_INDEX_VERSION, "active": slot.id, "slots": ["principal", slot.id]}
    path.with_name(path.name + ".bak").write_text(json.dumps(registry), encoding="utf-8")
    path.write_text("{corrompido", encoding="utf-8")
    monkeypatch.setattr(P, "_atomic_write", lambda _path, _raw: False)

    recovered, notice = P._registry_with_notice()

    assert slot.id in recovered["slots"]
    assert recovered["active"] == slot.id
    assert notice and "na memória" in notice


def test_indice_e_backups_perdidos_preservam_slots_orfaos_sem_ativar(data_dir):
    slot = P.create_profile_slot()
    assert slot is not None
    path = P.profiles_index_path()
    path.unlink()

    recovered, notice = P._registry_with_notice()

    assert recovered["active"] == P.DEFAULT_PROFILE_SLOT
    assert slot.id in recovered["slots"]
    assert notice and "sem a lista principal" in notice
    assert not path.exists()


def test_json_parcial_dos_novos_campos_nao_converte_valores_invalidos():
    profile = P.Profile.from_dict(
        {
            "opcoes": {
                "modo_exploracao": "false",
                "limite_voo_s": True,
                "assistencia_previsivel": 1,
                "semente_desafio": -1,
            }
        }
    )

    assert profile.opcoes.modo_exploracao is False
    assert profile.opcoes.limite_voo_s == 0
    assert profile.opcoes.assistencia_previsivel is False
    assert profile.opcoes.semente_desafio == 0


def test_temporario_incompleto_nao_substitui_perfil_valido(data_dir):
    assert P.save_profile(_profile(19))
    P.profile_path().with_name(P.profile_path().name + ".part.tmp").write_bytes(b"{")

    profile, notice = P.load_profile_with_notice()

    assert profile.pontos == 19
    assert notice is None


def test_preview_perfil_corrompido_nao_recupera_nem_escreve(data_dir):
    path = P.profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"{quebrado")

    assert P.peek_profile(P.DEFAULT_PROFILE_SLOT) is None
    assert path.read_bytes() == b"{quebrado"
    assert not list(data_dir.glob("*.corrompido*.json"))


def test_falha_ao_salvar_cancela_troca_de_perfil(app, monkeypatch):
    slot = P.create_profile_slot()
    assert slot is not None
    original = app.profile
    monkeypatch.setattr(app, "writer", lambda _profile: False)

    assert app.select_profile(slot.id) is False
    assert app.profile is original
    assert app.profile_slot == P.DEFAULT_PROFILE_SLOT
    assert "troca foi cancelada" in app.storage_notice


def test_registry_scene_e_fabrica_de_cena(app):
    scene = app.create_scene("perfis")
    scene.build()

    assert scene.__class__.__name__ == "ProfilesScene"
    assert any(button.key.startswith("perfil-") for button in scene.menu.buttons)

    scene.error = "Não foi possível salvar o piloto. A troca foi cancelada."
    scene.draw(app.canvas)
    scene._select(app.profile_slot)
    assert app.next_scene.__class__.__name__ == "VillageScene"


def test_profile_switch_clears_same_segment_calibration_and_stale_controls(app, monkeypatch):
    target = P.Profile()
    target.controle = "tronco_pe"
    slot = P.create_profile_slot()
    assert slot is not None
    assert P.save_profile(target, slot.id)

    source = FakeSource()
    body = BodyControl(source, SEGMENTS["tronco_pe"])
    body.mapper.base = (0.28, 0.37)
    body.mapper.ax, body.mapper.ay = 0.6, -0.4
    app.input.body = body
    app.input.segment_key = "tronco_pe"
    app.profile.controle = "tronco_pe"
    app.input.pressed.add(pygame.K_LEFT)
    app.input.mouse_pos = (400, 300)
    monkeypatch.setattr(app, "apply_options", lambda: None)

    assert app.select_profile(slot.id)

    assert body.mapper.base is None
    assert body.mapper.axes() == (0.0, 0.0)
    assert not app.input.pressed
    assert app.input.mouse_pos is None


def test_fullscreen_option_is_synced_when_profile_changes(app, monkeypatch):
    calls = []
    monkeypatch.setattr(pygame.display, "get_surface", lambda: type("Display", (), {"get_flags": lambda self: 0})())
    monkeypatch.setattr(app, "toggle_fullscreen", lambda: calls.append(True))
    app.profile.opcoes.tela_cheia = True

    app._sync_fullscreen()

    assert calls == [True]


def test_scene_factory_is_used_by_goto_and_map_start(app):
    from dobramundo.scenes import make_scene

    called = []

    def factory(core, name, *args, **kwargs):
        called.append(name)
        return make_scene(core, name, *args, **kwargs)

    app.scene_factory = factory
    app.create_scene("perfis").goto("vila")
    app.profile.tutorial_visto = True
    app.create_scene("mapa").start("amazonia")

    assert called == ["perfis", "vila", "mapa", "voo"]
