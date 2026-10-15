"""Help / how-to-play scene."""

from __future__ import annotations

import pygame

from .. import config, theme
from ..scene import Scene
from ..ui import Button, Label

LINES = [
    ("Objective", "Each trial is a tactical puzzle. You play the side to move "
                  "and must find the winning line."),
    ("Moving", "Click a piece to see its legal moves, then click a highlighted "
               "square. You can also drag and drop."),
    ("Feedback", "A wrong move flashes red and costs you reward. Correct moves "
                 "advance the scripted line."),
    ("Hints", "Stuck? Spend gold on a hint to highlight the next correct move."),
    ("Progression", "Solving trials earns XP and gold. Levelling up raises your "
                    "stats and unlocks the next chapter."),
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
        panel = pygame.Rect(40, 110, config.WINDOW_WIDTH - 80, config.WINDOW_HEIGHT - 160)
        theme.draw_panel(surface, panel, fill=theme.BG_PANEL, border=theme.GOLD_DARK, radius=14)

        y = panel.y + 30
        for title, body in LINES:
            theme.draw_text(surface, title, (panel.x + 40, y), size=24,
                            color=theme.GOLD, bold=True)
            theme.draw_text(surface, body, (panel.x + 40, y + 32), size=18,
                            color=theme.TEXT, wrap_width=panel.width - 80)
            y += 96

        super().draw(surface)
        surface.blit(theme.vignette((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)), (0, 0))
