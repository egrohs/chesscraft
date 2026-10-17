"""Combat scene: the tactical battlefield, HUD, spell bar and turn flow.

The scene renders the grid, the mage, chess-inspired enemies and the enemy
king, and translates clicks into movement or spell casts. It shows reachable
cells, valid spell targets and the cells threatened by enemies so the player
can plan like a chess puzzle.
"""

from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from .. import config, theme
from ..assets import ASSETS
from ..combat import (
    BLOCKING_TILES,
    Battlefield,
    CastResult,
    Enemy,
    EnemyKind,
    Outcome,
    SPELL_LIBRARY,
    Spell,
    SpellKind,
    Tile,
    cast_spell,
    chebyshev,
    end_player_turn,
    enemy_threat_cells,
    threatened_cells,
)
from ..run import Run
from ..scene import Scene
from ..ui import Button, IconButton

# --------------------------------------------------------------------------
# Palette for the battlefield
# --------------------------------------------------------------------------
FLOOR_A = (46, 50, 66)
FLOOR_B = (38, 42, 56)
WALL_COL = (92, 98, 122)
WALL_EDGE = (150, 160, 190)
PILLAR_COL = (108, 100, 138)
PILLAR_EDGE = (168, 158, 200)
RUBBLE_COL = (120, 104, 82)
RUBBLE_EDGE = (176, 152, 116)
SANCTUARY_COL = (86, 132, 150)
STAIRS_COL = (120, 104, 70)

REACHABLE = (96, 168, 120)
THREAT = (196, 74, 70)
TARGET = (232, 196, 108)
PATH = (150, 190, 255)

MAGE_COL = (120, 176, 232)
MAGE_CORE = (232, 240, 255)
KING_COL = (214, 96, 96)

ENEMY_COLORS = {
    EnemyKind.PAWN: (150, 158, 172),
    EnemyKind.ROOK: (176, 150, 110),
    EnemyKind.BISHOP: (150, 120, 200),
    EnemyKind.KNIGHT: (196, 148, 108),
    EnemyKind.KING: KING_COL,
}

# Map each enemy to the chess piece it is drawn as.
ENEMY_PIECES = {
    EnemyKind.PAWN: "pawn",
    EnemyKind.ROOK: "rook",
    EnemyKind.BISHOP: "bishop",
    EnemyKind.KNIGHT: "knight",
    EnemyKind.KING: "king",
}


