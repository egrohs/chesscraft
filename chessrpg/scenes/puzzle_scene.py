"""Puzzle gameplay scene: board, HUD, move log and result overlay."""

from __future__ import annotations

import chess
import pygame

from .. import config, theme
from ..board import BoardView
from ..puzzles import PuzzleSession, get_puzzle
from ..scene import Scene
from ..ui import Button, IconButton


class PuzzleScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self._bg = theme.vertical_gradient(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
            (22, 26, 40), (9, 10, 16),
        )
        self.session: PuzzleSession | None = None
        self.board_view: BoardView | None = None
        self._t = 0.0
        self._toast: tuple[str, tuple[int, int, int], float] | None = None
        self._result: str | None = None
        self._result_t = 0.0
        self._reward: tuple[int, int] = (0, 0)
        self._move_log: list[str] = []
        self._build_static()

    # ------------------------------------------------------------------
    def _build_static(self) -> None:
        w = config.WINDOW_WIDTH
        self.widgets.clear()
        self.widgets.append(IconButton((24, 24, 48, 48), "<", self._on_back,
                                       accent=theme.RED, tooltip="Back to map"))
        self.widgets.append(Button((w - 200, 24, 176, 48), "Restart",
                                   self._on_restart, size=20, accent=theme.BLUE))
        self.widgets.append(Button((w - 200, 84, 176, 48), "Hint",
                                   self._on_hint, size=20, accent=theme.PURPLE,
                                   subtitle=f"-{config.HINT_COST} gold"))

    # ------------------------------------------------------------------
    def on_enter(self, puzzle_id: str = "p1", **kwargs) -> None:
        puzzle = get_puzzle(puzzle_id)
        if puzzle is None:
            self.game.scenes_mgr.switch("level_select")
            return
        self.session = PuzzleSession(puzzle)
        self._result = None
        self._result_t = 0.0
        self._move_log = []
        self._toast = None

        board_x = (config.WINDOW_WIDTH - config.BOARD_PIXELS) // 2
        board_y = (config.WINDOW_HEIGHT - config.BOARD_PIXELS) // 2 + 20
        self.board_view = BoardView((board_x, board_y))
        self.board_view.art_set = self.game.profile.settings.get("art_set", "class")
        self.board_view.set_board(self.session.board)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _on_back(self) -> None:
        self.game.scenes_mgr.switch("level_select")

    def _on_restart(self) -> None:
        if self.session is None:
            return
        self.session.reset()
        self.board_view.set_board(self.session.board)
        self._move_log = []
        self._result = None
        self._toast = ("Puzzle reset", theme.BLUE, 1.4)

    def _on_hint(self) -> None:
        if self.session is None or self.session.solved:
            return
        hero = self.game.profile.hero
        if hero.gold < config.HINT_COST:
            self._toast = ("Not enough gold", theme.RED, 1.4)
            return
        move = self.session.hint_move()
        if move is None:
            return
        hero.gold -= config.HINT_COST
        self.board_view.hint_move = move
        self._toast = ("Hint revealed", theme.HINT_GLOW, 1.6)

    def _toast_msg(self, text: str, color, duration: float = 1.6) -> None:
        self._toast = (text, color, duration)

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if self._result is not None:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.handle_result_click(event.pos):
                    return
            super().handle_event(event)
            return

        if self.board_view is not None and self.session is not None:
            action = self.board_view.handle_event(event)
            if action is not None:
                self._handle_board_action(action)
                return
        super().handle_event(event)

    def _handle_board_action(self, action) -> None:
        kind = action[0]
        if kind != "move":
            return
        _, src, dst = action
        move = chess.Move(src, dst)
        # Auto-promote to queen for simplicity.
        piece = self.session.board.piece_at(src)
        if piece and piece.piece_type == chess.PAWN and chess.square_rank(dst) in (0, 7):
            move = chess.Move(src, dst, promotion=chess.QUEEN)

        result = self.session.try_move(move)
        self.board_view.hint_move = None

        if result == "wrong":
            self.board_view.flash_square(dst, theme.RED)
            self.board_view.flash_square(src, theme.RED)
            self._toast_msg("Not the move - try again", theme.RED)
            return

        # Correct: animate and update the view
        self.board_view.set_board(self.session.board)
        self.board_view.last_move = self.session.history[-1] if self.session.history else move
        self.board_view.animate_move(move)
        self._log_moves()

        if result == "solved":
            self._on_solved()
        else:
            self._toast_msg("Good! Keep going", theme.GREEN)

    def _log_moves(self) -> None:
        self._move_log = []
        board = chess.Board(self.session.puzzle.fen)
        for i, mv in enumerate(self.session.history):
            san = board.san(mv)
            board.push(mv)
            if i % 2 == 0:
                self._move_log.append(f"{i // 2 + 1}. {san}")
            else:
                self._move_log[-1] += f"  {san}"

    def _on_solved(self) -> None:
        xp, gold = self.session.score()
        self._reward = (xp, gold)
        hero = self.game.profile.hero
        levelled = hero.gain_xp(xp)
        hero.gold += gold
        if self.session.puzzle.id not in hero.solved:
            hero.solved.append(self.session.puzzle.id)
        self._unlock_next()
        self.game.profile.save()

        self._result = "victory"
        self._result_t = 0.0
        if levelled:
            self._toast_msg(f"Level up! You are now level {hero.level}", theme.GOLD_BRIGHT, 3.0)

    def _unlock_next(self) -> None:
        from ..puzzles import PUZZLES
        ids = [p.id for p in PUZZLES]
        idx = ids.index(self.session.puzzle.id)
        if idx + 1 < len(ids):
            nxt = ids[idx + 1]
            if nxt not in self.game.profile.hero.unlocked:
                self.game.profile.hero.unlocked.append(nxt)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self._t += dt
        if self.board_view is not None:
            self.board_view.update(dt)
        if self._toast is not None:
            text, color, t = self._toast
            t -= dt
            self._toast = None if t <= 0 else (text, color, t)
        if self._result is not None:
            self._result_t += dt
        super().update(dt)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._bg, (0, 0))
        if self.session is None or self.board_view is None:
            return

        self.board_view.draw(surface)
        self._draw_left_panel(surface)
        self._draw_right_panel(surface)
        self._draw_toast(surface)

        super().draw(surface)

        if self._result is not None:
            self._draw_result(surface)

    # ------------------------------------------------------------------
    def _draw_left_panel(self, surface: pygame.Surface) -> None:
        puzzle = self.session.puzzle
        panel = pygame.Rect(24, 96, 300, 420)
        theme.draw_panel(surface, panel, fill=theme.BG_PANEL, border=theme.GOLD_DARK, radius=12)

        theme.draw_text(surface, puzzle.name, (panel.x + 20, panel.y + 18), size=26,
                        color=theme.GOLD_BRIGHT, bold=True)
        theme.draw_text(surface, f"Difficulty {puzzle.stars}", (panel.x + 20, panel.y + 52),
                        size=16, color=theme.TEXT_DIM)
        theme.draw_text(surface, f"Goal: {puzzle.goal}", (panel.x + 20, panel.y + 74),
                        size=16, color=theme.TEXT_DIM)

        theme.draw_text(surface, "Briefing", (panel.x + 20, panel.y + 108), size=18,
                        color=theme.GOLD, bold=True)
        theme.draw_text(surface, puzzle.briefing, (panel.x + 20, panel.y + 134),
                        size=15, color=theme.TEXT, wrap_width=panel.width - 40)

        # Progress
        theme.draw_text(surface, "Progress", (panel.x + 20, panel.y + 250), size=18,
                        color=theme.GOLD, bold=True)
        bar = pygame.Rect(panel.x + 20, panel.y + 278, panel.width - 40, 18)
        theme.draw_bar(surface, bar, self.session.progress, fill=theme.GREEN)

        theme.draw_text(surface, f"Mistakes: {self.session.mistakes}",
                        (panel.x + 20, panel.y + 312), size=16, color=theme.RED)
        theme.draw_text(surface, f"Hints used: {self.session.hints_used}",
                        (panel.x + 20, panel.y + 336), size=16, color=theme.PURPLE)

        # Move log
        theme.draw_text(surface, "Moves", (panel.x + 20, panel.y + 368), size=18,
                        color=theme.GOLD, bold=True)
        y = panel.y + 394
        for line in self._move_log[-3:]:
            theme.draw_text(surface, line, (panel.x + 20, y), size=15, color=theme.TEXT_DIM)
            y += 20

    def _draw_right_panel(self, surface: pygame.Surface) -> None:
        hero = self.game.profile.hero
        panel = pygame.Rect(config.WINDOW_WIDTH - 324, 156, 300, 360)
        theme.draw_panel(surface, panel, fill=theme.BG_PANEL, border=theme.GOLD_DARK, radius=12)

        # Hero portrait
        portrait = self.game.assets.portrait("healer-king", 150)
        px = panel.centerx - portrait.get_width() // 2
        surface.blit(portrait, (px, panel.y + 14))

        theme.draw_text(surface, hero.name, (panel.centerx, panel.y + 176), size=24,
                        color=theme.GOLD_BRIGHT, bold=True, center=True)
        theme.draw_text(surface, hero.title, (panel.centerx, panel.y + 204), size=15,
                        color=theme.TEXT_DIM, center=True)

        theme.draw_text(surface, f"Level {hero.level}", (panel.x + 20, panel.y + 236),
                        size=18, color=theme.TEXT, bold=True)
        theme.draw_text(surface, f"{hero.xp}/{hero.xp_to_next} XP",
                        (panel.right - 20, panel.y + 238), size=15,
                        color=theme.TEXT_DIM, right=True)
        theme.draw_bar(surface, pygame.Rect(panel.x + 20, panel.y + 262, panel.width - 40, 14),
                       hero.xp_ratio, fill=theme.GOLD)

        theme.draw_text(surface, f"Gold: {hero.gold}", (panel.x + 20, panel.y + 292),
                        size=17, color=theme.GOLD_BRIGHT)
        theme.draw_text(surface, f"Rating: {hero.rating}", (panel.right - 20, panel.y + 292),
                        size=17, color=theme.TEXT_DIM, right=True)

        stats = [("Tactics", hero.tactics), ("Focus", hero.focus), ("Resolve", hero.resolve)]
        y = panel.y + 322
        for name, value in stats:
            theme.draw_text(surface, name, (panel.x + 20, y), size=15, color=theme.TEXT_DIM)
            theme.draw_text(surface, str(value), (panel.right - 20, y), size=15,
                            color=theme.TEXT, right=True)
            y += 22

    def _draw_toast(self, surface: pygame.Surface) -> None:
        if self._toast is None:
            return
        text, color, t = self._toast
        alpha = min(1.0, t * 2)
        f = theme.font(24, True)
        img = f.render(text, True, color)
        rect = img.get_rect(center=(config.WINDOW_WIDTH // 2, 120))
        pad = 16
        box = rect.inflate(pad * 2, pad)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*theme.BG_PANEL_DARK, int(230 * alpha)),
                         panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, (*color, int(255 * alpha)), panel.get_rect(),
                         width=2, border_radius=10)
        surface.blit(panel, box.topleft)
        img.set_alpha(int(255 * alpha))
        surface.blit(img, rect)

    def _draw_result(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        surface.blit(overlay, (0, 0))

        card = pygame.Rect(0, 0, 520, 340)
        card.center = (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2)
        theme.draw_panel(surface, card, fill=theme.BG_PANEL, border=theme.GOLD, radius=16,
                         border_width=3)

        theme.draw_text(surface, "VICTORY", (card.centerx, card.y + 50), size=48,
                        color=theme.GOLD_BRIGHT, bold=True, center=True)
        theme.draw_text(surface, self.session.puzzle.name, (card.centerx, card.y + 96),
                        size=22, color=theme.TEXT, center=True)

        xp, gold = self._reward
        theme.draw_text(surface, f"+{xp} XP", (card.centerx - 90, card.y + 150), size=26,
                        color=theme.GREEN, bold=True, center=True)
        theme.draw_text(surface, f"+{gold} Gold", (card.centerx + 90, card.y + 150), size=26,
                        color=theme.GOLD_BRIGHT, bold=True, center=True)

        theme.draw_text(surface, f"Mistakes: {self.session.mistakes}   "
                                 f"Hints: {self.session.hints_used}",
                        (card.centerx, card.y + 196), size=17, color=theme.TEXT_DIM, center=True)

        # Buttons drawn manually so they appear above the overlay
        bw, bh = 200, 52
        retry = pygame.Rect(card.centerx - bw - 12, card.bottom - 84, bw, bh)
        nxt = pygame.Rect(card.centerx + 12, card.bottom - 84, bw, bh)
        self._draw_overlay_button(surface, retry, "Retry", theme.BLUE)
        self._draw_overlay_button(surface, nxt, "Next Trial", theme.GOLD)

        self._overlay_buttons = {"retry": retry, "next": nxt}

    def _draw_overlay_button(self, surface, rect, text, accent) -> None:
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        fill = theme.BG_PANEL_LIGHT if hovered else theme.BG_PANEL_DARK
        theme.draw_panel(surface, rect, fill=fill, border=accent if hovered else theme.GOLD_DARK,
                         radius=10)
        theme.draw_text(surface, text, rect.center, size=22,
                        color=theme.GOLD_BRIGHT if hovered else theme.TEXT,
                        bold=True, center=True)

    # Result overlay buttons need their own click handling.
    def handle_result_click(self, pos) -> bool:
        buttons = getattr(self, "_overlay_buttons", None)
        if not buttons:
            return False
        if buttons["retry"].collidepoint(pos):
            self._on_restart()
            return True
        if buttons["next"].collidepoint(pos):
            self._go_next()
            return True
        return False

    def _go_next(self) -> None:
        from ..puzzles import PUZZLES
        ids = [p.id for p in PUZZLES]
        idx = ids.index(self.session.puzzle.id)
        if idx + 1 < len(ids):
            self.game.scenes_mgr.switch("puzzle", puzzle_id=ids[idx + 1])
        else:
            self.game.scenes_mgr.switch("level_select")
