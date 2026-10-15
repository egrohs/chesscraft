"""Chess board renderer and input handling.

The board owns the mapping between screen pixels and chess squares, draws
the board, pieces and all highlight overlays, and translates mouse input
into square selections. It is deliberately independent from the puzzle
rules: it reports *what the player did* and the scene decides what it means.
"""

from __future__ import annotations

from typing import Optional

import chess
import pygame

from . import config, theme
from .assets import ASSETS

FILES = "abcdefgh"


def square_to_xy(square: int, origin: tuple[int, int], flipped: bool = False) -> tuple[int, int]:
    """Top-left pixel of ``square`` given the board origin."""
    file = chess.square_file(square)
    rank = chess.square_rank(square)
    if flipped:
        file = 7 - file
        rank = 7 - rank
    return origin[0] + file * config.SQUARE_SIZE, origin[1] + (7 - rank) * config.SQUARE_SIZE


def xy_to_square(pos: tuple[int, int], origin: tuple[int, int], flipped: bool = False) -> Optional[int]:
    """Convert a pixel position to a square index, or None if outside."""
    dx = pos[0] - origin[0]
    dy = pos[1] - origin[1]
    if dx < 0 or dy < 0:
        return None
    file = dx // config.SQUARE_SIZE
    rank_from_top = dy // config.SQUARE_SIZE
    if file > 7 or rank_from_top > 7:
        return None
    if flipped:
        file = 7 - file
        rank = rank_from_top
    else:
        rank = 7 - rank_from_top
    return chess.square(int(file), int(rank))


