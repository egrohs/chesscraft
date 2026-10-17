"""Hero scene: character sheet, learned tactics and roguelike progress."""

from __future__ import annotations

import pygame

from .. import config, theme
from ..combat import SPELL_LIBRARY
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
        self.widgets.append(Label((40, 30), "Hero & Tactics", size=40,
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

        # Tactics panel
        panel = pygame.Rect(500, 110, config.WINDOW_WIDTH - 540, 560)
        theme.draw_panel(surface, panel, fill=theme.BG_PANEL, border=theme.GOLD_DARK, radius=14)
        theme.draw_text(surface, "Mastered Tactics", (panel.x + 30, panel.y + 24), size=26,
                        color=theme.GOLD, bold=True)

        theme.draw_text(surface, f"Runs: {hero.runs}    Best depth: {hero.best_depth}",
                        (panel.right - 30, panel.y + 30), size=16,
                        color=theme.TEXT_DIM, right=True)

        theme.draw_text(surface, "Spells whose chess trial you solved on the first "
                                 "try. These can be learned without the test.",
                        (panel.x + 30, panel.y + 64), size=15, color=theme.TEXT_DIM,
                        wrap_width=panel.width - 60)

        y = panel.y + 120
        if not hero.learned_tactics:
            theme.draw_text(surface, "None yet - reach a sanctuary and solve its "
                                     "puzzle first try.", (panel.x + 30, y),
                            size=17, color=theme.TEXT_MUTED)
        for sid in hero.learned_tactics:
            spell = SPELL_LIBRARY.get(sid)
            if spell is None:
                continue
            theme.draw_text(surface, f"[x]  {spell.name}", (panel.x + 30, y),
                            size=18, color=theme.GREEN)
            theme.draw_text(surface, spell.kind.value, (panel.right - 30, y), size=15,
                            color=theme.TEXT_DIM, right=True)
            y += 34

        super().draw(surface)
        surface.blit(theme.vignette((config.WINDOW_WIDTH, config.WINDOW_HEIGHT)), (0, 0))
