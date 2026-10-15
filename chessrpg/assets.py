"""Asset loading, sprite extraction and caching.

The ``art/`` folder contains painted *illustrations* (full scenes, mostly
1408x768) rather than isolated piece sprites. To use them on a chess board
we extract the character from each illustration:

1. find the horizontal band with the most visual detail (the character),
2. crop a square around it,
3. knock out the flat background so the piece sits cleanly on a square.

Two art sets exist:

* ``base``  - classic piece portraits (king, queen, rook, bishop, knight)
* ``class`` - RPG class variants (healer-king, sorcerer-queen, ...)

Missing files degrade gracefully to a generated placeholder so the game
always runs even with an incomplete art folder.
"""

from __future__ import annotations

import os

import pygame

from . import theme

# Logical piece name -> art file stem
BASE_ART = {
    "king": "king",
    "queen": "queen",
    "rook": "rook",
    "bishop": "bishop",
    "knight": "knight",
}

CLASS_ART = {
    "king": "healer-king",
    "queen": "sorcerer-queen",
    "rook": "tank-rook",
    "bishop": "dps-bishop",
    "knight": "cc-knight",
}

# Pawns reuse the base set (no dedicated pawn art yet).
PAWN_ART = {
    "king": "king",
    "queen": "queen",
    "rook": "rook",
    "bishop": "bishop",
    "knight": "knight",
}

# Illustrations wider than this are treated as scenes and cropped to the
# character; narrower images are assumed to already be piece portraits.
SCENE_ASPECT = 1.35


class AssetManager:
    """Loads, extracts, caches and scales game art."""

    def __init__(self) -> None:
        self._raw: dict[str, pygame.Surface] = {}
        self._sprite: dict[str, pygame.Surface] = {}
        self._scaled: dict[tuple[str, int, int], pygame.Surface] = {}
        self._portraits: dict[tuple[str, int], pygame.Surface] = {}

    # ------------------------------------------------------------------
    # Raw loading
    # ------------------------------------------------------------------
    def _load_raw(self, stem: str) -> pygame.Surface:
        if stem in self._raw:
            return self._raw[stem]

        path = theme.art_path(f"{stem}.jpg")
        if os.path.exists(path):
            try:
                surf = pygame.image.load(path).convert()
            except pygame.error:
                surf = self._placeholder(stem)
        else:
            surf = self._placeholder(stem)

        self._raw[stem] = surf
        return surf

    def _placeholder(self, stem: str) -> pygame.Surface:
        surf = pygame.Surface((256, 256))
        surf.fill(theme.BG_PANEL_LIGHT)
        pygame.draw.rect(surf, theme.GOLD_DARK, surf.get_rect(), 4)
        theme.draw_text(surf, stem[:6], (128, 128), size=28, color=theme.TEXT_DIM, center=True)
        return surf

    # ------------------------------------------------------------------
    # Sprite extraction
    # ------------------------------------------------------------------
    def _extract_sprite(self, stem: str) -> pygame.Surface:
        """Return the source image used to build a piece token."""
        if stem in self._sprite:
            return self._sprite[stem]

        raw = self._load_raw(stem)
        w, h = raw.get_size()

        if w / h <= SCENE_ASPECT:
            # Already portrait-ish: use as-is.
            sprite = raw.copy()
        else:
            sprite = self._crop_character(raw)

        self._sprite[stem] = sprite
        return sprite

    def _crop_character(self, raw: pygame.Surface) -> pygame.Surface:
        """Crop a square around the most detailed region of a scene."""
        w, h = raw.get_size()
        step = 8

        # Column-wise edge energy locates the character horizontally.
        energies = []
        for x in range(0, w - step, step):
            e = 0
            for y in range(0, h, step):
                c1 = raw.get_at((x, y))[:3]
                c2 = raw.get_at((x + step, y))[:3]
                e += abs(c1[0] - c2[0]) + abs(c1[1] - c2[1]) + abs(c1[2] - c2[2])
            energies.append((x, e))

        if not energies:
            return raw.copy()

        # Weight toward the centre so we lock onto the subject, not a busy
        # background edge.
        cx = w / 2
        scored = [(x, e * (1.0 - 0.5 * abs(x - cx) / cx)) for x, e in energies]
        scored.sort(key=lambda t: -t[1])
        peak = scored[0][0]

        # Square crop centred on the peak, sized to the image height.
        side = h
        left = int(peak - side / 2)
        left = max(0, min(w - side, left))
        return raw.subsurface(pygame.Rect(left, 0, side, h)).copy()

    def _token(self, sprite: pygame.Surface, size: int) -> pygame.Surface:
        """Render a sprite as a framed circular character token.

        The illustrations are full scenes, so instead of trying to cut the
        character out we present each piece as a medallion: a circular crop
        with a gold rim. This reads clearly on a board and suits the RPG look.
        """
        sw, sh = sprite.get_size()
        # Crop a square from the upper-middle (where the head/torso sits).
        side = min(sw, sh)
        left = (sw - side) // 2
        top = int((sh - side) * 0.18)
        top = max(0, min(sh - side, top))
        crop = sprite.subsurface(pygame.Rect(left, top, side, side)).copy()
        crop = pygame.transform.smoothscale(crop, (size, size))

        token = pygame.Surface((size, size), pygame.SRCALPHA)
        mask = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255), (size // 2, size // 2), size // 2)
        token.blit(crop, (0, 0))
        token.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Gold rim
        pygame.draw.circle(token, theme.GOLD_DARK, (size // 2, size // 2), size // 2 - 1, 3)
        pygame.draw.circle(token, (0, 0, 0, 120), (size // 2, size // 2), size // 2, 1)
        return token

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def piece_surface(self, piece_type: str, art_set: str, size: int) -> pygame.Surface:
        """Return a scaled piece token fitted into a ``size`` square."""
        table = CLASS_ART if art_set == "class" else BASE_ART
        stem = table.get(piece_type, BASE_ART.get(piece_type, "king"))
        key = (stem, size, 0 if art_set == "base" else 1)
        cached = self._scaled.get(key)
        if cached is not None:
            return cached

        sprite = self._extract_sprite(stem)
        token = self._token(sprite, size)
        self._scaled[key] = token
        return token

    def portrait(self, stem: str, height: int) -> pygame.Surface:
        """Return a wide portrait crop (used by hero / enemy cards)."""
        key = (stem, height)
        cached = self._portraits.get(key)
        if cached is not None:
            return cached

        raw = self._load_raw(stem)
        rw, rh = raw.get_size()
        scale = height / rh
        new_size = (max(1, int(rw * scale)), height)
        scaled = pygame.transform.smoothscale(raw, new_size)
        self._portraits[key] = scaled
        return scaled

    def has_art(self, stem: str) -> bool:
        return os.path.exists(theme.art_path(f"{stem}.jpg"))


ASSETS = AssetManager()
