"""Resultado do voo: estrelas, recursos levados para a vila e uma curiosidade do bioma."""

from __future__ import annotations

from datetime import datetime

import pygame

from .. import config as C
from ..content import texts
from ..content.items import WASTE_TYPES
from ..content.progress import PART_BY_KEY, parts_ok
from ..game.run import FlightRun
from ..ui import theme as T
from ..ui.widgets import row, star
from .base import Scene


def apply_run(profile, run: FlightRun) -> dict:
    """Leva o voo para o perfil: recursos, pontos, estrelas e recorde. Devolve o resumo."""
    key = run.biome.key
    best_before = profile.estrelas.get(key, 0)
    for waste, amount in run.resources.items():
        profile.recursos[waste] = profile.recursos.get(waste, 0) + amount
    profile.pontos += run.score
    profile.voos += 1
    profile.voos_fase[key] = profile.voos_fase.get(key, 0) + 1
    entry = run.summary()
    entry["data"] = datetime.now().isoformat(timespec="seconds")
    entry["controle"] = profile.controle
    profile.historico = (profile.historico + [entry])[-C.HISTORY_LIMIT :]
    if run.stars > best_before:
        profile.estrelas[key] = run.stars
    record_key = f"{key}:{run.mode}"
    new_record = run.score > profile.recordes.get(record_key, 0)
    if new_record:
        profile.recordes[record_key] = run.score
    return {"new_stars": max(0, run.stars - best_before), "new_record": new_record}


def movement_line(run: FlightRun) -> str:
    """Linha do movimento no resultado: tempo em ação, alcances percorridos e momentos de foco."""
    parts = []
    if run.body_time >= 5.0:
        minutes, seconds = divmod(int(run.active_time), 60)
        share = int(round(100 * run.active_time / max(1.0, run.body_time)))
        parts.append(f"Em movimento: {minutes}:{seconds:02d} ({share}% do voo)")
        parts.append(f"{run.travel:.0f} alcances percorridos")
    if run.focus.total:
        parts.append(f"Momentos de foco: {run.focus.successes} de {run.focus.total}")
    return "   ·   ".join(parts)


class ResultScene(Scene):
    def __init__(self, app, run: FlightRun) -> None:
        super().__init__(app)
        self.run = run
        self.summary = apply_run(app.profile, run)
        app.save()
        biome = run.biome
        facts = texts.BIOME_FACTS.get(biome.key, ())
        self.fact = facts[app.profile.voos % len(facts)] if facts else ""
        self.music = f"musica_{biome.music}_{min(2, run.stage) + 1}"

    def build(self) -> None:
        rects = row(pygame.Rect(C.WIDTH // 2 - 360, 548, 720, 76), 2)
        self.menu.set_buttons(
            [
                self.button(rects[0], texts.UI["tentar_de_novo"] if self.run.game_over else "Voar de novo", self.again),
                self.button(rects[1], "Voltar à vila", lambda: self.goto("vila")),
            ],
            keep_focus=False,
        )

    def again(self) -> None:
        self.fly(self.run.biome.key)

    def draw(self, screen: pygame.Surface) -> None:
        run = self.run
        self.app.backdrop(screen, self.last_dt, run.biome.key, min(100.0, run.restoration))
        T.veil(screen, (10, 18, 40), 120)
        card = pygame.Rect(C.WIDTH // 2 - 440, 40, 880, 490)
        T.panel(screen, card, T.PAPER, T.NAVY, 248, 24, 4)
        if run.complete:
            title = f"{run.biome.city} virou cidade solarpunk!"
        elif run.game_over:
            title = "O avião precisa de reparos"
        else:
            title = texts.UI["fim_de_fase"]
        self.text.blit(screen, title, (card.centerx, card.top + 22), T.SIZES["title"], T.NAVY, True, "midtop")
        # estrelas surgem uma a uma
        shown = min(run.stars, int(self.time / 0.5))
        for i in range(3):
            star(screen, (card.centerx - 110 + i * 110, card.top + 128), 44, i < shown)
        if run.complete and run.stars < 3 and not parts_ok(run.biome.required_parts, run.parts):
            need = ", ".join(PART_BY_KEY[k].name for k in run.biome.required_parts)
            self.text.blit(
                screen,
                f"Para a 3ª estrela aqui, instale no avião: {need}",
                (card.centerx, card.top + 182),
                T.SIZES["body"],
                T.RED,
                True,
                "midtop",
            )
        elif self.summary["new_stars"]:
            self.text.blit(
                screen, "Nova conquista!", (card.centerx, card.top + 182), T.SIZES["body"], T.ORANGE, True, "midtop"
            )
        self.text.blit(
            screen,
            f"Transformação: {int(run.restoration)}%   Pontos: {run.score}"
            + ("   (recorde!)" if self.summary["new_record"] else ""),
            (card.centerx, card.top + 216),
            T.SIZES["label"],
            T.INK,
            True,
            "midtop",
        )
        movement = movement_line(run)
        if movement:
            self.text.blit(screen, movement, (card.centerx, card.top + 250), T.SIZES["small"], T.TEAL, True, "midtop")
        self.text.blit(
            screen, "Recursos para a vila", (card.centerx, card.top + 274), T.SIZES["body"], T.MUTED, True, "midtop"
        )
        cells = row(pygame.Rect(card.left + 60, card.top + 302, card.width - 120, 70), 4, 16)
        for waste, rect in zip(WASTE_TYPES, cells):
            T.panel(screen, rect, T.PAPER, waste.color, 255, 14, 4)
            icon = self.app.assets.sprite("waste_sprites", waste.sprite)
            if icon is not None:
                screen.blit(self.scaled(icon, (52, 52)), (rect.left + 10, rect.top + 9))
            self.text.blit(
                screen,
                f"+{run.resources.get(waste.key, 0)}",
                (rect.left + 76, rect.top + 8),
                T.SIZES["label"],
                T.INK,
                True,
            )
            self.text.blit(screen, waste.name, (rect.left + 76, rect.top + 40), T.SIZES["small"], T.MUTED)
        self.text.blit(screen, "Você sabia?", (card.left + 60, card.top + 388), T.SIZES["body"], T.TEAL, True)
        self.text.paragraph(
            screen, self.fact, pygame.Rect(card.left + 60, card.top + 414, card.width - 120, 70), T.SIZES["body"], T.INK
        )
        self.draw_menu(screen)
