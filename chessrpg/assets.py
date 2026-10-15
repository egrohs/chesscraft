"""Asset loading, sprite extraction and caching.

Pieces are drawn in one of two styles (see ``config.PIECE_STYLE``):

* ``"standard"`` - classic Unicode chess glyphs rendered with a contrasting
  outline. This is the default and needs no art files.
* ``"art"`` - painted character tokens cropped from the illustrations in
  ``art/``. Those files are full scenes (mostly 1408x768) rather than isolated
  sprites, so each one is cropped to the character and framed as a medallion.

Two art sets exist for the ``"art"`` style:

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

# Standard chess piece glyphs (Unicode). These are the classic piece shapes
# every chess player recognises, used by the "standard" piece style.
WHITE_GLYPHS = {
    "king": "\u2654",
    "queen": "\u2655",
    "rook": "\u2656",
    "bishop": "\u2657",
    "knight": "\u2658",
    "pawn": "\u2659",
}
BLACK_GLYPHS = {
    "king": "\u265A",
    "queen": "\u265B",
    "rook": "\u265C",
    "bishop": "\u265D",
    "knight": "\u265E",
    "pawn": "\u265F",
}

# Fonts that ship a solid set of chess glyphs, best first.
GLYPH_FONTS = [
    "segoeuisymbol", "segoeui", "cambria", "dejavusans", "freesansbold",
    "arial", "timesnewroman",
]


class AssetManager:
    """Loads, extracts, caches and scales game art."""

    def __init__(self) -> None:
        self._raw: dict[str, pygame.Surface] = {}
        self._sprite: dict[str, pygame.Surface] = {}
        self._scaled: dict[tuple[str, int, int], pygame.Surface] = {}
        self._portraits: dict[tuple[str, int], pygame.Surface] = {}
        self._glyph_font: pygame.font.Font | None = None
        self._glyph_font_path: str | None = None
        self._glyph_font_resolved = False
        self._standard: dict[tuple[str, bool, int], pygame.Surface] = {}

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
    # Standard (Unicode glyph) pieces
    # ------------------------------------------------------------------
    def _font_has_chess_glyphs(self, path: str) -> bool:
        """Return True if ``path`` renders the six chess glyphs distinctly.

        Many fonts resolve via :func:`pygame.font.match_font` but do not
        actually contain the chess code points; they silently fall back to
        the same "missing glyph" box for every piece. We detect that by
        rendering two different pieces and comparing the results.
        """
        try:
            probe = pygame.font.Font(path, 48)
        except (pygame.error, OSError):
            return False
        king = pygame.image.tobytes(probe.render("\u2654", True, (0, 0, 0)), "RGBA")
        pawn = pygame.image.tobytes(probe.render("\u2659", True, (0, 0, 0)), "RGBA")
        return king != pawn

    def _resolve_glyph_font_path(self) -> str | None:
        """Find the first available font that really has chess glyphs."""
        if self._glyph_font_resolved:
            return self._glyph_font_path
        self._glyph_font_resolved = True
        for name in GLYPH_FONTS:
            found = pygame.font.match_font(name)
            if found and self._font_has_chess_glyphs(found):
                self._glyph_font_path = found
                break
        return self._glyph_font_path

    def _glyph_font_for(self, size: int) -> pygame.font.Font:
        """Return a font able to render the chess glyphs at ``size``."""
        if self._glyph_font is not None and self._glyph_font.get_height() >= size:
            return self._glyph_font
        path = self._resolve_glyph_font_path()
        # Render large then scale down for crisp edges.
        self._glyph_font = pygame.font.Font(path, int(size * 1.6)) if path \
            else pygame.font.Font(None, int(size * 1.6))
        return self._glyph_font

    def _draw_piece_shape(self, piece_type: str, is_black: bool, size: int) -> pygame.Surface:
        """Draw a distinct procedural silhouette for ``piece_type``.

        Used as a fallback when no installed font provides the chess glyphs,
        so every piece still renders with its own recognisable shape.
        """
        if is_black:
            body, outline = (28, 28, 34), (232, 232, 238)
        else:
            body, outline = (246, 246, 250), (26, 26, 32)

        piece = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = size // 2
        stroke = max(2, size // 18)
        base_y = int(size * 0.86)
        top_y = int(size * 0.16)

        def disc(center, radius):
            pygame.draw.circle(piece, body, center, radius)
            pygame.draw.circle(piece, outline, center, radius, stroke)

        def rect(r):
            pygame.draw.rect(piece, body, r, border_radius=max(2, size // 20))
            pygame.draw.rect(piece, outline, r, stroke, border_radius=max(2, size // 20))

        # Shared pedestal for every piece.
        rect(pygame.Rect(int(size * 0.22), base_y - int(size * 0.10),
                         int(size * 0.56), int(size * 0.12)))

        if piece_type == "pawn":
            disc((cx, int(size * 0.40)), int(size * 0.13))
            rect(pygame.Rect(cx - int(size * 0.10), int(size * 0.50),
                             int(size * 0.20), int(size * 0.28)))
        elif piece_type == "rook":
            rect(pygame.Rect(int(size * 0.28), int(size * 0.30),
                             int(size * 0.44), int(size * 0.48)))
            for i in range(3):
                bx = int(size * (0.28 + i * 0.16))
                rect(pygame.Rect(bx, top_y, int(size * 0.10), int(size * 0.12)))
        elif piece_type == "knight":
            pts = [(int(size * 0.30), base_y - int(size * 0.10)),
                   (int(size * 0.34), int(size * 0.34)),
                   (int(size * 0.52), top_y),
                   (int(size * 0.70), int(size * 0.30)),
                   (int(size * 0.62), int(size * 0.52)),
                   (int(size * 0.72), base_y - int(size * 0.10))]
            pygame.draw.polygon(piece, body, pts)
            pygame.draw.polygon(piece, outline, pts, stroke)
        elif piece_type == "bishop":
            disc((cx, int(size * 0.30)), int(size * 0.12))
            pygame.draw.polygon(piece, body, [
                (cx, int(size * 0.18)),
                (int(size * 0.34), int(size * 0.62)),
                (int(size * 0.66), int(size * 0.62)),
            ])
            pygame.draw.polygon(piece, outline, [
                (cx, int(size * 0.18)),
                (int(size * 0.34), int(size * 0.62)),
                (int(size * 0.66), int(size * 0.62)),
            ], stroke)
            rect(pygame.Rect(int(size * 0.30), int(size * 0.60),
                             int(size * 0.40), int(size * 0.16)))
        elif piece_type == "queen":
            disc((cx, int(size * 0.26)), int(size * 0.11))
            for i in range(3):
                px = int(size * (0.30 + i * 0.20))
                disc((px, int(size * 0.20)), int(size * 0.06))
            pygame.draw.polygon(piece, body, [
                (int(size * 0.30), int(size * 0.34)),
                (int(size * 0.70), int(size * 0.34)),
                (int(size * 0.62), int(size * 0.66)),
                (int(size * 0.38), int(size * 0.66)),
            ])
            pygame.draw.polygon(piece, outline, [
                (int(size * 0.30), int(size * 0.34)),
                (int(size * 0.70), int(size * 0.34)),
                (int(size * 0.62), int(size * 0.66)),
                (int(size * 0.38), int(size * 0.66)),
            ], stroke)
        else:  # king
            rect(pygame.Rect(cx - int(size * 0.05), int(size * 0.12),
                             int(size * 0.10), int(size * 0.20)))
            rect(pygame.Rect(cx - int(size * 0.13), int(size * 0.18),
                             int(size * 0.26), int(size * 0.08)))
            pygame.draw.polygon(piece, body, [
                (int(size * 0.30), int(size * 0.36)),
                (int(size * 0.70), int(size * 0.36)),
                (int(size * 0.62), int(size * 0.66)),
                (int(size * 0.38), int(size * 0.66)),
            ])
            pygame.draw.polygon(piece, outline, [
                (int(size * 0.30), int(size * 0.36)),
                (int(size * 0.70), int(size * 0.36)),
                (int(size * 0.62), int(size * 0.66)),
                (int(size * 0.38), int(size * 0.66)),
            ], stroke)

        return piece

    def standard_piece(self, piece_type: str, is_black: bool, size: int) -> pygame.Surface:
        """Render a classic chess piece glyph fitted into a ``size`` square.

        The glyph is drawn with a contrasting outline so it stays legible on
        both light and dark squares, then scaled to fill the square. If no
        installed font provides the chess glyphs, a distinct procedural
        silhouette is drawn instead so pieces never collapse to one shape.
        """
        key = (piece_type, is_black, size)
        cached = self._standard.get(key)
        if cached is not None:
            return cached

        if self._resolve_glyph_font_path() is None:
            piece = self._draw_piece_shape(piece_type, is_black, size)
            self._standard[key] = piece
            return piece

        glyph = (BLACK_GLYPHS if is_black else WHITE_GLYPHS).get(piece_type, WHITE_GLYPHS["pawn"])
        font = self._glyph_font_for(size)

        if is_black:
            body, outline = (28, 28, 34), (232, 232, 238)
        else:
            body, outline = (246, 246, 250), (26, 26, 32)

        # Draw the glyph several times offset to build a clean outline.
        base = font.render(glyph, True, body)
        out = font.render(glyph, True, outline)
        w, h = base.get_size()
        pad = max(2, size // 16)
        canvas = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        for dx in (-pad, 0, pad):
            for dy in (-pad, 0, pad):
                if dx or dy:
                    canvas.blit(out, (pad + dx, pad + dy))
        canvas.blit(base, (pad, pad))

        # Scale to fit the square, preserving aspect ratio.
        cw, ch = canvas.get_size()
        scale = size / max(cw, ch)
        new_size = (max(1, int(cw * scale)), max(1, int(ch * scale)))
        scaled = pygame.transform.smoothscale(canvas, new_size)

        piece = pygame.Surface((size, size), pygame.SRCALPHA)
        piece.blit(scaled, scaled.get_rect(center=(size // 2, size // 2)))
        self._standard[key] = piece
        return piece

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
