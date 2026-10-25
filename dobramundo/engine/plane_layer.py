"""Avião, manobras e efeitos visuais; conserva o fallback vetorial."""

from __future__ import annotations

import math
from typing import Tuple

import pygame

from .. import config as C
from ..content.items import POWERUP_COLORS
from ..content.planes import MANEUVER_STYLES
from ..util import clamp, lerp_color, rgb
from .contracts import FlightView, PlaneLook
from .sprites import project

HC_PLANE = rgb("ffeb3b")


class PlaneLayer:
    def draw_player(self, screen: pygame.Surface, run: FlightView, look: PlaneLook) -> None:
        player = run.player
        self.shadow(
            screen,
            player.x,
            C.PLAYER_Z,
            C.PLANE_WIDTH * (1.1 - player.y / 800),
            int(clamp(150 - player.y * 0.5, 40, 150)),
        )
        blink = not self.reduce_motion and not self.high_contrast
        if blink and run.invulnerable_timer > 0 and int(self.elapsed * 14) % 2:
            return  # pisca depois de uma colisão
        bob = 0 if self.reduce_motion else math.sin(self.elapsed * 3.0) * 3.0
        sx, sy, scale = project(player.x, player.y + bob, C.PLAYER_Z, self.cam)
        width = max(8, int(C.PLANE_WIDTH * scale))
        sprite = self.skin.surface(look.plane, "flight", look.color, look.pattern, look.pilot)
        look_key = self.skin.look_key(look.plane, look.color, look.pattern, look.pilot)
        if sprite is not None and self.high_contrast:
            sprite = self.cache.outlined_source(sprite, ("plane", look_key), HC_PLANE)
            look_key += "#hc"
        pose = player.maneuver_pose()
        if sprite is None:
            self.player_rect = pygame.Rect(0, 0, width, max(24, round(width * 0.6)))
            self.player_rect.center = round(sx), round(sy)
            self.draw_paper_fallback(screen, int(sx), int(sy), width, player.roll + (pose[0] if pose else 0.0))
            return
        aspect = sprite.get_height() / max(1, sprite.get_width())
        height = max(4, int(width * aspect))
        max_h = int(120 * scale)  # piloto alto não cobre a tela
        if height > max_h:
            height = max_h
            width = max(8, int(height / aspect))
        if pose is not None:
            m_roll, m_pitch, m_dx, m_dy, m_dz = pose
            style = MANEUVER_STYLES[player.maneuver]
            sx += m_dx * style.sway * width
            sy = max(C.MANEUVER_TOP_MARGIN, sy - m_dy * style.lift * width)
            depth = 1.0 / max(0.4, 1.0 + style.depth * m_dz)
            vertical = math.cos(math.radians(m_pitch))
            thickness = round(max(C.MANEUVER_MIN_THICKNESS, abs(vertical)) * 25) / 25
            # tamanho e ângulo em degraus: a manobra se repete e reaproveita as imagens prontas
            size = (max(8, int(width * depth)) // 4 * 4, max(4, int(height * depth * thickness)) // 4 * 4)
            angle = round((player.roll + m_roll) / 4.0) * 4.0
            key = ("manobra", look_key, size, angle, vertical < 0)
            image = self.rotations.get(key)
            if image is None:
                img = self.cache.get(sprite, ("plane", look_key), size)
                if vertical < 0:  # de cabeça para baixo (topo do looping)
                    img = pygame.transform.flip(img, False, True)
                image = self.remember_rotation(key, pygame.transform.rotozoom(img, angle, 1.0))
            width = size[0]
        else:
            # papel tremulando no ar e nariz que sobe ou desce com a velocidade vertical
            # (em degraus, para reaproveitar as imagens giradas prontas)
            flutter = 0 if self.reduce_motion else C.PAPER_FLUTTER_DEG * math.sin(self.elapsed * 7.0)
            if not self.reduce_motion and self.celebration > 0:
                flutter += 5 * math.sin(self.celebration * math.tau) * min(1.0, self.celebration)
            pitch = clamp(player.vy / C.MAX_VERTICAL_SPEED, -1.0, 1.0)
            height = max(4, int(height * (1.0 + round(pitch * C.PITCH_STRETCH * 25) / 25)))
            base = self.cache.get(sprite, ("plane", look_key), (width, height))
            angle = round((player.roll + flutter) / 2.0) * 2.0
            key = (look_key, width, height, angle)
            image = self.rotations.get(key)
            if image is None:
                image = self.remember_rotation(key, pygame.transform.rotozoom(base, angle, 1.0))
        self.player_rect = image.get_rect(center=(int(sx), int(sy)))
        screen.blit(image, self.player_rect)
        if run.shield_timer > 0:
            pulse = 0.5 + 0.5 * math.sin(self.elapsed * 8.0)
            pygame.draw.ellipse(
                screen,
                lerp_color(rgb("40c4ff"), (255, 255, 255), pulse * 0.4),
                pygame.Rect(int(sx - width * 0.62), int(sy - width * 0.36), int(width * 1.24), int(width * 0.72)),
                max(2, int(3 * scale)),
            )
        if run.magnet_timer > 0:
            pygame.draw.circle(
                screen,
                POWERUP_COLORS["magnet"],
                (int(sx), int(sy)),
                int(width * (0.7 + 0.05 * math.sin(self.elapsed * 10))),
                1,
            )
        if self.show_hitboxes:
            pygame.draw.rect(screen, rgb("40c4ff"), self.hitbox_rect(player.hitbox()), 2)

    @staticmethod
    def splash(screen: pygame.Surface, center, color, progress: float, scale: float) -> None:
        """Gotas que se abrem e somem (progress 0 -> 1), com um pingo claro no meio."""
        cx, cy = int(center[0]), int(center[1])
        pale = lerp_color(color, (255, 255, 255), 0.35)
        for k in range(7):
            angle = k * 0.9 + 0.3
            reach = (14 + 70 * progress) * scale
            r = max(1, int((7 - 5 * progress) * scale))
            px, py = int(cx + math.cos(angle) * reach), int(cy + math.sin(angle) * reach * 0.7)
            pygame.draw.circle(screen, color, (px, py), r)
        core = max(1, int((22 - 20 * progress) * scale))
        pygame.draw.circle(screen, pale, (cx, cy), core)
        if progress < 0.6:
            pygame.draw.circle(screen, (255, 255, 255), (cx - core // 3, cy - core // 3), max(1, core // 3))

    def remember_rotation(self, key: tuple, image: pygame.Surface) -> pygame.Surface:
        """Guarda uma rotação do avião (descarte gradual, como o cache de sprites)."""
        return self.rotations.put(key, image)

    @staticmethod
    def draw_paper_fallback(screen: pygame.Surface, cx: int, cy: int, width: int, roll: float) -> None:
        """Avião de papel desenhado por código (se os sprites faltarem)."""
        h = width * 0.28
        angle = math.radians(roll)

        def rot(px: float, py: float) -> Tuple[int, int]:
            return (
                int(cx + px * math.cos(angle) - py * math.sin(angle)),
                int(cy + px * math.sin(angle) + py * math.cos(angle)),
            )

        left = [rot(0, -h * 0.35), rot(-width / 2, h * 0.25), rot(0, h * 0.1)]
        right = [rot(0, -h * 0.35), rot(width / 2, h * 0.25), rot(0, h * 0.1)]
        keel = [rot(0, -h * 0.35), rot(-width * 0.05, h * 0.6), rot(width * 0.05, h * 0.6)]
        pygame.draw.polygon(screen, (232, 232, 226), left)
        pygame.draw.polygon(screen, (250, 250, 246), right)
        pygame.draw.polygon(screen, (180, 186, 190), keel)
        pygame.draw.lines(screen, rgb("78909c"), True, left + right[1:], 1)
