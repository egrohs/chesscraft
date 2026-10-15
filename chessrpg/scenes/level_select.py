"""Level select: a chapter map of puzzle nodes with lock / star states."""

from __future__ import annotations

import math

import pygame

from .. import config, theme
from ..puzzles import chapters, puzzles_in_chapter
from ..scene import Scene
from ..ui import Button, IconButton, Label


class LevelSelectScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self._t = 0.0
        self._bg = theme.vertical_gradient(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
            (24, 28, 44), (10, 11, 18),
        )
        self.chapter_index = 0
        self._nodes: list[tuple[pygame.Rect, str]] = []
        self._build()

    # ------------------------------------------------------------------
    def _build(self) -> None:
        self.widgets.clear()
        w = config.WINDOW_WIDTH
        self.widgets.append(Label((40, 30), "Campaign Map", size=40,
                                  color=theme.GOLD_BRIGHT, bold=True))
        self.widgets.append(Label((40, 78), "Choose a trial to begin",
                                  size=18, color=theme.TEXT_DIM))

        self.widgets.append(IconButton((w - 200, 34, 48, 48), "<",
                                       self._prev_chapter, accent=theme.GOLD,
                                       tooltip="Previous chapter"))
        self.widgets.append(IconButton((w - 140, 34, 48, 48), ">",
                                       self._next_chapter, accent=theme.GOLD,
                                       tooltip="Next chapter"))
        self.widgets.append(Button((w - 320, 34, 100, 48), "Back",
                                   self._on_back, size=20, accent=theme.RED))

    def _prev_chapter(self) -> None:
        self.chapter_index = (self.chapter_index - 1) % len(chapters())

    def _next_chapter(self) -> None:
        self.chapter_index = (self.chapter_index + 1) % len(chapters())

    def _on_back(self) -> None:
        self.game.scenes_mgr.switch("menu")

    # ------------------------------------------------------------------
    def _node_layout(self, count: int) -> list[tuple[int, int]]:
        """Lay puzzle nodes along a gentle serpentine path."""
        positions = []
        start_x = 200
        gap = 190
        for i in range(count):
            x = start_x + i * gap
            y = 380 + int(math.sin(i * 1.1) * 70)
            positions.append((x, y))
        return positions

    def update(self, dt: float) -> None:
        self._t += dt
        super().update(dt)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for rect, pid in self._nodes:
                if rect.collidepoint(event.pos):
                    if self._is_unlocked(pid):
                        self.game.scenes_mgr.switch("puzzle", puzzle_id=pid)
                    return
        super().handle_event(event)

    def _is_unlocked(self, pid: str) -> bool:
        return pid in self.game.profile.hero.unlocked

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._bg, (0, 0))

        chapter = chapters()[self.chapter_index]
        theme.draw_text(surface, chapter, (config.WINDOW_WIDTH // 2, 130),
                        size=30, color=theme.GOLD, bold=True, center=True)

        puzzles = puzzles_in_chapter(chapter)
        positions = self._node_layout(len(puzzles))
        self._nodes = []

        # Path line between nodes
        for i in range(len(positions) - 1):
            pygame.draw.line(surface, theme.GOLD_DARK, positions[i], positions[i + 1], 4)

        mouse = pygame.mouse.get_pos()
        for i, puzzle in enumerate(puzzles):
            cx, cy = positions[i]
            unlocked = self._is_unlocked(puzzle.id)
            solved = puzzle.id in self.game.profile.hero.solved
            hovered = math.dist(mouse, (cx, cy)) < 46

            radius = 44 if hovered else 40
            if solved:
                fill, border = theme.GREEN_DARK, theme.GREEN
            elif unlocked:
                fill, border = theme.BG_PANEL_LIGHT, theme.GOLD
            else:
                fill, border = theme.BG_PANEL_DARK, theme.TEXT_MUTED

            # Pulsing halo for the next available puzzle
            if unlocked and not solved:
                pulse = 6 + int(4 * math.sin(self._t * 3 + i))
                halo = pygame.Surface((radius * 2 + 40, radius * 2 + 40), pygame.SRCALPHA)
                pygame.draw.circle(halo, (*theme.GOLD, 60),
                                   (radius + 20, radius + 20), radius + pulse + 8)
                surface.blit(halo, (cx - radius - 20, cy - radius - 20))

            pygame.draw.circle(surface, fill, (cx, cy), radius)
            pygame.draw.circle(surface, border, (cx, cy), radius, 3)

            if unlocked:
                theme.draw_text(surface, str(i + 1), (cx, cy - 6), size=30,
                                color=theme.PARCHMENT, bold=True, center=True)
                theme.draw_text(surface, puzzle.stars, (cx, cy + 20), size=14,
                                color=theme.GOLD, center=True)
            else:
                theme.draw_text(surface, "?", (cx, cy), size=30,
                                color=theme.TEXT_MUTED, bold=True, center=True)

            theme.draw_text(surface, puzzle.name, (cx, cy + 62), size=16,
                            color=theme.TEXT if unlocked else theme.TEXT_MUTED,
                            center=True)

            self._nodes.append((pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2),
                                puzzle.id))

        # Hovered puzzle detail card
        for rect, pid in self._nodes:
            if rect.collidepoint(mouse):
                self._draw_detail(surface, pid)
                break

        super().draw(surface)
        surface.blit(theme.vignette((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)), (0, 0))

    def _draw_detail(self, surface: pygame.Surface, pid: str) -> None:
        from ..puzzles import get_puzzle
        puzzle = get_puzzle(pid)
        if puzzle is None:
            return
        card = pygame.Rect(40, config.WINDOW_HEIGHT - 190, config.WINDOW_WIDTH - 80, 150)
        theme.draw_panel(surface, card, fill=theme.BG_PANEL, border=theme.GOLD_DARK, radius=12)
        theme.draw_text(surface, puzzle.name, (card.x + 24, card.y + 18), size=26,
                        color=theme.GOLD_BRIGHT, bold=True)
        theme.draw_text(surface, f"Difficulty {puzzle.stars}   Goal: {puzzle.goal}",
                        (card.x + 24, card.y + 52), size=16, color=theme.TEXT_DIM)
        theme.draw_text(surface, f"Reward: {puzzle.xp} XP, {puzzle.gold} gold",
                        (card.x + 24, card.y + 76), size=16, color=theme.GREEN)
        theme.draw_text(surface, puzzle.briefing, (card.x + 24, card.y + 104),
                        size=16, color=theme.TEXT, wrap_width=card.width - 48)
