"""Renderiza o piloto em aquarela e o encaixa no avião.

As poses pintadas e os atlases modulares de cabelo/dispositivos são opcionais;
o desenho procedural de papel segue como fallback. ``anchors.json`` mantém o
posicionamento por modelo de avião, e as PNGs legadas seguem para compatibilidade.
"""

from __future__ import annotations

from typing import Optional, Tuple

import pygame

from ..content.pilot import SKIN_CHOICES, UNSELECTED, find_option, normalize_pilot
from .assets import Assets
from .cache import BoundedCache
from .painted_pilot import PaintedPilot
from .paper_pilot import draw_pilot

FOLDER = "pilot_layers"
MIN_PILOT_SHARE = 0.32  # leitura do piloto acima da escala do avião durante o voo
EXPRESSIONS = {"curious", "focused", "happy", "recover"}


def _expression_layer(size: Tuple[int, int], look: dict, pose: str, expression: str) -> pygame.Surface:
    """Expressão facial leve, composta uma vez por variante e mantida no cache.

    A base pintada é preservada. Os traços 2x acompanham as âncoras usadas pelos
    olhos personalizáveis no atlas Sprint 2, sem fazer trabalho por quadro.
    """
    width, height = size
    if expression not in EXPRESSIONS or pose.startswith("back_"):
        return pygame.Surface(size, pygame.SRCALPHA)
    layer = pygame.Surface((width * 2, height * 2), pygame.SRCALPHA)
    seated = pose.endswith("seated")
    mobility_ratio = 0.24 if look.get("cadeira") == "sim" else 0.30 if look.get("andador") == "sim" else 0.0
    body_width = max(1, round(width / (1 + 2 * mobility_ratio)))
    pad = (width - body_width) / 2
    eye_x = (0.333, 0.647) if seated else (0.377, 0.639)
    eye_y = (0.178 if seated else 0.144) * height
    centers = [(round(pad + body_width * x), round(eye_y)) for x in eye_x]
    mouth_x = round(pad + body_width * 0.50)
    mouth_y = round(height * (0.248 if seated else 0.218))
    q = 2
    ink = (48, 54, 76, 235)
    skin_rgb = find_option(SKIN_CHOICES, look.get("pele", UNSELECTED)).color or (243, 230, 210)
    if look.get("pele", UNSELECTED) == UNSELECTED:
        skin_rgb = (243, 230, 210)
    skin = (*skin_rgb, 190)

    def line(points, color, thickness):
        pygame.draw.lines(layer, color, False,
                          [(round(x * q), round(y * q)) for x, y in points],
                          max(1, round(thickness * q)))

    def arc(rect, start, stop, color, thickness):
        scaled = pygame.Rect(*(round(v * q) for v in rect))
        pygame.draw.arc(layer, color, scaled, start, stop, max(1, round(thickness * q)))

    # Keep the expression marks broad enough to read at the normal menu scale.
    brow_y = eye_y - height * 0.035
    brow_dx = body_width * 0.035
    if expression == "focused":
        for side, (cx, _) in enumerate(centers):
            direction = 1 if side == 0 else -1
            line([(cx - brow_dx, brow_y - height * 0.006),
                  (cx + brow_dx, brow_y + height * 0.008 * direction)], ink, max(2, height * 0.006))
    elif expression == "curious":
        for cx, _ in centers:
            arc((cx - brow_dx, brow_y - height * 0.018, 2 * brow_dx, height * 0.035), 0.25, 2.9, ink,
                max(2, height * 0.006))
    elif expression == "recover":
        for side, (cx, _) in enumerate(centers):
            direction = -1 if side == 0 else 1
            line([(cx - brow_dx, brow_y + height * 0.006 * direction),
                  (cx + brow_dx, brow_y - height * 0.014)], ink, max(2, height * 0.006))

    # Blend a small skin wash over the base smile before drawing the new mouth.
    wash = pygame.Surface((width * q, height * q), pygame.SRCALPHA)
    pygame.draw.ellipse(wash, skin, pygame.Rect(
        (mouth_x - round(body_width * 0.065)) * q,
        (mouth_y - round(height * 0.018)) * q,
        max(2, round(body_width * 0.13) * q),
        max(2, round(height * 0.058) * q),
    ))
    layer.blit(wash, (0, 0))
    if expression == "curious":
        pygame.draw.ellipse(layer, ink, pygame.Rect(
            (mouth_x - round(height * 0.012)) * q,
            (mouth_y - round(height * 0.014)) * q,
            max(3, round(height * 0.024) * q), max(3, round(height * 0.034) * q),
        ), max(1, round(height * 0.004) * q))
    elif expression == "focused":
        line([(mouth_x - body_width * 0.045, mouth_y), (mouth_x + body_width * 0.045, mouth_y)], ink,
             max(2, height * 0.006))
    elif expression == "recover":
        arc((mouth_x - body_width * 0.045, mouth_y - height * 0.002,
             body_width * 0.09, height * 0.026), 3.3, 6.1, ink, max(2, height * 0.006))
    else:  # happy: a broad, visibly upturned smile
        arc((mouth_x - body_width * 0.058, mouth_y - height * 0.026,
             body_width * 0.116, height * 0.056), 3.45, 5.95, (153, 68, 75, 240), max(2, height * 0.008))
    return pygame.transform.smoothscale(layer, size)


