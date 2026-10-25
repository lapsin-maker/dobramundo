"""Cartucho do console T-TEA: o Dobramundo rodando dentro do runtime do console.

O console é dono da janela, do relógio, dos eventos, da câmera e do modelo de
pose; o jogo recebe a cada quadro o passo de tempo, os eventos e o rastreamento
(perfil "body": os 33 pontos do corpo e os pés projetados no chão). Com isso o
cartucho oferece os mesmos segmentos do executável:

- pés sobre o chão interativo: a posição que o console projetou vira a posição
  do avião e do cursor (pisar sobre um botão o escolhe);
- tronco, uma das mãos ou a cabeça: o movimento em relação à postura neutra,
  medido nos pontos da câmera do console (projeção em mesa, parede ou monitor).

Perfil e opções ficam no armazenamento do jogador que o console oferece; com
jogador registrado, as opções de controle acompanham a criança e cada voo vira
um evento da sessão. ESC encerra o jogo e P pausa, como em todo cartucho.
"""

from __future__ import annotations

from typing import Callable, List, Optional

import pygame
from ttea.sdk.api import Game, GameContext, feet_centre

from . import config as C
from .core import GameCore, first_scene
from .input.console import TrackingSource, body_points
from .log import log
from .persistence import Profile, ProfileError
from .scenes.flight import FlightScene
from .ui import theme as T

PROFILE_KEY = "perfil"
PLATFORM_KEYS = (pygame.K_ESCAPE, pygame.K_p, pygame.K_F2)  # o console usa: o jogo não repete
# Opções que acompanham a criança registrada (o terapeuta pode ajustá-las no console).
PLAYER_OPTIONS = (
    "sensibilidade",
    "permanencia",
    "permanencia_editor",
    "controle_posicao",
    "momento_foco",
    "efeitos_fortes",
    "alto_contraste",
    "escala_contraste",
    "reduzir_movimento",
    "silencio",
    "inverter_vertical",
    "inverter_horizontal",
    "centralizar_sozinho",
)


def player_settings(profile: Profile) -> dict:
    values = {name: vars(profile.opcoes)[name] for name in PLAYER_OPTIONS}
    values.update(controle=profile.controle, modo=profile.modo)
    return values


def apply_settings(profile: Profile, values: dict) -> Profile:
    """Configuração do jogador registrado sobre o perfil salvo (validada como o perfil)."""
    data = profile.to_dict()
    for name in PLAYER_OPTIONS:
        if name in values:
            data["opcoes"][name] = values[name]
    for name in ("controle", "modo"):
        if name in values:
            data[name] = values[name]
    try:
        return Profile.from_dict(data)
    except ProfileError:
        return profile


class ConsoleCore(GameCore):
    """O núcleo do jogo com o armazenamento, os registros e o rastreamento do console."""

    platform = "ttea"

    def __init__(
        self,
        profile: Profile,
        context: GameContext,
        source: TrackingSource,
        scene_factory: Optional[Callable] = None,
    ) -> None:
        self.context = context
        self.source = source
        self.session: Optional[int] = None
        super().__init__(profile, audio=True, save=self.store, scene_factory=scene_factory)
        self.input.source_factory = lambda: source
        self.apply_options()

    def floor_setup(self):
        """No console, os pés sempre estão sobre a projeção calibrada pelo próprio console."""
        return self.source.locate_floor, "console"

    def store(self, profile: Profile) -> bool:
        try:
            self.context.storage.write(PROFILE_KEY, profile.to_dict())
            if self.context.records is not None:
                self.context.records.update_configuration(player_settings(profile))
        except Exception:
            log.exception("falha ao gravar dados do jogador no armazenamento T-TEA")
            return False
        return True

    def on_flight(self, summary: dict) -> None:
        """Cada voo terminado vira um evento da sessão do jogador registrado."""
        records = self.context.records
        if records is None:
            return
        try:
            if self.session is None:
                self.session = records.start_session({"jogo": "dobramundo"})
            records.record_event(self.session, summary)
        except Exception:
            log.exception("falha ao registrar resumo de voo no T-TEA")
            self.session = None


