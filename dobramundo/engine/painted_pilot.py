"""Optional watercolor base art for the pilot; procedural renderer remains fallback."""

from __future__ import annotations

import colorsys
import math
from typing import Mapping, Optional, Tuple

import pygame

from ..content.pilot import (
    EYE_COLORS,
    HAIR_COLORS,
    SHIRT_COLORS,
    SKIN_CHOICES,
    UNSELECTED,
    find_option,
    normalize_pilot,
)
from .assets import Assets
from .cache import BoundedCache

BASE_FOLDER = "watercolor"
ATLAS_KEY = "pilot_base"
POSES = {
    "menu": ("front_standing", "front_seated"),
    "flight": ("back_standing", "back_seated"),
    "segura": ("front_standing", "front_seated"),
    "lanca": ("front_standing", "front_seated"),
}
# These are the matte colors requested for the first watercolor atlas. The
# constructor accepts new keys once the delivered atlas defines exact swatches.
DEFAULT_SKIN_KEY = (252, 193, 128)
DEFAULT_SHIRT_KEY = (162, 200, 225)
HAIR_ORDER = (
    "curto", "cacheado", "crespo", "longo", "trancas", "coque",
    "franja", "chiquinhas", "puffs", "moicano", "hijab", "raspado",
)
HAIR_FIT = {
    # target head-width multiplier, crown offset as a fraction of body height
    "curto": (1.03, 0.0),
    "cacheado": (1.06, -0.012),
    "crespo": (1.10, -0.015),
    "longo": (1.12, -0.01),
    "trancas": (1.08, -0.018),
    "coque": (0.96, -0.04),
    "franja": (1.02, -0.015),
    "chiquinhas": (1.15, -0.025),
    "puffs": (1.15, -0.03),
    "moicano": (1.02, -0.02),
    "hijab": (1.06, -0.01),
    "raspado": (1.02, 0.0),
}
HAIR_BASE_COLOR = (112, 64, 39)


def _multiply_color(color: Tuple[int, int, int], tint: Tuple[int, int, int]) -> Tuple[int, int, int]:
    return tuple(max(0, min(255, round(a * b / 255))) for a, b in zip(color, tint))


