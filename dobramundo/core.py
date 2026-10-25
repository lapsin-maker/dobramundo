"""Núcleo do jogo, sem plataforma: cenas, perfil, som, desenho e entrada.

Não abre janela, não lê eventos do sistema nem controla o relógio: quem faz isso
é a plataforma. Há duas:

- o executável (app.py): janela própria, webcam com MediaPipe, teclado e mouse;
- o console T-TEA (cartridge.py): o console desenha, entrega os eventos e o
  rastreamento do corpo e cuida da pausa.

A cada quadro a plataforma entrega o passo de tempo e os eventos; o núcleo
desenha a cena atual em ``canvas`` (tela lógica de 1100x650).
"""

from __future__ import annotations

import math
import random
import time
from typing import Callable, List, Optional

import pygame

from . import config as C
from .audio import Audio
from .content.biomes import BIOME_ORDER, BIOMES
from .engine.assets import display_format, shared_assets
from .engine.world_view import PlaneLook, WorldView
from .game.world import World
from .input.hub import InputHub
from .persistence import Profile, save_profile
from .ui.theme import Text


def first_scene(app):
    """Aviso -> calibração -> treino de permanência -> piloto -> vila na primeira vez."""
    from .scenes import make_scene

    scene = make_scene(app, "vila")
    if not app.profile.piloto_montado:  # a primeira coisa: a criança monta o personagem da história
        pilot = make_scene(app, "piloto", first_time=True, return_to=scene)
        scene = make_scene(app, "dwell_treino", next_scene=pilot, return_to=pilot)
    if app.input.uses_body:
        scene = make_scene(app, "calibracao", return_to=scene)
    if not app.profile.consentimento:
        scene = make_scene(app, "aviso", scene)
    return scene


class GameCore:
    platform = "desktop"  # "ttea" no console: as cenas escondem o que é só do executável

    def __init__(
        self,
        profile: Profile,
        audio: bool = True,
        save: Optional[Callable[[Profile], bool]] = None,
        canvas: Optional[pygame.Surface] = None,
    ) -> None:
        self.profile = profile
        self.canvas = canvas if canvas is not None else display_format(pygame.Surface((C.WIDTH, C.HEIGHT)))
        self.assets = shared_assets()
        self.text = Text()
        self.view = WorldView(self.assets)
        self.audio = Audio(audio)
        self.input = InputHub()
        self.writer = save or save_profile
        self.running = True  # False: a plataforma encerra o jogo (sair na vila ou no aviso)
        self.save_failed = False
        self.frame = 0
        self.scene = None
        self.next_scene = None
        self.backdrop_world: Optional[World] = None
        self.backdrop_time = 0.0

    # ---------------------------------------------------------- serviços
    @property
    def options(self):
        return self.profile.opcoes

    def save(self) -> None:
        """Grava o perfil; se não der, a vila avisa (o jogo segue)."""
        self.save_failed = not self.writer(self.profile)

    def apply_options(self) -> None:
        self.audio.apply(self.options)
        self.view.high_contrast = self.options.alto_contraste
        self.view.contrast_scale = self.options.escala_contraste
        self.view.reduce_motion = self.options.reduzir_movimento
        o = self.options
        self.input.position_control = o.controle_posicao
        self.input.auto_center = o.centralizar_sozinho
        self.input.invert_x = o.inverter_horizontal
        self.input.set_floor(*self.floor_setup())
        if self.profile.controle != self.input.segment_key:
            self.input.set_segment(self.profile.controle, o.sensibilidade, 1.0, o.inverter_vertical)
        else:
            self.input.configure(o.sensibilidade, 1.0, o.inverter_vertical, o.controle_posicao)

    def floor_setup(self):
        """(localizador dos pés na imagem do jogo, token da calibração); None: sem chão calibrado."""
        return None, None

    def plane_look(self) -> PlaneLook:
        p = self.profile
        return PlaneLook(p.aviao, p.plane_color(p.aviao), p.plane_pattern(p.aviao), p.piloto)

    def toggle_fullscreen(self) -> None:
        """Só o executável tem janela própria; no console não faz nada."""

    def on_flight(self, summary: dict) -> None:
        """Voo terminado (resumo do histórico); o console o registra na sessão do jogador."""

    def backdrop(
        self, screen: pygame.Surface, dt: float, biome_key: Optional[str] = None, restoration: Optional[float] = None
    ) -> None:
        """Cenário em movimento lento atrás dos menus."""
        key = biome_key or BIOME_ORDER[0]
        world = self.backdrop_world
        if world is None or world.biome.key != key:
            world = World(BIOMES[key], "normal", random.Random(7))
            world.entities.clear()
            world.spawn_pattern = lambda z: None  # type: ignore[assignment]
            self.backdrop_world = world
        if restoration is not None and abs(world.restoration - restoration) > 0.5:
            world.set_restoration(restoration)
        motion_dt = 0.0 if self.options.reduzir_movimento else dt
        world.advance(motion_dt, 90.0 * motion_dt)
        self.backdrop_time += motion_dt
        self.view.mode = self.profile.modo
        camera = 0.0 if self.options.reduzir_movimento else math.sin(self.backdrop_time * 0.2) * 60.0
        self.view.background(screen, world, camera)

    # ------------------------------------------------------------- cenas
    def go(self, scene) -> None:
        """Troca de cena no fim do quadro (evita trocar no meio de um evento)."""
        self.next_scene = scene

    def _switch(self) -> None:
        if self.next_scene is None:
            return
        old, self.scene, self.next_scene = self.scene, self.next_scene, None
        if old is not None:
            old.leave()
        self.scene.enter()

    # ------------------------------------------------------------- quadro
    def advance(self, dt: float, events: List[pygame.event.Event]) -> None:
        """Um quadro: entrada, atualização e desenho da cena atual em ``canvas``.

        Os eventos já devem ter passado pelo InputHub (a plataforma faz isso).
        """
        frame_started = time.perf_counter()
        self._switch()
        self.input.update(dt)
        self.view.update(dt)
        scene = self.scene
        for event in events:
            scene.handle_event(event)
        scene.update(dt)
        scene.draw(self.canvas)
        self.input.note_rendered()  # idade do snapshot consumido até o canvas pronto
        # Reservar folga para apresentação; não iniciar pré-carga num quadro caro.
        elapsed_ms = (time.perf_counter() - frame_started) * 1000
        spare_ms = max(0.0, 1000 / C.FPS - elapsed_ms - 2.0)
        self.view.step_warm_up(min(6.0 if scene.idle_warm_up else 1.5, spare_ms))
        self.frame += 1

    def shutdown(self) -> None:
        if self.scene is not None:
            self.scene.settle_on_close()
        if self.next_scene is not None and self.next_scene is not self.scene:
            self.next_scene.settle_on_close()
        self.input.stop_camera()
        self.audio.stop()
        self.save()