def load_profile(context: GameContext) -> Profile:
    """Perfil salvo deste jogador; na primeira vez, já com os pés sobre o chão interativo."""
    try:
        data = context.storage.read(PROFILE_KEY)
    except Exception:
        log.exception("falha ao ler perfil do jogador no armazenamento T-TEA")
        data = None
    profile = None
    if isinstance(data, dict):
        try:
            profile = Profile.from_dict(data)
        except ProfileError:
            log.exception("perfil T-TEA inválido; iniciando perfil local do jogador")
            profile = None
    if profile is None:
        profile = Profile()
        profile.controle = "pes"
        profile.opcoes.superficie = "chao"
    if context.records is not None:
        try:
            profile = apply_settings(profile, context.records.configuration(player_settings(profile)))
        except Exception:
            log.exception("falha ao ler opções do jogador no T-TEA")
    return profile


class Dobramundo(Game):
    def start(self, context: GameContext) -> None:
        self.source = TrackingSource()
        self.core = ConsoleCore(load_profile(context), context, self.source)
        self.core.go(first_scene(self.core))
        self.lost_time = 0.0

    def update(self, context: GameContext) -> None:
        tracking = context.tracking
        usable = not (tracking.missing or tracking.stale)
        raw = tracking.observation.landmarks.get("body") if usable else None
        points = None if raw is None else [(p.x, p.y, p.visibility) for p in raw]
        self.source.push(body_points(points), feet_centre(tracking))
        events = [e for e in context.events if not (e.type == pygame.KEYDOWN and e.key in PLATFORM_KEYS)]
        events = self.to_canvas(context, events)
        for event in events:
            self.core.input.handle_event(event)
        self.core.advance(min(context.dt, C.MAX_DT), events)
        if not self.core.running:
            context.request_stop()

    def to_canvas(self, context: GameContext, events: List[pygame.event.Event]) -> List[pygame.event.Event]:
        """Mouse na superfície do console -> tela lógica do jogo (quando os tamanhos diferem)."""
        size = context.surface.get_size()
        if size == (C.WIDTH, C.HEIGHT):
            return events
        sx, sy = C.WIDTH / max(1, size[0]), C.HEIGHT / max(1, size[1])
        for event in events:
            if "pos" in event.dict:
                event.pos = (int(event.pos[0] * sx), int(event.pos[1] * sy))
        return events

    def draw(self, context: GameContext) -> None:
        surface = context.surface
        canvas = self.core.canvas
        if surface.get_size() == canvas.get_size():
            surface.blit(canvas, (0, 0))
        else:
            surface.blit(pygame.transform.smoothscale(canvas, surface.get_size()), (0, 0))
        if context.pause_reason == "tracking_loss":
            self.draw_lost(surface)

    def draw_lost(self, surface: pygame.Surface) -> None:
        """O console pausou por perda do rastreamento: o jogo pede para a criança voltar."""
        T.veil(surface, (10, 18, 40), 150)
        w, h = surface.get_size()
        card = pygame.Rect(0, 0, min(w - 40, 760), 150)
        card.center = (w // 2, h // 2)
        T.panel(surface, card, T.PAPER, T.NAVY, 250, 22, 4)
        text = self.core.text
        text.blit(
            surface, "Volte para a área do jogo", (card.centerx, card.top + 30), T.SIZES["hero"], T.NAVY, True, "midtop"
        )
        text.blit(
            surface,
            "O voo continua quando a câmera encontrar você.",
            (card.centerx, card.top + 96),
            T.SIZES["label"],
            T.INK,
            False,
            "midtop",
        )

    def pause(self, context: GameContext) -> None:
        self.core.audio.pause_music()

    def resume(self, context: GameContext) -> None:
        """De volta depois da pausa do console: no voo, a contagem de retomada do jogo."""
        self.core.audio.resume_music()
        scene = self.core.scene
        if isinstance(scene, FlightScene) and not scene.paused:
            scene.pause(auto=True)

    def stop(self, context: GameContext) -> dict:
        self.core.shutdown()
        profile = self.core.profile
        result = {"voos": profile.voos, "estrelas": profile.total_stars()}
        if profile.historico:
            result.update(profile.historico[-1])
        return result
