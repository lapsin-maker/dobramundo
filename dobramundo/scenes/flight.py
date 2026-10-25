"""Voo: a fase em si, com HUD, pausas (supervisor e automática) e trilha por estágio."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

import pygame

from .. import config as C
from ..content import texts
from ..content.biomes import BIOMES
from ..content.items import WASTE_TYPES
from ..content.planes import load_maneuvers
from ..content.progress import PART_BY_KEY, STAR_THRESHOLDS, parts_ok
from ..engine.sprites import project
from ..game.run import FlightRun
from ..ui import theme as T
from ..ui.widgets import row, star
from ..util import lerp_color
from .base import Scene

RESUME_COUNTDOWN = 3.0
FOCUS_SOUNDS = {"foco": "sfx_desvio_alerta", "foco_ok": "sfx_desvio_ok", "foco_quase": "sfx_desvio_quase"}
ARROW_VECTORS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
_maneuvers = None
_vignettes: Dict[Tuple[Tuple[int, int], bool], pygame.Surface] = {}


def maneuvers():
    global _maneuvers
    if _maneuvers is None:
        _maneuvers = load_maneuvers()
    return _maneuvers


def focus_vignette(size: Tuple[int, int], strong: bool) -> pygame.Surface:
    """Tom azul com bordas mais escuras do momento de foco (feito uma vez por tamanho)."""
    key = (size, strong)
    surf = _vignettes.get(key)
    if surf is None:
        small = pygame.Surface((88, 52), pygame.SRCALPHA)
        w, h = small.get_size()
        base, edge = (46, 120) if strong else (28, 60)
        for y in range(h):
            for x in range(w):
                dx, dy = (x - w / 2) / (w / 2), (y - h / 2) / (h / 2)
                d = min(1.0, (dx * dx + dy * dy) ** 0.5)
                small.set_at((x, y), (18, 44, 96, int(base + (edge - base) * d * d)))
        surf = pygame.transform.smoothscale(small, size)
        _vignettes[key] = surf
    return surf


class Banner:
    def __init__(
        self, title: str, subtitle: str = "", color=T.SUN, ttl: float = 2.6, stars: int = 0, action: str = ""
    ) -> None:
        self.title, self.subtitle, self.color, self.ttl, self.total = title, subtitle, color, ttl, ttl
        self.stars = stars  # estrelas desenhadas antes do título
        self.action = action  # up, down, side, collect; pictograma contextual à lição


class FlightScene(Scene):
    idle_warm_up = False

    def __init__(self, app, biome_key: str) -> None:
        super().__init__(app)
        self.biome = BIOMES[biome_key]
        p = app.profile
        # abertura didática: sempre no Normal; no Difícil, só no primeiro voo da fase
        intro = p.modo == "normal" or p.voos_fase.get(biome_key, 0) == 0
        self.run = FlightRun(self.biome, p.modo, p.pecas, maneuvers(), intro=intro, focus=app.options.momento_foco)
        self.look = app.plane_look()
        self.paused = False
        self.auto_paused = False
        self.countdown = 0.0
        self.banners: List[Banner] = []
        self.flash = 0.0
        self.shake = 0.0
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
        rects = row(pygame.Rect(C.WIDTH // 2 - 390, 500, 780, 70), 3)
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
        ix, iy, target = hub.flight_command()
        if hub.body_ready:
            self.run.record_movement(dt, hub.body.axes())
        self.run.update(dt, ix, iy, target)
        self.handle_run_events()
        for banner in self.banners:
            banner.ttl -= dt
        self.banners = [b for b in self.banners if b.ttl > 0]
        self.flash = max(0.0, self.flash - dt)
        self.shake = max(0.0, self.shake - dt)
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
                if self.app.options.efeitos_fortes and not self.app.options.reduzir_movimento:
                    self.shake = C.HIT_SHAKE_S
            elif name in FOCUS_SOUNDS:
                audio.play(FOCUS_SOUNDS[name])
            elif name == "lesson":
                title, subtitle = texts.LESSONS[str(data)]
                action = {"waste": "collect", "low": "up", "gate": "down", "tower": "side"}.get(str(data), "")
                self.banners.append(Banner(title, subtitle, T.WHITE, 2.6, action=action))
            elif name == "stage":
                audio.play("sfx_estagio")
                audio.music(self.stage_music(int(data)))
                self.banners.append(Banner(texts.STAGE_NAMES[int(data)], texts.STAGE_MESSAGES[int(data)], T.SUN, 3.4))
            elif name == "star":
                audio.play("sfx_estrela")
                self.flash = 0.6 if self.app.options.efeitos_fortes and not self.app.options.reduzir_movimento else 0.0
                if data == 2 and not parts_ok(self.biome.required_parts, self.run.parts):
                    need = ", ".join(PART_BY_KEY[k].name for k in self.biome.required_parts)
                    self.banners.append(
                        Banner("2 estrelas!", f"Para a 3ª estrela aqui, instale: {need}", T.SUN, 3.6, action="star")
                    )
                else:
                    self.banners.append(Banner(f"Estrela {data}!", "", T.SUN, 2.2, stars=int(data)))
            elif name == "mission":
                audio.play("sfx_compra")
                action = {"desviar": "side", "portal": "down", "coletar": "collect", "powerup": "collect"}.get(
                    data.kind, "star"
                )
                self.banners.append(Banner("Meta cumprida!", data.text(data.target), T.SUN, 2.4, action=action))
            elif name == "complete":
                audio.play("sfx_fim_fase")
                self.banners.append(Banner(f"{self.biome.city} solarpunk!", "A cidade se transformou.", T.SUN, 3.0))
            elif name == "game_over":
                audio.play("sfx_game_over")

    def draw(self, screen: pygame.Surface) -> None:
        view = self.app.view
        view.draw_run(screen, self.run, self.look)
        strong = self.app.options.efeitos_fortes and not self.app.options.reduzir_movimento
        if self.shake > 0:
            # tremor só do cenário (o HUD fica parado e legível)
            amount = 9.0 * self.shake / C.HIT_SHAKE_S
            screen.scroll(int(amount * math.sin(self.time * 63.0)), int(amount * 0.5 * math.cos(self.time * 51.0)))
        if self.run.hit_flash_timer > 0 and strong:
            T.veil(screen, (170, 30, 20), int(110 * self.run.hit_flash_timer / C.HIT_FLASH_S) // 10 * 10)
        if self.run.focus.state == "pending":
            screen.blit(focus_vignette(screen.get_size(), strong), (0, 0))
        self.draw_hud(screen)
        self.draw_focus(screen)
        self.draw_banners(screen)
        self.draw_camera(screen)
        if self.paused:
            self.draw_pause(screen)

    # --------------------------------------------------------------- HUD
    def draw_hud(self, screen: pygame.Surface) -> None:
        run = self.run
        text = self.text
        accent = self.biome.stages[run.stage].accent
        box = pygame.Rect(18, 14, 444, 70)
        T.panel(screen, box, T.PAPER, T.NAVY, 238, 16, 2)
        text.blit(
            screen,
            f"{self.biome.city} · {texts.STAGE_NAMES[run.stage]}",
            (32, 19),
            T.SIZES["body"],
            T.NAVY,
            True,
        )
        text.blit(screen, f"{int(run.restoration)}%", (box.right - 14, 19), T.SIZES["body"], T.INK, True, "topright")
        bar = pygame.Rect(32, 52, box.width - 30, 14)
        pygame.draw.rect(screen, (220, 213, 195), bar, border_radius=8)
        fill = bar.copy()
        fill.width = int(bar.width * run.restoration / 100.0)
        pygame.draw.rect(screen, lerp_color(accent, T.GREEN, 0.3), fill, border_radius=8)
        for limit in STAR_THRESHOLDS:
            x = bar.left + int(bar.width * limit / 100.0) - (8 if limit >= 100 else 0)
            star(
                screen, (x, bar.centery), 11, run.restoration >= limit - 1e-6 and (limit < 100 or run.stars >= 3), T.SUN
            )
        self.draw_mission(screen)
        status = pygame.Rect(C.WIDTH - 164, 14, 146, 70)
        T.panel(screen, status, T.PAPER, T.NAVY, 238, 16, 2)
        for i in range(C.MAX_LIVES):
            self.draw_life(screen, (status.left + 32 + i * 41, 48), i < run.lives)
        if run.shield_timer > 0 or run.magnet_timer > 0:
            active = "shield" if run.shield_timer > 0 else "powerup"
            screen.blit(T.icon_surface(active, 30, T.TEAL), (status.left + 56, status.bottom + 4))
            seconds = math.ceil(max(run.shield_timer, run.magnet_timer))
            text.blit(screen, f"{seconds}s", (status.left + 92, status.bottom + 7), T.SIZES["small"], T.TEAL, True)
        elif run.invincible:
            text.blit(
                screen,
                "DEMO",
                status.midbottom + pygame.Vector2(0, 4),
                T.SIZES["small"],
                T.MUTED,
                True,
                "midtop",
            )

    def draw_focus(self, screen: pygame.Surface) -> None:
        """Seta do momento de foco junto do avião, pedido em letras grandes e tempo que resta."""
        focus = self.run.focus
        if focus.state is None:
            return
        player = self.run.player
        sx, sy, _ = project(player.x, player.y, C.PLAYER_Z, self.app.view.cam)
        if focus.state != "pending":
            ok = focus.state == "success"
            self.text.blit(
                screen,
                texts.FOCUS_SUCCESS if ok else texts.FOCUS_MISS,
                (int(sx), int(sy) - 90),
                T.SIZES["title"],
                T.SUN if ok else T.WHITE,
                True,
                "center",
            )
            return
        dx, dy = ARROW_VECTORS[focus.direction]
        pulse = 1.0 if self.app.options.reduzir_movimento else 1.0 + 0.08 * math.sin(self.time * 16.0)
        self.draw_arrow(screen, (sx + dx * 130, sy + dy * 110), (dx, dy), 62 * pulse)
        prompt = texts.FOCUS_PROMPTS[focus.direction]
        width = max(340, self.text.font(T.SIZES["hero"], True).size(prompt)[0] + 60)
        # embaixo, longe do avião e da seta (que podem apontar para cima)
        card = pygame.Rect(C.WIDTH // 2 - width // 2, C.HEIGHT - 124, width, 108)
        T.panel(screen, card, T.NAVY, T.SUN, 225, 18, 3)
        self.text.blit(screen, prompt, (C.WIDTH // 2, card.top + 38), T.SIZES["hero"], T.SUN, True, "center")
        bar = pygame.Rect(C.WIDTH // 2 - 140, card.top + 80, 280, 14)
        pygame.draw.rect(screen, T.NAVY_DARK, bar.inflate(6, 6), border_radius=9)
        fill = bar.copy()
        fill.width = max(1, int(bar.width * focus.progress))
        pygame.draw.rect(screen, T.SUN, fill, border_radius=7)

    @staticmethod
    def draw_arrow(screen: pygame.Surface, center, direction, size: float) -> None:
        """Seta grossa apontando para direction ((1, 0) direita, (0, -1) cima...)."""
        cx, cy = center
        ux, uy = direction
        px, py = -uy, ux  # perpendicular

        def at(along: float, across: float):
            return (int(cx + ux * along + px * across), int(cy + uy * along + py * across))

        head, neck, tail, shaft, wing = size, size * 0.1, -size, size * 0.36, size * 0.8
        points = [
            at(head, 0),
            at(neck, wing),
            at(neck, shaft),
            at(tail, shaft),
            at(tail, -shaft),
            at(neck, -shaft),
            at(neck, -wing),
        ]
        pygame.draw.polygon(screen, T.SUN, points)
        pygame.draw.polygon(screen, T.NAVY, points, 5)

    def draw_mission(self, screen: pygame.Surface) -> None:
        """Meta pictográfica com texto auxiliar; mantém a instrução completa disponível."""
        mission = self.run.missions.current
        if mission is None:
            return
        width = 365
        box = pygame.Rect(18, 94, width, 58)
        T.panel(screen, box, T.PAPER, T.TEAL, 240, 15, 2)
        center = (box.left + 34, box.centery)
        if mission.kind == "desviar":
            self.draw_arrow(screen, (center[0] - 9, center[1]), (-1, 0), 17)
            self.draw_arrow(screen, (center[0] + 9, center[1]), (1, 0), 17)
        elif mission.kind == "portal":
            self.draw_arrow(screen, center, (0, 1), 20)
        elif mission.kind == "coletar":
            waste = next((item for item in WASTE_TYPES if item.key == mission.waste), None)
            icon = self.app.assets.sprite("waste_sprites", waste.sprite) if waste else None
            if icon is not None:
                icon = self.scaled(icon, (44, 44), ("mission", mission.waste))
            else:
                icon = T.icon_surface("paper", 44, T.TEAL)
            screen.blit(icon, icon.get_rect(center=center))
        else:
            screen.blit(T.icon_surface("powerup", 44, T.TEAL), (center[0] - 22, center[1] - 22))
        self.text.blit(
            screen,
            f"{self.run.missions.progress}/{mission.target}",
            (box.left + 66, box.top + 6),
            T.SIZES["label"],
            T.NAVY,
            True,
        )
        instruction = mission.text(0).split(" (")[0]
        self.text.blit(screen, instruction, (box.left + 68, box.top + 34), T.SIZES["small"], T.INK, True)

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
        if not self.banners or self.run.focus.state == "pending":
            return  # a seta do momento de foco fica sozinha na tela
        banner = self.banners[-1]
        reduced = self.app.options.reduzir_movimento
        fade = 1.0 if reduced else min(1.0, banner.ttl / 0.4, (banner.total - banner.ttl) / 0.3 + 0.2)
        # Faixa curta, junto à margem superior, sem cobrir o avião ou o corredor.
        rect = pygame.Rect(C.WIDTH // 2 - 300, 160, 600, 54)
        T.panel(screen, rect, T.PAPER, T.ORANGE, int(245 * fade), 15, 2)
        icon_center = (rect.left + 31, rect.centery)
        if banner.action in ("up", "down", "side"):
            if banner.action == "side":
                self.draw_arrow(screen, (icon_center[0] - 9, icon_center[1]), (-1, 0), 17)
                self.draw_arrow(screen, (icon_center[0] + 9, icon_center[1]), (1, 0), 17)
            else:
                direction = (0, -1) if banner.action == "up" else (0, 1)
                self.draw_arrow(screen, icon_center, direction, 20)
        else:
            icon_name = "paper" if banner.action == "collect" else "star"
            screen.blit(T.icon_surface(icon_name, 42, T.TEAL), (icon_center[0] - 21, icon_center[1] - 21))
        left = rect.left + 62
        right = rect.right - 15
        if banner.stars:
            for index in range(min(3, banner.stars)):
                star(screen, (left + 13 + index * 28, rect.centery), 11, True)
            left += 92
        title_font = self.text.font(T.SIZES["label"], True)
        subtitle_font = self.text.font(T.SIZES["small"])
        title_text = self._fit_banner_text(banner.title, title_font, right - left)
        title_surface = self.text.render(title_text, T.SIZES["label"], T.NAVY, True)
        if banner.subtitle:
            title_y = rect.top + 4
            subtitle_text = self._fit_banner_text(banner.subtitle, subtitle_font, right - left)
            subtitle_y = rect.top + 30
            subtitle_surface = self.text.render(subtitle_text, T.SIZES["small"], T.INK)
        else:
            title_y = rect.centery - title_surface.get_height() // 2
            subtitle_surface = None
        screen.blit(title_surface, (left, title_y))
        if subtitle_surface is not None:
            screen.blit(subtitle_surface, (left, subtitle_y))

    @staticmethod
    def _fit_banner_text(value: str, font: pygame.font.Font, max_width: int) -> str:
        """Evita que textos de missão/cidade ultrapassem a faixa compacta."""
        text = " ".join(value.split())
        if font.size(text)[0] <= max_width:
            return text
        suffix = "…"
        while text and font.size(text + suffix)[0] > max_width:
            text = text[:-1]
        return text.rstrip() + suffix

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
        card = pygame.Rect(C.WIDTH // 2 - 420, 82, 840, 520)
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
        self.text.blit(screen, title, (card.centerx, card.top + 28), T.SIZES["hero"], T.NAVY, True, "midtop")
        self.text.paragraph(
            screen, sub, pygame.Rect(card.left + 60, card.top + 100, card.width - 120, 76), T.SIZES["label"], T.INK
        )
        tip = texts.TIPS[int(self.time // 6) % len(texts.TIPS)]
        self.text.blit(screen, tip, (card.centerx, card.top + 200), T.SIZES["body"], T.MUTED, anchor="midtop")
        self.draw_pause_rewards(screen, card)
        self.draw_menu(screen)

    def draw_pause_rewards(self, screen: pygame.Surface, card: pygame.Rect) -> None:
        """Recursos e pontos saem do HUD em voo e ficam disponíveis na pausa."""
        x = card.left + 62
        y = card.top + 290
        for waste in WASTE_TYPES:
            icon = self.app.assets.sprite("waste_sprites", waste.sprite)
            if icon is not None:
                screen.blit(self.scaled(icon, (30, 30), ("pause_waste", waste.key)), (x, y))
            else:
                pygame.draw.circle(screen, waste.color, (x + 14, y + 14), 11)
            self.text.blit(
                screen,
                str(self.run.resources.get(waste.key, 0)),
                (x + 34, y + 3),
                T.SIZES["body"],
                T.INK,
                True,
            )
            x += 132
        self.text.blit(
            screen,
            f"{self.run.score} pontos",
            (card.right - 58, y + 3),
            T.SIZES["body"],
            T.NAVY,
            True,
            "topright",
        )