class BoardView:
    """Draws a chess position and handles click / drag selection."""

    def __init__(self, origin: tuple[int, int], *, flipped: bool = False) -> None:
        self.origin = origin
        self.flipped = flipped
        self.size = config.BOARD_PIXELS
        self.rect = pygame.Rect(origin[0], origin[1], self.size, self.size)

        self.board: chess.Board = chess.Board()

        # Interaction state
        self.selected: Optional[int] = None
        self.legal_targets: set[int] = set()
        self.dragging: Optional[int] = None
        self.drag_pos: tuple[int, int] = (0, 0)
        self.hover_square: Optional[int] = None

        # Overlays
        self.last_move: Optional[chess.Move] = None
        self.hint_move: Optional[chess.Move] = None
        self.check_square: Optional[int] = None
        self.flash: dict[int, tuple[tuple[int, int, int], float]] = {}
        self.interactive = True
        self.art_set = "class"

        # Animation
        self._anim: Optional[dict] = None

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def set_board(self, board: chess.Board) -> None:
        self.board = board
        self.clear_selection()
        self.last_move = None
        self.hint_move = None
        self.flash.clear()
        self._anim = None
        self._update_check()

    def _update_check(self) -> None:
        self.check_square = None
        if self.board.is_check():
            self.check_square = self.board.king(self.board.turn)

    def clear_selection(self) -> None:
        self.selected = None
        self.legal_targets = set()
        self.dragging = None

    def flash_square(self, square: int, color, duration_ms: int = config.FLASH_MS) -> None:
        self.flash[square] = (color, duration_ms / 1000.0)

    def animate_move(self, move: chess.Move, duration_ms: int = config.MOVE_ANIM_MS) -> None:
        """Start a slide animation for ``move`` (piece already applied)."""
        self._anim = {
            "move": move,
            "t": 0.0,
            "dur": duration_ms / 1000.0,
        }

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> Optional[tuple[str, int, Optional[int]]]:
        """Return an action tuple or None.

        Actions:
          ("select", square, None)  - a piece was picked up
          ("move", from_sq, to_sq)  - a destination was chosen
          ("deselect", sq, None)    - selection cleared
        """
        if not self.interactive:
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            sq = xy_to_square(event.pos, self.origin, self.flipped)
            if sq is None:
                if self.selected is not None:
                    self.clear_selection()
                    return ("deselect", 0, None)
                return None
            piece = self.board.piece_at(sq)
            if self.selected is not None and sq in self.legal_targets:
                src = self.selected
                self.clear_selection()
                return ("move", src, sq)
            if piece is not None and piece.color == self.board.turn:
                self.selected = sq
                self.legal_targets = {
                    m.to_square for m in self.board.legal_moves if m.from_square == sq
                }
                self.dragging = sq
                self.drag_pos = event.pos
                return ("select", sq, None)
            if self.selected is not None:
                self.clear_selection()
                return ("deselect", 0, None)
            return None

        if event.type == pygame.MOUSEMOTION:
            self.hover_square = xy_to_square(event.pos, self.origin, self.flipped)
            if self.dragging is not None:
                self.drag_pos = event.pos
            return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragging is not None:
                src = self.dragging
                self.dragging = None
                sq = xy_to_square(event.pos, self.origin, self.flipped)
                if sq is not None and sq != src and sq in self.legal_targets:
                    self.clear_selection()
                    return ("move", src, sq)
                # Snap back: keep the piece selected for click-click play.
                self.selected = src
                self.legal_targets = {
                    m.to_square for m in self.board.legal_moves if m.from_square == src
                }
            return None

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if self.selected is not None:
                self.clear_selection()
                return ("deselect", 0, None)
        return None

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        if self._anim is not None:
            self._anim["t"] += dt
            if self._anim["t"] >= self._anim["dur"]:
                self._anim = None

        expired = [sq for sq, (_, t) in self.flash.items() if t <= 0]
        for sq in expired:
            del self.flash[sq]
        for sq in list(self.flash):
            color, t = self.flash[sq]
            self.flash[sq] = (color, t - dt)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self._draw_frame(surface)
        self._draw_squares(surface)
        self._draw_coords(surface)
        self._draw_highlights(surface)
        self._draw_pieces(surface)

    def _draw_frame(self, surface: pygame.Surface) -> None:
        frame = self.rect.inflate(16, 16)
        theme.draw_panel(surface, frame, fill=theme.BG_PANEL_DARK,
                         border=theme.GOLD_DARK, radius=8, border_width=3)

    def _draw_squares(self, surface: pygame.Surface) -> None:
        for rank in range(8):
            for file in range(8):
                sq = chess.square(file, rank)
                x, y = square_to_xy(sq, self.origin, self.flipped)
                light = (file + rank) % 2 == 1
                color = theme.LIGHT_SQUARE if light else theme.DARK_SQUARE
                pygame.draw.rect(surface, color, (x, y, config.SQUARE_SIZE, config.SQUARE_SIZE))

    def _draw_coords(self, surface: pygame.Surface) -> None:
        for i in range(8):
            file = 7 - i if self.flipped else i
            rank = i if self.flipped else 7 - i
            # File letters along the bottom
            x = self.origin[0] + i * config.SQUARE_SIZE + config.SQUARE_SIZE - 6
            y = self.origin[1] + self.size - 18
            theme.draw_text(surface, FILES[file], (x, y), size=13,
                            color=theme.TEXT_MUTED, right=True)
            # Rank numbers along the left
            theme.draw_text(surface, str(rank + 1),
                            (self.origin[0] + 5, self.origin[1] + i * config.SQUARE_SIZE + 3),
                            size=13, color=theme.TEXT_MUTED)

    def _draw_highlights(self, surface: pygame.Surface) -> None:
        # Last move
        if self.last_move:
            for sq in (self.last_move.from_square, self.last_move.to_square):
                self._tint_square(surface, sq, theme.LAST_MOVE, 70)

        # Hint
        if self.hint_move:
            for sq in (self.hint_move.from_square, self.hint_move.to_square):
                self._tint_square(surface, sq, theme.HINT_GLOW, 90)

        # Check
        if self.check_square is not None:
            self._tint_square(surface, self.check_square, theme.CHECK_GLOW, 110)

        # Selection
        if self.selected is not None:
            self._tint_square(surface, self.selected, theme.SELECT, 110)

        # Legal move markers
        for sq in self.legal_targets:
            x, y = square_to_xy(sq, self.origin, self.flipped)
            cx = x + config.SQUARE_SIZE // 2
            cy = y + config.SQUARE_SIZE // 2
            if self.board.piece_at(sq) is not None:
                pygame.draw.circle(surface, theme.CAPTURE_RING, (cx, cy),
                                   config.SQUARE_SIZE // 2 - 4, 4)
            else:
                pygame.draw.circle(surface, theme.MOVE_DOT, (cx, cy), 9)

        # Hover outline
        if self.hover_square is not None and self.interactive:
            x, y = square_to_xy(self.hover_square, self.origin, self.flipped)
            pygame.draw.rect(surface, theme.GOLD_BRIGHT,
                             (x, y, config.SQUARE_SIZE, config.SQUARE_SIZE), 2)

        # Flash overlays
        for sq, (color, t) in self.flash.items():
            alpha = int(150 * min(1.0, t * 3))
            self._tint_square(surface, sq, color, alpha)

    def _tint_square(self, surface, square, color, alpha) -> None:
        x, y = square_to_xy(square, self.origin, self.flipped)
        overlay = pygame.Surface((config.SQUARE_SIZE, config.SQUARE_SIZE), pygame.SRCALPHA)
        overlay.fill((*color, max(0, min(255, alpha))))
        surface.blit(overlay, (x, y))

    def _draw_pieces(self, surface: pygame.Surface) -> None:
        anim = self._anim
        anim_sq = None
        if anim is not None:
            anim_sq = anim["move"].to_square

        for rank in range(8):
            for file in range(8):
                sq = chess.square(file, rank)
                if sq == anim_sq:
                    continue
                if self.dragging == sq:
                    continue
                piece = self.board.piece_at(sq)
                if piece is None:
                    continue
                self._blit_piece(surface, piece, sq)

        # Animated piece slides from origin to destination
        if anim is not None:
            move = anim["move"]
            piece = self.board.piece_at(move.to_square)
            if piece is not None:
                t = min(1.0, anim["t"] / anim["dur"])
                t = t * t * (3 - 2 * t)  # smoothstep
                x0, y0 = square_to_xy(move.from_square, self.origin, self.flipped)
                x1, y1 = square_to_xy(move.to_square, self.origin, self.flipped)
                x = int(x0 + (x1 - x0) * t)
                y = int(y0 + (y1 - y0) * t)
                self._blit_piece_at(surface, piece, (x, y))

        # Dragged piece follows the cursor
        if self.dragging is not None:
            piece = self.board.piece_at(self.dragging)
            if piece is not None:
                size = config.SQUARE_SIZE
                surf = ASSETS.piece_surface(piece.symbol().lower(), self.art_set, size)
                rect = surf.get_rect(center=self.drag_pos)
                shadow = pygame.Surface((size, size), pygame.SRCALPHA)
                shadow.blit(surf, (0, 0))
                shadow.set_alpha(90)
                surface.blit(shadow, (rect.x + 6, rect.y + 8))
                surface.blit(surf, rect)

    def _blit_piece(self, surface, piece, square) -> None:
        x, y = square_to_xy(square, self.origin, self.flipped)
        self._blit_piece_at(surface, piece, (x, y))

    def _blit_piece_at(self, surface, piece, pos) -> None:
        size = config.SQUARE_SIZE
        surf = ASSETS.piece_surface(piece.symbol().lower(), self.art_set, size)
        if piece.color == chess.BLACK:
            surf = _darken(surf, 0.55)
        surface.blit(surf, pos)


def _darken(surf: pygame.Surface, factor: float) -> pygame.Surface:
    """Return a cold, darkened copy of a token (used for the black army).

    The token is desaturated toward a deep blue-grey so black pieces read as
    a distinct army while keeping the painted detail visible.
    """
    out = surf.copy()
    tint = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    tint.fill((int(255 * factor), int(255 * factor), int(255 * (factor + 0.12)), 255))
    out.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return out
