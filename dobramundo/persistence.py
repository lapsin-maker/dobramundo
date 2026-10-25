"""Armazenamento atômico, recuperação e catálogo local de pilotos.

O modelo e as migrações ficam em profile_model; nomes públicos antigos são
reexportados para manter o contrato com cenas, console e ferramentas.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .content.planes import PLANE_KEYS
from .log import log
from .paths import legacy_data_dirs, profiles_dir, profiles_index_path, user_data_dir
from .profile_model import (
    CONTROL_SEGMENTS as CONTROL_SEGMENTS,
)
from .profile_model import (
    GAME_MODES as GAME_MODES,
)
from .profile_model import (
    MODE_LABELS as MODE_LABELS,
)
from .profile_model import (
    SCHEMA_VERSION as SCHEMA_VERSION,
)
from .profile_model import (
    SURFACES as SURFACES,
)
from .profile_model import (
    Options as Options,
)
from .profile_model import (
    Profile as Profile,
)
from .profile_model import (
    ProfileError as ProfileError,
)

PROFILE_FILENAME = "dobramundo_perfil.json"
DEFAULT_PROFILE_SLOT = "principal"
PROFILE_INDEX_VERSION = 1
PROFILE_SLOT_LIMIT = 8
_READ_BLOCKED_SLOT_IDS = set()


@dataclass(frozen=True)
class ProfileSlot:
    id: str
    label: str
    active: bool = False


def _valid_slot_id(slot_id: object) -> bool:
    return slot_id == DEFAULT_PROFILE_SLOT or (
        isinstance(slot_id, str) and re.fullmatch(r"[0-9a-f]{32}", slot_id) is not None
    )


def profile_path(slot_id: str = DEFAULT_PROFILE_SLOT) -> Path:
    """Caminho do slot; o principal permanece no arquivo legado para preservar dados."""
    if not _valid_slot_id(slot_id):
        raise ValueError("identificador de perfil inválido")
    if slot_id == DEFAULT_PROFILE_SLOT:
        return user_data_dir() / PROFILE_FILENAME
    return profiles_dir() / f"{slot_id}.json"


def _atomic_write(path: Path, raw: bytes) -> bool:
    temp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with temp.open("wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        temp.replace(path)
        return True
    except OSError as exc:
        log.error("não foi possível gravar %s (%s)", path, exc)
        return False
    finally:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            log.warning("não foi possível remover o temporário %s", temp)


def _archive_corrupt(path: Path) -> Optional[Path]:
    if not path.is_file():
        return None
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    first_copy = path.with_name(f"{path.stem}.corrompido{path.suffix}")
    if not first_copy.exists():
        candidate = first_copy
    else:
        candidate = path.with_name(f"{path.stem}.corrompido.{stamp}{path.suffix}")
    suffix = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}.corrompido.{stamp}.{suffix}{path.suffix}")
        suffix += 1
    try:
        path.replace(candidate)
        return candidate
    except OSError as exc:
        log.error("não foi possível preservar o arquivo inválido %s (%s)", path, exc)
        return None


def _backup_paths(path: Path) -> tuple[Path, Path]:
    return path.with_name(path.name + ".bak"), path.with_name(path.name + ".bak.1")


def _rotate_backup(path: Path, raw: bytes, validator) -> bool:
    backup, previous = _backup_paths(path)
    if backup.is_file():
        try:
            older = backup.read_bytes()
            if validator(older) is not None and not _atomic_write(previous, older):
                return False
        except OSError as exc:
            log.error("não foi possível ler o backup %s (%s)", backup, exc)
            return False
    return _atomic_write(backup, raw)


def _decode_json(raw: bytes) -> Optional[dict]:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _read_json(path: Path) -> Optional[dict]:
    try:
        return _decode_json(path.read_bytes())
    except OSError:
        return None


def _profile_from_bytes(raw: bytes) -> Optional[Profile]:
    data = _decode_json(raw)
    if data is None:
        return None
    try:
        return Profile.from_dict(data)
    except (ProfileError, TypeError, ValueError, AttributeError, IndexError):
        return None


def _future_profile(raw: bytes) -> bool:
    data = _decode_json(raw)
    return data is not None and type(data.get("versao")) is int and data["versao"] > SCHEMA_VERSION


def _remember_revision(profile: Profile, path: Path, raw: bytes) -> Profile:
    # Metadado de sessão: não é um campo do save nem vai para asdict().
    vars(profile)["_disk_revision"] = (str(path), hashlib.sha256(raw).hexdigest())
    return profile


def _registry_from_bytes(raw: bytes) -> Optional[dict]:
    data = _decode_json(raw)
    if data is None or data.get("version") != PROFILE_INDEX_VERSION:
        return None
    raw_slots = data.get("slots")
    if not isinstance(raw_slots, list):
        return None
    slots = []
    for slot_id in raw_slots:
        if _valid_slot_id(slot_id) and slot_id not in slots:
            slots.append(slot_id)
    if DEFAULT_PROFILE_SLOT not in slots:
        slots.insert(0, DEFAULT_PROFILE_SLOT)
    slots = slots[:PROFILE_SLOT_LIMIT]
    active = data.get("active")
    if active not in slots:
        active = DEFAULT_PROFILE_SLOT
    return {"version": PROFILE_INDEX_VERSION, "active": active, "slots": slots}


def _default_registry() -> dict:
    return {"version": PROFILE_INDEX_VERSION, "active": DEFAULT_PROFILE_SLOT, "slots": [DEFAULT_PROFILE_SLOT]}


def _discover_profile_slot_ids() -> List[str]:
    """Recupera arquivos nomeados por IDs válidos sem escolher nenhum como ativo."""
    found = []
    try:
        candidates = profiles_dir().glob("*.json")
        for path in candidates:
            slot_id = path.stem
            if not _valid_slot_id(slot_id) or slot_id == DEFAULT_PROFILE_SLOT:
                continue
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            if _valid_profile_bytes(raw):
                found.append(slot_id)
    except OSError as exc:
        log.warning("não foi possível procurar slots locais órfãos (%s)", exc)
    return sorted(set(found))[: PROFILE_SLOT_LIMIT - 1]


def _registry_with_notice() -> tuple[dict, Optional[str]]:
    path = profiles_index_path()
    raw = None
    missing = False
    read_error = False
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        missing = True
    except OSError as exc:
        log.error("não foi possível ler o índice de perfis %s (%s)", path, exc)
        read_error = True
    registry = _registry_from_bytes(raw) if raw is not None else None
    if registry is not None:
        return registry, None
    decoded = _decode_json(raw) if raw is not None else None
    if decoded and type(decoded.get("version")) is int and decoded["version"] > PROFILE_INDEX_VERSION:
        return _default_registry(), "Esta lista de pilotos foi salva por uma versão mais nova. Atualize o jogo."
    if not missing and not read_error:
        log.warning("índice de perfis inválido: %s", path)
        corrupt_copy = _archive_corrupt(path)
        if corrupt_copy is None and path.exists():
            read_error = True
    for backup in _backup_paths(path):
        try:
            backup_raw = backup.read_bytes()
        except OSError:
            continue
        registry = _registry_from_bytes(backup_raw)
        if registry is None:
            continue
        restored = _atomic_write(path, backup_raw)
        log.warning("índice de perfis recuperado de %s", backup)
        notice = "A lista de pilotos foi recuperada de um salvamento anterior."
        if not restored:
            notice = "Recuperei a lista de pilotos na memória, mas não consegui restaurar o arquivo do índice."
        return registry, notice
    recovered_slots = _discover_profile_slot_ids()
    if recovered_slots:
        registry = _default_registry()
        registry["slots"].extend(recovered_slots)
        notice = "Encontrei pilotos salvos sem a lista principal; confira os cartões antes de continuar."
        return registry, notice
    if missing and not read_error:
        return _default_registry(), None
    return _default_registry(), "A lista de pilotos estava danificada; mantive o perfil principal."


def list_profile_slots() -> List[ProfileSlot]:
    registry, _ = _registry_with_notice()
    return [
        ProfileSlot(slot_id, f"Piloto {index + 1}", slot_id == registry["active"])
        for index, slot_id in enumerate(registry["slots"])
    ]


def set_active_profile_slot(slot_id: str) -> bool:
    registry, _ = _registry_with_notice()
    if slot_id not in registry["slots"]:
        return False
    registry["active"] = slot_id
    raw = json.dumps(registry, ensure_ascii=False, indent=2).encode("utf-8")
    path = profiles_index_path()
    if path.is_file():
        try:
            current = path.read_bytes()
        except OSError as exc:
            log.error("não foi possível ler o índice antes da troca (%s)", exc)
            return False
        if _registry_from_bytes(current) is None or not _rotate_backup(path, current, _registry_from_bytes):
            return False
    return _atomic_write(path, raw)


def create_profile_slot() -> Optional[ProfileSlot]:
    """Cria um slot anônimo com defaults; não altera o perfil ativo."""
    registry, _ = _registry_with_notice()
    if len(registry["slots"]) >= PROFILE_SLOT_LIMIT:
        return None
    slot_id = uuid.uuid4().hex
    if not save_profile(Profile(), slot_id):
        return None
    registry["slots"].append(slot_id)
    raw = json.dumps(registry, ensure_ascii=False, indent=2).encode("utf-8")
    path = profiles_index_path()
    if path.is_file():
        try:
            current = path.read_bytes()
        except OSError as exc:
            log.error("não foi possível ler o índice ao criar perfil (%s)", exc)
            return None
        if _registry_from_bytes(current) is None or not _rotate_backup(path, current, _registry_from_bytes):
            return None
    if not _atomic_write(path, raw):
        return None
    return ProfileSlot(slot_id, f"Piloto {len(registry['slots'])}", False)


def _load_profile_with_notice(slot_id: str, allow_legacy: bool) -> tuple[Profile, Optional[str]]:
    path = profile_path(slot_id)
    existed = path.exists()
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        raw = b""
    except OSError as exc:
        log.error("não foi possível ler o perfil %s (%s)", path, exc)
        _READ_BLOCKED_SLOT_IDS.add(slot_id)
        return Profile(), "Não foi possível ler este perfil. Um perfil vazio foi aberto."
    else:
        if _future_profile(raw):
            _READ_BLOCKED_SLOT_IDS.add(slot_id)
            return (
                Profile(),
                "Este piloto foi salvo por uma versão mais nova. Atualize o jogo; o arquivo foi preservado.",
            )
        profile = _profile_from_bytes(raw)
        if profile is not None:
            _READ_BLOCKED_SLOT_IDS.discard(slot_id)
            return _remember_revision(profile, path, raw), None
    if existed:
        log.warning("perfil inválido: %s", path)
        corrupt_copy = _archive_corrupt(path)
        if corrupt_copy is None and path.exists():
            return Profile(), "O arquivo do perfil está danificado e não pôde ser preservado."
    for backup in _backup_paths(path):
        try:
            backup_raw = backup.read_bytes()
        except OSError:
            continue
        profile = _profile_from_bytes(backup_raw)
        if profile is None:
            continue
        restored = _atomic_write(path, backup_raw)
        if restored:
            _READ_BLOCKED_SLOT_IDS.discard(slot_id)
        else:
            _READ_BLOCKED_SLOT_IDS.add(slot_id)
        log.warning("perfil recuperado de %s", backup)
        notice = "Recuperei o último salvamento íntegro. Confira se o progresso recente aparece."
        if not restored:
            notice = "Recuperei o último salvamento íntegro na memória, mas não consegui restaurar o arquivo."
        return _remember_revision(profile, path, backup_raw), notice
    if existed:
        notice = "O arquivo do perfil estava danificado; guardei uma cópia. Confira os dados carregados."
    else:
        notice = (
            "O arquivo deste piloto não foi encontrado; abri um perfil novo."
            if slot_id != DEFAULT_PROFILE_SLOT
            else None
        )
    profile = Profile()
    if allow_legacy:
        import_legacy(profile)
    return _remember_revision(profile, path, b""), notice


def load_profile_with_notice(slot_id: str = DEFAULT_PROFILE_SLOT) -> tuple[Profile, Optional[str]]:
    if not _valid_slot_id(slot_id):
        raise ValueError("identificador de perfil inválido")
    return _load_profile_with_notice(slot_id, slot_id == DEFAULT_PROFILE_SLOT)


def peek_profile(slot_id: str) -> Optional[Profile]:
    """Lê perfil para miniatura sem recuperação, arquivo de aviso ou qualquer escrita."""
    if not _valid_slot_id(slot_id):
        return None
    try:
        raw = profile_path(slot_id).read_bytes()
    except OSError:
        return None
    return _profile_from_bytes(raw)


def load_profile() -> Profile:
    """Carrega o perfil legado/principal; a interface usa load_active_profile()."""
    return load_profile_with_notice(DEFAULT_PROFILE_SLOT)[0]


def load_active_profile() -> tuple[Profile, str, Optional[str]]:
    registry, registry_notice = _registry_with_notice()
    slot_id = registry["active"]
    profile, profile_notice = load_profile_with_notice(slot_id)
    notices = [notice for notice in (registry_notice, profile_notice) if notice]
    return profile, slot_id, " ".join(notices) or None


def profile_read_blocked(slot_id: str) -> bool:
    """True quando uma leitura falhou nesta sessão e salvar poderia apagar dados."""
    return slot_id in _READ_BLOCKED_SLOT_IDS


def _valid_profile_bytes(raw: bytes) -> bool:
    return _profile_from_bytes(raw) is not None


def save_profile(profile: Profile, slot_id: str = DEFAULT_PROFILE_SLOT) -> bool:
    """Grava atomicamente, mantendo duas cópias válidas anteriores quando possível."""
    path = profile_path(slot_id)
    if slot_id in _READ_BLOCKED_SLOT_IDS:
        log.error("gravação bloqueada: a leitura do perfil %s falhou nesta sessão", slot_id)
        return False
    try:
        raw = json.dumps(profile.to_dict(), ensure_ascii=False, indent=2).encode("utf-8")
    except (TypeError, ValueError) as exc:
        log.error("perfil não pôde ser serializado (%s)", exc)
        return False
    if path.is_file():
        try:
            previous = path.read_bytes()
        except OSError as exc:
            log.error("não foi possível ler o perfil antes de salvar %s (%s)", path, exc)
            return False
        if _future_profile(previous):
            log.error("perfil de versão futura preservado: %s", path)
            return False
        revision = vars(profile).get("_disk_revision")
        if revision is not None and revision != (str(path), hashlib.sha256(previous).hexdigest()):
            log.error("o perfil mudou em outra sessão; gravação cancelada: %s", path)
            return False
        if _valid_profile_bytes(previous):
            if not _rotate_backup(path, previous, _profile_from_bytes):
                return False
        else:
            log.warning("preservando perfil inválido antes de salvar: %s", path)
            if _archive_corrupt(path) is None:
                return False
    if not _atomic_write(path, raw):
        return False
    _remember_revision(profile, path, raw)
    return True


def import_legacy(profile: Profile) -> bool:
    """Traz pontos, padrões comprados, pintura e avião do protótipo Eco Runner."""
    imported = False
    for folder in legacy_data_dirs():
        record = _read_json(folder / "eco_runner_recorde.json")
        config = _read_json(folder / "eco_runner_config.json")
        if record:
            try:
                profile.pontos = max(profile.pontos, int(record.get("pontos", 0)))
            except (TypeError, ValueError):
                pass
            bought = record.get("padroes_comprados")
            if isinstance(bought, list):
                profile.padroes_comprados = sorted(set(profile.padroes_comprados) | set(bought))
            imported = True
        if config:
            if isinstance(config.get("cores"), dict):
                profile.cores.update(config["cores"])
            if isinstance(config.get("padroes"), dict):
                profile.padroes.update(config["padroes"])
            if config.get("aviao") in PLANE_KEYS:
                profile.aviao = config["aviao"]
            if config.get("modo") in GAME_MODES:
                profile.modo = config["modo"]
            imported = True
        if imported:
            break
    profile.normalize()
    return imported
