"""Voo: a fase em si, com HUD, pausas (supervisor e automática) e trilha por estágio."""

from __future__ import annotations

import math
import secrets
from typing import Dict, List, Optional, Tuple

import pygame

from .. import config as C
from ..content import texts
from ..content.biomes import BIOMES
from ..content.items import WASTE_TYPES
from ..content.planes import load_maneuvers
from ..content.progress import PART_BY_KEY, STAR_THRESHOLDS, VILLAGE_UPGRADES, parts_ok
from ..engine.sprites import project
from ..game.run import FlightRun
from ..game.settlement import apply_run, notify_settlement
from ..ui import theme as T
from ..ui.widgets import row
from .base import Scene
from .flight_hud import FlightHUDMixin

RESUME_COUNTDOWN = 3.0
FOCUS_SOUNDS = {"foco": "sfx_desvio_alerta", "foco_ok": "sfx_desvio_ok", "foco_quase": "sfx_desvio_quase"}
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


class FlightScene(FlightHUDMixin, Scene):
    idle_warm_up = False

    def __init__(
        self,
        app,
        biome_key: str,
        seed: Optional[int] = None,
        mode: Optional[str] = None,
        session_limit_s: Optional[int] = None,
        exploration: Optional[bool] = None,
        predictable_assistance: Optional[bool] = None,
        intro_override: Optional[bool] = None,
        community_challenge: Optional[bool] = None,
        mission_preferred_waste: Optional[str] = None,
        mission_preference_fixed: bool = False,
    ) -> None:
        super().__init__(app)
        self.biome = BIOMES[biome_key]
        p = app.profile
        # abertura didática: sempre no Normal; no Difícil, só no primeiro voo da fase
        flight_mode = mode if mode in ("normal", "dificil") else p.modo
        intro = (
            intro_override
            if intro_override is not None
            else flight_mode == "normal" or p.voos_fase.get(biome_key, 0) == 0
        )
        option_seed = app.options.semente_desafio
        flight_seed = seed if seed is not None else option_seed if option_seed > 0 else secrets.randbits(32)
        limit = app.options.limite_voo_s if session_limit_s is None else session_limit_s
        explore = app.options.modo_exploracao if exploration is None else exploration
        city_restoration = p.transformacao_cidades.get(biome_key)
        if city_restoration is None:
            old_stars = min(3, max(0, p.estrelas.get(biome_key, 0)))
            city_restoration = STAR_THRESHOLDS[old_stars - 1] if old_stars else C.START_RESTORATION
        assisted = (
            app.options.assistencia_previsivel or (not p.apoio_escolhido and p.voos < 3)
            if predictable_assistance is None
            else predictable_assistance
        )
        community = (seed is None and option_seed > 0) if community_challenge is None else community_challenge
        if mission_preference_fixed:
            preferred_waste = mission_preferred_waste
        elif community:
            next_build = next((item for item in VILLAGE_UPGRADES if item.key not in p.vila), None)
            shortages = (
                {
                    key: amount - p.recursos.get(key, 0)
                    for key, amount in next_build.cost.items()
                    if p.recursos.get(key, 0) < amount
                }
                if next_build is not None
                else {}
            )
            preferred_waste = max(shortages, key=shortages.get) if shortages else None
        else:
            preferred_waste = None
        self.run = FlightRun(
            self.biome,
            flight_mode,
            p.pecas,
            maneuvers(),
            intro=intro,
            focus=app.options.momento_foco,
            seed=flight_seed,
            session_limit_s=limit,
            exploration=explore,
            predictable_assistance=assisted,
            community_challenge=community,
            mission_preferred_waste=preferred_waste,
            city_restoration=city_restoration,
            starting_stars=p.estrelas.get(biome_key, 0),
        )
        self.look = app.plane_look()
        self.paused = False
        self.auto_paused = False
        self.countdown = 0.0
        self.banners: List[Banner] = []
        self.banner_occluded = False
        self.flash = 0.0
        self.shake = 0.0
        self.celebration = 0.0
        self.cam_surface: Optional[pygame.Surface] = None
        self.cam_bytes: Optional[bytes] = None
        self.music = self.stage_music(0)
        self.started = False
        self.departure_announced = False

    def stage_music(self, stage: int) -> str:
        return f"musica_{self.biome.music}_{stage + 1}"

    def enter(self) -> None:
        """Também é chamado ao voltar da recalibração: a trilha segue o estágio atual e a
        decolagem (som e aviso da cidade) só acontece na primeira entrada."""
        self.music = self.stage_music(self.run.stage)
        super().enter()
        self.app.view.set_biome(self.biome)
        self.app.view.prepare_look(self.look)
        self.app.view.prepare_first_frame(self.run, self.look)
        self.app.input.resync_keys()

    # ------------------------------------------------------------- pausa
    def build(self) -> None:
        if not self.paused:
            self.menu.set_buttons([])
            return
        rects = row(pygame.Rect(C.WIDTH // 2 - 390, 500, 780, 70), 3)
        buttons = [
            self.button(rects[0], texts.UI["continuar"], self.resume),
            self.button(rects[1], "Recalibrar", self.recalibrate, enabled=self.app.input.uses_body),
            self.button(rects[2], "Encerrar voo", self.quit_to_village),
        ]
        self.menu.set_buttons(buttons, keep_focus=False)

    def pause(self, auto: bool = False) -> None:
        if self.paused or self.run.finished:
            return
        self.paused = True
        self.run.pause_count += 1
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
        if not self.started:
            self.goto("vila")
            return
        if not self.run.complete and not self.run.game_over:
            self.run.interrupted = True
        self.run.finished = True
        self.goto("resultado", self.run)

    def settle_on_close(self) -> None:
        """Credita uma partida em andamento antes de a janela fechar; seguro para repetir."""
        # Core também consulta a cena pendente no shutdown: ela pode ser um voo
        # recém-agendado, que nunca entrou nem chegou a começar.
        if not self.started:
            return
        if not self.run.complete and not self.run.game_over:
            self.run.interrupted = True
        self.run.finished = True
        apply_run(self.app.profile, self.run)
        self.app.save()
        notify_settlement(self.app, self.run)

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
        if self.run.finished:
            if self.app.next_scene is None:
                self.goto("resultado", self.run)
            return
        hub = self.app.input
        if not self.paused and hub.out_of_area():
            self.pause(auto=True)
        if self.paused:
            self.run.pause_duration_s += max(0.0, dt)
            if self.auto_paused and hub.back_in_area():
                self.countdown += dt  # retomada automática com contagem
                if self.countdown >= RESUME_COUNTDOWN:
                    self.resume()
            else:
                self.countdown = 0.0
            if self.menu.update(dt, hub.pointer(), self.app.options.permanencia):
                self.app.audio.play("sfx_selecao")
            return
        if self.app.view.warmup_pending:
            # Aquecimento de renderização não consome tempo/vidas do voo.
            return
        body = hub.body
        if (
            self.app.profile.controle != "teclado"
            and body is not None
            and body.calibrated
            and body.error is None
            and not body.visible
            and not hub.held()
        ):
            # Durante a janela que antecede a pausa automática, um snapshot corporal
            # perdido não deixa o avião estacionado receber uma colisão.
            return
        if not self.started:
            self.started = True
            if not self.departure_announced:
                self.departure_announced = True
                self.app.audio.play("sfx_decolagem")
                theme = self.run.world.challenge_theme
                title = theme.title if theme is not None else f"{self.biome.city} — {self.biome.name}"
                subtitle = (
                    f"Desafio comunitário · semente {self.run.seed}" if theme is not None else texts.STAGE_MESSAGES[0]
                )
                self.banners.append(Banner(title, subtitle, T.WHITE, 3.2))
        ix, iy, target = hub.flight_command()
        if hub.body_ready:
            self.run.record_movement(dt, hub.body.axes())
        self.run.update(dt, ix, iy, target)
        self.handle_run_events()
        for banner in self.banners:
            if not self.banner_occluded:
                banner.ttl -= dt
        self.banners = [b for b in self.banners if b.ttl > 0]
        self.flash = max(0.0, self.flash - dt)
        self.shake = max(0.0, self.shake - dt)
        self.celebration = max(0.0, self.celebration - dt)
        if self.run.finished:
            self.goto("resultado", self.run)

    def handle_run_events(self) -> None:
        audio = self.app.audio
        for name, data in self.run.take_events():
            if name in ("star", "mission", "complete"):
                self.celebration = 1.8
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
            elif name == "mission_expired":
                self.banners.append(
                    Banner("Outra meta vem aí", "Esta não deu; nenhum recurso foi perdido.", T.TEAL, 2.4)
                )
            elif name == "complete":
                audio.play("sfx_fim_fase")
                self.banners.append(Banner(f"{self.biome.city} solarpunk!", "A cidade se transformou.", T.SUN, 3.0))
            elif name == "session_end":
                self.banners.append(
                    Banner("Tempo combinado", "Este voo terminou. Veja as conquistas no resultado.", T.TEAL, 2.5)
                )
            elif name == "exploration_continue":
                self.banners.append(
                    Banner("Vamos continuar", "No modo Explorar, as batidas não encerram o voo.", T.TEAL, 2.2)
                )
            elif name == "game_over":
                audio.play("sfx_game_over")

    def draw(self, screen: pygame.Surface) -> None:
        if self.app.view.warmup_pending:
            screen.fill((230, 239, 235))
            card = pygame.Rect(C.WIDTH // 2 - 250, C.HEIGHT // 2 - 86, 500, 172)
            T.panel(screen, card, T.PAPER, T.NAVY, 248, 24, 3)
            label = "Preparando seu voo"
            self.text.blit(screen, label, (card.centerx, card.top + 45), T.SIZES["title"], T.NAVY, True, "center")
            bar = pygame.Rect(card.left + 64, card.top + 112, card.width - 128, 18)
            pygame.draw.rect(screen, (222, 215, 197), bar, border_radius=9)
            fill = bar.copy()
            fill.width = round(bar.width * max(0.0, min(1.0, self.app.view.warmup_progress)))
            if fill.width:
                pygame.draw.rect(screen, T.TEAL, fill, border_radius=9)
            if self.paused:
                self.draw_pause(screen)
            return
        view = self.app.view
        view.draw_run(screen, self.run, self.look, celebration=self.celebration)
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
        if self.celebration > 0 and self.run.focus.state != "pending":
            player = self.run.player
            sx, sy, _ = project(player.x, player.y, C.PLAYER_Z, view.cam)
            sx, sy = view.screen_point((sx, sy))
            # Mesmo selo estático no movimento reduzido; a recompensa continua
            # visível sem balanço, flash nem necessidade de escutar a fanfarra.
            center = (max(30, min(C.WIDTH - 30, round(sx))), max(244, round(sy) - 105))
            screen.blit(T.icon_surface("reward", 48, T.NAVY), (center[0] - 24, center[1] - 24))
        self.draw_banners(screen)
        self.draw_camera(screen)
        if self.paused:
            self.draw_pause(screen)

    # --------------------------------------------------------------- HUD
    def draw_pause(self, screen: pygame.Surface) -> None:
        T.veil(screen, (10, 18, 40), 170)
        card = pygame.Rect(C.WIDTH // 2 - 420, 82, 840, 520)
        T.panel(screen, card, T.PAPER, T.NAVY, 250, 22, 4)
        if self.auto_paused:
            title = "Pausa automática"
            body = self.app.input.body
            if body is not None and body.error is not None:
                sub = "A câmera parou. Recalibre; na calibração, escolha Teclado para continuar."
            elif body is not None and not body.receiving:
                sub = "Aguardando a câmera. Mantenha-se visível para continuar."
            elif body is not None and not body.calibrated:
                sub = "Calibre novamente para continuar com o corpo."
            elif self.app.input.back_in_area():
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
