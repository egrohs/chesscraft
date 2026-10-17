"""Help / how-to-play scene."""

from __future__ import annotations

import pygame

from .. import config, theme
from ..scene import Scene
from ..ui import Button, Label

LINES = [
    ("Objective", "You are a mage crossing a battlefield. Slay the enemy king "
                  "at the far side by finding a clear line of fire."),
    ("Turns", "Each turn you take one action - move one cell or cast a spell - "
              "then every enemy acts. Press Space to end your turn."),
    ("Enemies", "They move like chess pieces: pawns march forward, rooks sweep "
                "ranks and files, bishops hold diagonals, knights leap in an L. "
                "Red cells show where they can strike."),
    ("Spells", "Press 1-9 or click a spell to ready it, then click a target. "
               "Bolt flies straight, Blink teleports, Blast hits an area, "
               "Aegis shields you. Each has range, cooldown and rules."),
    ("Sanctuary", "Step on a glowing shrine to learn a new spell. Pick one of "
                  "three, then solve its chess puzzle to master it."),
    ("Roguelike", "Each descent is a fresh, harder battlefield. Death ends the "
                  "run - but tactics you solve on the first try are remembered "
                  "and can be learned without the trial next time."),
]


class HelpScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self._bg = theme.vertical_gradient(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
            (26, 30, 46), (10, 11, 18),
        )
        self.widgets.append(Label((40, 30), "How to Play", size=40,
                                  color=theme.GOLD_BRIGHT, bold=True))
        self.widgets.append(Button((config.WINDOW_WIDTH - 180, 34, 140, 48), "Back",
                                   self._on_back, size=20, accent=theme.RED))

    def _on_back(self) -> None:
        self.game.scenes_mgr.switch("menu")

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._bg, (0, 0))
        panel = pygame.Rect(40, 100, config.WINDOW_WIDTH - 80, config.WINDOW_HEIGHT - 140)
        theme.draw_panel(surface, panel, fill=theme.BG_PANEL, border=theme.GOLD_DARK, radius=14)

        y = panel.y + 24
        for title, body in LINES:
            theme.draw_text(surface, title, (panel.x + 40, y), size=22,
                            color=theme.GOLD, bold=True)
            rect = theme.draw_text(surface, body, (panel.x + 40, y + 30), size=17,
                                   color=theme.TEXT, wrap_width=panel.width - 80)
            y = rect.bottom + 18

        super().draw(surface)
        surface.blit(theme.vignette((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)), (0, 0))
