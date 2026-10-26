"""Proteção de arquivos futuros, snapshots antigos e instâncias concorrentes."""

import json
import subprocess
import sys

import pytest

from dobramundo import persistence as P
from dobramundo.instance_lock import InstanceLock
from dobramundo.profile_model import FutureProfileError, migrate_profile


def test_future_profile_is_preserved_without_backup_recovery(data_dir):
    assert P.save_profile(P.Profile())
    path = P.profile_path()
    raw = json.dumps({"versao": 999, "future": {"important": True}}).encode()
    path.write_bytes(raw)
    try:
        profile, notice = P.load_profile_with_notice()
        assert "mais nova" in notice
        assert not P.save_profile(profile)
        assert path.read_bytes() == raw
        assert not list(data_dir.glob("*.corrompido*"))
        with pytest.raises(FutureProfileError):
            P.Profile.from_dict(json.loads(raw))
    finally:
        P._READ_BLOCKED_SLOT_IDS.discard(P.DEFAULT_PROFILE_SLOT)


def test_migration_is_idempotent_and_preserves_old_choices():
    old = {"versao": 1, "voos": 4, "opcoes": {"assistencia_previsivel": False}}
    migrated = migrate_profile(old)
    assert migrated == migrate_profile(migrated)
    assert old["versao"] == 1
    profile = P.Profile.from_dict(migrated)
    assert profile.apoio_escolhido and not profile.opcoes.assistencia_previsivel


def test_stale_profile_cannot_overwrite_newer_resources(data_dir):
    assert P.save_profile(P.Profile())
    a, b = P.load_profile(), P.load_profile()
    a.recursos["papel"] = 100
    assert P.save_profile(a)
    b.recursos["plastico"] = 7
    assert not P.save_profile(b)
    assert P.load_profile().recursos["papel"] == 100
    a.recursos["papel"] = 101
    assert P.save_profile(a)


def test_migration_recovers_recorded_city_progress_without_inventing_completion():
    old = {
        "versao": 1,
        "estrelas": {"amazonia": 2, "caatinga": 1},
        "historico": [
            {"fase": "amazonia", "transformacao": 88.4},
            {"fase": "caatinga", "transformacao": 42},
            {"fase": "amazonia", "transformacao": float("nan")},
            {"fase": "desconhecida", "transformacao": 100},
        ],
    }
    migrated = migrate_profile(old)
    assert migrated["transformacao_cidades"] == {"amazonia": 88.4, "caatinga": 42.0}
    assert migrate_profile(migrated) == migrated
    assert "transformacao_cidades" not in old


def test_migration_uses_only_the_stage_proven_by_old_stars_when_history_is_absent():
    from dobramundo.content.progress import STAR_THRESHOLDS

    profile = P.Profile.from_dict({"versao": 1, "estrelas": {"amazonia": 3, "caatinga": 2}})
    assert profile.transformacao_cidades == {"amazonia": 100.0, "caatinga": STAR_THRESHOLDS[1]}


CHILD = """
from pathlib import Path
import sys
from dobramundo.instance_lock import InstanceLock, InstanceBusyError
try:
    with InstanceLock(Path(sys.argv[1])):
        print('locked', flush=True)
        if len(sys.argv) > 2: sys.stdin.readline()
except InstanceBusyError:
    sys.exit(2)
"""


def test_two_processes_and_other_directory(data_dir, tmp_path):
    with InstanceLock(data_dir):
        busy = subprocess.run([sys.executable, "-c", CHILD, str(data_dir)], capture_output=True, timeout=10)
        assert busy.returncode == 2
        independent = subprocess.run(
            [sys.executable, "-c", CHILD, str(tmp_path / "other")], capture_output=True, timeout=10
        )
        assert independent.returncode == 0
    released = subprocess.run([sys.executable, "-c", CHILD, str(data_dir)], capture_output=True, timeout=10)
    assert released.returncode == 0


def test_crashed_process_releases_os_lock(data_dir):
    child = subprocess.Popen(
        [sys.executable, "-c", CHILD, str(data_dir), "wait"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True
    )
    try:
        assert child.stdout.readline().strip() == "locked"
        child.kill()
        child.wait(timeout=10)
        with InstanceLock(data_dir):
            pass
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
