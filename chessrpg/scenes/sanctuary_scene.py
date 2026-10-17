"""Sanctuary scene: choose a spell, then solve its chess puzzle to learn it.

Reaching a sanctuary offers three spells the mage does not yet know. The
player picks one; a themed chess puzzle appears. Solving it teaches the spell.
A wrong move costs a retry with a penalty (the puzzle resets and the mage
loses a little life). Solving it on the first try records the tactic in the
profile so future runs can learn that spell without the test.
"""

from __future__ import annotations

import chess
import pygame

from .. import config, theme
from ..board import BoardView
from ..combat import SPELL_LIBRARY
from ..puzzles import PuzzleSession, themed_puzzle_for
from ..run import Run, spell_offers
from ..scene import Scene
from ..ui import Button, IconButton

# Penalty applied to the mage when a puzzle attempt fails.
FAIL_PENALTY = 1


class SanctuaryScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self._bg = theme.vertical_gradient(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
            (24, 30, 44), (8, 10, 16),
        )
        self.run: Run | None = None
        self.offers: list[str] = []
        self.chosen: str | None = None
        self.session: PuzzleSession | None = None
        self.board_view: BoardView | None = None
        self.phase = "choose"          # "choose" | "puzzle" | "learned" | "failed"
        self._toast: tuple[str, tuple, float] | None = None
        self._t = 0.0
        self._first_try = True
        self._build_widgets()

    def _build_widgets(self) -> None:
        self.widgets.clear()
        w = config.WINDOW_WIDTH
        self.widgets.append(IconButton((24, 24, 48, 48), "<", self._on_leave,
                                       accent=theme.RED, tooltip="Leave sanctuary"))

    # ------------------------------------------------------------------
    def on_enter(self, run: Run | None = None, **kwargs) -> None:
        if run is not None:
            self.run = run
        if self.run is None:
            self.game.scenes_mgr.switch("menu")
            return
        self.offers = spell_offers(self.run, self.run.rng, 3)
        self.chosen = None
        self.session = None
        self.board_view = None
        self.phase = "choose"
        self._first_try = True
        self._toast = None

    def _on_leave(self) -> None:
        self.game.scenes_mgr.switch("combat", run=self.run)

    # ------------------------------------------------------------------
    def _choose(self, spell_id: str) -> None:
        self.chosen = spell_id
        puzzle = themed_puzzle_for(spell_id)
        if puzzle is None:
            # No puzzle defined: grant the spell directly.
            self._learn()
            return
        self.session = PuzzleSession(puzzle)
        board_x = (config.WINDOW_WIDTH - config.BOARD_PIXELS) // 2
        board_y = (config.WINDOW_HEIGHT - config.BOARD_PIXELS) // 2 + 20
        self.board_view = BoardView((board_x, board_y))
        self.board_view.art_set = self.game.profile.settings.get("art_set", "class")
        self.board_view.set_board(self.session.board)
        self.phase = "puzzle"

    def _learn(self) -> None:
        assert self.run is not None and self.chosen is not None
        self.run.learn_spell(self.chosen)
        # Record the tactic permanently if solved on the first try.
        if self._first_try:
            hero = self.game.profile.hero
            if self.chosen not in hero.learned_tactics:
                hero.learned_tactics.append(self.chosen)
            self.game.profile.save()
        self.phase = "learned"

    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.phase == "choose":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_choose_click(event.pos)
                return
        elif self.phase == "puzzle" and self.board_view is not None and self.session is not None:
            action = self.board_view.handle_event(event)
            if action is not None:
                self._handle_board_action(action)
                return
        elif self.phase in ("learned", "failed"):
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_leave()
                return
        super().handle_event(event)

    def _handle_choose_click(self, pos) -> None:
        for i, sid in enumerate(self.offers):
            if self._card_rect(i).collidepoint(pos):
                self._choose(sid)
                return

    def _handle_board_action(self, action) -> None:
        if action[0] != "move":
            return
        _, src, dst = action
        move = chess.Move(src, dst)
        piece = self.session.board.piece_at(src)
        if piece and piece.piece_type == chess.PAWN and chess.square_rank(dst) in (0, 7):
            move = chess.Move(src, dst, promotion=chess.QUEEN)

        result = self.session.try_move(move)
        if result == "wrong":
            self._first_try = False
            self.board_view.flash_square(dst, theme.RED)
            self.board_view.flash_square(src, theme.RED)
            # Penalty: reset the puzzle and cost the mage a little life.
            self.session.reset()
            self.board_view.set_board(self.session.board)
            if self.run is not None and self.run.mage is not None:
                self.run.mage.hp = max(1, self.run.mage.hp - FAIL_PENALTY)
            self._toast = ("Wrong - the trial resets. You lose 1 life.", theme.RED, 2.2)
            return

        self.board_view.set_board(self.session.board)
        self.board_view.last_move = self.session.history[-1] if self.session.history else move
        self.board_view.animate_move(move)

        if result == "solved":
            self._learn()

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self._t += dt
        if self.board_view is not None:
            self.board_view.update(dt)
        if self._toast is not None:
            text, color, t = self._toast
            t -= dt
            self._toast = None if t <= 0 else (text, color, t)
        super().update(dt)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._bg, (0, 0))
        if self.phase == "choose":
            self._draw_choose(surface)
        elif self.phase == "puzzle":
            self._draw_puzzle(surface)
        else:
            self._draw_result(surface)
        self._draw_toast(surface)
        super().draw(surface)

    def _card_rect(self, i: int) -> pygame.Rect:
        cw, ch = 300, 360
        gap = 40
        total = 3 * cw + 2 * gap
        x0 = (config.WINDOW_WIDTH - total) // 2
        y = (config.WINDOW_HEIGHT - ch) // 2 + 20
        return pygame.Rect(x0 + i * (cw + gap), y, cw, ch)

    def _draw_choose(self, surface) -> None:
        theme.draw_text(surface, "ARCANE SANCTUARY", (config.WINDOW_WIDTH // 2, 70),
                        size=44, color=theme.GOLD_BRIGHT, bold=True, center=True)
        theme.draw_text(surface, "Choose a spell. Solve its chess trial to master it.",
                        (config.WINDOW_WIDTH // 2, 118), size=18, color=theme.TEXT_DIM, center=True)

        mouse = pygame.mouse.get_pos()
        for i, sid in enumerate(self.offers):
            spell = SPELL_LIBRARY[sid]
            r = self._card_rect(i)
            hovered = r.collidepoint(mouse)
            border = theme.GOLD_BRIGHT if hovered else theme.GOLD_DARK
            theme.draw_panel(surface, r, fill=theme.BG_PANEL_LIGHT if hovered else theme.BG_PANEL,
                             border=border, radius=14, border_width=3)
            theme.draw_text(surface, spell.name, (r.centerx, r.y + 40), size=28,
                            color=theme.GOLD_BRIGHT, bold=True, center=True)
            theme.draw_text(surface, spell.kind.value.upper(), (r.centerx, r.y + 74),
                            size=14, color=theme.TEXT_MUTED, center=True)
            theme.draw_text(surface, spell.description, (r.x + 24, r.y + 110), size=16,
                            color=theme.TEXT, wrap_width=r.width - 48)
            # Stats.
            stats = []
            if spell.range:
                stats.append(f"Range {spell.range}")
            if spell.damage:
                stats.append(f"Dmg {spell.damage}")
            if spell.radius:
                stats.append(f"Radius {spell.radius}")
            if spell.cooldown:
                stats.append(f"CD {spell.cooldown}")
            theme.draw_text(surface, "  ".join(stats), (r.centerx, r.bottom - 60),
                            size=14, color=theme.TEXT_DIM, center=True)
            theme.draw_text(surface, "Click to choose", (r.centerx, r.bottom - 30),
                            size=15, color=theme.GOLD if hovered else theme.TEXT_MUTED, center=True)

    def _draw_puzzle(self, surface) -> None:
        assert self.session is not None and self.board_view is not None
        self.board_view.draw(surface)
        puzzle = self.session.puzzle
        spell = SPELL_LIBRARY[self.chosen] if self.chosen else None

        panel = pygame.Rect(24, 96, 300, 420)
        theme.draw_panel(surface, panel, fill=theme.BG_PANEL, border=theme.GOLD_DARK, radius=12)
        theme.draw_text(surface, "Trial of the Mind", (panel.x + 20, panel.y + 18), size=24,
                        color=theme.GOLD_BRIGHT, bold=True)
        if spell:
            theme.draw_text(surface, f"Learning: {spell.name}", (panel.x + 20, panel.y + 52),
                            size=16, color=theme.GOLD)
        theme.draw_text(surface, puzzle.name, (panel.x + 20, panel.y + 84), size=18,
                        color=theme.TEXT, bold=True)
        theme.draw_text(surface, puzzle.briefing, (panel.x + 20, panel.y + 116), size=15,
                        color=theme.TEXT, wrap_width=panel.width - 40)
        theme.draw_text(surface, "Find the winning line.", (panel.x + 20, panel.y + 220),
                        size=15, color=theme.TEXT_DIM)
        theme.draw_text(surface, f"Mistakes: {self.session.mistakes}",
                        (panel.x + 20, panel.y + 250), size=15, color=theme.RED)
        if self._first_try:
            theme.draw_text(surface, "First try: tactic will be remembered!",
                            (panel.x + 20, panel.y + 280), size=14, color=theme.GREEN,
                            wrap_width=panel.width - 40)

    def _draw_result(self, surface) -> None:
        overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))
        card = pygame.Rect(0, 0, 560, 300)
        card.center = (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2)
        theme.draw_panel(surface, card, fill=theme.BG_PANEL, border=theme.GOLD, radius=16, border_width=3)
        spell = SPELL_LIBRARY[self.chosen] if self.chosen else None
        theme.draw_text(surface, "SPELL LEARNED", (card.centerx, card.y + 50), size=40,
                        color=theme.GOLD_BRIGHT, bold=True, center=True)
        if spell:
            theme.draw_text(surface, spell.name, (card.centerx, card.y + 100), size=26,
                            color=theme.TEXT, center=True)
            theme.draw_text(surface, spell.description, (card.centerx, card.y + 140), size=16,
                            color=theme.TEXT_DIM, center=True, wrap_width=card.width - 80)
        if self._first_try:
            theme.draw_text(surface, "Tactic mastered - remembered for future runs.",
                            (card.centerx, card.y + 210), size=16, color=theme.GREEN, center=True)
        theme.draw_text(surface, "Click to return to the field", (card.centerx, card.bottom - 40),
                        size=17, color=theme.GOLD, center=True)

    def _draw_toast(self, surface) -> None:
        if self._toast is None:
            return
        text, color, t = self._toast
        alpha = min(1.0, t * 2)
        f = theme.font(22, True)
        img = f.render(text, True, color)
        rect = img.get_rect(center=(config.WINDOW_WIDTH // 2, 70))
        box = rect.inflate(28, 14)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*theme.BG_PANEL_DARK, int(230 * alpha)), panel.get_rect(), border_radius=8)
        pygame.draw.rect(panel, (*color, int(255 * alpha)), panel.get_rect(), width=2, border_radius=8)
        surface.blit(panel, box.topleft)
        img.set_alpha(int(255 * alpha))
        surface.blit(img, rect)
