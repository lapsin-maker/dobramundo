"""Modelo validado e migrações de perfis, sem operações de disco."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List

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
from .content.progress import MAX_PART_LEVEL, PART_KEYS, STAR_THRESHOLDS, VILLAGE_KEYS

SCHEMA_VERSION = 2
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
    transformacao_cidades: Dict[str, float] = field(default_factory=dict)
    apoio_escolhido: bool = False
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
        self.versao = SCHEMA_VERSION
        self.transformacao_cidades = {
            b: min(100.0, max(0.0, float(v)))
            for b, v in self.transformacao_cidades.items()
            if b in BIOME_ORDER and isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
        }
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
        data = migrate_profile(data)
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
    if not isinstance(points, (list, tuple)):
        return []
    try:
        result = [[float(p[0]), float(p[1])] for p in points]
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
        elif isinstance(default, (int, float)) and isinstance(value, (str, int, float)) and not isinstance(value, bool):
            setattr(target, name, type(default)(value))
        elif isinstance(default, type(value)):
            setattr(target, name, value)
    except (TypeError, ValueError):
        pass


class FutureProfileError(ProfileError):
    """Versão posterior: o arquivo deve permanecer intacto e somente para leitura."""


def _legacy_city_progress(data: dict) -> Dict[str, float]:
    """Recover recorded progress; stars provide only their proven lower bound."""
    progress: Dict[str, float] = {}
    stars = data.get("estrelas", {})
    if isinstance(stars, dict):
        for biome in BIOME_ORDER:
            count = stars.get(biome)
            if type(count) is int and 1 <= count <= 3:
                progress[biome] = STAR_THRESHOLDS[count - 1]
    history = data.get("historico", [])
    if isinstance(history, (list, tuple)):
        for entry in history:
            if not isinstance(entry, dict):
                continue
            biome, value = entry.get("fase"), entry.get("transformacao")
            if (
                biome in BIOME_ORDER
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
            ):
                progress[biome] = max(progress.get(biome, 0.0), min(100.0, max(0.0, float(value))))
    return progress


def migrate_profile(data: dict) -> dict:
    """Migra cópia do documento antigo; nunca reinterpreta uma versão futura."""
    version = data.get("versao", 1)
    if type(version) is not int or version < 1:
        raise ProfileError("versão de perfil inválida")
    if version > SCHEMA_VERSION:
        raise FutureProfileError("este piloto foi salvo por uma versão mais nova do Dobramundo")
    result = dict(data)
    if version == 1:
        result.setdefault("transformacao_cidades", _legacy_city_progress(result))
        # Em perfis anteriores, conservar a escolha de assistência já configurada.
        result.setdefault("apoio_escolhido", int(result.get("voos", 0) or 0) > 0)
        result["versao"] = 2
    return result
