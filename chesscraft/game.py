"""Application entry point: window, main loop and scene wiring."""

from __future__ import annotations

import sys

import pygame

from . import config, theme
from .assets import ASSETS
from .rpg import Profile
from .scene import SceneManager
from .scenes import CombatScene, HeroScene, MenuScene, SanctuaryScene
from .scenes.help_scene import HelpScene


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        self.screen = pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SCALED | pygame.DOUBLEBUF
        )
        self.clock = pygame.time.Clock()
        self.running = True

        self.assets = ASSETS
        self.profile = Profile()
        self.profile.load()

        self.scenes: dict = {}
        self.scenes_mgr = SceneManager(self)
        self._register_scenes()
        self.scenes_mgr.switch("menu")

    def _register_scenes(self) -> None:
        self.scenes_mgr.register("menu", MenuScene(self))
        self.scenes_mgr.register("combat", CombatScene(self))
        self.scenes_mgr.register("sanctuary", SanctuaryScene(self))
        self.scenes_mgr.register("hero", HeroScene(self))
        self.scenes_mgr.register("help", HelpScene(self))

    # ------------------------------------------------------------------
    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0
            dt = min(dt, 0.05)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._on_escape()
                else:
                    self.scenes_mgr.handle_event(event)

            self.scenes_mgr.update(dt)
            self.screen.fill(theme.BG_DEEP)
            self.scenes_mgr.draw(self.screen)
            pygame.display.flip()

        self.profile.save()
        pygame.quit()

    def _on_escape(self) -> None:
        current = self.scenes_mgr.scene
        if isinstance(current, MenuScene):
            self.running = False
        else:
            self.scenes_mgr.switch("menu")


def main() -> int:
    game = Game()
    game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
