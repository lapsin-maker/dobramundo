"""Perfil do jogador num único JSON versionado (dobramundo_perfil.json).

Guarda progresso (estrelas, recursos, vila, peças), personalização (avião,
pintura, piloto) e opções (controle, som, acessibilidade, superfície). Na
primeira execução, importa o recorde, os pontos e a pintura do protótipo
Eco Runner, se existirem.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .config import HISTORY_LIMIT
from .content.biomes import BIOME_ORDER
from .content.items import WASTE_KEYS
from .content.pilot import DEFAULT_PILOT, normalize_pilot
from .content.planes import (
    DEFAULT_PATTERN,
    DEFAULT_PLANE,
    FREE_PATTERNS,
    PATTERN_PRICES,
    PLANE_COLOR_KEYS,
    PLANE_KEYS,
    PLANE_PATTERN_KEYS,
)
from .content.progress import MAX_PART_LEVEL, PART_KEYS, VILLAGE_KEYS
from .log import log
from .paths import legacy_data_dirs, profiles_dir, profiles_index_path, user_data_dir

PROFILE_FILENAME = "dobramundo_perfil.json"
DEFAULT_PROFILE_SLOT = "principal"
PROFILE_INDEX_VERSION = 1
PROFILE_SLOT_LIMIT = 8
_READ_BLOCKED_SLOT_IDS = set()
SCHEMA_VERSION = 1
GAME_MODES = ("normal", "dificil")
MODE_LABELS = {"normal": "Normal", "dificil": "Difícil"}
# Segmentos corporais de controle (GDD, seção 4) e o teclado do supervisor.
CONTROL_SEGMENTS = ("teclado", "pes", "tronco_pe", "tronco_sentado", "mao_direita", "mao_esquerda", "cabeca")
SURFACES = ("monitor", "parede", "mesa", "chao")


@dataclass
class Options:
    volume_geral: float = 0.8
    volume_musica: float = 0.6
    volume_efeitos: float = 0.8
    silencio: bool = False
    alto_contraste: bool = False
    superficie: str = "monitor"
    espelhar: bool = False  # inverte a imagem na horizontal (projeção por trás)
    rotacao: int = 0  # 0, 90, 180 ou 270 graus no sentido horário (projetor no teto, chão, mesa)
    tela_cheia: bool = False
    permanencia: float = 2.0  # segundos parado sobre um botão para selecioná-lo (padrão do console)
    sensibilidade: float = 1.0  # alcance do movimento corporal (maior = movimento menor basta)
    inverter_vertical: bool = False  # câmera vista de cima (chão, mesa): subir e descer trocados
    inverter_horizontal: bool = False  # imagem da câmera sem espelho: esquerda e direita trocadas
    controle_posicao: bool = True  # o corpo indica onde o avião fica (não: indica a velocidade)
    momento_foco: bool = True  # câmera lenta guiada perto de uma batida
    efeitos_fortes: bool = True  # clarões e tremor de tela (desligar para sensibilidade sensorial)
    reduzir_movimento: bool = False  # menos movimento decorativo; mantém avanço do percurso
    abertura_automatica: bool = False  # avança sozinha a história opcional
    centralizar_sozinho: bool = False  # recentralização automática após perda longa (opt-in)
    # Calibração do chão (projeção + webcam): onde a câmera vê os 4 alvos projetados
    # (superior esquerdo, superior direito, inferior direito, inferior esquerdo), 0..1.
    chao_pontos: List[List[float]] = field(default_factory=list)
    alvo_frente: float = 0.12  # cursor dos pés à frente dos dedos (fração da altura da imagem)
    permanencia_editor: float = 3.0
    escala_contraste: float = 1.3
    modo_exploracao: bool = False
    limite_voo_s: int = 0
    assistencia_previsivel: bool = False
    semente_desafio: int = 0


@dataclass
class Profile:
    versao: int = SCHEMA_VERSION
    consentimento: bool = False  # supervisor leu o aviso de uso e privacidade
    consentimento_em: str = ""  # data e hora (ISO) da confirmação do supervisor
    abertura_vista: bool = False
    piloto_montado: bool = False  # a criança já montou o personagem (primeira tela do jogo)
    tutorial_visto: bool = False  # ensaio opcional de controles antes da primeira decolagem
    modo: str = "normal"
    controle: str = "teclado"
    estrelas: Dict[str, int] = field(default_factory=dict)
    recordes: Dict[str, int] = field(default_factory=dict)  # "bioma:modo" -> pontos
    recursos: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in WASTE_KEYS})
    pontos: int = 0  # carteira da loja de padrões
    padroes_comprados: List[str] = field(default_factory=list)
    vila: List[str] = field(default_factory=list)
    pedidos_vila: Dict[str, str] = field(default_factory=dict)
    pecas: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in PART_KEYS})
    aviao: str = DEFAULT_PLANE
    cores: Dict[str, str] = field(default_factory=dict)  # avião -> cor
    padroes: Dict[str, str] = field(default_factory=dict)  # avião -> padrão
    piloto: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_PILOT))
    voos: int = 0
    voos_fase: Dict[str, int] = field(default_factory=dict)  # bioma -> voos concluídos
    historico: List[dict] = field(default_factory=list)  # resumo dos últimos voos (supervisor)
    opcoes: Options = field(default_factory=Options)

    # ------------------------------------------------------------ consultas
    @property
    def owned_patterns(self) -> set:
        return set(FREE_PATTERNS) | set(self.padroes_comprados)

    def plane_color(self, plane: str) -> str:
        return self.cores.get(plane, "original")

    def plane_pattern(self, plane: str) -> str:
        return self.padroes.get(plane, DEFAULT_PATTERN)

    def record(self, biome: str, mode: str) -> int:
        return self.recordes.get(f"{biome}:{mode}", 0)

    def total_stars(self) -> int:
        return sum(self.estrelas.values())

    def unlocked(self, biome: str) -> bool:
        """A Caatinga abre com 1 estrela em Manaus (a primeira fase está sempre aberta)."""
        index = BIOME_ORDER.index(biome)
        return index == 0 or self.estrelas.get(BIOME_ORDER[index - 1], 0) >= 1

    # ------------------------------------------------------------ validação
    def normalize(self) -> Profile:
        self.modo = self.modo if self.modo in GAME_MODES else "normal"
        self.controle = self.controle if self.controle in CONTROL_SEGMENTS else "teclado"
        self.aviao = self.aviao if self.aviao in PLANE_KEYS else DEFAULT_PLANE
        self.estrelas = {b: max(0, min(3, int(self.estrelas.get(b, 0)))) for b in BIOME_ORDER if self.estrelas.get(b)}
        self.recursos = {k: max(0, int(self.recursos.get(k, 0))) for k in WASTE_KEYS}
        self.pontos = max(0, int(self.pontos))
        self.padroes_comprados = sorted({p for p in self.padroes_comprados if p in PATTERN_PRICES})
        self.vila = [k for k in VILLAGE_KEYS if k in set(self.vila)]
        self.pedidos_vila = {
            str(k): str(v)
            for k, v in self.pedidos_vila.items()
            if k in VILLAGE_KEYS and v in ("solicitada", "concluida")
        }
        self.pecas = {k: max(0, min(MAX_PART_LEVEL, int(self.pecas.get(k, 0)))) for k in PART_KEYS}
        self.cores = {m: c for m, c in self.cores.items() if m in PLANE_KEYS and c in PLANE_COLOR_KEYS}
        self.padroes = {m: c for m, c in self.padroes.items() if m in PLANE_KEYS and c in PLANE_PATTERN_KEYS}
        self.piloto = normalize_pilot(self.piloto)
        self.voos_fase = {b: max(0, int(self.voos_fase[b])) for b in BIOME_ORDER if b in self.voos_fase}
        self.historico = [_flat(e) for e in self.historico if isinstance(e, dict)][-HISTORY_LIMIT:]
        o = self.opcoes
        for name in ("volume_geral", "volume_musica", "volume_efeitos"):
            setattr(o, name, max(0.0, min(1.0, float(vars(o)[name]))))
        o.superficie = o.superficie if o.superficie in SURFACES else "monitor"
        o.rotacao = o.rotacao if o.rotacao in (0, 90, 180, 270) else 0
        o.alvo_frente = max(0.0, min(0.35, float(o.alvo_frente)))
        o.chao_pontos = _floor_points(o.chao_pontos)
        o.permanencia = max(1.0, min(3.5, float(o.permanencia)))
        o.permanencia_editor = max(1.0, min(5.0, float(o.permanencia_editor)))
        o.escala_contraste = max(1.0, min(1.6, float(o.escala_contraste)))
        o.sensibilidade = max(0.5, min(2.0, float(o.sensibilidade)))
        o.modo_exploracao = o.modo_exploracao if isinstance(o.modo_exploracao, bool) else False
        o.limite_voo_s = o.limite_voo_s if type(o.limite_voo_s) is int and o.limite_voo_s in (0, 120, 180, 240) else 0
        o.assistencia_previsivel = o.assistencia_previsivel if isinstance(o.assistencia_previsivel, bool) else False
        o.semente_desafio = (
            o.semente_desafio if type(o.semente_desafio) is int and 0 <= o.semente_desafio <= 0xFFFFFFFF else 0
        )
        return self

    # ---------------------------------------------------------------- JSON
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> Profile:
        """Lê campo a campo, aceitando só o tipo esperado. ProfileError se não der para validar."""
        profile = cls()
        if not isinstance(data, dict):
            raise ProfileError("o perfil não é um objeto JSON")
        for name in profile.__dataclass_fields__:
            if name != "opcoes" and name in data:
                _assign(profile, name, data[name])
        options = data.get("opcoes")
        if isinstance(options, dict) and "rotacao" not in options and _as_bool(options.get("girar", False)):
            options = {**options, "rotacao": 180}  # perfis até a 1.2 tinham só "girar 180°"
        if isinstance(options, dict):
            for name in profile.opcoes.__dataclass_fields__:
                if name in options:
                    if name in ("modo_exploracao", "assistencia_previsivel"):
                        if not isinstance(options[name], bool):
                            continue
                    elif name == "limite_voo_s":
                        if type(options[name]) is not int or options[name] not in (0, 120, 180, 240):
                            continue
                    elif name == "semente_desafio":
                        if type(options[name]) is not int or not 0 <= options[name] <= 0xFFFFFFFF:
                            continue
                    _assign(profile.opcoes, name, options[name])
        try:
            return profile.normalize()
        except (TypeError, ValueError, AttributeError, IndexError) as exc:
            raise ProfileError(f"perfil inválido ({exc.__class__.__name__})") from exc


def _floor_points(points: object) -> List[List[float]]:
    """Quatro pontos (x, y) entre 0 e 1, ou nenhum (calibração ausente ou inválida)."""
    try:
        result = [[float(p[0]), float(p[1])] for p in points]  # type: ignore[union-attr]
    except (TypeError, ValueError, IndexError):
        return []
    ok = len(result) == 4 and all(0.0 <= v <= 1.0 for p in result for v in p)
    return result if ok else []


def _flat(entry: dict) -> dict:
    """Entrada do histórico só com textos e números (nada que quebre o JSON)."""
    return {str(k): v for k, v in entry.items() if isinstance(v, (str, int, float)) and not isinstance(v, bool)}


class ProfileError(ValueError):
    """Perfil salvo que não pôde ser lido ou validado."""


def _as_bool(value: object) -> bool:
    """Booleanos também vindos de texto ("false", "0", "não") quando o JSON foi editado à mão."""
    if isinstance(value, str):
        return value.strip().lower() not in ("", "0", "false", "falso", "nao", "não", "no", "off")
    return bool(value)


def _assign(target: object, name: str, value: object) -> None:
    """Grava value em target.name convertendo para o tipo do valor padrão (ignora o que não serve)."""
    default = vars(target)[name]
    try:
        if isinstance(default, bool):
            setattr(target, name, _as_bool(value))
        elif isinstance(default, (int, float)) and not isinstance(value, bool):
            setattr(target, name, type(default)(value))
        elif isinstance(default, type(value)):
            setattr(target, name, value)
    except (TypeError, ValueError):
        pass


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
        profile = _profile_from_bytes(raw)
        if profile is not None:
            _READ_BLOCKED_SLOT_IDS.discard(slot_id)
            return profile, None
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
        return profile, notice
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
    return profile, notice


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
        if _valid_profile_bytes(previous):
            if not _rotate_backup(path, previous, _profile_from_bytes):
                return False
        else:
            log.warning("preservando perfil inválido antes de salvar: %s", path)
            if _archive_corrupt(path) is None:
                return False
    return _atomic_write(path, raw)


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
