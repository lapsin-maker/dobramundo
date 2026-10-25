"""Botões que funcionam por permanência, mouse ou teclado.

Seleção por permanência (GDD, seção 4): o cursor do segmento corporal (ou o
mouse) para sobre o alvo e um anel se completa em ``Options.permanencia``
segundos; então o botão é acionado. Depois disso, o mesmo botão só volta a
contar quando o cursor sai dele, para não repetir sem querer. O teclado
(setas + ENTER) e o clique do mouse acionam na hora.
"""

from __future__ import annotations

import math
from typing import Callable, List, Optional, Sequence, Tuple

import pygame

from ..util import Color, lerp_color
from . import theme as T


class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        action: Optional[Callable[[], None]] = None,
        *,
        sublabel: str = "",
        icon: Optional[pygame.Surface] = None,
        enabled: bool = True,
        selected: bool = False,
        color: Color = T.NAVY,
        size: int = T.SIZES["label"],
        swatch: Optional[Color] = None,
        key: str = "",
        align: str = "center",
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.sublabel = sublabel
        self.icon = icon
        self.enabled = enabled
        self.selected = selected
        self.color = color
        self.size = size
        self.swatch = swatch
        self.key = key or label
        self.align = align

    def draw(self, screen: pygame.Surface, text: T.Text, focused: bool, progress: float) -> None:
        rect = self.rect
        base = self.color if self.enabled else T.LOCKED
        fill = T.PAPER if not self.selected else lerp_color(T.PAPER, T.SUN, 0.55)
        if focused and self.enabled:
            fill = lerp_color(fill, T.SUN, 0.35)
            glow = rect.inflate(10, 10)
            pygame.draw.rect(screen, T.SUN, glow, 4, border_radius=20)
        T.panel(screen, rect, fill, base, 250, radius=16, width=4 if (focused or self.selected) else 3)
        if self.swatch is not None:
            sw = pygame.Rect(0, 0, rect.height - 22, rect.height - 22)
            sw.midleft = (rect.left + 12, rect.centery)
            pygame.draw.rect(screen, self.swatch, sw, border_radius=10)
            pygame.draw.rect(screen, T.INK, sw, 2, border_radius=10)
        content_left = rect.left + 14
        if self.icon is not None:
            icon_rect = self.icon.get_rect()
            if self.label:
                icon_rect.midleft = (rect.left + 12, rect.centery)
                content_left = icon_rect.right + 10
            else:
                icon_rect.center = rect.center
            screen.blit(self.icon, icon_rect)
        color = T.INK if self.enabled else T.MUTED
        if self.label and self.align == "top":  # cartão: título no alto, conteúdo desenhado pela cena
            text.blit(screen, self.label, (rect.centerx, rect.top + 10), self.size, color, True, "midtop")
            if self.sublabel:
                text.blit(
                    screen,
                    self.sublabel,
                    (rect.centerx, rect.top + 14 + self.size + 4),
                    T.SIZES["small"],
                    T.MUTED,
                    anchor="midtop",
                )
        elif self.label:
            if self.icon is None and self.swatch is None:
                if self.sublabel:
                    text.blit(screen, self.label, (rect.centerx, rect.centery - 10), self.size, color, True, "center")
                    text.blit(
                        screen,
                        self.sublabel,
                        (rect.centerx, rect.centery + 13),
                        T.SIZES["small"],
                        T.MUTED,
                        anchor="center",
                    )
                else:
                    text.blit(screen, self.label, rect.center, self.size, color, True, "center")
            else:
                left = content_left if self.swatch is None else rect.left + rect.height + 2
                if self.sublabel:
                    text.blit(screen, self.label, (left, rect.centery - 10), self.size, color, True, "midleft")
                    text.blit(
                        screen, self.sublabel, (left, rect.centery + 12), T.SIZES["small"], T.MUTED, anchor="midleft"
                    )
                else:
                    text.blit(screen, self.label, (left, rect.centery), self.size, color, True, "midleft")
        if progress > 0.0 and self.enabled:
            bar = pygame.Rect(rect.left + 10, rect.bottom - 9, int((rect.width - 20) * min(1.0, progress)), 5)
            pygame.draw.rect(screen, T.ORANGE, bar, border_radius=3)


