"""Perfil do jogador num único JSON versionado (dobramundo_perfil.json).

Guarda progresso (estrelas, recursos, vila, peças), personalização (avião,
pintura, piloto) e opções (controle, som, acessibilidade, superfície). Na
primeira execução, importa o recorde, os pontos e a pintura do protótipo
Eco Runner, se existirem.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
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
from .paths import legacy_data_dirs, user_data_dir

PROFILE_FILENAME = "dobramundo_perfil.json"
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
    girar: bool = False  # gira 180° (projetor no teto, imagem no chão ou na mesa)
    tela_cheia: bool = False
    permanencia: float = 1.2  # segundos parado sobre um botão para selecioná-lo
    sensibilidade: float = 1.0  # alcance do movimento corporal (maior = movimento menor basta)
    inverter_vertical: bool = False  # câmera vista de cima (chão, mesa): subir e descer trocados
    controle_posicao: bool = True  # o corpo indica onde o avião fica (não: indica a velocidade)
    momento_foco: bool = True  # câmera lenta guiada perto de uma batida
    efeitos_fortes: bool = True  # clarões e tremor de tela (desligar para sensibilidade sensorial)


@dataclass
class Profile:
    versao: int = SCHEMA_VERSION
    consentimento: bool = False  # supervisor leu o aviso de uso e privacidade
    consentimento_em: str = ""  # data e hora (ISO) da confirmação do supervisor
    abertura_vista: bool = False
    modo: str = "normal"
    controle: str = "teclado"
    estrelas: Dict[str, int] = field(default_factory=dict)
    recordes: Dict[str, int] = field(default_factory=dict)  # "bioma:modo" -> pontos
    recursos: Dict[str, int] = field(default_factory=lambda: {k: 0 for k in WASTE_KEYS})
    pontos: int = 0  # carteira da loja de padrões
    padroes_comprados: List[str] = field(default_factory=list)
    vila: List[str] = field(default_factory=list)
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
        self.pecas = {k: max(0, min(MAX_PART_LEVEL, int(self.pecas.get(k, 0)))) for k in PART_KEYS}
        self.cores = {m: c for m, c in self.cores.items() if m in PLANE_KEYS and c in PLANE_COLOR_KEYS}
        self.padroes = {m: c for m, c in self.padroes.items() if m in PLANE_KEYS and c in PLANE_PATTERN_KEYS}
        self.piloto = normalize_pilot(self.piloto)
        self.voos_fase = {b: max(0, int(self.voos_fase[b])) for b in BIOME_ORDER if b in self.voos_fase}
        self.historico = [_flat(e) for e in self.historico if isinstance(e, dict)][-HISTORY_LIMIT:]
        o = self.opcoes
        for name in ("volume_geral", "volume_musica", "volume_efeitos"):
            setattr(o, name, max(0.0, min(1.0, float(getattr(o, name)))))
        o.superficie = o.superficie if o.superficie in SURFACES else "monitor"
        o.permanencia = max(0.6, min(3.0, float(o.permanencia)))
        o.sensibilidade = max(0.5, min(2.0, float(o.sensibilidade)))
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
        if isinstance(options, dict):
            for name in profile.opcoes.__dataclass_fields__:
                if name in options:
                    _assign(profile.opcoes, name, options[name])
        try:
            return profile.normalize()
        except (TypeError, ValueError, AttributeError, IndexError) as exc:
            raise ProfileError(f"perfil inválido ({exc.__class__.__name__})") from exc


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
    default = getattr(target, name)
    try:
        if isinstance(default, bool):
            setattr(target, name, _as_bool(value))
        elif isinstance(default, (int, float)) and not isinstance(value, bool):
            setattr(target, name, type(default)(value))
        elif isinstance(default, type(value)):
            setattr(target, name, value)
    except (TypeError, ValueError):
        pass


def profile_path() -> Path:
    return user_data_dir() / PROFILE_FILENAME


def _read_json(path: Path) -> Optional[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


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


def load_profile() -> Profile:
    path = profile_path()
    data = _read_json(path)
    if data is not None:
        try:
            return Profile.from_dict(data)
        except ProfileError as exc:
            log.warning("perfil descartado: %s", exc)
    if path.is_file():  # ilegível ou inválido: guarda uma cópia antes de recomeçar o perfil
        backup = path.with_name(path.stem + ".corrompido.json")
        try:
            path.replace(backup)
            log.warning("perfil ilegível guardado em %s", backup)
        except OSError:
            log.error("não foi possível guardar a cópia do perfil ilegível %s", path)
    profile = Profile()
    import_legacy(profile)
    return profile


def save_profile(profile: Profile) -> bool:
    """Grava de forma atômica (arquivo temporário + troca). False se a pasta não aceitar."""
    path = profile_path()
    temp = path.with_suffix(".tmp")
    try:
        temp.write_text(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
        return True
    except OSError as exc:
        log.error("não foi possível gravar o perfil em %s (%s)", path, exc)
        return False