def _tint_by_key(
    source: pygame.Surface,
    base_color: Tuple[int, int, int],
    target_color: Tuple[int, int, int],
    tolerance: int = 46,
) -> pygame.Surface:
    """Recolor a watercolor swatch while preserving each pixel's pigment variation."""
    if base_color == target_color:
        return source.copy()
    multipliers = tuple(min(255, round(target * 255 / max(1, base))) for base, target in zip(base_color, target_color))
    tinted = source.copy()
    tinted.fill((*multipliers, 255), special_flags=pygame.BLEND_RGBA_MULT)
    threshold = (tolerance, tolerance, tolerance, 255)
    mask = pygame.mask.from_threshold(source, (*base_color, 255), threshold)
    selector = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    selector.blit(tinted, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    result = source.copy()
    result.blit(selector, (0, 0))
    return result


def _shift_hsv(pixel, base, target):
    source_h, source_s, source_v = colorsys.rgb_to_hsv(*(value / 255 for value in pixel))
    base_h, base_s, base_v = colorsys.rgb_to_hsv(*(value / 255 for value in base))
    target_h, target_s, target_v = colorsys.rgb_to_hsv(*(value / 255 for value in target))
    hue = (source_h + target_h - base_h) % 1.0
    saturation = min(1.0, source_s * target_s / max(base_s, 0.05))
    value = min(1.0, source_v * target_v / max(base_v, 0.05))
    return tuple(round(c * 255) for c in colorsys.hsv_to_rgb(hue, saturation, value))


def _palette_layers(source: pygame.Surface):
    """Precomputes skin and shirt masks once per source pose, not once per look."""
    width, height = source.get_size()
    skin_mask, shirt_mask = pygame.mask.Mask((width, height)), pygame.mask.Mask((width, height))
    pixels = pygame.PixelArray(source)
    skin_stop = int(height * 0.84)
    shirt_start, shirt_stop = int(height * 0.22), int(height * 0.66)
    for y in range(height):
        for x in range(width):
            color = source.unmap_rgb(pixels[x, y])
            if color.a < 90:
                continue
            r, g, b = color.r, color.g, color.b
            if y < skin_stop and r >= g + 10 and g >= b + 7 and g > 65 and r > 100:
                skin_mask.set_at((x, y))
            elif shirt_start <= y <= shirt_stop and b - r > 8 and g - r > 2 and b > 65 and r > 40:
                shirt_mask.set_at((x, y))
    del pixels
    skin_surface = skin_mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    shirt_surface = shirt_mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    return source, pygame.transform.grayscale(source), skin_surface, shirt_surface


def _tinted_luminance(gray: pygame.Surface, base: Tuple[int, int, int], target: Tuple[int, int, int]):
    peak = max(target)
    base_luma = max(1, round(base[0] * 0.299 + base[1] * 0.587 + base[2] * 0.114))
    tinted = gray.copy()
    if peak >= base_luma:
        lift = min(255, peak - base_luma)
        tinted.fill((lift, lift, lift, 0), special_flags=pygame.BLEND_RGBA_ADD)
    else:
        multiplier = round(peak * 255 / base_luma)
        tinted.fill((multiplier, multiplier, multiplier, 255), special_flags=pygame.BLEND_RGBA_MULT)
    channels = tuple(round(c * 255 / peak) for c in target)
    tinted.fill((*channels, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return tinted


def _recolor_watercolor(prepared, skin: Tuple[int, int, int], shirt: Tuple[int, int, int], skin_key, shirt_key):
    """Fast masked colorization keeps watercolor luminosity and fibers."""
    source, gray, skin_mask, shirt_mask = prepared
    # Keep the original painted pixels outside recolorable regions (pants,
    # shoes, linework, and all transparent paper) intact.
    result = source.copy()
    skin_layer = _tinted_luminance(gray, skin_key, skin)
    skin_layer.blit(skin_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    result.blit(skin_layer, (0, 0))
    shirt_layer = _tinted_luminance(gray, shirt_key, shirt)
    shirt_layer.blit(shirt_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    result.blit(shirt_layer, (0, 0))
    # Pixels outside the two selected regions keep their original painted hues.
    return result


def _tint_hair(source: pygame.Surface, color: Tuple[int, int, int]) -> pygame.Surface:
    """Recolors painted hair without losing its watercolor value and alpha."""
    peak = max(color)
    if peak <= 0:
        return source.copy()
    result = pygame.transform.grayscale(source)
    multipliers = tuple(round(channel * 255 / peak) for channel in color)
    result.fill((*multipliers, 255), special_flags=pygame.BLEND_RGBA_MULT)
    return result


def _clean_hair_tile(tile: pygame.Surface, style: str) -> pygame.Surface:
    """Drops disconnected generation specks while keeping multi-part styles."""
    mask = pygame.mask.from_surface(tile, 18)
    parts = mask.connected_components(minimum=max(900, tile.get_width() * tile.get_height() // 150))
    selected = parts
    if style in {"franja", "moicano"} and parts:
        selected = [max(parts, key=lambda part: part.count())]
    if len(selected) == len(parts):
        return tile
    if not selected:
        return pygame.Surface(tile.get_size(), pygame.SRCALPHA)
    keep = pygame.mask.Mask(tile.get_size())
    for part in selected:
        keep.draw(part, (0, 0))
    selector = keep.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    cleaned = tile.copy()
    cleaned.blit(selector, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return cleaned


def _hair_layers(sprites, pose: str, look: Mapping[str, str], size, padding: int):
    """Fits the matching front/back painted hairstyle to the watercolor head."""
    style = look.get("cabelo", UNSELECTED)
    if style not in HAIR_ORDER:
        return None, None
    front = sprites.get(("front", style))
    back = sprites.get(("back", style))
    if front is None and back is None:
        return None, None
    width, height = size
    seated = pose.endswith("seated")
    if seated:
        head_width = width * 0.86
        head_x = width * 0.055
    else:
        head_width = width * 0.72
        head_x = width * 0.143
    color = find_option(HAIR_COLORS, look.get("cor_cabelo", UNSELECTED)).color
    if color is None or look.get("cor_cabelo") == UNSELECTED:
        color = (105, 76, 58)
    q = 3

    def fit(layer, layer_style):
        if layer is None:
            return None
        # The atlas pieces have different crowns and side volumes. These
        # per-style anchors preserve the same forehead/eye line on the base.
        width_scale, y_offset = HAIR_FIT.get(layer_style, (1.06, 0.0))
        target_w = max(1, round(head_width * width_scale * q))
        scale = target_w / layer.get_width()
        target_h = max(1, round(layer.get_height() * scale))
        tinted = _tint_hair(layer, color)
        scaled = pygame.transform.smoothscale(tinted, (target_w, target_h))
        output = pygame.Surface(((width + 2 * padding) * q, height * q), pygame.SRCALPHA)
        x = round((padding + head_x + head_width / 2) * q - target_w / 2)
        # The hair crowns sit on the top of the source head; long locks extend
        # naturally below it because their painted overlays are taller.
        output.blit(scaled, (x, round(y_offset * height * q)))
        if pose.startswith("front_") and layer_style in {"coque", "chiquinhas", "puffs", "moicano"}:
            # These four generated caps carry extra forehead strands or small
            # stray tufts. Keep the face oval open while side locks remain.
            face_clip = pygame.Rect(
                round((padding + head_x + head_width * 0.32) * q),
                round(height * 0.105 * q),
                max(1, round(head_width * 0.36 * q)),
                max(1, round(height * 0.22 * q)),
            )
            pygame.draw.ellipse(output, (0, 0, 0, 0), face_clip)
        if layer_style == "moicano":
            # Shaved temples stay skin-colored; retain only the central crest.
            keep_left = round((padding + head_x + head_width * 0.30) * q)
            keep_right = round((padding + head_x + head_width * 0.70) * q)
            trim_top = round(height * 0.045 * q)
            trim_height = round(height * 0.30 * q)
            pygame.draw.rect(output, (0, 0, 0, 0), (0, trim_top, keep_left, trim_height))
            pygame.draw.rect(output, (0, 0, 0, 0), (keep_right, trim_top, output.get_width() - keep_right, trim_height))
        return output

    def composite(side: str, selected_style: str):
        target = pygame.Surface(((width + 2 * padding) * q, height * q), pygame.SRCALPHA)
        if side == "back" and pose.startswith("front_") and selected_style == "moicano":
            # The back-view mohawk has broad side pieces; the front view uses
            # only the narrow central crest so the temples stay visibly shaved.
            return target
        underlay = {"chiquinhas": "curto", "puffs": "crespo"}.get(selected_style)
        if underlay:
            base = sprites.get((side, underlay))
            if base is not None:
                target.blit(fit(base, underlay), (0, 0))
        main = sprites.get((side, selected_style))
        if main is not None:
            target.blit(fit(main, selected_style), (0, 0))
        if selected_style == "puffs":
            # Scalloped ellipses round the generated side perimeter instead of
            # leaving a square crop at the cell edge.
            mask = pygame.Surface(target.get_size(), pygame.SRCALPHA)
            puffs = (
                (head_x + head_width * 0.12, -height * 0.02, head_width * 0.76, height * 0.30),
                (head_x - head_width * 0.035, height * 0.005, head_width * 0.39, height * 0.235),
                (head_x + head_width * 0.645, height * 0.005, head_width * 0.39, height * 0.235),
            )
            for x, y, w, h in puffs:
                pygame.draw.ellipse(
                    mask,
                    (255, 255, 255, 255),
                    pygame.Rect(
                        round((padding + x) * q),
                        round(y * q),
                        round(w * q),
                        round(h * q),
                    ),
                )
            target.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return target

    if pose.startswith("back_"):
        # The back-facing base art has an opaque bald scalp, so its hairstyle
        # must be layered on top of that scalp rather than hidden underneath.
        return None, composite("back", style)
    return composite("back", style), composite("front", style)


def _mobility_layer(sprites, pose: str, look: Mapping[str, str], size, padding: int):
    """Scales the painted wheelchair/walker atlas behind the child body."""
    if look.get("cadeira") == "sim":
        device = "wheelchair"
        target_height = 0.66
        top = 0.30
    elif look.get("andador") == "sim":
        device = "walker"
        target_height = 0.60
        top = 0.40
    else:
        return None
    direction = "front" if pose.startswith("front_") else "back"
    image = sprites.get(f"{device}_{direction}")
    if image is None:
        return None
    width, height = size
    q = 3
    wanted_h = max(1, round(height * target_height * q))
    scale = wanted_h / image.get_height()
    wanted_w = max(1, round(image.get_width() * scale))
    canvas_w = (width + 2 * padding) * q
    if wanted_w > canvas_w:
        scale *= canvas_w / wanted_w
        wanted_w = canvas_w
        wanted_h = max(1, round(image.get_height() * scale))
    scaled = pygame.transform.smoothscale(image, (wanted_w, wanted_h))
    layer = pygame.Surface((canvas_w, height * q), pygame.SRCALPHA)
    x = round((canvas_w - wanted_w) / 2)
    y = round(height * top * q)
    layer.blit(scaled, (x, y))
    return layer


def _painted_hair_back(canvas):
    width = canvas['width']
    style = canvas['style']
    ellipse = canvas['ellipse']
    hx = canvas['hx']
    hw = canvas['hw']
    hy = canvas['hy']
    hh = canvas['hh']
    hair = canvas['hair']
    ink = canvas['ink']

    if style == UNSELECTED or style == "raspado":
        return
    if style == "hijab":
        ellipse((hx - hw * 0.08, hy - hh * 0.05, hw * 1.16, hh * 1.03), hair, ink, max(2, round(width * 0.009)))
        return
    # Cap base is behind the painted face and leaves all original features intact.
    cap_h = hh * 0.48
    ellipse((hx - hw * 0.055, hy - hh * 0.08, hw * 1.11, cap_h), hair, ink, max(2, round(width * 0.008)))
    if style in ("longo", "trancas"):
        for side in (-1, 1):
            x = hx + (0 if side < 0 else hw * 0.78)
            w = hw * 0.22
            ellipse((x, hy + hh * 0.28, w, hh * 1.05), hair, ink, max(2, round(width * 0.008)))
    if style in ("coque", "chiquinhas"):
        centers = (hx + hw * 0.12, hx + hw * 0.88) if style == "chiquinhas" else (hx + hw * 0.5,)
        for x in centers:
            ellipse((x - hw * 0.12, hy - hh * 0.16, hw * 0.24, hh * 0.27), hair, ink, max(2, round(width * 0.008)))
    elif style == "puffs":
        for x in (hx - hw * 0.09, hx + hw * 0.91):
            ellipse((x - hw * 0.12, hy + hh * 0.04, hw * 0.24, hh * 0.28), hair, ink, max(2, round(width * 0.008)))

def _painted_front_hair(canvas):
    width = canvas['width']
    style = canvas['style']
    ellipse = canvas['ellipse']
    line = canvas['line']
    poly = canvas['poly']
    hx = canvas['hx']
    hw = canvas['hw']
    hy = canvas['hy']
    hh = canvas['hh']
    hair = canvas['hair']
    ink = canvas['ink']
    light_hair = canvas['light_hair']
    layer = canvas['layer']
    r = canvas['r']

    if style == UNSELECTED or style == "raspado":
        return
    if style == "hijab":
        # Framing folds track the temple line without covering eyes or cheeks.
        for side in (-1, 1):
            x = hx - hw * 0.045 if side < 0 else hx + hw * 0.91
            line(
                [
                    (x, hy + hh * 0.16),
                    (x - hw * 0.025 if side < 0 else x + hw * 0.025, hy + hh * 0.42),
                    (x + hw * 0.015 if side < 0 else x - hw * 0.015, hy + hh * 0.68),
                ],
                light_hair,
                max(
                    2,
                    round(width * 0.008),
                ),
                None,
            )
        return
    top = hy - hh * 0.015
    cap_bottom = hy + hh * 0.39
    if style in ("crespo", "cacheado", "puffs"):
        count = 10 if style == "crespo" else 8
        radius = hw * 0.085 if style == "crespo" else hw * 0.071
        for i in range(count):
            x = hx + hw * 0.02 + i * (hw * 0.96 / (count - 1))
            y = top + hh * 0.18 + math.sin(i * 1.8) * hh * 0.045
            ellipse((x - radius, y - radius, radius * 2, radius * 2), hair, ink, max(2, round(width * 0.006)))
            pygame.draw.arc(
                layer,
                light_hair,
                r(x - radius * 0.45, y - radius * 0.45, radius * 0.9, radius * 0.85),
                3.5,
                5.9,
                max(1, round(width * 0.004)),
            )
    elif style == "moicano":
        poly(
            [(hx + hw * 0.31, cap_bottom), (hx + hw * 0.5, top - hh * 0.12), (hx + hw * 0.7, cap_bottom)],
            hair,
            ink,
            max(2, round(width * 0.008)),
        )
    elif style == "franja":
        poly(
            [
                (hx, hy + hh * 0.32),
                (hx + hw * 0.18, hy + hh * 0.25),
                (hx + hw * 0.35, hy + hh * 0.43),
                (hx + hw * 0.5, hy + hh * 0.25),
                (hx + hw * 0.67, hy + hh * 0.43),
                (hx + hw * 0.84, hy + hh * 0.25),
                (hx + hw, hy + hh * 0.35),
                (hx + hw, top),
                (hx, top),
            ],
            hair,
            ink,
            max(2, round(width * 0.006)),
        )
    else:
        ellipse((hx, top, hw, hh * 0.42), hair, ink, max(2, round(width * 0.007)))
    # Fine hand-painted strands pick up the selected hair color.
    for i in range(5):
        x = hx + hw * (0.14 + i * 0.18)
        line(
            [(x, hy + hh * 0.08), (x - hw * 0.025, hy + hh * 0.20), (x, hy + hh * 0.31)],
            light_hair,
            max(1, round(width * 0.004)),
            None,
        )
    if style == "trancas":
        for side in (-1, 1):
            x = hx - hw * 0.02 if side < 0 else hx + hw * 0.98
            for j in range(5):
                y = hy + hh * (0.35 + j * 0.17)
                ellipse((x - hw * 0.055, y, hw * 0.11, hh * 0.12), hair, ink, max(1, round(width * 0.005)))
                line(
                    [
                        (x - hw * 0.025, y + hh * 0.02),
                        (x + hw * 0.025, y + hh * 0.07),
                        (x - hw * 0.02, y + hh * 0.11),
                    ],
                    light_hair,
                    max(1, round(width * 0.004)),
                    None,
                )
    elif style == "longo":
        for side in (-1, 1):
            x = hx + hw * 0.06 if side < 0 else hx + hw * 0.94
            line(
                [
                    (x, hy + hh * 0.27),
                    (x + side * hw * 0.035, hy + hh * 0.52),
                    (x + side * hw * 0.01, hy + hh * 0.82),
                ],
                light_hair,
                max(1, round(width * 0.004)),
                None,
            )

def _painted_device_back(canvas):
    width = canvas['width']
    height = canvas['height']
    look = canvas['look']
    layer = canvas['layer']
    ink = canvas['ink']
    q = canvas['q']
    padding = canvas['padding']
    line = canvas['line']

    if look["cadeira"] == "sim":
        radius = width * 0.20
        cy = height * 0.73
        for cx in (-width * 0.02, width * 1.02):
            pygame.draw.circle(
                layer,
                ink,
                (round((cx + padding) * q), round(cy * q)),
                round(radius * q),
                max(2, round(width * 0.012 * q)),
            )
            pygame.draw.circle(
                layer,
                (228, 235, 227),
                (round((cx + padding) * q), round(cy * q)),
                round(radius * 0.88 * q),
                max(2, round(width * 0.007 * q)),
            )
            for angle in range(0, 360, 45):
                ex = cx + radius * 0.76 * math.cos(math.radians(angle))
                ey = cy + radius * 0.76 * math.sin(math.radians(angle))
                line([(cx, cy), (ex, ey)], (120, 151, 163), max(1, round(width * 0.004)), None)
        line(
            [(width * 0.31, height * 0.64), (width * 0.69, height * 0.64)],
            (81, 139, 157),
            max(3, round(width * 0.015)),
        )
        line(
            [(width * 0.30, height * 0.70), (width * 0.70, height * 0.70)],
            (235, 181, 111),
            max(3, round(width * 0.018)),
        )
    elif look["andador"] == "sim":
        for x, inward in ((width * 0.045, width * 0.17), (width * 0.955, width * 0.83)):
            line(
                [(x, height * 0.52), (x, height * 0.82), (x + (inward - x) * 0.32, height * 0.95)],
                (83, 143, 160),
                max(4, round(width * 0.018)),
            )
        line(
            [(width * 0.045, height * 0.52), (width * 0.17, height * 0.52)],
            (83, 143, 160),
            max(5, round(width * 0.022)),
        )
        line(
            [(width * 0.83, height * 0.52), (width * 0.955, height * 0.52)],
            (83, 143, 160),
            max(5, round(width * 0.022)),
        )
        line(
            [(width * 0.045, height * 0.78), (width * 0.955, height * 0.78)],
            (117, 167, 177),
            max(3, round(width * 0.012)),
        )

def _painted_device_front(canvas):
    width = canvas['width']
    height = canvas['height']
    look = canvas['look']
    layer = canvas['layer']
    ink = canvas['ink']
    q = canvas['q']
    padding = canvas['padding']
    line = canvas['line']

    if look["cadeira"] == "sim":
        line(
            [(width * 0.30, height * 0.80), (width * 0.70, height * 0.80)],
            (80, 136, 154),
            max(3, round(width * 0.014)),
        )
        line(
            [
                (width * 0.35, height * 0.78),
                (width * 0.35, height * 0.88),
                (width * 0.65, height * 0.88),
                (width * 0.65, height * 0.78),
            ],
            (80, 136, 154),
            max(3, round(width * 0.014)),
        )
        line(
            [(width * 0.34, height * 0.89), (width * 0.47, height * 0.89)],
            (240, 191, 110),
            max(3, round(width * 0.012)),
        )
        line(
            [(width * 0.53, height * 0.89), (width * 0.66, height * 0.89)],
            (240, 191, 110),
            max(3, round(width * 0.012)),
        )
    elif look["andador"] == "sim":
        for x in (width * 0.045, width * 0.955):
            pygame.draw.circle(
                layer,
                ink,
                (round((x + padding) * q), round(height * 0.95 * q)),
                max(7, round(width * 0.038 * q)),
            )
            pygame.draw.circle(
                layer,
                (115, 169, 179),
                (round((x + padding) * q), round(height * 0.95 * q)),
                max(5, round(width * 0.027 * q)),
            )

def _compose_painted_overlays(canvas):
    width = canvas['width']
    height = canvas['height']
    padding = canvas['padding']
    q = canvas['q']
    layer = canvas['layer']
    hair_back_art = canvas['hair_back_art']
    hair_front_art = canvas['hair_front_art']
    mobility_art = canvas['mobility_art']
    view = canvas['view']
    look = canvas['look']
    eye_points = canvas['eye_points']
    r = canvas['r']
    ink = canvas['ink']
    line = canvas['line']
    poly = canvas['poly']
    hx = canvas['hx']
    hw = canvas['hw']
    hy = canvas['hy']
    hh = canvas['hh']

    _painted_hair_back(canvas)
    if hair_back_art is not None:
        layer.blit(hair_back_art, (0, 0))
    if mobility_art is not None:
        layer.blit(mobility_art, (0, 0))
    else:
        _painted_device_back(canvas)
    # A single layer combines back details, then caller places base art over it.
    final_size = (width + 2 * padding, height)
    back = pygame.transform.smoothscale(layer, final_size)
    layer.fill((0, 0, 0, 0))
    _painted_front_hair(canvas)
    if hair_front_art is not None:
        layer.blit(hair_front_art, (0, 0))
    if mobility_art is None:
        _painted_device_front(canvas)

    # Personalized iris overlays sit on top of painted sclera only after a selection.
    if view != "flight" and look["olhos"] != UNSELECTED:
        iris = find_option(EYE_COLORS, look["olhos"]).color or (78, 64, 52)
        for cx, cy in eye_points:
            pygame.draw.circle(
                layer, iris, (round((cx + padding) * q), round(cy * q)), max(3, round(width * 0.028 * q))
            )
            pygame.draw.circle(
                layer, (30, 35, 44), (round((cx + padding) * q), round(cy * q)), max(2, round(width * 0.014 * q))
            )
            pygame.draw.circle(
                layer,
                (255, 255, 255),
                (round((cx - width * 0.007 + padding) * q), round((cy - height * 0.008) * q)),
                max(1, round(width * 0.006 * q)),
            )

    # Optional glasses, hearing aid, and accessories remain distinct at flight scale.
    if view != "flight" and look["oculos"] != "nenhum":
        frame = (35, 54, 84) if look["oculos"] != "sol" else (53, 66, 84)
        for cx, cy in eye_points:
            box = r(cx - width * 0.105, cy - height * 0.034, width * 0.21, height * 0.064)
            pygame.draw.rect(
                layer,
                frame,
                box,
                width=max(2, round(width * 0.009 * q)),
                border_radius=max(4, round(width * 0.025 * q)),
            )
            if look["oculos"] == "sol":
                lens = pygame.Surface(box.size, pygame.SRCALPHA)
                lens.fill((103, 151, 179, 115))
                layer.blit(lens, box.topleft)
        line(
            [(eye_points[0][0] + width * 0.10, eye_points[0][1]), (eye_points[1][0] - width * 0.10, eye_points[1][1])],
            frame,
            max(2, round(width * 0.008)),
            None,
        )
    if look["aparelho"] == "sim":
        cx = hx + hw * 0.98
        cy = hy + hh * 0.58
        pygame.draw.circle(layer, ink, (round((cx + padding) * q), round(cy * q)), max(4, round(width * 0.035 * q)))
        pygame.draw.circle(
            layer, (43, 149, 161), (round((cx + padding) * q), round(cy * q)), max(3, round(width * 0.025 * q))
        )
        pygame.draw.circle(
            layer, (247, 211, 119), (round((cx + padding) * q), round(cy * q)), max(2, round(width * 0.009 * q))
        )
    accessory = look["acessorio"]
    if view != "flight" and accessory in ("bone", "capacete"):
        cap = (244, 190, 75) if accessory == "bone" else (223, 151, 73)
        box = r(hx - hw * 0.03, hy - hh * 0.08, hw * 1.06, hh * 0.42)
        pygame.draw.arc(layer, ink, box, math.pi, 2 * math.pi, max(3, round(width * 0.018 * q)))
        pygame.draw.arc(
            layer,
            cap,
            box.inflate(-max(3, round(width * 0.02 * q)), -max(3, round(width * 0.02 * q))),
            math.pi,
            2 * math.pi,
            max(3, round(width * 0.016 * q)),
        )
    elif view != "flight" and accessory in ("tiara", "coroa", "flor"):
        if accessory == "coroa":
            poly(
                [
                    (hx + hw * 0.2, hy + hh * 0.13),
                    (hx + hw * 0.29, hy - hh * 0.02),
                    (hx + hw * 0.43, hy + hh * 0.13),
                    (hx + hw * 0.52, hy - hh * 0.04),
                    (hx + hw * 0.64, hy + hh * 0.13),
                    (hx + hw * 0.8, hy - hh * 0.01),
                    (hx + hw * 0.83, hy + hh * 0.18),
                ],
                (247, 202, 74),
                ink,
                max(2, round(width * 0.008)),
            )
        elif accessory == "tiara":
            pygame.draw.arc(
                layer,
                (245, 194, 75),
                r(hx + hw * 0.13, hy + hh * 0.05, hw * 0.74, hh * 0.24),
                math.pi,
                2 * math.pi,
                max(2, round(width * 0.012 * q)),
            )
        else:
            pygame.draw.circle(
                layer, ink, (round((hx + hw * 0.95) * q), round((hy + hh * 0.19) * q)), max(7, round(width * 0.05 * q))
            )
            pygame.draw.circle(
                layer,
                (235, 112, 145),
                (round((hx + hw * 0.95) * q), round((hy + hh * 0.19) * q)),
                max(5, round(width * 0.035 * q)),
            )
            pygame.draw.circle(
                layer,
                (250, 210, 87),
                (round((hx + hw * 0.95) * q), round((hy + hh * 0.19) * q)),
                max(2, round(width * 0.012 * q)),
            )

    front = pygame.transform.smoothscale(layer, final_size)
    return back, front


def _painted_overlays(
    size,
    pose,
    look,
    skin_key,
    seated,
    view,
    padding=0,
    hair_back_art=None,
    hair_front_art=None,
    mobility_art=None,
):
    """Paint hair, selectable eyes, accessories and mobility in a 3x transparent layer."""
    width, height = size
    padding = max(0, int(padding))
    q = 3
    layer = pygame.Surface(((width + 2 * padding) * q, height * q), pygame.SRCALPHA)
    ink = (48, 54, 76)
    style = look["cabelo"] if hair_back_art is None and hair_front_art is None else UNSELECTED
    hair = find_option(HAIR_COLORS, look["cor_cabelo"]).color
    if hair is None or look["cor_cabelo"] == UNSELECTED:
        hair = (105, 76, 58)
    dark_hair = tuple(round(c * 0.62) for c in hair)
    light_hair = tuple(min(255, c + 48) for c in hair)
    if seated:
        hx, hy, hw, hh = width * 0.055, 0, width * 0.86, height * 0.33
        eye_points = ((width * 0.333, height * 0.178), (width * 0.647, height * 0.178))
    else:
        hx, hy, hw, hh = width * 0.143, 0, width * 0.72, height * 0.253
        eye_points = ((width * 0.377, height * 0.144), (width * 0.639, height * 0.144))

    def r(x, y, w, h):
        return pygame.Rect(round((x + padding) * q), round(y * q), max(1, round(w * q)), max(1, round(h * q)))

    def ellipse(box, fill, outline=dark_hair, width_px=2):
        pygame.draw.ellipse(layer, outline, r(box[0], box[1], box[2], box[3]).inflate(width_px * q, width_px * q))
        pygame.draw.ellipse(layer, fill, r(*box))

    def line(points, color, width_px=3, outline=ink):
        pts = [(round((x + padding) * q), round(y * q)) for x, y in points]
        if outline:
            pygame.draw.lines(layer, outline, False, pts, max(1, round((width_px + 2) * q)))
        pygame.draw.lines(layer, color, False, pts, max(1, round(width_px * q)))

    def poly(points, color, outline=dark_hair, width_px=2):
        pts = [(round((x + padding) * q), round(y * q)) for x, y in points]
        pygame.draw.polygon(layer, outline, pts) if outline else None
        pygame.draw.polygon(layer, color, pts)
        if outline and width_px:
            pygame.draw.lines(layer, outline, True, pts, width_px * q)

    canvas = locals()
    return _compose_painted_overlays(canvas)


def _action_overlay(image, view, skin, base_size, padding):
    """Distinct paper-plane gestures layered over the painted base pose."""
    if view not in ("segura", "lanca"):
        return image
    base_w, height = base_size
    padding = int(padding)
    q = 3
    layer = pygame.Surface((image.get_width() * q, image.get_height() * q), pygame.SRCALPHA)
    ink = (48, 54, 76)

    def p(x, y):
        return (round((padding + x * base_w) * q), round(y * height * q))

    def line(points, color, width_px, outline=ink):
        points = [p(x, y) for x, y in points]
        if outline:
            pygame.draw.lines(layer, outline, False, points, max(1, round((width_px + 2) * q)))
        pygame.draw.lines(layer, color, False, points, max(1, round(width_px * q)))

    def polygon(points, color):
        pygame.draw.polygon(layer, color, [p(x, y) for x, y in points])
        pygame.draw.lines(layer, ink, True, [p(x, y) for x, y in points], 2 * q)

    if view == "segura":
        cx, cy = 0.5, 0.42
        polygon(
            [(cx - 0.13, cy), (cx + 0.11, cy - 0.015), (cx + 0.13, cy + 0.045), (cx - 0.13, cy + 0.05)], (252, 247, 232)
        )
        polygon([(cx - 0.115, cy + 0.006), (cx - 0.01, cy + 0.021), (cx - 0.112, cy + 0.04)], (226, 238, 237))
        line([(cx - 0.10, cy + 0.008), (cx - 0.112, cy + 0.04)], (67, 83, 104), 1, None)
    else:
        polygon([(0.83, 0.15), (0.96, 0.08), (0.91, 0.22)], (255, 248, 228))
        polygon([(0.84, 0.151), (0.93, 0.137), (0.91, 0.205)], (222, 235, 235))
    image.blit(pygame.transform.smoothscale(layer, image.get_size()), (0, 0))
    return image


class PaintedPilot:
    """Loads and tints optional painted poses; returns None when not installed."""

    def __init__(
        self,
        assets: Assets,
        *,
        skin_key: Tuple[int, int, int] = DEFAULT_SKIN_KEY,
        shirt_key: Tuple[int, int, int] = DEFAULT_SHIRT_KEY,
        tolerance: int = 46,
    ) -> None:
        self.assets = assets
        self.skin_key = skin_key
        self.shirt_key = shirt_key
        self.tolerance = tolerance
        # Pedir apenas as camadas do piloto: esta pasta também contém cenários
        # grandes que pertencem a outras cenas e devem continuar sob demanda.
        names = (ATLAS_KEY, "pilot_hair_front", "pilot_hair_back", "pilot_mobility",
                 "front_standing", "back_standing", "front_seated", "back_seated")
        self.sprites = dict(assets.folder(BASE_FOLDER, names=names))
        atlas = self.sprites.get(ATLAS_KEY)
        if atlas is not None:
            cell_w = atlas.get_width() // 2
            split_y = round(atlas.get_height() * 710 / 1295)
            row_bounds = ((0, split_y), (split_y, atlas.get_height()))
            # Atlas order: front standing, back standing, front seated, back seated.
            for index, pose in enumerate(("front_standing", "back_standing", "front_seated", "back_seated")):
                column, row = index % 2, index // 2
                top, bottom = row_bounds[row]
                cell = pygame.Rect(column * cell_w, top, cell_w, bottom - top)
                framed = atlas.subsurface(cell).copy()
                bounds = framed.get_bounding_rect(min_alpha=15)
                self.sprites.setdefault(pose, framed.subsurface(bounds).copy())
        self.hair_sprites = {}
        for side in ("front", "back"):
            hair_atlas = self.sprites.get(f"pilot_hair_{side}")
            if hair_atlas is None:
                continue
            cell_w, cell_h = hair_atlas.get_width() // 4, hair_atlas.get_height() // 3
            for index, style in enumerate(HAIR_ORDER):
                cell = pygame.Rect((index % 4) * cell_w, (index // 4) * cell_h, cell_w, cell_h)
                tile = hair_atlas.subsurface(cell).copy()
                tile = _clean_hair_tile(tile, style)
                bounds = tile.get_bounding_rect(min_alpha=15)
                if bounds.width and bounds.height:
                    self.hair_sprites[(side, style)] = tile.subsurface(bounds).copy()
        self.mobility_sprites = {}
        mobility_atlas = self.sprites.get("pilot_mobility")
        if mobility_atlas is not None:
            mid_x, mid_y = mobility_atlas.get_width() // 2, mobility_atlas.get_height() // 2
            boxes = (
                pygame.Rect(0, 0, mid_x, mid_y),
                pygame.Rect(mid_x, 0, mobility_atlas.get_width() - mid_x, mid_y),
                pygame.Rect(0, mid_y, mid_x, mobility_atlas.get_height() - mid_y),
                pygame.Rect(mid_x, mid_y, mobility_atlas.get_width() - mid_x, mobility_atlas.get_height() - mid_y),
            )
            for name, box in zip(
                ("wheelchair_front", "wheelchair_back", "walker_front", "walker_back"), boxes
            ):
                tile = mobility_atlas.subsurface(box).copy()
                bounds = tile.get_bounding_rect(min_alpha=15)
                if bounds.width and bounds.height:
                    self.mobility_sprites[name] = tile.subsurface(bounds).copy()
        for atlas_name in (ATLAS_KEY, "pilot_hair_front", "pilot_hair_back", "pilot_mobility"):
            self.sprites.pop(atlas_name, None)
        try:
            assets.release_folder(
                BASE_FOLDER, (ATLAS_KEY, "pilot_hair_front", "pilot_hair_back", "pilot_mobility")
            )
        except AttributeError:  # compatibilidade com provedores mínimos usados por ferramentas/testes
            pass
        self.palette = {name: _palette_layers(sprite) for name, sprite in self.sprites.items() if name in {
            "front_standing", "back_standing", "front_seated", "back_seated"
        }}
        self.cache = BoundedCache(24, 20 * 1024 * 1024)
        # Each cached pair is rendered at 3x for antialiasing; keep the raster
        # working set small so rapid appearance changes stay memory-bounded.
        self.hair_cache = BoundedCache(8, 12 * 1024 * 1024)
        self.mobility_cache = BoundedCache(4, 6 * 1024 * 1024)

    @property
    def available(self) -> bool:
        return any(name in self.sprites for pair in POSES.values() for name in pair)

    @staticmethod
    def pose_key(view: str, look: Mapping[str, str], pose_override: Optional[str] = None) -> str:
        if pose_override in {"front_standing", "back_standing", "front_seated", "back_seated"}:
            return pose_override
        standing, seated = POSES.get(view, POSES["menu"])
        return seated if look.get("cadeira") == "sim" else standing

    def compose(self, view: str, raw_look: dict, pose: Optional[str] = None) -> Optional[pygame.Surface]:
        look = normalize_pilot(raw_look)
        pose = self.pose_key(view, look, pose)
        source = self.sprites.get(pose)
        if source is None:
            return None
        key = (view, pose, tuple(sorted(look.items())))
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        skin = find_option(SKIN_CHOICES, look["pele"]).color or (243, 230, 210)
        if look["pele"] == UNSELECTED:
            skin = (243, 230, 210)  # neutral paper tone; no chosen complexion
        shirt = find_option(SHIRT_COLORS, look["roupa"]).color or (239, 226, 194)
        prepared = self.palette.get(pose)
        if prepared is None:
            return None
        image = _recolor_watercolor(prepared, skin, shirt, self.skin_key, self.shirt_key)
        seated = pose.endswith("seated")
        padding = round(
            image.get_width() * (0.24 if look["cadeira"] == "sim" else 0.30 if look["andador"] == "sim" else 0)
        )
        hair_style = look.get("cabelo", UNSELECTED)
        hair_color = look.get("cor_cabelo", UNSELECTED)
        hair_key = (pose, hair_style, hair_color, padding, image.get_size())
        cached_hair = self.hair_cache.get(hair_key)
        if cached_hair is None:
            cached_hair = _hair_layers(self.hair_sprites, pose, look, image.get_size(), padding)
            self.hair_cache[hair_key] = cached_hair
        hair_back_art, hair_front_art = cached_hair
        mobility_key = (pose, look["cadeira"], look["andador"], image.get_size(), padding)
        mobility_art = self.mobility_cache.get(mobility_key)
        if mobility_art is None:
            mobility_art = _mobility_layer(self.mobility_sprites, pose, look, image.get_size(), padding)
            self.mobility_cache[mobility_key] = mobility_art
        back_layer, front_layer = _painted_overlays(
            image.get_size(),
            pose,
            look,
            skin,
            seated,
            view,
            padding,
            hair_back_art,
            hair_front_art,
            mobility_art,
        )
        result = pygame.Surface((image.get_width() + 2 * padding, image.get_height()), pygame.SRCALPHA)
        result.blit(back_layer, (0, 0))
        result.blit(image, (padding, 0))
        result.blit(front_layer, (0, 0))
        result = _action_overlay(result, view, skin, image.get_size(), padding)
        self.cache[key] = result
        return result
