"""Resultado do voo: estrelas, recursos levados para a vila e uma curiosidade do bioma."""

from __future__ import annotations

from datetime import datetime

import pygame

from .. import config as C
from ..content import texts
from ..content.items import WASTE_TYPES
from ..content.progress import PART_BY_KEY, VILLAGE_UPGRADES, can_afford, missing
from ..engine.village_art import village_prop
from ..game.run import FlightRun
from ..ui import theme as T
from ..ui.widgets import row, star
from .base import Scene
from .village import VILLAGE_REQUESTS


def apply_run(profile, run: FlightRun) -> dict:
    """Leva o voo para o perfil: recursos, pontos, estrelas e recorde. Devolve o resumo."""
    if run.settlement is not None:
        return dict(run.settlement)
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
    run.settlement = {"new_stars": max(0, run.stars - best_before), "new_record": new_record}
    return dict(run.settlement)


def notify_settlement(app, run: FlightRun) -> None:
    """Notifica o cartucho uma vez, inclusive se o processo fechar durante um voo."""
    if run.settlement_callback_sent or not run.settlement:
        return
    app.on_flight(app.profile.historico[-1])
    run.settlement_callback_sent = True


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
        notify_settlement(app, run)
        biome = run.biome
        facts = texts.BIOME_FACTS.get(biome.key, ())
        self.fact = facts[app.profile.voos % len(facts)] if facts else ""
        self.music = f"musica_{biome.music}_{min(2, run.stage) + 1}"

    def build(self) -> None:
        count = 3 if self.app.save_failed else 2
        width = C.WIDTH - 100 if self.app.save_failed else 720
        rects = row(pygame.Rect((C.WIDTH - width) // 2, 548, width, 76), count)
        next_build = next((item for item in VILLAGE_UPGRADES if item.key not in self.app.profile.vila), None)
        has_materials = next_build is not None and can_afford(self.app.profile.recursos, next_build.cost)
        if next_build is None:
            village_label = "Voltar à vila"

            def village_action() -> None:
                self.goto("vila")

        else:
            village_label = "Construir na vila" if has_materials else "Ver próxima obra"

            def village_action(key: str = next_build.key) -> None:
                self.goto("melhorias", tab="vila", initial_key=key)

        buttons = [
            self.button(rects[0], texts.UI["tentar_de_novo"] if self.run.game_over else "Voar de novo", self.again),
            self.button(
                rects[-1],
                village_label,
                village_action,
                icon=T.icon_surface("village", 42, T.GREEN),
                color=T.GREEN,
                key="vila_proxima_obra",
            ),
        ]
        if self.app.save_failed:
            buttons.insert(1, self.button(rects[1], "Salvar de novo", self.retry_save, key="retry_save"))
        self.menu.set_buttons(buttons, keep_focus=False)

    def retry_save(self) -> None:
        self.app.save()
        self.toast.show("Progresso salvo!" if not self.app.save_failed else "Ainda não foi possível salvar.")
        self.build()

    def again(self) -> None:
        self.fly(self.run.biome.key)

    def draw(self, screen: pygame.Surface) -> None:
        run = self.run
        T.watercolor_backdrop(screen, "river" if run.biome.river else "warm")
        card = pygame.Rect(34, 18, C.WIDTH - 68, 520)
        T.panel(screen, card, T.PAPER, T.NAVY, 250, 24, 3)
        # A reação do piloto reforça o resultado sem pedir leitura adicional.
        expression = "recover" if run.game_over or run.interrupted else "happy" if run.complete else "curious"
        mood_color = T.TEAL if run.game_over or run.interrupted else T.GREEN if run.complete else T.SUN
        mood = pygame.Rect(card.left + 28, card.top + 76, 104, 124)
        pygame.draw.ellipse(screen, T.NAVY, mood.inflate(6, 6))
        pygame.draw.ellipse(screen, T.PAPER, mood)
        pygame.draw.ellipse(screen, mood_color, mood, 4)
        pilot = self.app.view.skin.pilots.compose("menu", self.app.profile.piloto, expression=expression)
        if pilot is not None:
            image = self.scaled(pilot, (86, 108), ("result-pilot", expression))
            screen.blit(image, image.get_rect(center=mood.center))
        if run.complete:
            title = f"{run.biome.city} floresceu!"
        elif run.game_over:
            title = "Seu avião precisa de reparos"
        elif run.interrupted:
            title = "Voo encerrado por agora"
        else:
            title = "Bom voo!"
        self.text.blit(
            screen,
            title,
            (card.centerx, card.top + 12),
            T.SIZES["title"],
            T.NAVY,
            True,
            "midtop",
        )
        shown = run.stars if self.app.options.reduzir_movimento else min(run.stars, int(self.time / 0.42))
        for i in range(3):
            star(screen, (card.centerx - 82 + i * 82, card.top + 89), 32, i < shown)
        if self.summary["new_stars"]:
            self.text.blit(
                screen,
                "Nova conquista!",
                (card.centerx, card.top + 126),
                T.SIZES["body"],
                T.ORANGE,
                True,
                "midtop",
            )
        self.text.blit(
            screen,
            f"Cidade transformada {int(run.restoration)}%   ·   +{run.score} pontos"
            + ("   ·   recorde!" if self.summary["new_record"] else ""),
            (card.centerx, card.top + 153),
            T.SIZES["body"],
            T.INK,
            True,
            "midtop",
        )
        movement = movement_line(run)
        if movement:
            self.text.blit(
                screen,
                movement,
                (card.centerx, card.top + 178),
                T.SIZES["small"],
                T.TEAL,
                True,
                "midtop",
            )
        self.text.blit(screen, "Recursos para a vila", (card.left + 38, card.top + 213), T.SIZES["body"], T.NAVY, True)
        cells = row(pygame.Rect(card.left + 32, card.top + 242, card.width - 64, 66), 4, 12)
        for waste, rect in zip(WASTE_TYPES, cells):
            T.panel(screen, rect, T.PAPER, waste.color, 250, 14, 2)
            icon = self.app.assets.sprite("waste_sprites", waste.sprite)
            if icon is not None:
                screen.blit(self.scaled(icon, (48, 48), ("result_waste", waste.key)), (rect.left + 8, rect.top + 9))
            self.text.blit(
                screen,
                f"+{run.resources.get(waste.key, 0)}",
                (rect.left + 62, rect.top + 6),
                T.SIZES["label"],
                T.INK,
                True,
            )
            self.text.blit(screen, waste.name, (rect.left + 62, rect.top + 39), T.SIZES["small"], T.MUTED)
        self.draw_next_build(screen, pygame.Rect(card.left + 32, card.top + 322, 468, 92))
        self.draw_missing_parts(screen, pygame.Rect(card.left + 520, card.top + 322, card.width - 552, 92))
        if self.app.save_failed:
            warn = pygame.Rect(card.left + 32, card.top + 424, card.width - 64, 84)
            T.panel(screen, warn, T.PAPER, T.RED, 250, 16, 3)
            self.text.blit(
                screen,
                "Progresso ainda não foi salvo. Use “Salvar de novo”.",
                warn.center,
                T.SIZES["body"],
                T.RED,
                True,
                "center",
            )
        else:
            self.text.blit(screen, "Curiosidade", (card.left + 38, card.top + 425), T.SIZES["small"], T.TEAL, True)
            self.text.paragraph(
                screen,
                self.fact,
                pygame.Rect(card.left + 38, card.top + 448, card.width - 76, 58),
                T.SIZES["small"],
                T.INK,
                spacing=1.1,
            )
        self.draw_menu(screen)

    def draw_next_build(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        profile = self.app.profile
        next_build = next((item for item in VILLAGE_UPGRADES if item.key not in profile.vila), None)
        T.panel(screen, rect, T.PAPER, T.TEAL, 245, 16, 2)
        if next_build is None:
            screen.blit(T.icon_surface("village", 48, T.TEAL), (rect.left + 10, rect.top + 21))
            self.text.blit(screen, "Vila completa!", (rect.left + 68, rect.top + 12), T.SIZES["body"], T.NAVY, True)
            self.text.blit(
                screen,
                "Todos os espaços ganharam vida.",
                (rect.left + 68, rect.top + 48),
                T.SIZES["small"],
                T.MUTED,
            )
            return
        icon = village_prop(next_build.key, self.app.assets.sprite("watercolor", "village_props"))
        screen.blit(self.scaled(icon, (76, 76), ("next_build", next_build.key)), (rect.left + 48, rect.top + 8))
        self.text.blit(
            screen,
            f"Próxima obra · {next_build.name}",
            (rect.left + 132, rect.top + 10),
            T.SIZES["body"],
            T.NAVY,
            True,
        )
        request = VILLAGE_REQUESTS.get(next_build.key, "A vila pede ajuda!")
        self.text.blit(screen, request, (rect.left + 132, rect.top + 38), T.SIZES["small"], T.TEAL)
        shortfall = missing(profile.recursos, next_build.cost)
        if not shortfall:
            self.text.blit(
                screen,
                "Pronta para construir!",
                (rect.left + 132, rect.top + 62),
                T.SIZES["small"],
                T.GREEN,
                True,
            )
            return
        self.text.blit(screen, "Materiais", (rect.left + 132, rect.top + 62), T.SIZES["small"], T.ORANGE, True)
        x = rect.left + 226
        for waste in WASTE_TYPES:
            needed = next_build.cost.get(waste.key, 0)
            if not needed:
                continue
            icon = self.app.assets.sprite("waste_sprites", waste.sprite)
            if icon is not None:
                screen.blit(self.scaled(icon, (24, 24), ("next-build-waste", waste.key)), (x, rect.top + 68))
            have = profile.recursos.get(waste.key, 0)
            color = T.GREEN if have >= needed else T.ORANGE
            self.text.blit(
                screen,
                f"{have}/{needed}",
                (x + 25, rect.top + 71),
                15,
                color,
                True,
            )
            x += 78

    def draw_missing_parts(self, screen: pygame.Surface, rect: pygame.Rect) -> None:
        T.panel(screen, rect, T.PAPER, T.NAVY, 245, 16, 2)
        required = self.run.biome.required_parts
        self.text.blit(
            screen,
            "Peças para a 3ª estrela",
            (rect.left + 14, rect.top + 8),
            T.SIZES["small"],
            T.NAVY,
            True,
        )
        if not required:
            self.text.blit(
                screen,
                "Nenhuma peça necessária",
                (rect.left + 14, rect.top + 42),
                T.SIZES["small"],
                T.GREEN,
            )
            return
        keys = list(required)
        each = (rect.width - 24) // len(keys)
        for index, key in enumerate(keys):
            level = required[key]
            owned = self.run.parts.get(key, 0)
            x = rect.left + 12 + index * each
            icon_kind = {"estabilizador": "stabilizer", "leme": "rudder", "quilha": "keel"}.get(key, "part")
            color = T.GREEN if owned >= level else T.ORANGE
            screen.blit(T.icon_surface(icon_kind, 38, color), (x, rect.top + 39))
            label = PART_BY_KEY[key].name
            self.text.blit(screen, label, (x + 44, rect.top + 42), T.SIZES["small"], T.INK, True)
            status = "Instalado" if owned >= level else f"Falta nível {level}"
            self.text.blit(screen, status, (x + 44, rect.top + 65), 14, color, True)
