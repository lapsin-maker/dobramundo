"""Base das cenas: menu com permanência, barra de recursos e cabeçalho."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

import pygame

from .. import config as C
from ..content.items import WASTE_TYPES
from ..ui import theme as T
from ..ui.widgets import Button, Menu

if TYPE_CHECKING:
    from ..app import App


class Toast:
    """Aviso curto no rodapé da tela (compra feita, faltam recursos...)."""

    def __init__(self, seconds: float = 3.0) -> None:
        self.seconds = seconds
        self.text = ""
        self.time_left = 0.0

    def show(self, text: str) -> None:
        self.text, self.time_left = text, self.seconds

    def update(self, dt: float) -> None:
        self.time_left = max(0.0, self.time_left - dt)

    def draw(self, screen: pygame.Surface, text: T.Text, center, width: int = 640) -> None:
        if self.time_left <= 0 or not self.text:
            return
        box = pygame.Rect(0, 0, width, 54)
        box.center = center
        T.panel(screen, box, T.PAPER, T.ORANGE, 250, 14, 3)
        label, size = T.fit_text(text, self.text, width - 30, bold=True)
        text.blit(screen, label, box.center, size, T.INK, True, "center")


class Scene:
    music: Optional[str] = "musica_vila"
    idle_warm_up = True  # usa a folga do quadro para preparar sprites
    editor_dwell = False  # telas de edição usam permanência própria mais lenta

    def __init__(self, app: App) -> None:
        self.app = app
        self.menu = Menu()
        self.time = 0.0
        self.last_dt = 1.0 / C.FPS  # dt do último quadro (o cenário de fundo anda com ele)
        self.toast = Toast()
        # Cache de fundo aquarelado usado pela vila e pelo painel de melhorias.
        self.watercolor_backgrounds = {}
        self.watercolor_mix: Optional[pygame.Surface] = None
        self.menu.on_focus = lambda: app.audio.play("sfx_foco", 0.5)  # tique suave ao mirar um botão

    # ----------------------------------------------------------- ciclo
    def enter(self) -> None:
        self.app.audio.music(self.music)
        self.build()

    def leave(self) -> None:
        pass

    def settle_on_close(self) -> None:
        """Conclui efeitos pendentes antes do fechamento normal da plataforma."""

    def build(self) -> None:
        """Monta os botões da tela (chamado ao entrar e quando algo muda)."""

    def back(self) -> None:
        """ESC / Backspace: a maioria das telas volta para a vila."""
        self.goto("vila")

    def fly(self, biome_key: str) -> None:
        """Decola: voo direto ou, com controle corporal ainda não calibrado, a calibração antes."""
        flight = self.app.create_scene("voo", biome_key)
        body = self.app.input.body
        if body is not None and body.error is None and not body.calibrated:
            flight = self.app.create_scene("calibracao", return_to=flight)
        self.app.save()
        self.app.go(flight)

    def goto(self, name: str, *args, **kwargs) -> None:
        """Troca para a cena registrada com esse nome (ver scenes/__init__.py)."""
        self.app.go(self.app.create_scene(name, *args, **kwargs))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
            self.app.audio.play("sfx_selecao", 0.6)
            self.back()
            return
        if self.menu.handle_event(event):
            self.app.audio.play("sfx_selecao")

    def update(self, dt: float) -> None:
        self.time += dt
        self.last_dt = dt
        self.toast.update(dt)
        if self.menu.update(dt, self.app.input.pointer(), self.dwell_time):
            self.app.audio.play("sfx_selecao")

    def draw(self, screen: pygame.Surface) -> None:
        self.draw_menu(screen)

    # --------------------------------------------------------- utilidades
    @property
    def text(self) -> T.Text:
        return self.app.text

    def font(self, size="body", bold: bool = False, hand: bool = False) -> pygame.font.Font:
        """Fonte comum por nome da escala visual ou tamanho explícito."""
        return self.text.font(T.SIZES[size] if isinstance(size, str) else size, bold, hand)

    def button(self, rect, label: str, action: Callable[[], None], **kwargs) -> Button:
        return Button(pygame.Rect(rect), label, action, **kwargs)

    def draw_menu(self, screen: pygame.Surface) -> None:
        dwell = self.dwell_time
        self.menu.draw(screen, self.text, dwell)
        self.menu.draw_pointer(screen, dwell, self.app.input.body_pointer() is not None)

    @property
    def dwell_time(self) -> float:
        if self.editor_dwell:
            return self.app.options.permanencia_editor
        return self.app.options.permanencia

    def title(self, screen: pygame.Surface, title: str, subtitle: str = "") -> None:
        width = (
            max(
                self.font("title", True).size(title)[0],
                self.font("small").size(subtitle)[0],
            )
            + 70
        )
        bar = pygame.Rect(-20, -16, width, 92 if subtitle else 74)
        T.panel(screen, bar, T.PAPER, T.NAVY, 240, 18)
        self.text.blit(screen, title, (24, 6), T.SIZES["title"], T.NAVY, True)
        if subtitle:
            self.text.blit(screen, subtitle, (26, 50), T.SIZES["small"], T.MUTED)

    def resource_bar(
        self, screen: pygame.Surface, right: int = C.WIDTH - 20, top: int = 12, values: Optional[dict] = None
    ) -> None:
        """Os quatro recursos com as cores da coleta seletiva."""
        values = self.app.profile.recursos if values is None else values
        x = right
        for waste in reversed(WASTE_TYPES):
            label = self.text.render(str(values.get(waste.key, 0)), T.SIZES["label"], T.INK, True)
            w = label.get_width() + 46
            x -= w + 8
            box = pygame.Rect(x, top, w, 38)
            T.panel(screen, box, T.PAPER, waste.color, 245, 12, 3)
            icon = self.app.assets.sprite("waste_sprites", waste.sprite)
            dot = pygame.Rect(box.left + 6, box.top + 5, 28, 28)
            if icon is not None:
                screen.blit(self.scaled(icon, dot.size), dot)
            else:
                pygame.draw.circle(screen, waste.color, dot.center, 12)
            screen.blit(label, label.get_rect(midleft=(dot.right + 6, box.centery)))

    @staticmethod
    def fit(surface: pygame.Surface, size) -> tuple:
        ratio = min(size[0] / surface.get_width(), size[1] / surface.get_height())
        return max(1, int(surface.get_width() * ratio)), max(1, int(surface.get_height() * ratio))

    def scaled(self, surface: pygame.Surface, size, key=None) -> pygame.Surface:
        """Cópia reduzida em cache (miniaturas dos menus).

        Sem key, a imagem é identificada pelo id(): use só com imagens dos assets, que
        vivem o jogo inteiro. Imagens montadas na hora (avião pintado, piloto) precisam de
        key, porque o cache delas descarta e um id() poderia se repetir em outra imagem.
        """
        key = (key if key is not None else id(surface), size)
        cache = self.app.view.cache
        hit = cache.scaled.get(("menu",) + key)
        if hit is None:
            hit = pygame.transform.smoothscale(surface, self.fit(surface, size))
            cache.put(("menu",) + key, hit)
        return hit

    def cost_text(self, cost: dict) -> str:
        names = {w.key: w.name for w in WASTE_TYPES}
        return "  ".join(f"{amount} {names[key].lower()}" for key, amount in cost.items())

    def draw_cost(self, screen: pygame.Surface, cost: dict, pos, wallet: Optional[dict] = None) -> int:
        """Ícones e quantidades do custo; vermelho onde faltam recursos. Devolve a largura."""
        wallet = self.app.profile.recursos if wallet is None else wallet
        x, y = pos
        start = x
        for waste in WASTE_TYPES:
            amount = cost.get(waste.key)
            if not amount:
                continue
            pygame.draw.circle(screen, waste.color, (x + 9, y + 10), 9)
            pygame.draw.circle(screen, T.INK, (x + 9, y + 10), 9, 2)
            color = T.INK if wallet.get(waste.key, 0) >= amount else T.RED
            rect = self.text.blit(screen, str(amount), (x + 22, y), T.SIZES["body"], color, True)
            x = rect.right + 12
        return x - start
