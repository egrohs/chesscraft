"""Visual theme: palette, fonts and reusable drawing helpers.

The look is a dark-fantasy RPG: deep slate backgrounds, warm gold accents
and parchment-toned text, so the painted character art sits naturally.
"""

from __future__ import annotations

import os
from functools import lru_cache

import pygame

from . import config

# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
BG_DEEP = (14, 16, 24)
BG = (22, 25, 36)
BG_PANEL = (31, 35, 50)
BG_PANEL_LIGHT = (42, 47, 66)
BG_PANEL_DARK = (18, 20, 30)

GOLD = (214, 173, 96)
GOLD_BRIGHT = (245, 214, 140)
GOLD_DARK = (140, 106, 48)

PARCHMENT = (232, 220, 196)
TEXT = (222, 226, 238)
TEXT_DIM = (150, 158, 178)
TEXT_MUTED = (104, 112, 132)

GREEN = (108, 190, 118)
GREEN_DARK = (52, 110, 66)
RED = (206, 88, 84)
RED_DARK = (120, 46, 46)
BLUE = (96, 152, 214)
PURPLE = (150, 110, 200)

# Board squares (warm wood / stone)
LIGHT_SQUARE = (198, 178, 148)
DARK_SQUARE = (118, 96, 74)
LIGHT_SQUARE_HL = (222, 206, 168)
DARK_SQUARE_HL = (142, 118, 88)

SELECT = (246, 214, 120)
MOVE_DOT = (120, 200, 140)
CAPTURE_RING = (226, 110, 96)
CHECK_GLOW = (232, 96, 88)
LAST_MOVE = (206, 178, 96)
HINT_GLOW = (140, 190, 255)

# Rarity / class colours used by the RPG layer
CLASS_COLORS = {
    "king": (232, 196, 108),
    "queen": (176, 132, 224),
    "rook": (150, 158, 172),
    "bishop": (120, 176, 232),
    "knight": (196, 148, 108),
    "pawn": (168, 176, 190),
}

# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------
_FONT_CACHE: dict[tuple[str, int], pygame.font.Font] = {}


def font(size: int, bold: bool = False) -> pygame.font.Font:
    """Return a cached font, falling back gracefully if none is available."""
    key = (f"bold{size}" if bold else f"reg{size}", size)
    cached = _FONT_CACHE.get(key)
    if cached is not None:
        return cached

    candidates = [
        "georgia", "constantia", "cambria", "palatino linotype",
        "book antiqua", "times new roman", "dejavuserif",
    ]
    path = None
    for name in candidates:
        found = pygame.font.match_font(name, bold=bold)
        if found:
            path = found
            break

    f = pygame.font.Font(path, size) if path else pygame.font.Font(None, size)
    _FONT_CACHE[key] = f
    return f


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------
def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill=BG_PANEL,
    border=GOLD_DARK,
    radius: int = 10,
    border_width: int = 2,
    shadow: bool = True,
) -> None:
    """Draw a rounded panel with an optional drop shadow and border."""
    if shadow:
        shadow_surf = pygame.Surface((rect.width + 8, rect.height + 8), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow_surf, (0, 0, 0, 90),
            pygame.Rect(4, 4, rect.width, rect.height),
            border_radius=radius,
        )
        surface.blit(shadow_surf, (rect.x - 4, rect.y - 4))

    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    if border_width > 0:
        pygame.draw.rect(surface, border, rect, width=border_width, border_radius=radius)


def draw_text(
    surface: pygame.Surface,
    text: str,
    pos: tuple[int, int],
    *,
    size: int = 20,
    color=TEXT,
    bold: bool = False,
    center: bool = False,
    right: bool = False,
    shadow: bool = False,
    wrap_width: int | None = None,
    line_spacing: int = 4,
) -> pygame.Rect:
    """Blit text and return its bounding rect.

    When ``wrap_width`` is given the text is word-wrapped to that width and
    drawn as multiple lines starting at ``pos``.
    """
    f = font(size, bold)

    if wrap_width is None:
        img = f.render(text, True, color)
        rect = img.get_rect()
        if center:
            rect.center = pos
        elif right:
            rect.midright = pos
        else:
            rect.topleft = pos
        if shadow:
            sh = f.render(text, True, (0, 0, 0))
            surface.blit(sh, (rect.x + 2, rect.y + 2))
        surface.blit(img, rect)
        return rect

    lines = _wrap_lines(f, text, wrap_width)
    lh = f.get_height() + line_spacing
    y = pos[1]
    first_rect = pygame.Rect(pos[0], pos[1], 0, 0)
    for i, line in enumerate(lines):
        img = f.render(line, True, color)
        rect = img.get_rect()
        if center:
            rect.midtop = (pos[0], y)
        elif right:
            rect.topright = (pos[0], y)
        else:
            rect.topleft = (pos[0], y)
        if i == 0:
            first_rect = rect.copy()
        if shadow:
            sh = f.render(line, True, (0, 0, 0))
            surface.blit(sh, (rect.x + 2, rect.y + 2))
        surface.blit(img, rect)
        y += lh
    first_rect.height = y - first_rect.y
    return first_rect


def _wrap_lines(f: pygame.font.Font, text: str, width: int) -> list[str]:
    """Word-wrap ``text`` to ``width`` pixels, honouring explicit newlines."""
    out: list[str] = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            trial = f"{line} {word}".strip()
            if f.size(trial)[0] <= width or not line:
                line = trial
            else:
                out.append(line)
                line = word
        out.append(line)
    return out


def draw_bar(
    surface: pygame.Surface,
    rect: pygame.Rect,
    ratio: float,
    *,
    fill=GREEN,
    back=BG_PANEL_DARK,
    border=GOLD_DARK,
    radius: int = 6,
) -> None:
    """Draw a progress / stat bar filled to ``ratio`` (0..1)."""
    ratio = max(0.0, min(1.0, ratio))
    pygame.draw.rect(surface, back, rect, border_radius=radius)
    if ratio > 0:
        inner = pygame.Rect(rect.x, rect.y, max(radius * 2, int(rect.width * ratio)), rect.height)
        pygame.draw.rect(surface, fill, inner, border_radius=radius)
    pygame.draw.rect(surface, border, rect, width=1, border_radius=radius)


def vertical_gradient(size: tuple[int, int], top, bottom) -> pygame.Surface:
    """Create a vertical gradient surface (used for scene backdrops)."""
    w, h = size
    surf = pygame.Surface((1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        surf.set_at((0, y), (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        ))
    return pygame.transform.smoothscale(surf, (w, h))


@lru_cache(maxsize=64)
def vignette(size: tuple[int, int], strength: int = 170) -> pygame.Surface:
    """Cached radial vignette overlay to darken scene edges."""
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w / 2, h / 2
    max_d = (cx ** 2 + cy ** 2) ** 0.5
    step = 4
    for y in range(0, h, step):
        for x in range(0, w, step):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / max_d
            a = int(max(0.0, (d - 0.45)) * strength * 1.6)
            if a > 0:
                pygame.draw.rect(surf, (0, 0, 0, min(255, a)), (x, y, step, step))
    return surf


def art_path(name: str) -> str:
    return os.path.join(config.ART_DIR, name)
