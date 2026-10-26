"""Apresentação HUD e retorno visual do voo, separada das regras da sessão."""

from __future__ import annotations

import math

import pygame

from .. import config as C
from ..content import texts
from ..content.items import WASTE_TYPES
from ..content.progress import STAR_THRESHOLDS
from ..engine.sprites import project
from ..game.missions import MISSION_TIMEOUT_S
from ..ui import theme as T
from ..ui.widgets import star
from ..util import lerp_color

ARROW_VECTORS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}


class FlightHUDMixin:
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
        if run.session_limit_s:
            clock = max(0, run.session_limit_s - int(run.flight_time))
            minutes, seconds = divmod(clock, 60)
            timer_box = pygame.Rect(C.WIDTH // 2 - 62, 14, 124, 56)
            T.panel(screen, timer_box, T.PAPER, T.TEAL, 245, 14, 2)
            text.blit(
                screen, "TEMPO", (timer_box.centerx, timer_box.top + 7), T.SIZES["small"], T.MUTED, True, "midtop"
            )
            text.blit(
                screen,
                f"{minutes:02d}:{seconds:02d}",
                (timer_box.centerx, timer_box.top + 28),
                T.SIZES["label"],
                T.NAVY,
                True,
                "midtop",
            )
        self.draw_mission(screen)
        status = pygame.Rect(C.WIDTH - 244, 14, 226, 70)
        T.panel(screen, status, T.PAPER, T.NAVY, 238, 16, 2)
        spacing = 39
        start_x = status.left + (status.width - (run.max_lives - 1) * spacing) // 2
        life_y = 40 if run.exploration or run.predictable_assistance else 48
        for i in range(run.max_lives):
            self.draw_life(screen, (start_x + i * spacing, life_y), i < run.lives)
        label_anchor = (status.centerx, status.bottom - 24)
        if run.exploration:
            label = "EXPLORAR" + (" · APOIO" if run.predictable_assistance else "")
            text.blit(screen, label, label_anchor, T.SIZES["small"], T.MUTED_STRONG, True, "midtop")
        elif run.predictable_assistance:
            text.blit(screen, "APOIO", label_anchor, T.SIZES["small"], T.MUTED_STRONG, True, "midtop")
        if run.shield_timer > 0 or run.magnet_timer > 0:
            # Ambos os benefícios têm um relógio visual próprio. A leitura de
            # segundos é auxiliar; o arco se esvazia sem piscar.
            benefits = (("shield", run.shield_timer, C.SHIELD_S), ("magnet", run.magnet_timer, C.MAGNET_S))
            for i, (active, timer, total) in enumerate(benefits):
                if timer <= 0:
                    continue
                center = (status.left + 36 + i * 74, status.bottom + 36)
                pygame.draw.circle(screen, T.PAPER, center, 27)
                pygame.draw.circle(screen, T.NAVY, center, 27, 2)
                screen.blit(T.icon_surface(active, 30, T.NAVY), (center[0] - 15, center[1] - 15))
                arc = pygame.Rect(center[0] - 23, center[1] - 23, 46, 46)
                pygame.draw.arc(screen, T.TEAL, arc, math.pi / 2, math.pi / 2 + math.tau * min(1.0, timer / total), 5)
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
        sx, sy = self.app.view.screen_point((sx, sy))
        if focus.state != "pending":
            ok = focus.state == "success"
            center = (int(sx), max(178, int(sy) - 120))
            pygame.draw.circle(screen, T.PAPER, center, 26)
            pygame.draw.circle(screen, T.NAVY, center, 26, 3)
            if ok:
                pygame.draw.lines(
                    screen,
                    T.TEAL,
                    False,
                    [(center[0] - 13, center[1]), (center[0] - 3, center[1] + 10), (center[0] + 15, center[1] - 12)],
                    6,
                )
            else:
                screen.blit(T.icon_surface("plane", 36, T.NAVY), (center[0] - 18, center[1] - 18))
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
        width = max(340, self.font("hero", True).size(prompt)[0] + 60)
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
        box = pygame.Rect(18, 94, width, 66)
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
        # Uma conta por ação: permite acompanhar a missão sem ler números.
        for i in range(mission.target):
            center = (box.left + 145 + i * 24, box.top + 18)
            pygame.draw.circle(screen, T.TEAL if i < self.run.missions.progress else T.PAPER, center, 8)
            pygame.draw.circle(screen, T.NAVY, center, 8, 2)
        instruction = mission.text(0).split(" (")[0]
        self.text.blit(screen, instruction, (box.left + 68, box.top + 32), T.SIZES["small"], T.INK, True)
        remaining = max(0.0, 1.0 - self.run.missions.current_age / MISSION_TIMEOUT_S)
        timer = pygame.Rect(box.left + 5, box.bottom - 9, box.width - 10, 8)
        pygame.draw.rect(screen, (211, 222, 218), timer, border_radius=2)
        fill = timer.copy()
        fill.width = round(timer.width * remaining)
        if fill.width:
            pygame.draw.rect(screen, T.TEAL if remaining > 0.25 else T.ORANGE, fill, border_radius=2)

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
            self.banner_occluded = False
            return
        # Área periférica inferior direita, longe da prévia da webcam. Se um
        # obstáculo projetado cruzar a faixa, a mensagem espera em vez de cobri-lo.
        rect = pygame.Rect(C.WIDTH - 538, C.HEIGHT - 72, 520, 54)
        self.banner_occluded = self._banner_overlaps_obstacle(rect)
        if self.run.focus.state == "pending" or self.banner_occluded:
            return
        banner = self.banners[-1]
        reduced = self.app.options.reduzir_movimento
        fade = 1.0 if reduced else min(1.0, banner.ttl / 0.4, (banner.total - banner.ttl) / 0.3 + 0.2)
        # Faixa compacta na borda inferior, subordinada a obstáculos próximos.
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
        title_font = self.font("label", True)
        subtitle_font = self.font("small")
        title_text = T.elide_text(banner.title, title_font, right - left)
        title_surface = self.text.render(title_text, T.SIZES["label"], T.NAVY, True)
        if banner.subtitle:
            title_y = rect.top + 4
            subtitle_text = T.elide_text(banner.subtitle, subtitle_font, right - left)
            subtitle_y = rect.top + 30
            subtitle_surface = self.text.render(subtitle_text, T.SIZES["small"], T.INK)
        else:
            title_y = rect.centery - title_surface.get_height() // 2
            subtitle_surface = None
        screen.blit(title_surface, (left, title_y))
        if subtitle_surface is not None:
            screen.blit(subtitle_surface, (left, subtitle_y))

    def _banner_overlaps_obstacle(self, banner: pygame.Rect) -> bool:
        view = self.app.view
        for entity in self.run.world.entities:
            spec = entity.spec
            if spec is None or entity.collected or entity.hit or entity.dodged or entity.passed:
                continue
            corners = [
                view.screen_point(project(x, y, entity.z, view.cam)[:2])
                for x in (entity.x - spec.width * 0.5, entity.x + spec.width * 0.5)
                for y in (spec.y_min, spec.y_max)
            ]
            xs = [point[0] for point in corners]
            ys = [point[1] for point in corners]
            bounds = pygame.Rect(
                round(min(xs)), round(min(ys)), max(1, round(max(xs) - min(xs))), max(1, round(max(ys) - min(ys)))
            )
            if banner.colliderect(bounds.inflate(12, 12)):
                return True
        return False

    def draw_camera(self, screen: pygame.Surface) -> None:
        """Miniatura para o supervisor e avisos de calibração ou de câmera."""
        body = self.app.input.body
        if body is None:
            return
        if body.error:
            self.text.blit(
                screen,
                f"Câmera indisponível ({body.error}): voo pausado; tente Recalibrar",
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
