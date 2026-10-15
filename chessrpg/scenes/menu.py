"""Main menu scene: title, hero card and navigation."""

from __future__ import annotations

import math

import pygame

from .. import config, theme
from ..assets import ASSETS
from ..scene import Scene
from ..ui import Button, Label


class MenuScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self._t = 0.0
        self._bg = theme.vertical_gradient(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
            (26, 30, 46), (10, 11, 18),
        )
        self._build()

    def _build(self) -> None:
        self.widgets.clear()
        w, h = config.WINDOW_WIDTH, config.WINDOW_HEIGHT
        cx = w // 2

        self.widgets.append(Label((cx, 96), "CHESS RPG", size=76,
                                  color=theme.GOLD_BRIGHT, bold=True, center=True))
        self.widgets.append(Label((cx, 152), "T A C T I C A L   T R I A L S",
                                  size=22, color=theme.TEXT_DIM, center=True))

        bw, bh = 300, 58
        x = cx - bw // 2
        self.widgets.append(Button((x, 300, bw, bh), "Continue Campaign",
                                   self._on_play, size=24, accent=theme.GOLD))
        self.widgets.append(Button((x, 372, bw, bh), "Hero & Progress",
                                   self._on_hero, size=22, accent=theme.BLUE))
        self.widgets.append(Button((x, 444, bw, bh), "How to Play",
                                   self._on_help, size=22, accent=theme.PURPLE))
        self.widgets.append(Button((x, 516, bw, bh), "Quit",
                                   self._on_quit, size=22, accent=theme.RED))

        self.widgets.append(Label((cx, h - 40),
                                  "A tactical puzzle RPG  -  built with pygame-ce",
                                  size=15, color=theme.TEXT_MUTED, center=True))

    # ------------------------------------------------------------------
    def _on_play(self) -> None:
        self.game.scenes_mgr.switch("level_select")

    def _on_hero(self) -> None:
        self.game.scenes_mgr.switch("hero")

    def _on_help(self) -> None:
        self.game.scenes_mgr.switch("help")

    def _on_quit(self) -> None:
        self.game.running = False

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self._t += dt
        super().update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._bg, (0, 0))

        # Decorative hero portrait on the left, enemy on the right
        hero = ASSETS.portrait("healer-king", 420)
        surface.blit(hero, (60, config.WINDOW_HEIGHT - 420 - 40))
        enemy = ASSETS.portrait("sorcerer-queen", 420)
        surface.blit(enemy, (config.WINDOW_WIDTH - enemy.get_width() - 60,
                             config.WINDOW_HEIGHT - 420 - 40))

        # Soft glow behind the title
        glow = pygame.Surface((520, 200), pygame.SRCALPHA)
        pulse = 40 + int(20 * math.sin(self._t * 2))
        pygame.draw.ellipse(glow, (*theme.GOLD, pulse), glow.get_rect())
        surface.blit(glow, (config.WINDOW_WIDTH // 2 - 260, 40))

        super().draw(surface)
        surface.blit(theme.vignette((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)), (0, 0))
