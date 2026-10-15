"""Scene base class and scene manager with fade transitions."""

from __future__ import annotations

from typing import Optional

import pygame


class Scene:
    """Base class for all screens."""

    def __init__(self, game) -> None:
        self.game = game
        self.widgets: list = []

    def on_enter(self, **kwargs) -> None:
        """Called when the scene becomes active."""

    def on_exit(self) -> None:
        """Called when the scene is replaced."""

    def handle_event(self, event: pygame.event.Event) -> None:
        for w in self.widgets:
            if w.handle_event(event):
                return

    def update(self, dt: float) -> None:
        mouse = pygame.mouse.get_pos()
        for w in self.widgets:
            w.update(dt, mouse)

    def draw(self, surface: pygame.Surface) -> None:
        for w in self.widgets:
            w.draw(surface)

    def draw_tooltips(self, surface: pygame.Surface) -> None:
        from .ui import Tooltip
        Tooltip.draw(surface, self.widgets, pygame.mouse.get_pos())


class SceneManager:
    """Holds the active scene and performs fade transitions."""

    def __init__(self, game) -> None:
        self.game = game
        self.scene: Optional[Scene] = None
        self._next: Optional[tuple[str, dict]] = None
        self._fade = 0.0          # 0 = clear, 1 = fully black
        self._fade_dir = 0        # -1 fading in, +1 fading out

    def register(self, name: str, scene: Scene) -> None:
        self.game.scenes[name] = scene

    def switch(self, name: str, **kwargs) -> None:
        """Begin a fade-out then swap to ``name``."""
        self._next = (name, kwargs)
        self._fade_dir = 1

    def _do_switch(self) -> None:
        assert self._next is not None
        name, kwargs = self._next
        self._next = None
        if self.scene is not None:
            self.scene.on_exit()
        self.scene = self.game.scenes[name]
        self.scene.on_enter(**kwargs)
        self._fade_dir = -1

    def update(self, dt: float) -> None:
        if self._fade_dir > 0:
            self._fade = min(1.0, self._fade + dt * 4.5)
            if self._fade >= 1.0:
                self._do_switch()
        elif self._fade_dir < 0:
            self._fade = max(0.0, self._fade - dt * 4.5)
            if self._fade <= 0.0:
                self._fade_dir = 0

        if self.scene is not None and self._fade_dir <= 0:
            self.scene.update(dt)

    def handle_event(self, event: pygame.event.Event) -> None:
        if self.scene is not None and self._fade_dir <= 0:
            self.scene.handle_event(event)

    def draw(self, surface: pygame.Surface) -> None:
        if self.scene is not None:
            self.scene.draw(surface)
            self.scene.draw_tooltips(surface)
        if self._fade > 0.001:
            overlay = pygame.Surface(surface.get_size())
            overlay.fill((0, 0, 0))
            overlay.set_alpha(int(255 * self._fade))
            surface.blit(overlay, (0, 0))
