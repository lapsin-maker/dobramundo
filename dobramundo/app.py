"""Executável: janela, laço principal, eventos do sistema e projeção.

O jogo em si fica no núcleo (core.py). Aqui ficam só as partes do computador: a
janela escalável (pygame.SCALED desenha a tela lógica de 1100x650 em qualquer
tamanho), o mixer de som, o relógio, a tela cheia e a orientação da imagem para
projeção no chão, na mesa ou na parede (espelhar e girar 90°, 180° ou 270°). O
mouse é convertido de volta para as coordenadas lógicas.
"""

from __future__ import annotations

import os
from typing import List, Optional

import pygame

from . import APP_NAME
from . import config as C
from .core import GameCore
from .persistence import Profile, load_profile


class App(GameCore):
    def __init__(self, audio: bool = True, profile: Optional[Profile] = None) -> None:
        pygame.init()
        pygame.display.set_caption(APP_NAME)
        if audio and not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            except pygame.error:
                pass  # sem dispositivo de áudio: o jogo segue em silêncio
        self.display = self.open_window()
        super().__init__(profile or load_profile(), audio, canvas=pygame.Surface((C.WIDTH, C.HEIGHT)).convert())
        icon = self.assets.sprite("ui", "icone")
        if icon is not None:
            pygame.display.set_icon(icon)
        self.clock = pygame.time.Clock()
        self.smooth_dt = 1.0 / C.FPS
        self.apply_options()
        if self.profile.opcoes.tela_cheia:
            self.toggle_fullscreen()

    def floor_setup(self):
        """Pés sobre a projeção só com a superfície "chão" e os 4 cantos calibrados."""
        o = self.options
        if o.superficie != "chao":
            return None, None
        from .input.floor import FloorMap

        floor = FloorMap.maybe(o.chao_pontos)
        if floor is None:
            return None, None
        token = (tuple(map(tuple, o.chao_pontos)), o.rotacao, o.espelhar, o.alvo_frente)
        return floor.locator(o.rotacao, o.espelhar, o.alvo_frente), token

    @staticmethod
    def open_window() -> pygame.Surface:
        """Janela escalável (SDL ajusta a tela lógica à janela ou à tela cheia)."""
        current = pygame.display.get_surface()
        if current is not None and current.get_size() == (C.WIDTH, C.HEIGHT):
            return current  # testes e self-test reaproveitam a janela
        headless = os.environ.get("SDL_VIDEODRIVER") == "dummy"
        return pygame.display.set_mode((C.WIDTH, C.HEIGHT), 0 if headless else pygame.SCALED)

    def toggle_fullscreen(self) -> None:
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass

    # ------------------------------------------------------------ entrada
    def to_logical(self, pos) -> tuple:
        """Posição na janela -> tela lógica, desfazendo espelho e rotação da projeção."""
        from .engine.orientation import screen_to_game

        # centro do pixel, para que espelhar e girar levem cada pixel exatamente a outro
        x, y = screen_to_game(
            (pos[0] + 0.5) / C.WIDTH, (pos[1] + 0.5) / C.HEIGHT, self.options.rotacao, self.options.espelhar
        )
        return int(min(C.WIDTH - 1, max(0, x * C.WIDTH))), int(min(C.HEIGHT - 1, max(0, y * C.HEIGHT)))

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
        from .engine.orientation import orient

        self.display.blit(orient(self.canvas, self.options.rotacao, self.options.espelhar), (0, 0))
        pygame.display.flip()

    def step(self, dt: float, events: Optional[List[pygame.event.Event]] = None) -> None:
        """Um quadro: entrada, atualização, desenho e apresentação na janela."""
        self.advance(dt, self.events() if events is None else events)
        self.present()

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
