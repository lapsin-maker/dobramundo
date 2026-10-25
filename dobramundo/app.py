"""Executável: janela, laço principal, eventos do sistema e projeção.

O jogo em si fica no núcleo (core.py). Aqui ficam só as partes do computador: a
janela escalável (pygame.SCALED desenha a tela lógica de 1100x650 em qualquer
tamanho), o mixer de som, o relógio, a tela cheia e a orientação da imagem para
projeção no chão, na mesa ou na parede (espelhar e girar 90°, 180° ou 270°). O
mouse é convertido de volta para as coordenadas lógicas.
"""

from __future__ import annotations

import os
from typing import Callable, List, Optional

import pygame

from . import APP_NAME
from . import config as C
from .core import GameCore
from .persistence import (
    Profile,
    create_profile_slot,
    list_profile_slots,
    load_active_profile,
    load_profile_with_notice,
    profile_read_blocked,
    save_profile,
    set_active_profile_slot,
)


class App(GameCore):
    def __init__(
        self,
        audio: bool = True,
        profile: Optional[Profile] = None,
        scene_factory: Optional[Callable] = None,
    ) -> None:
        pygame.init()
        pygame.display.set_caption(APP_NAME)
        if audio and not pygame.mixer.get_init():
            try:
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            except pygame.error:
                pass  # sem dispositivo de áudio: o jogo segue em silêncio
        self.display = self.open_window()
        if profile is None:
            selected_profile, self.profile_slot, self.storage_notice = load_active_profile()
        else:
            selected_profile, self.profile_slot, self.storage_notice = profile, "principal", None
        super().__init__(
            selected_profile,
            audio,
            save=self._save_selected_profile,
            canvas=pygame.Surface((C.WIDTH, C.HEIGHT)).convert(),
            scene_factory=scene_factory,
        )
        icon = self.assets.sprite("ui", "icone")
        if icon is not None:
            pygame.display.set_icon(icon)
        self.clock = pygame.time.Clock()
        self.smooth_dt = 1.0 / C.FPS
        self.apply_options()

    def apply_options(self) -> None:
        super().apply_options()
        self._sync_fullscreen()

    def _sync_fullscreen(self) -> None:
        display = pygame.display.get_surface()
        if display is None:
            return
        fullscreen = bool(display.get_flags() & pygame.FULLSCREEN)
        if self.options.tela_cheia != fullscreen:
            self.toggle_fullscreen()

    def _save_selected_profile(self, profile: Profile) -> bool:
        return save_profile(profile, self.profile_slot)

    def list_profiles(self) -> list:
        """Slots locais anônimos disponíveis para esta instalação desktop."""
        return list_profile_slots()

    def dismiss_storage_notice(self) -> None:
        self.storage_notice = None

    def _activate_profile(self, slot_id: str) -> bool:
        profile, notice = load_profile_with_notice(slot_id)
        if profile_read_blocked(slot_id):
            self.storage_notice = notice or "Não consegui ler este piloto. O perfil atual continua aberto."
            return False
        if not set_active_profile_slot(slot_id):
            self.storage_notice = "Não consegui salvar a escolha deste piloto. O perfil atual continua aberto."
            return False
        self.profile_slot = slot_id
        self.profile = profile
        self.storage_notice = notice
        self.save_failed = False
        self.input.clear_keys()
        self.input.mouse_pos = None
        self.apply_options()
        body = self.input.body
        if body is not None:
            body.recalibrate()
            if hasattr(body, "point"):
                body.point = None
        from .core import first_scene

        self.go(first_scene(self))
        return True

    def select_profile(self, slot_id: str) -> bool:
        """Salva o piloto atual antes de abrir outro; falha de escrita cancela a troca."""
        if self.platform != "desktop" or slot_id == self.profile_slot:
            return slot_id == self.profile_slot
        if not any(slot.id == slot_id for slot in self.list_profiles()):
            return False
        self.save()
        if self.save_failed:
            self.storage_notice = "Não foi possível salvar este piloto. A troca foi cancelada."
            return False
        return self._activate_profile(slot_id)

    def create_profile(self) -> bool:
        """Cria um slot anônimo e o abre sem pedir nome ou dado pessoal."""
        if self.platform != "desktop":
            return False
        self.save()
        if self.save_failed:
            self.storage_notice = "Não foi possível salvar este piloto. O novo piloto não foi criado."
            return False
        slot = create_profile_slot()
        if slot is None:
            self.storage_notice = "Não consegui criar outro piloto. Confira o espaço disponível."
            return False
        return self._activate_profile(slot.id)

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
        self.input.note_presented()

    def step(self, dt: float, events: Optional[List[pygame.event.Event]] = None) -> None:
        """Um quadro: entrada, atualização, desenho e apresentação na janela."""
        pending = self.events() if events is None else events
        if not self.running:
            return
        self.advance(dt, pending)
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
