"""Ensaio pictográfico, repetível e sem perda de vidas antes da primeira decolagem."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pygame

from .. import config as C
from ..content.biomes import BIOMES
from ..content.items import WASTE_BY_KEY
from ..engine.sprites import project
from ..game.entities import Entity
from ..game.run import FlightRun
from ..input.hub import FLIGHT_KEYS
from ..ui import theme as T
from ..ui.widgets import ring
from . import make_scene
from .base import Scene

MOVE_DISTANCE = 36.0
COLLECT_LANE_DISTANCE = 105.0
UP_TARGET = 120.0
DOWN_TARGET = 60.0
SIDE_TARGET = 112.0
SUCCESS_S = 0.65
OBSTACLE_APPROACH_Z = 450.0
PRACTICE_STEPS = (
    ("move", "Mova o avião", "Use o corpo ou as setas."),
    ("collect", "Pegue o papel", "Chegue até o papel azul."),
    ("up", "Passe por cima", "Suba para passar por cima."),
    ("down", "Passe por baixo", "Desça para passar por baixo."),
    ("side", "Desvie para o lado", "Vá para a esquerda ou para a direita."),
)
DWELL_TARGET = pygame.Rect(330, 214, 440, 225)


def dwell_target_icon(size: int = 64) -> pygame.Surface:
    """Mira pictográfica: anéis concêntricos, cruz e ponto central."""
    image = pygame.Surface((size, size), pygame.SRCALPHA)
    center = (size // 2, size // 2)
    for fraction, color, width in ((0.42, T.NAVY, 4), (0.25, T.TEAL, 4), (0.08, T.ORANGE, 0)):
        radius = int(size * fraction)
        if width:
            pygame.draw.circle(image, color, center, radius, max(2, round(width * size / 64)))
        else:
            pygame.draw.circle(image, color, center, radius)
    arm = int(size * 0.18)
    pygame.draw.line(image, T.NAVY, (center[0] - arm, center[1]), (center[0] + arm, center[1]), 3)
    pygame.draw.line(image, T.NAVY, (center[0], center[1] - arm), (center[0], center[1] + arm), 3)
    return image


class DwellPracticeScene(Scene):
    """Ensina mirar, esperar o anel e sair do alvo antes da primeira personalização."""

    editor_dwell = True
    music = "musica_vila"

    def __init__(self, app, next_scene=None, return_to=None) -> None:
        super().__init__(app)
        self.next_scene = next_scene
        self.return_to = return_to
        self.phase = "aim"
        self.exit_time = 0.0

    def build(self) -> None:
        if self.phase == "aim":
            target_action = self.begin_exit
        else:
            target_action = None
        buttons = [
            self.button(
                DWELL_TARGET,
                "MIRE AQUI",
                target_action,
                key="alvo_treino",
                icon=dwell_target_icon(76),
                color=T.TEAL,
                size=T.SIZES["hero"],
            ),
            self.button(
                (418, 540, 264, 72),
                "Continuar" if self.phase == "leave" else "Pular treino",
                self.finish,
                key="seguir" if self.phase == "leave" else "pular",
                icon=T.icon_surface("next", 34, T.ORANGE),
                color=T.ORANGE,
                size=T.SIZES["label"],
            ),
        ]
        self.menu.set_buttons(buttons, keep_focus=False)

    def begin_exit(self) -> None:
        self.phase = "leave"
        self.exit_time = 0.0
        self.build()

    def finish(self) -> None:
        target = self.next_scene or self.return_to or make_scene(self.app, "vila")
        self.app.go(target)

    def back(self) -> None:
        self.finish()

    def update(self, dt: float) -> None:
        super().update(dt)
        if self.phase != "leave":
            return
        pointer = self.app.input.pointer()
        if pointer is None or DWELL_TARGET.inflate(20, 20).collidepoint(pointer):
            self.exit_time = 0.0
            return
        self.exit_time += dt
        if self.exit_time >= 0.35:
            self.finish()

    def draw(self, screen: pygame.Surface) -> None:
        self.app.backdrop(screen, self.last_dt, None, 18.0)
        T.veil(screen, (16, 35, 52), 104)
        self.title(screen, "Vamos treinar", "Sem voo e sem perder nada")
        if self.phase == "aim":
            instruction = "Mire no alvo e espere o anel completar"
            icon = dwell_target_icon(58)
        else:
            instruction = "Agora afaste o cursor do alvo"
            icon = T.icon_surface("next", 58, T.ORANGE)
        panel = pygame.Rect(180, 114, 740, 70)
        T.panel(screen, panel, T.PAPER, T.TEAL, 245, 18, 3)
        screen.blit(icon, icon.get_rect(midleft=(panel.left + 14, panel.centery)))
        self.text.blit(screen, instruction, (panel.left + 88, panel.centery), T.SIZES["label"], T.NAVY, True, "midleft")
        if self.phase == "leave":
            start_x, y = DWELL_TARGET.right + 12, DWELL_TARGET.centery
            pygame.draw.line(screen, T.ORANGE, (start_x, y), (start_x + 48, y), 8)
            pygame.draw.polygon(
                screen,
                T.ORANGE,
                [(start_x + 70, y), (start_x + 38, y - 22), (start_x + 38, y + 22)],
            )
        self.draw_menu(screen)
        if self.phase == "aim" and (self.menu.hover is None or self.menu.hover.key != "alvo_treino"):
            # Um arco parado antecipa a ação antes da criança pousar o cursor.
            ring(screen, (DWELL_TARGET.right - 62, DWELL_TARGET.top + 58), 30, 7, 0.76, T.TEAL)


@dataclass
class Trial:
    entity: Entity
    kind: str


class TutorialScene(Scene):
    """Treino prático: move, coleta e testa as três manobras sem pontuação real."""

    music = "musica_vila"
    idle_warm_up = False

    def __init__(self, app, next_scene=None, return_to=None) -> None:
        super().__init__(app)
        self.next_scene = next_scene
        self.return_to = return_to
        self.run = FlightRun(BIOMES["amazonia"], app.profile.modo, app.profile.pecas, focus=False)
        self.run.invincible = True
        self.run.player.x = 0.0
        self.run.player.y = C.REST_ALTITUDE
        self.run.player.vx = self.run.player.vy = 0.0
        self.run.world.entities.clear()
        self.run.world.pending_lessons.clear()
        self.run.world.spawn_pattern = lambda _z: None  # type: ignore[method-assign]
        self.step_index = 0
        self.trial: Optional[Trial] = None
        self.feedback = 0.0
        self.paused = False
        self._origin = (0.0, C.REST_ALTITUDE)
        self._start_step()

    def build(self) -> None:
        if self.paused:
            buttons = [
                self.button(
                    (280, 570, 250, 64),
                    "Continuar",
                    self.resume,
                    key="continuar",
                    icon=T.icon_surface("next", 32, T.GREEN),
                ),
                self.button(
                    (570, 570, 250, 64),
                    "Voltar ao mapa",
                    self.back,
                    key="mapa",
                    icon=T.icon_surface("village", 32, T.NAVY),
                ),
            ]
        else:
            buttons = [
                self.button(
                    (64, 570, 264, 64),
                    "Voltar ao mapa",
                    self.back,
                    key="mapa",
                    icon=T.icon_surface("village", 32, T.NAVY),
                ),
                self.button(
                    (418, 570, 264, 64),
                    "Seguir",
                    self.advance_step,
                    key="avancar",
                    icon=T.icon_surface("next", 32, T.NAVY),
                ),
                self.button(
                    (772, 570, 264, 64),
                    "Pular treino",
                    self.skip,
                    key="pular",
                    icon=T.icon_surface("paper", 32, T.ORANGE),
                ),
            ]
        self.menu.set_buttons(buttons, keep_focus=False)

    def _start_step(self) -> None:
        # A seta mantida ao concluir uma lição não pode pilotar a próxima às cegas.
        self.app.input.clear_keys()
        player = self.run.player
        player.x, player.y = 0.0, C.REST_ALTITUDE
        player.vx = player.vy = player.cam_x = 0.0
        self._origin = (player.x, player.y)
        self.feedback = 0.0
        self.run.world.entities.clear()
        self.trial = None
        kind = PRACTICE_STEPS[self.step_index][0]
        if kind == "collect":
            waste = WASTE_BY_KEY["papel"]
            entity = Entity(C.PLAYER_Z + 240.0, 1, "waste", C.REST_ALTITUDE, waste.sprite)
            self._add_trial(entity, kind)
        elif kind in ("up", "down", "side"):
            spec = self.run.biome.industrial_obstacles[kind_to_obstacle(kind)][0]
            entity = Entity(C.PLAYER_Z + OBSTACLE_APPROACH_Z, 0, kind_to_obstacle(kind), 0.0, spec.sprite, spec)
            self._add_trial(entity, kind)

    def _add_trial(self, entity: Entity, kind: str) -> None:
        self.run.world.entities.append(entity)
        self.trial = Trial(entity, kind)

    def _replace_trial(self) -> None:
        if self.trial is None:
            return
        old = self.trial
        self.run.world.entities = [entity for entity in self.run.world.entities if entity is not old.entity]
        entity = old.entity
        entity.z = C.PLAYER_Z + (240.0 if old.kind == "collect" else OBSTACLE_APPROACH_Z)
        entity.collected = entity.hit = entity.passed = False
        self.run.world.entities.append(entity)

    def _target_reached(self) -> bool:
        player = self.run.player
        kind = PRACTICE_STEPS[self.step_index][0]
        if kind == "move":
            return abs(player.x - self._origin[0]) >= MOVE_DISTANCE or abs(player.y - self._origin[1]) >= MOVE_DISTANCE
        if kind == "collect":
            return self.trial is not None and self.trial.entity.collected
        if kind == "up":
            return (
                self.trial is not None
                and self.trial.entity.passed
                and not self.trial.entity.hit
                and player.y >= UP_TARGET
            )
        if kind == "down":
            return (
                self.trial is not None
                and self.trial.entity.passed
                and not self.trial.entity.hit
                and player.y <= DOWN_TARGET
            )
        if kind == "side":
            return (
                self.trial is not None
                and self.trial.entity.passed
                and not self.trial.entity.hit
                and abs(player.x) >= SIDE_TARGET
            )
        return False

    def _check_trial(self) -> None:
        if self.feedback > 0.0:
            return
        if self._target_reached():
            self.feedback = SUCCESS_S
            if self.trial is not None and self.trial.entity.spec is not None:
                # O sucesso já foi registrado; não deixe a peça em primeiro plano
                # cobrir o painel enquanto a criança recebe o retorno visual.
                passed_entity = self.trial.entity
                self.run.world.entities = [entity for entity in self.run.world.entities if entity is not passed_entity]
            self.app.audio.play("sfx_estrela", 0.65)
            return
        if self.trial is None:
            return
        entity, kind = self.trial.entity, self.trial.kind
        if kind != "collect" and entity.passed and not entity.hit:
            if self._target_reached():
                self.feedback = SUCCESS_S
                self.app.audio.play("sfx_estrela", 0.65)
                return
            self._replace_trial()
        elif kind == "collect" and entity.z < C.PLAYER_Z + 10.0 and not entity.collected:
            self._replace_trial()
        elif kind != "collect" and entity.z < C.PLAYER_Z - 30.0:
            self._replace_trial()

    def update(self, dt: float) -> None:
        self.time += dt
        self.last_dt = dt
        self.toast.update(dt)
        if self.menu.update(dt, self.app.input.pointer(), self.app.options.permanencia):
            self.app.audio.play("sfx_selecao")
        if self.app.next_scene is not None or self.paused:
            return
        ix, iy, target = self.app.input.flight_command()
        self.run.update(dt, ix, iy, target)
        self.run.take_events()  # treino não lança recompensas, alertas ou eventos no voo real
        self._check_trial()
        if self.feedback > 0.0:
            self.feedback = max(0.0, self.feedback - dt)
            if self.feedback == 0.0:
                self.advance_step()

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.back()
                return
            if event.key == pygame.K_p:
                self.paused = not self.paused
                self.build()
                return
            if event.key in FLIGHT_KEYS and not self.paused:
                return  # a entrada já está no InputHub; setas não trocam o foco do menu
        if self.menu.handle_event(event):
            self.app.audio.play("sfx_selecao")

    def advance_step(self) -> None:
        if self.step_index + 1 >= len(PRACTICE_STEPS):
            self.finish()
            return
        self.step_index += 1
        self._start_step()
        self.build()

    def skip(self) -> None:
        self.finish()

    def finish(self) -> None:
        self.app.profile.tutorial_visto = True
        self.app.save()
        next_scene = self.next_scene or make_scene(self.app, "vila")
        self.app.go(next_scene)

    def back(self) -> None:
        self.app.go(self.return_to or make_scene(self.app, "mapa"))

    def resume(self) -> None:
        self.paused = False
        self.build()

    def draw(self, screen: pygame.Surface) -> None:
        self.app.view.draw_run(screen, self.run, self.app.plane_look())
        player_x, player_y, scale = project(self.run.player.x, self.run.player.y, C.PLAYER_Z, self.app.view.cam)
        player_x, player_y = self.app.view.screen_point((player_x, player_y))
        zoom = C.WIDTH / max(1, self.app.view.viewport.width)
        pygame.draw.circle(screen, T.SUN, (int(player_x), int(player_y)), max(34, int(42 * scale * zoom)), 3)

        step_kind, title, subtitle = PRACTICE_STEPS[self.step_index]
        if self.feedback <= 0.0:
            self._draw_action_cue(screen, step_kind, player_x, player_y, zoom)
        panel = pygame.Rect(250, 16, 600, 112)
        T.panel(screen, panel, T.PAPER, T.NAVY, 245, 20, 3)
        icon = self._step_icon(step_kind)
        screen.blit(icon, icon.get_rect(midleft=(panel.left + 22, panel.centery)))
        self.text.blit(
            screen,
            f"Treino · {self.step_index + 1}/{len(PRACTICE_STEPS)}",
            (panel.left + 118, panel.top + 12),
            T.SIZES["small"],
            T.MUTED,
            True,
        )
        self.text.blit(screen, title, (panel.left + 118, panel.top + 34), T.SIZES["title"], T.NAVY, True)
        self.text.blit(screen, subtitle, (panel.left + 118, panel.top + 78), T.SIZES["body"], T.INK, True)
        self._draw_life_badge(screen)
        if self.feedback > 0.0:
            feedback_y = 250 if player_y > 360 else 430
            T.panel(screen, pygame.Rect(390, feedback_y, 320, 72), T.PAPER, T.GREEN, 245, 18, 3)
            self.text.blit(
                screen, "Muito bem!", (550, feedback_y + 36), T.SIZES["label"], T.GREEN, True, "center"
            )
        if self.paused:
            T.veil(screen, (10, 18, 40), 170)
            T.panel(screen, pygame.Rect(330, 198, 440, 230), T.PAPER, T.NAVY, 250, 24, 4)
            self.text.blit(screen, "Treino pausado", (550, 250), T.SIZES["hero"], T.NAVY, True, "center")
            self.text.blit(screen, "P para continuar", (550, 302), T.SIZES["body"], T.INK, anchor="center")
        self.draw_menu(screen)

    def _step_icon(self, kind: str) -> pygame.Surface:
        if kind == "collect":
            sprite = self.app.assets.sprite("waste_sprites", "papel")
            icon = self.scaled(sprite, (52, 52), ("tutorial", "papel")) if sprite is not None else T.icon_surface(
                "paper", 52, T.TEAL
            )
            surface = pygame.Surface((72, 72), pygame.SRCALPHA)
            surface.blit(icon, (0, 10))
            self._draw_arrow(surface, (58, 36), (1, 0), 16)
            return surface
        surface = pygame.Surface((72, 72), pygame.SRCALPHA)
        if kind == "move":
            surface.blit(T.icon_surface("paper", 42, T.TEAL), (15, 15))
            self._draw_arrow(surface, (36, 7), (0, -1), 12)
            self._draw_arrow(surface, (36, 65), (0, 1), 12)
            self._draw_arrow(surface, (7, 36), (-1, 0), 12)
            self._draw_arrow(surface, (65, 36), (1, 0), 12)
        elif kind == "up":
            self._draw_arrow(surface, (36, 36), (0, -1), 27)
        elif kind == "down":
            self._draw_arrow(surface, (36, 36), (0, 1), 27)
        else:
            self._draw_arrow(surface, (20, 36), (-1, 0), 20)
            self._draw_arrow(surface, (52, 36), (1, 0), 20)
        return surface

    def _draw_action_cue(
        self, screen: pygame.Surface, kind: str, player_x: float, player_y: float, zoom: float = 1.0
    ) -> None:
        """Setas grandes ligam a instrução pictográfica ao avião e ao alvo real."""
        if kind == "move":
            self._draw_arrow(screen, (player_x, player_y - 100 * zoom), (0, -1), 32 * zoom)
            self._draw_arrow(screen, (player_x, player_y + 100 * zoom), (0, 1), 32 * zoom)
            self._draw_arrow(screen, (player_x - 150 * zoom, player_y), (-1, 0), 32 * zoom)
            self._draw_arrow(screen, (player_x + 150 * zoom, player_y), (1, 0), 32 * zoom)
        elif kind == "collect" and self.trial is not None:
            target_x, target_y, _ = project(
                self.trial.entity.x, self.trial.entity.y, self.trial.entity.z, self.app.view.cam
            )
            target_x, target_y = self.app.view.screen_point((target_x, target_y))
            self._draw_link_arrow(screen, (player_x, player_y), (target_x, target_y))
        elif kind == "up":
            self._draw_arrow(screen, (player_x + 180 * zoom, player_y + 30 * zoom), (0, -1), 38 * zoom)
        elif kind == "down":
            self._draw_arrow(screen, (player_x + 180 * zoom, player_y + 30 * zoom), (0, 1), 38 * zoom)
        elif kind == "side":
            self._draw_arrow(screen, (player_x - 170 * zoom, player_y), (-1, 0), 38 * zoom)
            self._draw_arrow(screen, (player_x + 170 * zoom, player_y), (1, 0), 38 * zoom)

    @staticmethod
    def _draw_arrow(screen: pygame.Surface, center, direction, size: float) -> None:
        cx, cy = center
        ux, uy = direction
        px, py = -uy, ux

        def point(along: float, across: float):
            return (int(cx + ux * along + px * across), int(cy + uy * along + py * across))

        points = [
            point(size, 0),
            point(size * 0.12, size * 0.72),
            point(size * 0.12, size * 0.30),
            point(-size, size * 0.30),
            point(-size, -size * 0.30),
            point(size * 0.12, -size * 0.30),
            point(size * 0.12, -size * 0.72),
        ]
        pygame.draw.polygon(screen, T.NAVY, points)
        inset = [(cx + (x - cx) * 0.78, cy + (y - cy) * 0.78) for x, y in points]
        pygame.draw.polygon(screen, T.SUN, inset)

    @classmethod
    def _draw_link_arrow(cls, screen: pygame.Surface, start, target) -> None:
        dx, dy = target[0] - start[0], target[1] - start[1]
        distance = (dx * dx + dy * dy) ** 0.5
        if distance < 72:
            return
        ux, uy = dx / distance, dy / distance
        origin = (start[0] + ux * 48, start[1] + uy * 48)
        tip = (target[0] - ux * 34, target[1] - uy * 34)
        cls._draw_arrow(screen, ((origin[0] + tip[0]) / 2, (origin[1] + tip[1]) / 2), (ux, uy), min(42, distance / 3))

    def _draw_life_badge(self, screen: pygame.Surface) -> None:
        box = pygame.Rect(930, 16, 152, 64)
        T.panel(screen, box, T.PAPER, T.GREEN, 240, 16, 2)
        for i in range(C.MAX_LIVES):
            x, y = box.left + 34 + i * 40, box.centery
            wing = [(x - 13, y + 8), (x + 14, y - 9), (x + 2, y + 8)]
            pygame.draw.polygon(screen, T.WHITE, wing)
            pygame.draw.polygon(screen, T.GREEN, wing, 2)
            pygame.draw.line(screen, T.GREEN, (x + 2, y + 8), (x + 14, y - 9), 2)


def kind_to_obstacle(kind: str) -> str:
    return {"up": "low", "down": "gate", "side": "tower"}[kind]
