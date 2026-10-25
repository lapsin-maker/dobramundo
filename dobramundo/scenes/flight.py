"""Voo: a fase em si, com HUD, pausas (supervisor e automática) e trilha por estágio."""

from __future__ import annotations

import math
from typing import List, Optional

import pygame

from .. import config as C
from ..content import texts
from ..content.biomes import BIOMES
from ..content.items import WASTE_TYPES
from ..content.planes import load_maneuvers
from ..content.progress import PART_BY_KEY, STAR_THRESHOLDS, parts_ok
from ..game.run import FlightRun
from ..ui import theme as T
from ..ui.widgets import row, star
from ..util import lerp_color
from .base import Scene

RESUME_COUNTDOWN = 3.0
_maneuvers = None


def maneuvers():
    global _maneuvers
    if _maneuvers is None:
        _maneuvers = load_maneuvers()
    return _maneuvers


class Banner:
    def __init__(self, title: str, subtitle: str = "", color=T.SUN, ttl: float = 2.6, stars: int = 0) -> None:
        self.title, self.subtitle, self.color, self.ttl, self.total = title, subtitle, color, ttl, ttl
        self.stars = stars  # estrelas desenhadas antes do título


class FlightScene(Scene):
    idle_warm_up = False

    def __init__(self, app, biome_key: str) -> None:
        super().__init__(app)
        self.biome = BIOMES[biome_key]
        p = app.profile
        self.run = FlightRun(self.biome, p.modo, p.pecas, maneuvers())
        self.look = app.plane_look()
        self.paused = False
        self.auto_paused = False
        self.countdown = 0.0
        self.banners: List[Banner] = []
        self.flash = 0.0
        self.cam_surface: Optional[pygame.Surface] = None
        self.cam_bytes: Optional[bytes] = None
        self.music = self.stage_music(0)
        self.started = False

    def stage_music(self, stage: int) -> str:
        return f"musica_{self.biome.music}_{stage + 1}"

    def enter(self) -> None:
        """Também é chamado ao voltar da recalibração: a trilha segue o estágio atual e a
        decolagem (som e aviso da cidade) só acontece na primeira entrada."""
        self.music = self.stage_music(self.run.stage)
        super().enter()
        self.app.view.set_biome(self.biome)
        self.app.input.resync_keys()
        if not self.started:
            self.started = True
            self.app.audio.play("sfx_decolagem")
            self.banners.append(Banner(f"{self.biome.city} — {self.biome.name}", texts.STAGE_MESSAGES[0], T.WHITE, 3.2))

    # ------------------------------------------------------------- pausa
    def build(self) -> None:
        if not self.paused:
            self.menu.set_buttons([])
            return
        rects = row(pygame.Rect(C.WIDTH // 2 - 390, 400, 780, 76), 3)
        buttons = [
            self.button(rects[0], texts.UI["continuar"], self.resume),
            self.button(rects[1], "Recalibrar", self.recalibrate, enabled=self.app.input.uses_body),
            self.button(rects[2], "Voltar à vila", self.quit_to_village),
        ]
        self.menu.set_buttons(buttons, keep_focus=False)

    def pause(self, auto: bool = False) -> None:
        if self.paused or self.run.finished:
            return
        self.paused = True
        self.auto_paused = auto
        self.countdown = 0.0
        self.app.input.clear_keys()
        self.build()

    def resume(self) -> None:
        self.paused = False
        self.auto_paused = False
        self.countdown = 0.0
        self.app.input.resync_keys()
        self.build()

    def recalibrate(self) -> None:
        self.goto("calibracao", return_to=self)

    def quit_to_village(self) -> None:
        self.goto("vila")

    def back(self) -> None:
        if self.paused:
            self.resume()
        else:
            self.pause()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.back()
                return
            if event.key == pygame.K_F3:
                self.app.view.show_hitboxes = not self.app.view.show_hitboxes
                return
            if event.key == pygame.K_F2:  # modo de demonstração do supervisor
                self.run.invincible = not self.run.invincible
                return
            if self.paused and event.key == pygame.K_c:
                self.quit_to_village()
                return
        if self.paused and self.menu.handle_event(event):
            self.app.audio.play("sfx_selecao")

    # ------------------------------------------------------------ quadro
    def update(self, dt: float) -> None:
        self.time += dt
        hub = self.app.input
        if not self.paused and hub.out_of_area():
            self.pause(auto=True)
        if self.paused:
            if self.auto_paused and hub.back_in_area():
                self.countdown += dt  # retomada automática com contagem
                if self.countdown >= RESUME_COUNTDOWN:
                    self.resume()
            else:
                self.countdown = 0.0
            if self.menu.update(dt, hub.pointer(), self.app.options.permanencia):
                self.app.audio.play("sfx_selecao")
            return
        ix, iy = hub.flight_axes()
        self.run.update(dt, ix, iy)
        self.handle_run_events()
        for banner in self.banners:
            banner.ttl -= dt
        self.banners = [b for b in self.banners if b.ttl > 0]
        self.flash = max(0.0, self.flash - dt)
        if self.run.finished:
            self.goto("resultado", self.run)

    def handle_run_events(self) -> None:
        audio = self.app.audio
        for name, data in self.run.take_events():
            if name == "collect":
                audio.collect(data)
            elif name == "powerup":
                audio.play("sfx_powerup")
            elif name == "shield_end":
                audio.play("sfx_escudo_fim")
            elif name == "hit":
                audio.play("sfx_colisao")
            elif name == "stage":
                audio.play("sfx_estagio")
                audio.music(self.stage_music(int(data)))
                self.banners.append(Banner(texts.STAGE_NAMES[int(data)], texts.STAGE_MESSAGES[int(data)], T.SUN, 3.4))
            elif name == "star":
                audio.play("sfx_estrela")
                self.flash = 0.6
                if data == 2 and not parts_ok(self.biome.required_parts, self.run.parts):
                    need = ", ".join(PART_BY_KEY[k].name for k in self.biome.required_parts)
                    self.banners.append(Banner("2 estrelas!", f"Para a 3ª estrela aqui, instale: {need}", T.SUN, 3.6))
                else:
                    self.banners.append(Banner(f"Estrela {data}!", "", T.SUN, 2.2, stars=int(data)))
            elif name == "complete":
                audio.play("sfx_fim_fase")
                self.banners.append(Banner(f"{self.biome.city} solarpunk!", "A cidade se transformou.", T.SUN, 3.0))
            elif name == "game_over":
                audio.play("sfx_game_over")

    def draw(self, screen: pygame.Surface) -> None:
        view = self.app.view
        view.draw_run(screen, self.run, self.look)
        if self.run.hit_flash_timer > 0:
            T.veil(screen, (170, 30, 20), int(110 * self.run.hit_flash_timer / C.HIT_FLASH_S) // 10 * 10)
        self.draw_hud(screen)
        self.draw_banners(screen)
        self.draw_camera(screen)
        if self.paused:
            self.draw_pause(screen)

    # --------------------------------------------------------------- HUD
    def draw_hud(self, screen: pygame.Surface) -> None:
        run = self.run
        text = self.text
        accent = self.biome.stages[run.stage].accent
        box = pygame.Rect(10, 10, 560, 96)
        T.panel(screen, box, T.PAPER, T.NAVY, 235, 16, 3)
        text.blit(screen, f"{self.biome.city}: {texts.STAGE_NAMES[run.stage]}", (26, 18), T.SIZES["body"], T.NAVY, True)
        text.blit(screen, f"{int(run.restoration)}%", (box.right - 16, 18), T.SIZES["body"], T.INK, True, "topright")
        bar = pygame.Rect(26, 48, box.width - 32, 16)
        pygame.draw.rect(screen, (210, 202, 186), bar, border_radius=8)
        fill = bar.copy()
        fill.width = int(bar.width * run.restoration / 100.0)
        pygame.draw.rect(screen, lerp_color(accent, T.GREEN, 0.3), fill, border_radius=8)
        for limit in STAR_THRESHOLDS:
            x = bar.left + int(bar.width * limit / 100.0) - (8 if limit >= 100 else 0)
            star(
                screen, (x, bar.centery), 12, run.restoration >= limit - 1e-6 and (limit < 100 or run.stars >= 3), T.SUN
            )
        # recursos do voo
        x = 26
        for waste in WASTE_TYPES:
            pygame.draw.circle(screen, waste.color, (x + 9, 86), 9)
            pygame.draw.circle(screen, T.INK, (x + 9, 86), 9, 2)
            rect = text.blit(screen, str(run.resources.get(waste.key, 0)), (x + 22, 75), T.SIZES["body"], T.INK, True)
            x = rect.right + 16
        mode = "Normal" if run.mode == "normal" else f"Difícil  combo x{run.combo}"
        text.blit(
            screen, f"{mode}   {run.score} pts", (box.right - 16, 75), T.SIZES["small"], T.MUTED, True, "topright"
        )
        # vidas e power-ups
        status = pygame.Rect(C.WIDTH - 250, 10, 240, 96)
        T.panel(screen, status, T.PAPER, T.NAVY, 235, 16, 3)
        text.blit(screen, texts.UI["vidas"], (status.left + 16, 18), T.SIZES["body"], T.NAVY, True)
        for i in range(C.MAX_LIVES):
            self.draw_life(screen, (status.left + 104 + i * 42, 30), i < run.lives)
        timers = []
        if run.shield_timer > 0:
            timers.append(f"Escudo {math.ceil(run.shield_timer)}s")
        if run.magnet_timer > 0:
            timers.append(f"Ímã {math.ceil(run.magnet_timer)}s")
        if run.invincible:
            timers.append("demonstração")
        text.blit(
            screen,
            "   ".join(timers) or "P: pausa",
            (status.left + 16, 66),
            T.SIZES["body"],
            T.TEAL if timers else T.MUTED,
            True,
        )

    @staticmethod
    def draw_life(screen: pygame.Surface, center, alive: bool) -> None:
        """Vida = aviãozinho de papel."""
        x, y = center
        color = T.WHITE if alive else (190, 184, 170)
        wing = [(x - 16, y + 8), (x + 16, y - 10), (x - 2, y + 12)]
        pygame.draw.polygon(screen, color, wing)
        pygame.draw.polygon(screen, T.NAVY if alive else T.LOCKED, wing, 2)
        pygame.draw.line(screen, T.NAVY if alive else T.LOCKED, (x - 2, y + 12), (x + 16, y - 10), 2)

    def draw_banners(self, screen: pygame.Surface) -> None:
        if self.flash > 0:
            T.veil(screen, (255, 236, 150), int(80 * self.flash / 0.6) // 10 * 10)
        if not self.banners:
            return
        banner = self.banners[-1]
        fade = min(1.0, banner.ttl / 0.4, (banner.total - banner.ttl) / 0.3 + 0.2)
        title = self.text.render(banner.title, T.SIZES["title"], T.NAVY, True)
        icons = banner.stars * 34
        width = max(title.get_width() + icons, self.text.font(T.SIZES["body"]).size(banner.subtitle)[0]) + 60
        rect = pygame.Rect(0, 0, width, 92 if banner.subtitle else 60)
        rect.center = (C.WIDTH // 2, 168)
        T.panel(screen, rect, T.PAPER, T.ORANGE, int(235 * fade), 18, 3)
        left = rect.centerx - (title.get_width() + icons) // 2
        for i in range(banner.stars):
            star(screen, (left + 14 + i * 34, rect.top + 30), 14, True)
        screen.blit(title, (left + icons, rect.top + 10))
        if banner.subtitle:
            self.text.blit(
                screen, banner.subtitle, (rect.centerx, rect.top + 56), T.SIZES["body"], T.INK, anchor="midtop"
            )

    def draw_camera(self, screen: pygame.Surface) -> None:
        """Miniatura para o supervisor e avisos de calibração ou de câmera."""
        body = self.app.input.body
        if body is None:
            return
        if body.error:
            self.text.blit(
                screen,
                f"Câmera indisponível ({body.error}): use o teclado",
                (C.WIDTH // 2, C.HEIGHT - 30),
                T.SIZES["small"],
                T.WHITE,
                True,
                "center",
            )
            return
        if body.preview is not None:
            if self.cam_bytes is not body.preview:  # só converte quando chega quadro novo
                self.cam_surface = pygame.image.frombytes(body.preview, (160, 120), "RGB")
                self.cam_bytes = body.preview
            rect = self.cam_surface.get_rect(bottomleft=(12, C.HEIGHT - 12))
            screen.blit(self.cam_surface, rect)
            pygame.draw.rect(screen, T.WHITE if body.visible else T.RED, rect, 3)

    def draw_pause(self, screen: pygame.Surface) -> None:
        T.veil(screen, (10, 18, 40), 170)
        card = pygame.Rect(C.WIDTH // 2 - 420, 150, 840, 350)
        T.panel(screen, card, T.PAPER, T.NAVY, 250, 22, 4)
        if self.auto_paused:
            title = "Pausa automática"
            if self.app.input.back_in_area():
                left = max(0, math.ceil(RESUME_COUNTDOWN - self.countdown))
                sub = f"Você voltou! Retomando em {left}..."
            else:
                sub = "Volte para a área da câmera para continuar o voo."
        else:
            title = texts.UI["pausado"]
            sub = "O voo está pausado. Respire, alongue-se e continue quando quiser."
        self.text.blit(screen, title, (card.centerx, card.top + 40), T.SIZES["hero"], T.NAVY, True, "midtop")
        self.text.paragraph(
            screen, sub, pygame.Rect(card.left + 60, card.top + 120, card.width - 120, 80), T.SIZES["label"], T.INK
        )
        tip = texts.TIPS[int(self.time // 6) % len(texts.TIPS)]
        self.text.blit(screen, tip, (card.centerx, card.top + 206), T.SIZES["body"], T.MUTED, anchor="midtop")
        self.draw_menu(screen)