class Menu:
    """Grupo de botões de uma tela: foco pelo teclado, clique e permanência."""

    def __init__(self, buttons: Sequence[Button] = (), focus: int = 0) -> None:
        self.buttons: List[Button] = list(buttons)
        self.focus = min(max(0, focus), max(0, len(self.buttons) - 1))
        self.hover: Optional[Button] = None
        self.dwell = 0.0
        self.armed = True
        self.pointer: Optional[Tuple[int, int]] = None
        self.on_focus: Optional[Callable[[], None]] = None

    def set_buttons(self, buttons: Sequence[Button], keep_focus: bool = True) -> None:
        old = self.buttons[self.focus].key if keep_focus and self.buttons else None
        self.buttons = list(buttons)
        self.focus = 0
        if old is not None:
            for i, button in enumerate(self.buttons):
                if button.key == old:
                    self.focus = i
                    break
        if self.hover is not None and self.hover.key not in {b.key for b in self.buttons}:
            self.hover, self.dwell = None, 0.0

    @property
    def focused(self) -> Optional[Button]:
        return self.buttons[self.focus] if self.buttons else None

    def activate(self, button: Optional[Button]) -> bool:
        if button is None or not button.enabled or button.action is None:
            return False
        button.action()
        return True

    def move_focus(self, dx: int, dy: int) -> None:
        """Foco para o botão mais próximo na direção pedida."""
        current = self.focused
        if current is None:
            return
        cx, cy = current.rect.center
        best, best_score = None, math.inf
        for i, button in enumerate(self.buttons):
            if button is current:
                continue
            bx, by = button.rect.center
            ddx, ddy = bx - cx, by - cy
            along = ddx * dx + ddy * dy
            if along <= 0:
                continue
            across = abs(ddx * dy) + abs(ddy * dx)
            score = along + across * 2.5
            if score < best_score:
                best, best_score = i, score
        if best is not None:
            self.focus = best
            if self.on_focus:
                self.on_focus()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """True se o evento foi usado pelo menu."""
        if event.type == pygame.KEYDOWN:
            moves = {
                pygame.K_LEFT: (-1, 0),
                pygame.K_a: (-1, 0),
                pygame.K_RIGHT: (1, 0),
                pygame.K_d: (1, 0),
                pygame.K_UP: (0, -1),
                pygame.K_w: (0, -1),
                pygame.K_DOWN: (0, 1),
                pygame.K_s: (0, 1),
            }
            if event.key in moves:
                self.move_focus(*moves[event.key])
                return True
            if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                return self.activate(self.focused)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.rect.collidepoint(event.pos):
                    self.focus = self.buttons.index(button)
                    return self.activate(button)
        return False

    def update(self, dt: float, pointer: Optional[Tuple[int, int]], dwell_time: float) -> bool:
        """Avança a permanência; True quando um botão foi acionado por ela."""
        self.pointer = pointer
        hovered = None
        if pointer is not None:
            for button in self.buttons:
                if button.enabled and button.rect.inflate(16, 16).collidepoint(pointer):
                    hovered = button
                    break
        if hovered is not self.hover:
            self.hover = hovered
            self.dwell = 0.0
            self.armed = True
            if hovered is not None:
                self.focus = self.buttons.index(hovered)
                if self.on_focus:
                    self.on_focus()
        if hovered is None or not self.armed:
            return False
        self.dwell += dt
        if self.dwell >= dwell_time:
            self.dwell = 0.0
            self.armed = False  # sai do botão para poder acionar de novo
            return self.activate(hovered)
        return False

    def progress_of(self, button: Button, dwell_time: float) -> float:
        return self.dwell / dwell_time if button is self.hover and self.armed else 0.0

    def draw(self, screen: pygame.Surface, text: T.Text, dwell_time: float) -> None:
        focused = self.focused
        for button in self.buttons:
            button.draw(screen, text, button is focused, self.progress_of(button, dwell_time))

    def draw_pointer(self, screen: pygame.Surface, dwell_time: float, body: bool) -> None:
        """Cursor do corpo: anel que se completa durante a permanência."""
        if self.pointer is None or not body:
            return
        x, y = self.pointer
        pygame.draw.circle(screen, T.WHITE, (x, y), 18)
        pygame.draw.circle(screen, T.NAVY, (x, y), 18, 4)
        progress = self.dwell / dwell_time if self.hover is not None and self.armed else 0.0
        if progress > 0:
            ring(screen, (x, y), 25, 7, progress, T.ORANGE)
        pygame.draw.circle(screen, T.ORANGE, (x, y), 6)


def ring(
    screen: pygame.Surface, center: Tuple[int, int], radius: int, width: int, progress: float, color: Color
) -> None:
    """Anel de progresso (polígono cheio, sem o serrilhado do pygame.draw.arc grosso)."""
    progress = max(0.0, min(1.0, progress))
    if progress <= 0:
        return
    steps = max(3, int(48 * progress))
    cx, cy = center
    outer, inner = [], []
    for i in range(steps + 1):
        a = -math.pi / 2 + 2 * math.pi * progress * i / steps
        outer.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
        inner.append((cx + (radius - width) * math.cos(a), cy + (radius - width) * math.sin(a)))
    pygame.draw.polygon(screen, color, outer + inner[::-1])


def grid(
    rect: pygame.Rect, count: int, columns: int, gap: int = 14, row_height: Optional[int] = None
) -> List[pygame.Rect]:
    """Divide rect em células (esquerda para a direita, de cima para baixo)."""
    rows = max(1, math.ceil(count / columns))
    w = (rect.width - gap * (columns - 1)) // columns
    h = row_height or (rect.height - gap * (rows - 1)) // rows
    return [
        pygame.Rect(rect.left + (i % columns) * (w + gap), rect.top + (i // columns) * (h + gap), w, h)
        for i in range(count)
    ]


def row(rect: pygame.Rect, count: int, gap: int = 14) -> List[pygame.Rect]:
    return grid(rect, count, count, gap)


def star(
    screen: pygame.Surface,
    center: Tuple[int, int],
    radius: int,
    filled: bool,
    color: Color = T.SUN,
    outline: Color = T.NAVY_DARK,
) -> None:
    """Estrela de cinco pontas (cheia ou só o contorno)."""
    cx, cy = center
    points = []
    for i in range(10):
        r = radius if i % 2 == 0 else radius * 0.45
        angle = -math.pi / 2 + i * math.pi / 5
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    if filled:
        pygame.draw.polygon(screen, color, points)
    pygame.draw.polygon(screen, outline, points, 3)
