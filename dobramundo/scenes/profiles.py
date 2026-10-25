"""Seleção local de pilotos anônimos para computadores compartilhados."""

from __future__ import annotations

import math

import pygame

from .. import config as C
from ..engine.paper_pilot import draw_pilot
from ..persistence import PROFILE_SLOT_LIMIT, peek_profile
from ..ui import theme as T
from ..util import rgb
from .base import Scene

_BADGE_COLORS = (
    rgb("eeaa58"),
    rgb("4fae9b"),
    rgb("7e8ecf"),
    rgb("d8758e"),
    rgb("87aa58"),
    rgb("a57bc5"),
    rgb("cf8848"),
    rgb("4c9bc2"),
)


def _pilot_badge(profile, index: int, active: bool, painted=None) -> pygame.Surface:
    badge = pygame.Surface((96, 112), pygame.SRCALPHA)
    color = _BADGE_COLORS[index % len(_BADGE_COLORS)]
    pygame.draw.ellipse(badge, (color[0], color[1], color[2], 90), (8, 4, 80, 104))
    # O anel pontilhado identifica o slot mesmo quando o avatar ainda não foi montado.
    for angle in range(index % 4, 360, 45):
        x = 48 + int(43 * math.cos(math.radians(angle)))
        y = 54 + int(53 * math.sin(math.radians(angle)))
        pygame.draw.circle(badge, color, (x, y), 3 + (1 if angle // 45 == index % 8 else 0))
    if profile is not None:
        portrait = painted if painted is not None else draw_pilot("menu", profile.piloto)
        badge.blit(pygame.transform.smoothscale(portrait, (72, 96)), (12, 8))
    else:
        pygame.draw.circle(badge, color, (48, 40), 15)
        pygame.draw.ellipse(badge, color, (22, 56, 52, 39))
    if active:
        pygame.draw.circle(badge, T.GREEN, (82, 14), 8)
    return badge


class ProfilesScene(Scene):
    music = "musica_vila"

    def __init__(self, app) -> None:
        super().__init__(app)
        self.page = 0
        self.error = ""

    def build(self) -> None:
        slots = self.app.list_profiles()
        page_count = max(1, (len(slots) + 3) // 4)
        self.page = min(self.page, page_count - 1)
        visible = slots[self.page * 4 : (self.page + 1) * 4]
        buttons = []
        for index, slot in enumerate(visible, self.page * 4):
            x = 70 + (index % 2) * 490
            y = 130 + ((index % 4) // 2) * 175
            stored = peek_profile(slot.id)
            portrait = self.app.view.skin.pilots.compose("menu", stored.piloto) if stored is not None else None
            buttons.append(
                self.button(
                    (x, y, 430, 145),
                    slot.label,
                    lambda selected=slot: self._select(selected.id),
                    sublabel="Piloto atual" if slot.active else "Abrir este piloto",
                    icon=_pilot_badge(stored, index, slot.active, portrait),
                    selected=slot.active,
                    size=T.SIZES["title"],
                    key=f"perfil-{slot.id}",
                )
            )
        if len(slots) < PROFILE_SLOT_LIMIT:
            buttons.append(
                self.button(
                    (70, 485, 300, 76),
                    "Novo piloto",
                    self._create,
                    sublabel="Começar do início",
                    key="perfil-novo",
                    size=T.SIZES["label"],
                )
            )
        if page_count > 1:
            buttons.append(
                self.button(
                    (390, 485, 90, 76),
                    "",
                    lambda: self._page(-1),
                    icon=T.icon_surface("back", 54),
                    enabled=self.page > 0,
                    key="perfil-pagina-anterior",
                )
            )
            buttons.append(
                self.button(
                    (500, 485, 90, 76),
                    "",
                    lambda: self._page(1),
                    icon=T.icon_surface("next", 54),
                    enabled=self.page + 1 < page_count,
                    key="perfil-pagina-proxima",
                )
            )
        buttons.append(self.button((800, 485, 220, 76), "Voltar", lambda: self.goto("vila"), key="perfil-voltar"))
        self.menu.set_buttons(buttons)

    def _page(self, direction: int) -> None:
        self.page += direction
        self.error = ""
        self.build()

    def _select(self, slot_id: str) -> None:
        if slot_id == self.app.profile_slot:
            self.goto("vila")
            return
        if not self.app.select_profile(slot_id):
            self.error = self.app.storage_notice or "Não consegui abrir este piloto."

    def _create(self) -> None:
        if not self.app.create_profile():
            self.error = self.app.storage_notice or "Não consegui criar um piloto agora."

    def draw(self, screen: pygame.Surface) -> None:
        screen.fill(T.PAPER)
        self.title(screen, "Quem vai voar?", "Cada piloto guarda seu próprio progresso")
        self.menu.draw(screen, self.text, self.dwell_time)
        self.menu.draw_pointer(screen, self.dwell_time, self.app.input.body_pointer() is not None)
        if self.error:
            box = pygame.Rect(80, C.HEIGHT - 54, C.WIDTH - 160, 42)
            T.panel(screen, box, T.PAPER, T.ORANGE, 245, 12, 3)
            label, size = T.fit_text(self.text, self.error, box.width - 24, T.SIZES["small"], bold=True)
            self.text.blit(screen, label, box.center, size, T.INK, True, "center")