class CombatScene(Scene):
    def __init__(self, game) -> None:
        super().__init__(game)
        self._bg = theme.vertical_gradient(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT),
            (20, 24, 38), (8, 9, 15),
        )
        self.run: Optional[Run] = None
        self.bf: Optional[Battlefield] = None
        self.cell = 56
        self.origin = (0, 0)
        self._t = 0.0

        # Interaction state
        self.mode = "move"                 # "move" or a spell id
        self.selected_spell: Optional[str] = None
        self.hover: Optional[tuple[int, int]] = None
        self.reachable: set = set()
        self.targets: set = set()
        self.threats: set = set()
        self.preview_path: list = []

        # Feedback
        self._toast: Optional[tuple[str, tuple, float]] = None
        self._flash: dict = {}             # cell -> (color, ttl)
        self._shake = 0.0
        self._busy = 0.0                   # enemy-phase animation lock
        self._pending_enemy_phase = False
        self._outcome: Optional[Outcome] = None
        self._outcome_t = 0.0
        self._log: list[str] = []

        self._build_widgets()

    # ------------------------------------------------------------------
    def _build_widgets(self) -> None:
        self.widgets.clear()
        w = config.WINDOW_WIDTH
        self.widgets.append(IconButton((24, 24, 48, 48), "<", self._on_abandon,
                                       accent=theme.RED, tooltip="Abandon run"))
        self.widgets.append(Button((w - 210, 24, 186, 46), "End Turn",
                                   self._on_end_turn, size=20, accent=theme.GOLD,
                                   subtitle="Space"))

    # ------------------------------------------------------------------
    def on_enter(self, run: Optional[Run] = None, **kwargs) -> None:
        if run is not None:
            self.run = run
        if self.run is None or self.run.level is None:
            self.game.scenes_mgr.switch("menu")
            return
        self.bf = self.run.level.battlefield
        self._layout()
        self._outcome = None
        self._outcome_t = 0.0
        self._busy = 0.0
        self._pending_enemy_phase = False
        self._log = []
        self.mode = "move"
        self.selected_spell = None
        self._recompute()

    def _layout(self) -> None:
        assert self.bf is not None
        # Fit the grid into the play area (left of the HUD panel).
        avail_w = config.WINDOW_WIDTH - 360
        avail_h = config.WINDOW_HEIGHT - 150
        self.cell = min(avail_w // self.bf.width, avail_h // self.bf.height, 64)
        grid_w = self.cell * self.bf.width
        grid_h = self.cell * self.bf.height
        self.origin = ((avail_w - grid_w) // 2 + 20, (config.WINDOW_HEIGHT - grid_h) // 2 + 30)

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------
    def cell_rect(self, p: tuple[int, int]) -> pygame.Rect:
        return pygame.Rect(self.origin[0] + p[0] * self.cell,
                           self.origin[1] + p[1] * self.cell,
                           self.cell, self.cell)

    def cell_center(self, p: tuple[int, int]) -> tuple[int, int]:
        r = self.cell_rect(p)
        return r.center

    def pos_to_cell(self, pos: tuple[int, int]) -> Optional[tuple[int, int]]:
        assert self.bf is not None
        x = (pos[0] - self.origin[0]) // self.cell
        y = (pos[1] - self.origin[1]) // self.cell
        if 0 <= x < self.bf.width and 0 <= y < self.bf.height:
            return (int(x), int(y))
        return None

    # ------------------------------------------------------------------
    # Selection / targeting
    # ------------------------------------------------------------------
    def _recompute(self) -> None:
        assert self.bf is not None and self.bf.mage is not None
        self.threats = threatened_cells(self.bf)
        self.reachable = set()
        self.targets = set()
        self.preview_path = []

        if self.mode == "move":
            self.reachable = self.bf.reachable(self.bf.mage.pos, 1)
        else:
            spell = SPELL_LIBRARY.get(self.mode)
            if spell is not None:
                self.targets = self._valid_targets(spell)

    def _valid_targets(self, spell: Spell) -> set:
        assert self.bf is not None and self.bf.mage is not None
        origin = self.bf.mage.pos
        out: set = set()
        if spell.kind in (SpellKind.SHIELD, SpellKind.SACRIFICE, SpellKind.TEMPO):
            return {origin}
        for y in range(self.bf.height):
            for x in range(self.bf.width):
                p = (x, y)
                if self._target_ok(spell, origin, p):
                    out.add(p)
        return out

    def _target_ok(self, spell: Spell, origin, p) -> bool:
        assert self.bf is not None
        if chebyshev(origin, p) > spell.range:
            return False
        if spell.kind == SpellKind.TELEPORT:
            return self.bf.is_walkable(p) and not self.bf.occupied(p) and self.bf.has_los(origin, p)
        if spell.kind == SpellKind.BLAST:
            return self.bf.has_los(origin, p)
        if spell.kind == SpellKind.CHARM:
            e = self.bf.enemy_at(p)
            return e is not None and not e.is_king and self.bf.has_los(origin, p)
        if spell.kind in (SpellKind.BOLT, SpellKind.PIERCE):
            if not self.bf.straight_line(origin, p):
                return False
            if spell.kind == SpellKind.BOLT and not self.bf.has_los(origin, p):
                return False
            return True
        if spell.kind == SpellKind.REFLECT:
            return p != origin
        if spell.kind == SpellKind.PUSH:
            e = self.bf.enemy_at(p)
            return (e is not None and not e.is_king
                    and self.bf.straight_line(origin, p) and self.bf.has_los(origin, p))
        if spell.kind == SpellKind.BREAK:
            return self.bf.tile(p) in BLOCKING_TILES
        if spell.kind == SpellKind.CROSS:
            return True  # hits the whole rank + file; any cell is a valid aim
        if spell.kind == SpellKind.FORK:
            return self.bf.enemy_at(p) is not None and self.bf.has_los(origin, p)
        if spell.kind == SpellKind.ESCAPE:
            return False  # self-cast; the target is chosen automatically
        if spell.kind == SpellKind.FEAR:
            return False  # self-centred; no target needed
        if spell.kind == SpellKind.DISCOVER:
            return self.bf.enemy_at(p) is not None and self.bf.has_los(origin, p)
        if spell.kind == SpellKind.PIN:
            e = self.bf.enemy_at(p)
            return e is not None and not e.is_king and self.bf.has_los(origin, p)
        if spell.kind == SpellKind.MINE:
            return self.bf.is_walkable(p) and not self.bf.occupied(p)
        if spell.kind == SpellKind.SNIPER:
            return self.bf.straight_line(origin, p) and p != origin
        if spell.kind == SpellKind.WALL:
            return self.bf.is_walkable(p) and not self.bf.occupied(p)
        if spell.kind == SpellKind.CLEARANCE:
            return chebyshev(origin, p) == 1 and self.bf.tile(p) not in BLOCKING_TILES
        return False

    def _select_spell(self, spell_id: str) -> None:
        assert self.bf is not None and self.bf.mage is not None
        if not self.bf.mage.has_spell(spell_id):
            return
        if not self.bf.mage.ready(spell_id):
            self._toast_msg("Spell not ready", theme.RED)
            return
        self.mode = spell_id
        self.selected_spell = spell_id
        self._recompute()

    def _select_move(self) -> None:
        self.mode = "move"
        self.selected_spell = None
        self._recompute()

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------
    def handle_event(self, event: pygame.event.Event) -> None:
        if self._outcome is not None:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_outcome_click(event.pos)
                return
            super().handle_event(event)
            return

        if self._busy > 0:
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self._on_end_turn()
                return
            if event.key == pygame.K_TAB:
                self._select_move()
                return
            # Number keys select spells.
            if pygame.K_1 <= event.key <= pygame.K_9:
                idx = event.key - pygame.K_1
                assert self.bf is not None and self.bf.mage is not None
                if idx < len(self.bf.mage.spells):
                    self._select_spell(self.bf.mage.spells[idx])
                return

        if event.type == pygame.MOUSEMOTION:
            self.hover = self.pos_to_cell(event.pos)
            self._update_preview()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self.pos_to_cell(event.pos)
            if cell is not None:
                self._on_cell_click(cell)
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._select_move()
            return

        super().handle_event(event)

    def _update_preview(self) -> None:
        self.preview_path = []
        if self.hover is None or self.bf is None or self.bf.mage is None:
            return
        if self.mode in ("bolt", "pierce", "reflect", "sniper"):
            spell = SPELL_LIBRARY.get(self.mode)
            if spell is not None and self.hover in self.targets:
                from ..combat import _bolt_path, _reflect_path
                if spell.kind == SpellKind.REFLECT:
                    self.preview_path = _reflect_path(self.bf, self.bf.mage.pos, self.hover, spell.range)
                else:
                    pierce = spell.kind in (SpellKind.PIERCE, SpellKind.SNIPER)
                    self.preview_path = _bolt_path(self.bf, self.bf.mage.pos, self.hover,
                                                   pierce=pierce)

    def _on_cell_click(self, cell: tuple[int, int]) -> None:
        assert self.bf is not None and self.bf.mage is not None
        mage = self.bf.mage

        if self.mode == "move":
            if cell in self.reachable:
                mage.pos = cell
                # Entering a sanctuary opens the spell-learning shrine, but only
                # once per level.
                if (self.bf.tile(cell) == Tile.SANCTUARY
                        and not self.run.level.sanctuary_used):
                    self.run.level.sanctuary_used = True
                    self.game.scenes_mgr.switch("sanctuary", run=self.run)
                    return
                self._after_player_action()
            return

        spell = SPELL_LIBRARY.get(self.mode)
        if spell is None:
            return
        # Self-centred spells (Escape, Deflection) fire on any click.
        self_centred = spell.kind in (SpellKind.ESCAPE, SpellKind.FEAR)
        if not self_centred and cell not in self.targets:
            self._toast_msg("Invalid target", theme.RED)
            return
        result = cast_spell(self.bf, spell, cell)
        if not result.ok:
            self._toast_msg(result.message, theme.RED)
            return
        self._apply_cast_feedback(result)
        self._after_player_action()

    def _apply_cast_feedback(self, result: CastResult) -> None:
        for c in result.affected:
            self._flash[c] = (theme.GOLD_BRIGHT, 0.5)
        for c in result.path:
            self._flash.setdefault(c, (PATH, 0.35))
        if result.killed:
            self._shake = 0.25
        if result.hit_king:
            self._toast_msg("The king is wounded!", theme.GOLD_BRIGHT, 1.6)

    def _after_player_action(self) -> None:
        assert self.bf is not None
        # Check for immediate victory (king slain by the cast).
        if self.bf.king() is None:
            self._finish(Outcome.VICTORY)
            return
        # Discovered Attack grants a free extra action: skip the enemy phase.
        if self.bf.mage is not None and self.bf.mage.extra_action:
            self.bf.mage.extra_action = False
            self._toast_msg("Extra action!", theme.GOLD_BRIGHT, 1.2)
            self._select_move()
            return
        # Enter the enemy phase.
        self._busy = 0.45
        self._pending_enemy_phase = True
        self._select_move()

    # ------------------------------------------------------------------
    def _on_end_turn(self) -> None:
        if self._busy > 0 or self._outcome is not None:
            return
        self._busy = 0.35
        self._pending_enemy_phase = True
        self._select_move()

    def _run_enemy_phase(self) -> None:
        assert self.bf is not None and self.run is not None
        outcome, events = end_player_turn(self.bf, self.run.rng)
        for line in events:
            self._log.append(line)
        if events:
            self._toast_msg(events[-1], theme.RED, 1.8)
            self._shake = 0.2
        self._recompute()
        if outcome != Outcome.ONGOING:
            self._finish(outcome)

    def _finish(self, outcome: Outcome) -> None:
        self._outcome = outcome
        self._outcome_t = 0.0
        if self.run is not None:
            self.run.end(victory=(outcome == Outcome.VICTORY))

    def _handle_outcome_click(self, pos) -> None:
        assert self.run is not None
        if self._outcome == Outcome.VICTORY:
            # Descend to the next level.
            self.run.descend()
            self.game.scenes_mgr.switch("combat", run=self.run)
        else:
            self.game.scenes_mgr.switch("menu")

    def _on_abandon(self) -> None:
        self.game.scenes_mgr.switch("menu")

    def _toast_msg(self, text: str, color, duration: float = 1.6) -> None:
        self._toast = (text, color, duration)

    # ------------------------------------------------------------------
    def update(self, dt: float) -> None:
        self._t += dt
        if self._toast is not None:
            text, color, t = self._toast
            t -= dt
            self._toast = None if t <= 0 else (text, color, t)
        for c in list(self._flash):
            color, t = self._flash[c]
            t -= dt
            if t <= 0:
                del self._flash[c]
            else:
                self._flash[c] = (color, t)
        if self._shake > 0:
            self._shake = max(0.0, self._shake - dt)

        if self._busy > 0:
            self._busy -= dt
            if self._busy <= 0 and self._pending_enemy_phase:
                self._pending_enemy_phase = False
                self._run_enemy_phase()

        if self._outcome is not None:
            self._outcome_t += dt
        super().update(dt)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self._bg, (0, 0))
        if self.bf is None:
            return

        shake = (0, 0)
        if self._shake > 0:
            amp = int(6 * self._shake / 0.25)
            shake = (random.randint(-amp, amp), random.randint(-amp, amp))

        self._draw_grid(surface, shake)
        self._draw_highlights(surface, shake)
        self._draw_entities(surface, shake)
        self._draw_hud(surface)
        self._draw_spellbar(surface)
        self._draw_toast(surface)
        super().draw(surface)

        if self._outcome is not None:
            self._draw_outcome(surface)

    def _draw_grid(self, surface, shake) -> None:
        assert self.bf is not None
        for y in range(self.bf.height):
            for x in range(self.bf.width):
                p = (x, y)
                r = self.cell_rect(p).move(shake)
                tile = self.bf.tile(p)
                if tile == Tile.WALL:
                    col, edge = WALL_COL, WALL_EDGE
                elif tile == Tile.PILLAR:
                    col, edge = PILLAR_COL, PILLAR_EDGE
                elif tile == Tile.RUBBLE:
                    col, edge = RUBBLE_COL, RUBBLE_EDGE
                elif tile == Tile.SANCTUARY:
                    col, edge = SANCTUARY_COL, None
                elif tile == Tile.STAIRS:
                    col, edge = STAIRS_COL, None
                else:
                    col = FLOOR_A if (x + y) % 2 == 0 else FLOOR_B
                    edge = None
                pygame.draw.rect(surface, col, r)

                if edge is not None:
                    # Impassable terrain: raised bevel + bright outline so it
                    # reads instantly as "you cannot walk here".
                    self._draw_bevel(surface, r, edge)
                else:
                    pygame.draw.rect(surface, (0, 0, 0, 40), r, 1)

                if tile == Tile.PILLAR:
                    pygame.draw.circle(surface, (78, 74, 96), r.center, self.cell // 3)
                    pygame.draw.circle(surface, PILLAR_EDGE, r.center, self.cell // 3, 2)
                elif tile == Tile.RUBBLE:
                    pygame.draw.circle(surface, (92, 82, 68), (r.x + self.cell // 3, r.centery), 5)
                    pygame.draw.circle(surface, (92, 82, 68), (r.right - self.cell // 3, r.centery), 4)
                elif tile == Tile.SANCTUARY:
                    self._draw_sanctuary(surface, r)
                elif tile == Tile.STAIRS:
                    self._draw_stairs(surface, r)

    def _draw_bevel(self, surface, r, edge) -> None:
        """Raised-block look: light top/left, dark bottom/right, bright rim."""
        light = tuple(min(255, c + 40) for c in edge)
        dark = tuple(max(0, c - 60) for c in edge)
        t = max(2, self.cell // 14)
        pygame.draw.line(surface, light, r.topleft, r.topright, t)
        pygame.draw.line(surface, light, r.topleft, r.bottomleft, t)
        pygame.draw.line(surface, dark, r.bottomleft, r.bottomright, t)
        pygame.draw.line(surface, dark, r.topright, r.bottomright, t)
        pygame.draw.rect(surface, edge, r, 2)

    def _draw_sanctuary(self, surface, r) -> None:
        used = self.run is not None and self.run.level is not None and self.run.level.sanctuary_used
        if used:
            # Spent shrine: dim, no pulse.
            pygame.draw.circle(surface, (120, 130, 140), r.center, self.cell // 4, 2)
            pygame.draw.line(surface, (120, 130, 140), (r.centerx, r.y + 8), (r.centerx, r.bottom - 8), 2)
            return
        pulse = 0.5 + 0.5 * math.sin(self._t * 3)
        glow = pygame.Surface(r.size, pygame.SRCALPHA)
        pygame.draw.circle(glow, (150, 220, 240, int(60 + 60 * pulse)), r.center, self.cell // 2 - 4)
        surface.blit(glow, r.topleft)
        pygame.draw.circle(surface, (200, 240, 255), r.center, self.cell // 4, 2)
        pygame.draw.line(surface, (200, 240, 255), (r.centerx, r.y + 8), (r.centerx, r.bottom - 8), 2)

    def _draw_stairs(self, surface, r) -> None:
        for i in range(3):
            y = r.y + 10 + i * (self.cell // 4)
            pygame.draw.line(surface, (200, 180, 120), (r.x + 8, y), (r.right - 8, y), 3)

    def _draw_highlights(self, surface, shake) -> None:
        assert self.bf is not None
        # Threatened cells (danger overlay).
        for p in self.threats:
            r = self.cell_rect(p).move(shake)
            overlay = pygame.Surface(r.size, pygame.SRCALPHA)
            overlay.fill((*THREAT, 46))
            surface.blit(overlay, r.topleft)

        # Reachable cells.
        for p in self.reachable:
            r = self.cell_rect(p).move(shake)
            overlay = pygame.Surface(r.size, pygame.SRCALPHA)
            overlay.fill((*REACHABLE, 60))
            surface.blit(overlay, r.topleft)
            pygame.draw.circle(surface, REACHABLE, r.center, 6)

        # Spell targets.
        for p in self.targets:
            r = self.cell_rect(p).move(shake)
            overlay = pygame.Surface(r.size, pygame.SRCALPHA)
            overlay.fill((*TARGET, 40))
            surface.blit(overlay, r.topleft)
            pygame.draw.rect(surface, TARGET, r, 2)

        # Preview path.
        for p in self.preview_path:
            r = self.cell_rect(p).move(shake)
            pygame.draw.circle(surface, PATH, r.center, 5)

        # Hover outline.
        if self.hover is not None:
            r = self.cell_rect(self.hover).move(shake)
            pygame.draw.rect(surface, theme.GOLD_BRIGHT, r, 2)

        # Flash overlays.
        for p, (color, t) in self._flash.items():
            r = self.cell_rect(p).move(shake)
            overlay = pygame.Surface(r.size, pygame.SRCALPHA)
            overlay.fill((*color, int(160 * min(1.0, t * 3))))
            surface.blit(overlay, r.topleft)

    def _draw_entities(self, surface, shake) -> None:
        assert self.bf is not None
        # Enemies.
        for e in self.bf.living_enemies():
            r = self.cell_rect(e.pos).move(shake)
            self._draw_enemy(surface, e, r)
        # Mage.
        if self.bf.mage is not None:
            r = self.cell_rect(self.bf.mage.pos).move(shake)
            self._draw_mage(surface, r)

    def _piece_surface(self, piece_type: str, size: int, color) -> pygame.Surface:
        """Return a chess-piece sprite tinted to ``color``.

        The base sprite comes from :data:`ASSETS`, which already resolves a
        font that truly contains the chess glyphs (with a procedural fallback),
        so enemies always read as real chess pieces.
        """
        base = ASSETS.standard_piece(piece_type, False, size).copy()
        tint = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        tint.fill((*color, 255))
        base.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return base

    def _draw_enemy(self, surface, e: Enemy, r) -> None:
        col = ENEMY_COLORS[e.kind]
        if e.charmed:
            col = (120, 200, 140)
        cx, cy = r.center
        radius = self.cell // 2 - 6
        # Soft disc so the piece reads against the floor, kept subtle so the
        # chess piece itself is the dominant shape.
        disc = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(disc, (*col, 46), (radius, radius), radius)
        surface.blit(disc, (cx - radius, cy - radius))
        pygame.draw.circle(surface, col, (cx, cy), radius, 2)
        # The chess piece is the enemy.
        size = int(self.cell * 0.9)
        piece = self._piece_surface(ENEMY_PIECES[e.kind], size, col)
        surface.blit(piece, piece.get_rect(center=(cx, cy - 2)))
        # HP pips.
        if e.max_hp > 1:
            for i in range(e.max_hp):
                px = cx - (e.max_hp - 1) * 5 + i * 10
                py = r.bottom - 8
                filled = i < e.hp
                pygame.draw.circle(surface, col if filled else (60, 60, 70), (px, py), 3)
        if e.is_king:
            pygame.draw.circle(surface, theme.GOLD_BRIGHT, (cx, cy), radius + 3, 2)

    def _draw_mage(self, surface, r) -> None:
        assert self.bf is not None and self.bf.mage is not None
        mage = self.bf.mage
        cx, cy = r.center
        radius = self.cell // 2 - 5
        # Shield ring.
        if mage.shield > 0:
            pygame.draw.circle(surface, (150, 220, 255), (cx, cy), radius + 4, 3)
        pygame.draw.circle(surface, (18, 18, 24), (cx, cy), radius)
        pygame.draw.circle(surface, MAGE_COL, (cx, cy), radius, 3)
        size = int(self.cell * 0.9)
        piece = self._piece_surface("king", size, MAGE_CORE)
        surface.blit(piece, piece.get_rect(center=(cx, cy - 2)))

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------
    def _draw_hud(self, surface) -> None:
        assert self.bf is not None and self.run is not None and self.bf.mage is not None
        mage = self.bf.mage
        panel = pygame.Rect(config.WINDOW_WIDTH - 320, 90, 296, config.WINDOW_HEIGHT - 120)
        theme.draw_panel(surface, panel, fill=theme.BG_PANEL, border=theme.GOLD_DARK, radius=12)

        theme.draw_text(surface, f"Depth {self.run.depth}", (panel.x + 20, panel.y + 16),
                        size=26, color=theme.GOLD_BRIGHT, bold=True)
        theme.draw_text(surface, f"Turn {self.bf.turn + 1}", (panel.right - 20, panel.y + 20),
                        size=16, color=theme.TEXT_DIM, right=True)

        # HP bar.
        theme.draw_text(surface, "Life", (panel.x + 20, panel.y + 56), size=16,
                        color=theme.TEXT_DIM, bold=True)
        theme.draw_text(surface, f"{max(0, mage.hp)}/{mage.max_hp}",
                        (panel.right - 20, panel.y + 56), size=16, color=theme.TEXT, right=True)
        theme.draw_bar(surface, pygame.Rect(panel.x + 20, panel.y + 78, panel.width - 40, 16),
                       max(0, mage.hp) / mage.max_hp, fill=theme.RED)
        if mage.shield > 0:
            theme.draw_text(surface, f"Aegis x{mage.shield}", (panel.x + 20, panel.y + 100),
                            size=14, color=(150, 220, 255))

        # Objective.
        theme.draw_text(surface, "Objective", (panel.x + 20, panel.y + 128), size=16,
                        color=theme.GOLD, bold=True)
        theme.draw_text(surface, "Slay the enemy king at the top of the field. "
                                 "Find a line of fire.",
                        (panel.x + 20, panel.y + 150), size=14, color=theme.TEXT,
                        wrap_width=panel.width - 40)

        # Enemy count.
        alive = len(self.bf.living_enemies())
        theme.draw_text(surface, f"Enemies: {alive}", (panel.x + 20, panel.y + 210),
                        size=15, color=theme.TEXT_DIM)

        # Log.
        theme.draw_text(surface, "Chronicle", (panel.x + 20, panel.y + 244), size=16,
                        color=theme.GOLD, bold=True)
        y = panel.y + 268
        for line in self._log[-6:]:
            theme.draw_text(surface, line, (panel.x + 20, y), size=13,
                            color=theme.TEXT_DIM, wrap_width=panel.width - 40)
            y += 30

    def _draw_spellbar(self, surface) -> None:
        assert self.bf is not None and self.bf.mage is not None
        mage = self.bf.mage
        n = len(mage.spells)
        if n == 0:
            return
        bw, bh = 150, 64
        gap = 10
        # Available width left of the HUD panel.
        avail = config.WINDOW_WIDTH - 340
        per_row = max(1, (avail + gap) // (bw + gap))
        rows = (n + per_row - 1) // per_row
        # Stack rows upward from the bottom edge.
        for i, sid in enumerate(mage.spells):
            spell = SPELL_LIBRARY[sid]
            row = i // per_row
            col = i % per_row
            in_row = min(per_row, n - row * per_row)
            row_w = in_row * bw + (in_row - 1) * gap
            x0 = (avail - row_w) // 2 + 20
            y0 = config.WINDOW_HEIGHT - bh - 16 - (rows - 1 - row) * (bh + gap)
            r = pygame.Rect(x0 + col * (bw + gap), y0, bw, bh)
            active = self.mode == sid
            ready = mage.ready(sid)
            fill = theme.BG_PANEL_LIGHT if active else theme.BG_PANEL
            border = theme.GOLD_BRIGHT if active else (theme.GOLD_DARK if ready else theme.TEXT_MUTED)
            theme.draw_panel(surface, r, fill=fill, border=border, radius=8, shadow=False)
            theme.draw_text(surface, f"{i + 1}. {spell.name}", (r.x + 10, r.y + 8),
                            size=15, color=theme.GOLD_BRIGHT if ready else theme.TEXT_MUTED,
                            bold=True)
            theme.draw_text(surface, spell.description, (r.x + 10, r.y + 28),
                            size=11, color=theme.TEXT_DIM, wrap_width=bw - 20)
            if not ready:
                cd = mage.cooldowns.get(sid, 0)
                label = f"CD {cd}" if cd > 0 else "spent"
                theme.draw_text(surface, label, (r.right - 8, r.y + 8), size=12,
                                color=theme.RED, right=True)

    def _draw_toast(self, surface) -> None:
        if self._toast is None:
            return
        text, color, t = self._toast
        alpha = min(1.0, t * 2)
        f = theme.font(22, True)
        img = f.render(text, True, color)
        rect = img.get_rect(center=(config.WINDOW_WIDTH // 2 - 160, 70))
        box = rect.inflate(28, 14)
        panel = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, (*theme.BG_PANEL_DARK, int(230 * alpha)), panel.get_rect(), border_radius=8)
        pygame.draw.rect(panel, (*color, int(255 * alpha)), panel.get_rect(), width=2, border_radius=8)
        surface.blit(panel, box.topleft)
        img.set_alpha(int(255 * alpha))
        surface.blit(img, rect)

    def _draw_outcome(self, surface) -> None:
        overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        card = pygame.Rect(0, 0, 560, 320)
        card.center = (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2)
        victory = self._outcome == Outcome.VICTORY
        border = theme.GOLD if victory else theme.RED
        theme.draw_panel(surface, card, fill=theme.BG_PANEL, border=border, radius=16, border_width=3)

        title = "THE KING FALLS" if victory else "YOU HAVE FALLEN"
        theme.draw_text(surface, title, (card.centerx, card.y + 56), size=44,
                        color=theme.GOLD_BRIGHT if victory else theme.RED, bold=True, center=True)

        if victory:
            body = ("The enemy king is slain. The pieces fade and the stairs "
                    "to the next depth open.")
            hint = "Click to descend"
        else:
            body = ("Your life is spent. The dungeon claims another mage - but "
                    "the tactics you mastered endure.")
            hint = "Click to return to the menu"
        theme.draw_text(surface, body, (card.centerx, card.y + 130), size=18,
                        color=theme.TEXT, center=True, wrap_width=card.width - 80)
        theme.draw_text(surface, hint, (card.centerx, card.bottom - 50), size=18,
                        color=theme.GOLD, center=True)
