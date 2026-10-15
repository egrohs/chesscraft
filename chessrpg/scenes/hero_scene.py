"""Hero scene: character sheet, stats and campaign progress."""

from __future__ import annotations

import pygame

from .. import config, theme
from ..puzzles import PUZZLES
from ..scene import Scene
from ..ui import Button, Label


class HeroScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self._bg = theme.vertical_gradient(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
            (26, 30, 46), (10, 11, 18),
        )
        self._build()

    def _build(self) -> None:
        self.widgets.clear()
        self.widgets.append(Label((40, 30), "Hero & Progress", size=40,
                                  color=theme.GOLD_BRIGHT, bold=True))
        self.widgets.append(Button((config.WINDOW_WIDTH - 180, 34, 140, 48), "Back",
                                   self._on_back, size=20, accent=theme.RED))
        self.widgets.append(Button((config.WINDOW_WIDTH - 340, 34, 140, 48), "Reset Save",
                                   self._on_reset, size=18, accent=theme.PURPLE))

    def _on_back(self) -> None:
        self.game.scenes_mgr.switch("menu")

    def _on_reset(self) -> None:
        self.game.profile.reset()

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._bg, (0, 0))
        hero = self.game.profile.hero

        # Character card
        card = pygame.Rect(40, 110, 420, 560)
        theme.draw_panel(surface, card, fill=theme.BG_PANEL, border=theme.GOLD_DARK, radius=14)

        portrait = self.game.assets.portrait("healer-king", 300)
        px = card.centerx - portrait.get_width() // 2
        surface.blit(portrait, (px, card.y + 20))

        theme.draw_text(surface, hero.name, (card.centerx, card.y + 340), size=34,
                        color=theme.GOLD_BRIGHT, bold=True, center=True)
        theme.draw_text(surface, hero.title, (card.centerx, card.y + 376), size=17,
                        color=theme.TEXT_DIM, center=True)

        theme.draw_text(surface, f"Level {hero.level}", (card.x + 30, card.y + 416),
                        size=22, color=theme.TEXT, bold=True)
        theme.draw_text(surface, f"{hero.xp} / {hero.xp_to_next} XP",
                        (card.right - 30, card.y + 420), size=16,
                        color=theme.TEXT_DIM, right=True)
        theme.draw_bar(surface, pygame.Rect(card.x + 30, card.y + 448, card.width - 60, 18),
                       hero.xp_ratio, fill=theme.GOLD)

        stats = [
            ("Tactics", hero.tactics, theme.RED),
            ("Focus", hero.focus, theme.BLUE),
            ("Resolve", hero.resolve, theme.GREEN),
        ]
        y = card.y + 490
        for name, value, color in stats:
            theme.draw_text(surface, name, (card.x + 30, y), size=18, color=theme.TEXT)
            theme.draw_text(surface, str(value), (card.right - 30, y), size=18,
                            color=color, bold=True, right=True)
            theme.draw_bar(surface, pygame.Rect(card.x + 30, y + 24, card.width - 60, 10),
                           min(1.0, value / 20), fill=color)
            y += 52

        # Progress panel
        panel = pygame.Rect(500, 110, config.WINDOW_WIDTH - 540, 560)
        theme.draw_panel(surface, panel, fill=theme.BG_PANEL, border=theme.GOLD_DARK, radius=14)
        theme.draw_text(surface, "Campaign Progress", (panel.x + 30, panel.y + 24), size=26,
                        color=theme.GOLD, bold=True)

        solved = len(hero.solved)
        total = len(PUZZLES)
        theme.draw_text(surface, f"{solved} / {total} trials solved",
                        (panel.right - 30, panel.y + 30), size=18,
                        color=theme.TEXT_DIM, right=True)
        theme.draw_bar(surface, pygame.Rect(panel.x + 30, panel.y + 64, panel.width - 60, 16),
                       solved / max(1, total), fill=theme.GREEN)

        y = panel.y + 110
        for puzzle in PUZZLES:
            done = puzzle.id in hero.solved
            unlocked = puzzle.id in hero.unlocked
            color = theme.GREEN if done else (theme.TEXT if unlocked else theme.TEXT_MUTED)
            mark = "[x]" if done else ("[ ]" if unlocked else "[ ]")
            theme.draw_text(surface, f"{mark}  {puzzle.name}", (panel.x + 30, y),
                            size=18, color=color)
            theme.draw_text(surface, puzzle.stars, (panel.right - 30, y), size=16,
                            color=theme.GOLD if unlocked else theme.TEXT_MUTED, right=True)
            y += 34

        super().draw(surface)
        surface.blit(theme.vignette((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)), (0, 0))
