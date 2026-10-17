"""Reusable UI widgets: buttons, panels, labels, bars and tooltips.

Widgets are immediate-mode-ish: they own a rect, are updated with the
current mouse state and draw themselves. Scenes keep a list of widgets
and forward events to them.
"""

from __future__ import annotations

from typing import Callable, Optional

import pygame

from . import theme


class Widget:
    """Base widget."""

    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)
        self.visible = True
        self.enabled = True
        self.hovered = False
        self.tooltip: Optional[str] = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Return True if the event was consumed."""
        return False

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        self.hovered = self.visible and self.enabled and self.rect.collidepoint(mouse_pos)

    def draw(self, surface: pygame.Surface) -> None:
        pass


class Button(Widget):
    """A themed push button with hover / pressed / disabled states."""

    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        on_click: Optional[Callable[[], None]] = None,
        *,
        size: int = 22,
        accent=theme.GOLD,
        icon: Optional[str] = None,
        subtitle: Optional[str] = None,
    ) -> None:
        super().__init__(rect)
        self.text = text
        self.subtitle = subtitle
        self.on_click = on_click
        self.font_size = size
        self.accent = accent
        self.icon = icon
        self.pressed = False
        self._pulse = 0.0

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not (self.visible and self.enabled):
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
                return True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was = self.pressed
            self.pressed = False
            if was and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        super().update(dt, mouse_pos)
        target = 1.0 if self.hovered else 0.0
        self._pulse += (target - self._pulse) * min(1.0, dt * 12)

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        rect = self.rect
        if not self.enabled:
            fill, border, text_col = theme.BG_PANEL_DARK, theme.TEXT_MUTED, theme.TEXT_MUTED
        else:
            lift = int(4 * self._pulse)
            rect = rect.move(0, -lift)
            if self.pressed:
                fill = theme.BG_PANEL_DARK
            elif self.hovered:
                fill = theme.BG_PANEL_LIGHT
            else:
                fill = theme.BG_PANEL
            border = self.accent if self.hovered else theme.GOLD_DARK
            text_col = theme.GOLD_BRIGHT if self.hovered else theme.TEXT

        theme.draw_panel(surface, rect, fill=fill, border=border, radius=10)

        if self.icon:
            theme.draw_text(surface, self.icon, (rect.x + 18, rect.centery),
                            size=self.font_size, color=border, center=False)
            text_x = rect.x + 46
        else:
            text_x = rect.centerx

        if self.subtitle:
            theme.draw_text(surface, self.text, (text_x, rect.centery - 11),
                            size=self.font_size, color=text_col, bold=True,
                            center=not self.icon)
            theme.draw_text(surface, self.subtitle, (text_x, rect.centery + 12),
                            size=max(12, self.font_size - 8), color=theme.TEXT_DIM,
                            center=not self.icon)
        else:
            theme.draw_text(surface, self.text, (text_x, rect.centery),
                            size=self.font_size, color=text_col, bold=True,
                            center=not self.icon)


class IconButton(Widget):
    """Small square button used for HUD actions."""

    def __init__(self, rect, glyph: str, on_click=None, *, accent=theme.GOLD, tooltip=None):
        super().__init__(rect)
        self.glyph = glyph
        self.on_click = on_click
        self.accent = accent
        self.tooltip = tooltip
        self.pressed = False

    def handle_event(self, event):
        if not (self.visible and self.enabled):
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.pressed = True
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was = self.pressed
            self.pressed = False
            if was and self.rect.collidepoint(event.pos):
                if self.on_click:
                    self.on_click()
                return True
        return False

    def draw(self, surface):
        if not self.visible:
            return
        fill = theme.BG_PANEL_LIGHT if self.hovered else theme.BG_PANEL
        border = self.accent if self.hovered else theme.GOLD_DARK
        theme.draw_panel(surface, self.rect, fill=fill, border=border, radius=8, shadow=False)
        theme.draw_text(surface, self.glyph, self.rect.center, size=22,
                        color=border, center=True)


class Label(Widget):
    """Static text block, optionally multi-line."""

    def __init__(self, pos, text, *, size=20, color=theme.TEXT, bold=False,
                 center=False, right=False, wrap_width=None, line_spacing=4):
        super().__init__(pygame.Rect(pos[0], pos[1], 0, 0))
        self.pos = pos
        self.text = text
        self.size = size
        self.color = color
        self.bold = bold
        self.center = center
        self.right = right
        self.wrap_width = wrap_width
        self.line_spacing = line_spacing

    def _lines(self) -> list[str]:
        if not self.wrap_width:
            return self.text.split("\n")
        f = theme.font(self.size, self.bold)
        return theme._wrap_lines(f, self.text, self.wrap_width)

    def draw(self, surface):
        if not self.visible:
            return
        f = theme.font(self.size, self.bold)
        lines = self._lines()
        lh = f.get_height() + self.line_spacing
        y = self.pos[1]
        for line in lines:
            img = f.render(line, True, self.color)
            rect = img.get_rect()
            if self.center:
                rect.midtop = (self.pos[0], y)
            elif self.right:
                rect.topright = self.pos[0], y
            else:
                rect.topleft = (self.pos[0], y)
            surface.blit(img, rect)
            y += lh


class StatBar(Widget):
    """Labelled progress bar (HP, XP, timer...)."""

    def __init__(self, rect, *, label="", color=theme.GREEN, back=theme.BG_PANEL_DARK,
                 show_value=True, size=15):
        super().__init__(rect)
        self.label = label
        self.color = color
        self.back = back
        self.show_value = show_value
        self.size = size
        self.ratio = 1.0
        self.value_text = ""

    def draw(self, surface):
        if not self.visible:
            return
        r = self.rect
        if self.label:
            theme.draw_text(surface, self.label, (r.x, r.y - 18), size=self.size,
                            color=theme.TEXT_DIM, bold=True)
        theme.draw_bar(surface, r, self.ratio, fill=self.color, back=self.back)
        if self.show_value and self.value_text:
            theme.draw_text(surface, self.value_text, r.center, size=self.size,
                            color=theme.PARCHMENT, bold=True, center=True)


class Tooltip:
    """Draws a floating tooltip for the hovered widget."""

    @staticmethod
    def draw(surface, widgets, mouse_pos):
        for w in widgets:
            if w.visible and w.enabled and w.tooltip and w.rect.collidepoint(mouse_pos):
                f = theme.font(15)
                img = f.render(w.tooltip, True, theme.PARCHMENT)
                pad = 8
                rect = pygame.Rect(0, 0, img.get_width() + pad * 2, img.get_height() + pad)
                rect.midbottom = (w.rect.centerx, w.rect.top - 6)
                rect.clamp_ip(surface.get_rect())
                theme.draw_panel(surface, rect, fill=theme.BG_PANEL_DARK,
                                 border=theme.GOLD_DARK, radius=6, shadow=True)
                surface.blit(img, (rect.x + pad, rect.y + pad // 2))
                break
