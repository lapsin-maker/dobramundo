"""Som: trilha própria por estágio (com troca suave) e efeitos de coleta e colisão.

O volume é regulável (geral, música, efeitos) e há opção de silêncio, que
reduz a carga sensorial em casos de hipersensibilidade auditiva (GDD, seção 7).
Sem dispositivo de áudio (ou em testes), tudo vira operação vazia.
Arquivos em assets/audio, gerados por tools/make_audio.py.
"""

from __future__ import annotations

from typing import Dict, Optional

import pygame

from .paths import find_asset_file

MUSIC_FADE_MS = 1600
COLLECT_SFX = {
    "papel": "sfx_coleta_papel",
    "plastico": "sfx_coleta_plastico",
    "metal": "sfx_coleta_metal",
    "vidro": "sfx_coleta_vidro",
}


class Audio:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = False
        self.sounds: Dict[str, Optional[pygame.mixer.Sound]] = {}
        self.master = 0.8
        self.music_volume = 0.6
        self.sfx_volume = 0.8
        self.muted = False
        self.current: Optional[str] = None
        self.channels = []
        self.active = 0
        if not enabled:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
            pygame.mixer.set_num_channels(16)
            pygame.mixer.set_reserved(2)
            self.channels = [pygame.mixer.Channel(0), pygame.mixer.Channel(1)]
            self.enabled = True
        except pygame.error:
            self.enabled = False

    def apply(self, options) -> None:
        self.master = options.volume_geral
        self.music_volume = options.volume_musica
        self.sfx_volume = options.volume_efeitos
        self.muted = options.silencio
        if self.enabled:
            volume = self.effective_music()
            for channel in self.channels:
                channel.set_volume(volume)

    def effective_music(self) -> float:
        return 0.0 if self.muted else self.master * self.music_volume

    def sound(self, name: str) -> Optional[pygame.mixer.Sound]:
        if name not in self.sounds:
            path = find_asset_file("audio", f"{name}.ogg") or find_asset_file("audio", f"{name}.wav")
            sound = None
            if path is not None and self.enabled:
                try:
                    sound = pygame.mixer.Sound(str(path))
                except pygame.error:
                    sound = None
            self.sounds[name] = sound
        return self.sounds[name]

    def play(self, name: str, volume: float = 1.0) -> None:
        if not self.enabled or self.muted:
            return
        sound = self.sound(name)
        if sound is None:
            return
        sound.set_volume(min(1.0, self.master * self.sfx_volume * volume))
        sound.play()

    def collect(self, waste: str) -> None:
        self.play(COLLECT_SFX.get(waste, "sfx_coleta_papel"), 0.8)

    def music(self, name: Optional[str]) -> None:
        """Troca a trilha com fade cruzado entre dois canais reservados."""
        if not self.enabled or name == self.current:
            return
        self.current = name
        old = self.channels[self.active]
        old.fadeout(MUSIC_FADE_MS)
        if name is None:
            return
        sound = self.sound(name)
        if sound is None:
            return
        self.active = 1 - self.active
        channel = self.channels[self.active]
        channel.set_volume(self.effective_music())
        channel.play(sound, loops=-1, fade_ms=MUSIC_FADE_MS)

    def stop(self) -> None:
        if self.enabled:
            for channel in self.channels:
                channel.stop()
        self.current = None
