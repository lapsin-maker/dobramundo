"""Aplicação: janela, laço principal, cenas e serviços compartilhados.

A imagem é desenhada numa tela lógica de 1100x650 e o SDL a escala para a
janela ou para a tela cheia (pygame.SCALED). Para projeção no chão, na mesa ou
por trás de uma parede, a imagem pode ser espelhada e/ou girada 180°; o mouse
é convertido de volta para as coordenadas lógicas.
"""

from __future__ import annotations

import math
import os
import random
from typing import List, Optional

import pygame

from . import APP_NAME
from . import config as C
from .audio import Audio
from .content.biomes import BIOME_ORDER, BIOMES
from .content.progress import plane_stats
from .engine.assets import shared_assets
from .engine.world_view import PlaneLook, WorldView
from .game.world import World
from .input.hub import InputHub
from .persistence import Profile, load_profile, save_profile
from .ui.theme import Text


class App:
    def __init__(self, audio: bool = True, profile: Optional[Profile] = None) -> None:
        pygame.init()
        pygame.display.set_caption(APP_NAME)
        self.profile = profile or load_profile()
        self.display = self.open_window()
        self.canvas = pygame.Surface((C.WIDTH, C.HEIGHT)).convert()
        self.assets = shared_assets()
        icon = self.assets.sprite("ui", "icone")
        if icon is not None:
            pygame.display.set_icon(icon)
        self.clock = pygame.time.Clock()
        self.text = Text()
        self.view = WorldView(self.assets)
        self.audio = Audio(audio)
        self.input = InputHub()
        self.running = True
        self.smooth_dt = 1.0 / C.FPS
        self.frame = 0
        self.scene = None
        self.next_scene = None
        self.backdrop_world: Optional[World] = None
        self.backdrop_time = 0.0
        self.apply_options()
        if self.profile.opcoes.tela_cheia:
            self.toggle_fullscreen()

    @staticmethod
    def open_window() -> pygame.Surface:
        """Janela escalável (SDL ajusta a tela lógica à janela ou à tela cheia)."""
        current = pygame.display.get_surface()
        if current is not None and current.get_size() == (C.WIDTH, C.HEIGHT):
            return current  # testes e self-test reaproveitam a janela
        headless = os.environ.get("SDL_VIDEODRIVER") == "dummy"
        return pygame.display.set_mode((C.WIDTH, C.HEIGHT), 0 if headless else pygame.SCALED)

    # ---------------------------------------------------------- serviços
    @property
    def options(self):
        return self.profile.opcoes

    def save(self) -> None:
        save_profile(self.profile)

    def apply_options(self) -> None:
        self.audio.apply(self.options)
        self.view.high_contrast = self.options.alto_contraste
        stats = plane_stats(self.profile.pecas)
        if self.profile.controle != self.input.segment_key:
            self.input.set_segment(self.profile.controle, self.options.sensibilidade, stats.dead_zone)
        else:
            self.input.configure(self.options.sensibilidade, stats.dead_zone)

    def plane_look(self) -> PlaneLook:
        p = self.profile
        return PlaneLook(p.aviao, p.plane_color(p.aviao), p.plane_pattern(p.aviao), p.piloto)

    def toggle_fullscreen(self) -> None:
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

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
        world.advance(dt, 90.0 * dt)
        self.backdrop_time += dt
        self.view.mode = self.profile.modo
        self.view.background(screen, world, math.sin(self.backdrop_time * 0.2) * 60.0)

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

    # ------------------------------------------------------------ entrada
    def to_logical(self, pos) -> tuple:
        x, y = pos
        if self.options.espelhar:
            x = C.WIDTH - 1 - x
        if self.options.girar:
            x, y = C.WIDTH - 1 - x, C.HEIGHT - 1 - y
        return int(x), int(y)

    def events(self) -> List[pygame.event.Event]:
        out = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                event = pygame.event.Event(event.type, {**event.dict, "pos": self.to_logical(event.pos)})
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                self.options.tela_cheia = not self.options.tela_cheia
                self.toggle_fullscreen()
                continue
            self.input.handle_event(event)
            out.append(event)
        return out

    # ------------------------------------------------------------- quadro
    def present(self) -> None:
        frame = self.canvas
        if self.options.espelhar or self.options.girar:
            flipped = pygame.transform.flip(frame, self.options.espelhar != self.options.girar, self.options.girar)
            self.display.blit(flipped, (0, 0))
        else:
            self.display.blit(frame, (0, 0))
        pygame.display.flip()

    def step(self, dt: float, events: Optional[List[pygame.event.Event]] = None) -> None:
        """Um quadro: entrada, atualização e desenho da cena atual."""
        self._switch()
        events = self.events() if events is None else events
        self.input.update(dt)
        self.view.update(dt)
        scene = self.scene
        for event in events:
            scene.handle_event(event)
        scene.update(dt)
        scene.draw(self.canvas)
        self.present()
        self.view.step_warm_up(6.0 if scene.idle_warm_up else 1.5)
        self.frame += 1

    def run(self, first_scene, max_frames: Optional[int] = None) -> None:
        self.go(first_scene)
        try:
            while self.running:
                raw = min(self.clock.tick(C.FPS) / 1000.0, C.MAX_DT)
                # O relógio oscila 1–2 ms entre quadros; suavizar evita tremor no cenário.
                self.smooth_dt += (raw - self.smooth_dt) * C.DT_SMOOTHING
                self.step(self.smooth_dt)
                if max_frames is not None and self.frame >= max_frames:
                    self.running = False
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.input.stop_body()
        self.audio.stop()
        self.save()