class PilotRenderer:
    def __init__(self, assets: Assets) -> None:
        self.assets = assets
        self.anchors = assets.json(FOLDER, "anchors.json") or {}
        self.painted = PaintedPilot(assets)
        self.cache = BoundedCache(32)  # piloto montado por vista e aparência
        self.expression_cache = BoundedCache(16)

    def compose(self, view: str, look: dict, pose: Optional[str] = None,
                expression: Optional[str] = None) -> Optional[pygame.Surface]:
        """Piloto 2D de papel, independente das antigas camadas low-poly."""
        look = normalize_pilot(look)
        key = (view, pose, tuple(sorted(look.items())))
        cached = self.cache.get(key)
        if cached is not None:
            canvas = cached
        else:
            canvas = self.painted.compose(view, look, pose=pose)
            if canvas is None:
                canvas = draw_pilot(view, look)
            self.cache[key] = canvas
        if expression not in EXPRESSIONS:
            return canvas
        pose_key = self.painted.pose_key(view, look, pose)
        expression_key = (key, pose_key, expression)
        expressed = self.expression_cache.get(expression_key)
        if expressed is not None:
            return expressed
        expressed = canvas.copy()
        expressed.blit(_expression_layer(canvas.get_size(), look, pose_key, expression), (0, 0))
        self.expression_cache[expression_key] = expressed
        return expressed

    def anchor(self, plane: str, view: str) -> Optional[Tuple[int, int, int, int]]:
        box = self.anchors.get(view, {}).get(plane)
        return tuple(box) if box and len(box) == 4 else None  # type: ignore[return-value]

    def mount(
        self,
        plane_surface: pygame.Surface,
        plane: str,
        view: str,
        look: dict,
        *,
        pilot_pose: Optional[str] = None,
    ) -> pygame.Surface:
        """Avião + piloto. Sem camadas geradas, devolve o avião como está.

        O corpo do piloto (caixa "body" do anchors.json, sem cabelo nem cadeira) é
        escalado para a altura da caixa do avião e alinhado pelo centro da base.
        """
        pilot = self.compose(view, look, pose=pilot_pose)
        box = self.anchor(plane, view)
        body = self.anchors.get("body", {}).get(view)
        if pilot is None or box is None or not body:
            return plane_surface
        x0, y0, x1, y1 = box
        y0 = min(y0, y1 - int(plane_surface.get_height() * MIN_PILOT_SHARE))  # 14-Bis: boneco quase escondido
        bx0, by0, bx1, by1 = body
        scale = max(4, y1 - y0) / max(1, by1 - by0)
        size = (max(2, int(pilot.get_width() * scale)), max(2, int(pilot.get_height() * scale)))
        pilot_scaled = pygame.transform.smoothscale(pilot, size)
        left = int((x0 + x1) / 2 - (bx0 + bx1) / 2 * scale)
        top = int(y1 - by1 * scale)
        pad_top = max(0, -top)
        pad_left = max(0, -left)
        pad_right = max(0, left + size[0] - plane_surface.get_width())
        pad_bottom = max(0, top + size[1] - plane_surface.get_height())
        out = pygame.Surface(
            (plane_surface.get_width() + pad_left + pad_right, plane_surface.get_height() + pad_top + pad_bottom),
            pygame.SRCALPHA,
        )
        out.blit(plane_surface, (pad_left, pad_top))
        out.blit(pilot_scaled, (left + pad_left, top + pad_top))
        return out
