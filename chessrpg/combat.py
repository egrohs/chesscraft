"""Core tactical combat model for the roguelike.

This module is pure logic (no pygame): a grid battlefield, the mage, enemies
whose behaviour mirrors chess pieces, spells, line-of-sight, turn resolution
and win/lose conditions. The scenes render and drive it.

Coordinate system
-----------------
The battlefield is a ``width x height`` grid. ``(x, y)`` are integer cell
coordinates with ``(0, 0)`` at the top-left. ``y`` grows downward, so the
enemy king sits near the top (``y == 0``) and the mage starts near the bottom.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional

# --------------------------------------------------------------------------
# Terrain
# --------------------------------------------------------------------------


class Tile(Enum):
    FLOOR = "floor"
    WALL = "wall"          # blocks movement and line of sight
    PILLAR = "pillar"      # blocks movement, blocks line of sight
    RUBBLE = "rubble"      # blocks movement, does NOT block line of sight
    SANCTUARY = "sanctuary"  # walkable; entering opens the spell-learning shrine
    STAIRS = "stairs"      # walkable; the exit after the king falls


BLOCKING_TILES = {Tile.WALL, Tile.PILLAR, Tile.RUBBLE}
SIGHT_BLOCKING_TILES = {Tile.WALL, Tile.PILLAR}


# --------------------------------------------------------------------------
# Geometry helpers
# --------------------------------------------------------------------------

Point = tuple[int, int]


def chebyshev(a: Point, b: Point) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def manhattan(a: Point, b: Point) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def sign(n: int) -> int:
    return (n > 0) - (n < 0)


# --------------------------------------------------------------------------
# Spells
# --------------------------------------------------------------------------


class SpellKind(Enum):
    BOLT = "bolt"            # straight-line projectile
    TELEPORT = "teleport"    # blink to a visible cell
    BLAST = "blast"          # area explosion around a target cell
    SHIELD = "shield"        # absorb the next hit
    PIERCE = "pierce"        # bolt that passes through walls
    REFLECT = "reflect"      # bolt that bounces off the first obstacle
    CHARM = "charm"          # convert an enemy to an ally for a few turns


@dataclass(frozen=True)
class Spell:
    """A castable spell with clear tactical rules."""

    id: str
    name: str
    kind: SpellKind
    description: str
    range: int = 6
    radius: int = 0            # blast radius (BLAST)
    damage: int = 0
    cooldown: int = 0          # turns before it can be cast again
    charges: int = -1          # -1 = unlimited
    needs_los: bool = True
    theme: str = "arcane"      # flavour tag for the UI

    @property
    def unlimited(self) -> bool:
        return self.charges < 0


# The full spell catalogue. The mage starts with a small subset; the rest are
# learned at sanctuaries by solving chess puzzles.
SPELL_LIBRARY: dict[str, Spell] = {
    "bolt": Spell(
        id="bolt", name="Arcane Bolt", kind=SpellKind.BOLT,
        description="A straight-line projectile. Hits the first enemy in a "
                    "clear line of sight.",
        range=6, damage=2, cooldown=0, theme="arcane",
    ),
    "teleport": Spell(
        id="teleport", name="Blink", kind=SpellKind.TELEPORT,
        description="Teleport to any visible cell within range. Reposition "
                    "without crossing the space between.",
        range=5, cooldown=2, theme="shadow",
    ),
    "blast": Spell(
        id="blast", name="Arcane Blast", kind=SpellKind.BLAST,
        description="Detonate a 1-cell radius explosion at a visible target. "
                    "Hits every enemy caught in the area.",
        range=5, radius=1, damage=2, cooldown=2, theme="fire",
    ),
    "shield": Spell(
        id="shield", name="Aegis", kind=SpellKind.SHIELD,
        description="Raise a ward that absorbs the next enemy hit. Lasts "
                    "until it breaks.",
        range=0, cooldown=3, theme="holy",
    ),
    "pierce": Spell(
        id="pierce", name="Phase Lance", kind=SpellKind.PIERCE,
        description="A bolt that ignores walls and pillars, striking the "
                    "first enemy along the line.",
        range=7, damage=2, cooldown=2, needs_los=False, theme="shadow",
    ),
    "reflect": Spell(
        id="reflect", name="Ricochet", kind=SpellKind.REFLECT,
        description="A bolt that bounces off the first wall it meets, "
                    "continuing along the reflected line.",
        range=7, damage=2, cooldown=2, theme="arcane",
    ),
    "charm": Spell(
        id="charm", name="Dominate", kind=SpellKind.CHARM,
        description="Turn a visible enemy into a temporary ally for 3 turns. "
                    "It fights for you, then crumbles.",
        range=4, cooldown=4, theme="mind",
    ),
}

STARTING_SPELLS = ["bolt", "teleport"]


# --------------------------------------------------------------------------
# Entities
# --------------------------------------------------------------------------


class EnemyKind(Enum):
    PAWN = "pawn"
    ROOK = "rook"
    BISHOP = "bishop"
    KNIGHT = "knight"
    KING = "king"


@dataclass
class Enemy:
    """A chess-inspired enemy with a predictable movement/attack pattern."""

    kind: EnemyKind
    pos: Point
    hp: int = 2
    max_hp: int = 2
    charmed_turns: int = 0     # >0 means it fights for the player
    alive: bool = True
    is_king: bool = False

    @property
    def charmed(self) -> bool:
        return self.charmed_turns > 0

    @property
    def name(self) -> str:
        return {
            EnemyKind.PAWN: "Pawn",
            EnemyKind.ROOK: "Rook",
            EnemyKind.BISHOP: "Bishop",
            EnemyKind.KNIGHT: "Knight",
            EnemyKind.KING: "Enemy King",
        }[self.kind]


@dataclass
class Mage:
    """The player character."""

    pos: Point
    hp: int = 6
    max_hp: int = 6
    shield: int = 0
    spells: list[str] = field(default_factory=lambda: list(STARTING_SPELLS))
    cooldowns: dict[str, int] = field(default_factory=dict)
    charges: dict[str, int] = field(default_factory=dict)

    def has_spell(self, spell_id: str) -> bool:
        return spell_id in self.spells

    def learn(self, spell_id: str) -> None:
        if spell_id not in self.spells:
            self.spells.append(spell_id)
            spell = SPELL_LIBRARY[spell_id]
            if not spell.unlimited:
                self.charges[spell_id] = spell.charges

    def ready(self, spell_id: str) -> bool:
        if self.cooldowns.get(spell_id, 0) > 0:
            return False
        if spell_id in self.charges and self.charges[spell_id] <= 0:
            return False
        return True

    def tick_cooldowns(self) -> None:
        for k in list(self.cooldowns):
            if self.cooldowns[k] > 0:
                self.cooldowns[k] -= 1


# --------------------------------------------------------------------------
# Battlefield
# --------------------------------------------------------------------------


class Battlefield:
    """The grid, its terrain and the entities standing on it."""

    def __init__(self, width: int, height: int, tiles: list[list[Tile]]) -> None:
        self.width = width
        self.height = height
        self.tiles = tiles
        self.mage: Optional[Mage] = None
        self.enemies: list[Enemy] = []
        self.turn = 0
        self.log: list[str] = []

    # -- queries -------------------------------------------------------
    def in_bounds(self, p: Point) -> bool:
        return 0 <= p[0] < self.width and 0 <= p[1] < self.height

    def tile(self, p: Point) -> Tile:
        return self.tiles[p[1]][p[0]]

    def is_walkable(self, p: Point) -> bool:
        return self.in_bounds(p) and self.tile(p) not in BLOCKING_TILES

    def blocks_sight(self, p: Point) -> bool:
        return self.tile(p) in SIGHT_BLOCKING_TILES

    def enemy_at(self, p: Point) -> Optional[Enemy]:
        for e in self.enemies:
            if e.alive and e.pos == p:
                return e
        return None

    def occupied(self, p: Point) -> bool:
        if self.mage is not None and self.mage.pos == p:
            return True
        return self.enemy_at(p) is not None

    def king(self) -> Optional[Enemy]:
        for e in self.enemies:
            if e.alive and e.is_king:
                return e
        return None

    def living_enemies(self) -> list[Enemy]:
        return [e for e in self.enemies if e.alive]

    # -- line of sight -------------------------------------------------
    def line_cells(self, a: Point, b: Point) -> list[Point]:
        """Cells strictly between ``a`` and ``b`` (exclusive), Bresenham."""
        cells: list[Point] = []
        x0, y0 = a
        x1, y1 = b
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = sign(x1 - x0)
        sy = sign(y1 - y0)
        err = dx - dy
        x, y = x0, y0
        while (x, y) != (x1, y1):
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy
            if (x, y) != (x1, y1):
                cells.append((x, y))
        return cells

    def has_los(self, a: Point, b: Point) -> bool:
        for c in self.line_cells(a, b):
            if self.blocks_sight(c):
                return False
        return True

    def straight_line(self, a: Point, b: Point) -> bool:
        """True if ``a`` and ``b`` share a row, column or diagonal."""
        dx = b[0] - a[0]
        dy = b[1] - a[1]
        return dx == 0 or dy == 0 or abs(dx) == abs(dy)

    # -- movement ------------------------------------------------------
    def reachable(self, start: Point, steps: int) -> set[Point]:
        """Cells reachable within ``steps`` orthogonal moves (BFS)."""
        seen = {start}
        frontier = {start}
        for _ in range(steps):
            nxt: set[Point] = set()
            for (x, y) in frontier:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    p = (x + dx, y + dy)
                    if p in seen:
                        continue
                    if not self.is_walkable(p) or self.occupied(p):
                        continue
                    seen.add(p)
                    nxt.add(p)
            frontier = nxt
            if not frontier:
                break
        seen.discard(start)
        return seen

    def path_step(self, start: Point, goal: Point) -> Optional[Point]:
        """First step of a shortest orthogonal path from start toward goal."""
        if start == goal:
            return None
        prev: dict[Point, Point] = {start: start}
        frontier = [start]
        while frontier:
            nxt: list[Point] = []
            for cur in frontier:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    p = (cur[0] + dx, cur[1] + dy)
                    if p in prev or not self.is_walkable(p):
                        continue
                    if self.occupied(p) and p != goal:
                        continue
                    prev[p] = cur
                    if p == goal:
                        # Walk back to the first step.
                        step = p
                        while prev[step] != start:
                            step = prev[step]
                        return step
                    nxt.append(p)
            frontier = nxt
        return None


# --------------------------------------------------------------------------
# Enemy attack patterns (chess-inspired)
# --------------------------------------------------------------------------


def enemy_threat_cells(bf: Battlefield, enemy: Enemy) -> set[Point]:
    """Cells the enemy can attack from its current position.

    These mirror chess pieces so the player can read the board like a puzzle:
    pawns strike diagonally forward, rooks along ranks/files, bishops along
    diagonals, knights in an L, and the king in all eight directions.
    """
    x, y = enemy.pos
    cells: set[Point] = set()

    def ray(dirs: Iterable[Point], limit: int) -> None:
        for dx, dy in dirs:
            cx, cy = x + dx, y + dy
            dist = 1
            while 0 <= cx < bf.width and 0 <= cy < bf.height and dist <= limit:
                cells.add((cx, cy))
                if bf.blocks_sight((cx, cy)):
                    break
                cx += dx
                cy += dy
                dist += 1

    if enemy.kind == EnemyKind.PAWN:
        # Pawns threaten the two forward diagonals (toward the mage, i.e. down).
        for dx in (-1, 1):
            p = (x + dx, y + 1)
            if bf.in_bounds(p):
                cells.add(p)
    elif enemy.kind == EnemyKind.ROOK:
        ray(((1, 0), (-1, 0), (0, 1), (0, -1)), 8)
    elif enemy.kind == EnemyKind.BISHOP:
        ray(((1, 1), (1, -1), (-1, 1), (-1, -1)), 8)
    elif enemy.kind == EnemyKind.KNIGHT:
        for dx, dy in ((1, 2), (2, 1), (-1, 2), (-2, 1),
                       (1, -2), (2, -1), (-1, -2), (-2, -1)):
            p = (x + dx, y + dy)
            if bf.in_bounds(p):
                cells.add(p)
    elif enemy.kind == EnemyKind.KING:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                p = (x + dx, y + dy)
                if bf.in_bounds(p):
                    cells.add(p)
    return cells


def threatened_cells(bf: Battlefield) -> set[Point]:
    """Union of every hostile enemy's threat cells (for the danger overlay)."""
    cells: set[Point] = set()
    for e in bf.living_enemies():
        if e.charmed:
            continue
        cells |= enemy_threat_cells(bf, e)
    return cells


# --------------------------------------------------------------------------
# Spell resolution
# --------------------------------------------------------------------------


@dataclass
class CastResult:
    ok: bool
    message: str = ""
    affected: list[Point] = field(default_factory=list)
    path: list[Point] = field(default_factory=list)
    killed: list[Enemy] = field(default_factory=list)
    hit_king: bool = False


def _bolt_path(bf: Battlefield, origin: Point, target: Point, pierce: bool) -> list[Point]:
    """Cells a bolt travels through from origin toward target."""
    path: list[Point] = []
    for c in bf.line_cells(origin, target):
        if not pierce and bf.blocks_sight(c):
            break
        path.append(c)
    path.append(target)
    return path


def _reflect_path(bf: Battlefield, origin: Point, target: Point, max_len: int) -> list[Point]:
    """Bolt path that bounces once off the first wall it meets."""
    dx = sign(target[0] - origin[0])
    dy = sign(target[1] - origin[1])
    if dx == 0 and dy == 0:
        return [origin]
    path: list[Point] = []
    x, y = origin
    bounced = False
    for _ in range(max_len):
        nx, ny = x + dx, y + dy
        if not bf.in_bounds((nx, ny)):
            break
        if bf.blocks_sight((nx, ny)):
            if bounced:
                break
            # Reflect: flip the axis that hit the wall.
            if bf.in_bounds((x + dx, y)) and bf.blocks_sight((x + dx, y)):
                dx = -dx
            if bf.in_bounds((x, y + dy)) and bf.blocks_sight((x, y + dy)):
                dy = -dy
            if dx == 0 and dy == 0:
                break
            bounced = True
            continue
        x, y = nx, ny
        path.append((x, y))
        if bf.enemy_at((x, y)) is not None:
            break
    return path


def cast_spell(bf: Battlefield, spell: Spell, target: Point) -> CastResult:
    """Resolve casting ``spell`` at ``target``. Mutates the battlefield."""
    mage = bf.mage
    assert mage is not None
    origin = mage.pos

    if not mage.ready(spell.id):
        return CastResult(False, "Spell is on cooldown")

    # --- self / utility spells --------------------------------------
    if spell.kind == SpellKind.SHIELD:
        mage.shield += 1
        _spend(mage, spell)
        bf.log.append("You raise an Aegis ward.")
        return CastResult(True, "Aegis raised", affected=[origin])

    if spell.kind == SpellKind.TELEPORT:
        if not bf.in_bounds(target) or not bf.is_walkable(target) or bf.occupied(target):
            return CastResult(False, "Cannot blink there")
        if chebyshev(origin, target) > spell.range:
            return CastResult(False, "Out of range")
        if not bf.has_los(origin, target):
            return CastResult(False, "No line of sight")
        mage.pos = target
        _spend(mage, spell)
        bf.log.append("You blink across the field.")
        return CastResult(True, "Blinked", affected=[target])

    # --- offensive spells -------------------------------------------
    if spell.kind == SpellKind.BLAST:
        if chebyshev(origin, target) > spell.range:
            return CastResult(False, "Out of range")
        if not bf.has_los(origin, target):
            return CastResult(False, "No line of sight")
        affected = [
            (target[0] + dx, target[1] + dy)
            for dx in range(-spell.radius, spell.radius + 1)
            for dy in range(-spell.radius, spell.radius + 1)
            if bf.in_bounds((target[0] + dx, target[1] + dy))
        ]
        killed, hit_king = _damage_cells(bf, affected, spell.damage)
        _spend(mage, spell)
        bf.log.append("Arcane Blast detonates!")
        return CastResult(True, "Blast!", affected=affected, killed=killed, hit_king=hit_king)

    if spell.kind == SpellKind.CHARM:
        enemy = bf.enemy_at(target)
        if enemy is None:
            return CastResult(False, "No enemy there")
        if enemy.is_king:
            return CastResult(False, "The king's will is unbreakable")
        if chebyshev(origin, target) > spell.range or not bf.has_los(origin, target):
            return CastResult(False, "Out of range or sight")
        enemy.charmed_turns = 3
        _spend(mage, spell)
        bf.log.append(f"You dominate the {enemy.name}.")
        return CastResult(True, "Dominated", affected=[target])

    # Bolt / pierce / reflect: straight-line projectiles.
    if spell.kind in (SpellKind.BOLT, SpellKind.PIERCE, SpellKind.REFLECT):
        if chebyshev(origin, target) > spell.range:
            return CastResult(False, "Out of range")
        if spell.kind == SpellKind.BOLT:
            if not bf.straight_line(origin, target):
                return CastResult(False, "A bolt flies in a straight line")
            if not bf.has_los(origin, target):
                return CastResult(False, "No line of sight")
            path = _bolt_path(bf, origin, target, pierce=False)
        elif spell.kind == SpellKind.PIERCE:
            if not bf.straight_line(origin, target):
                return CastResult(False, "A lance flies in a straight line")
            path = _bolt_path(bf, origin, target, pierce=True)
        else:  # REFLECT
            path = _reflect_path(bf, origin, target, spell.range)

        # Find the first enemy along the path.
        hit: Optional[Enemy] = None
        hit_cells: list[Point] = []
        for c in path:
            hit_cells.append(c)
            e = bf.enemy_at(c)
            if e is not None:
                hit = e
                break
        _spend(mage, spell)
        if hit is None:
            bf.log.append("The spell fizzles into the dark.")
            return CastResult(True, "Missed", path=hit_cells)
        killed, hit_king = _damage_cells(bf, [hit.pos], spell.damage)
        return CastResult(True, f"Hit the {hit.name}", path=hit_cells,
                          affected=[hit.pos], killed=killed, hit_king=hit_king)

    return CastResult(False, "Unknown spell")


def _spend(mage: Mage, spell: Spell) -> None:
    if spell.cooldown > 0:
        mage.cooldowns[spell.id] = spell.cooldown + 1  # +1 because we tick at turn end
    if spell.id in mage.charges:
        mage.charges[spell.id] -= 1


def _damage_cells(bf: Battlefield, cells: list[Point], damage: int) -> tuple[list[Enemy], bool]:
    killed: list[Enemy] = []
    hit_king = False
    for c in cells:
        e = bf.enemy_at(c)
        if e is None:
            continue
        if e.is_king:
            hit_king = True
        e.hp -= damage
        if e.hp <= 0:
            e.alive = False
            killed.append(e)
    return killed, hit_king


# --------------------------------------------------------------------------
# Enemy turn
# --------------------------------------------------------------------------


def _enemy_attack_target(bf: Battlefield, enemy: Enemy) -> Optional[Point]:
    """Return the mage's cell if ``enemy`` can attack it this turn."""
    threats = enemy_threat_cells(bf, enemy)
    mage = bf.mage
    if mage is None:
        return None
    if mage.pos in threats and bf.has_los(enemy.pos, mage.pos):
        return mage.pos
    return None


def run_enemy_turn(bf: Battlefield, rng: random.Random) -> list[str]:
    """Move and attack with every enemy. Returns log lines."""
    events: list[str] = []
    mage = bf.mage
    assert mage is not None

    for enemy in bf.living_enemies():
        if enemy.charmed:
            # Charmed enemies attack the nearest hostile enemy instead.
            _charmed_act(bf, enemy, events)
            continue

        # 1) Attack the mage if in range.
        target = _enemy_attack_target(bf, enemy)
        if target is not None:
            _hit_mage(bf, enemy, events)
            continue

        # 2) Otherwise advance toward the mage.
        step = _enemy_step(bf, enemy, rng)
        if step is not None:
            enemy.pos = step
            # Attacking after moving.
            if _enemy_attack_target(bf, enemy) is not None:
                _hit_mage(bf, enemy, events)

    # Decay charm counters.
    for enemy in bf.living_enemies():
        if enemy.charmed:
            enemy.charmed_turns -= 1
            if enemy.charmed_turns <= 0:
                enemy.alive = False
                events.append(f"The dominated {enemy.name} crumbles to dust.")
    return events


def _hit_mage(bf: Battlefield, enemy: Enemy, events: list[str]) -> None:
    mage = bf.mage
    assert mage is not None
    if mage.shield > 0:
        mage.shield -= 1
        events.append(f"Your Aegis absorbs the {enemy.name}'s strike.")
        return
    mage.hp -= 1
    events.append(f"The {enemy.name} strikes you for 1 damage.")


def _enemy_step(bf: Battlefield, enemy: Enemy, rng: random.Random) -> Optional[Point]:
    """Choose a step toward the mage, respecting each piece's movement."""
    mage = bf.mage
    assert mage is not None
    goal = mage.pos

    if enemy.kind == EnemyKind.KNIGHT:
        # Knights leap in an L toward the mage.
        options = []
        for dx, dy in ((1, 2), (2, 1), (-1, 2), (-2, 1),
                       (1, -2), (2, -1), (-1, -2), (-2, -1)):
            p = (enemy.pos[0] + dx, enemy.pos[1] + dy)
            if bf.is_walkable(p) and not bf.occupied(p):
                options.append(p)
        if not options:
            return None
        options.sort(key=lambda p: manhattan(p, goal))
        return options[0]

    if enemy.kind == EnemyKind.PAWN:
        # Pawns only march forward (downward) and never retreat.
        p = (enemy.pos[0], enemy.pos[1] + 1)
        if bf.is_walkable(p) and not bf.occupied(p):
            return p
        return None

    # Rook / bishop / king: step along their allowed directions toward mage.
    if enemy.kind == EnemyKind.ROOK:
        dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    elif enemy.kind == EnemyKind.BISHOP:
        dirs = ((1, 1), (1, -1), (-1, 1), (-1, -1))
    else:  # KING
        dirs = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx, dy) != (0, 0)]

    best: Optional[Point] = None
    best_dist = manhattan(enemy.pos, goal)
    for dx, dy in dirs:
        p = (enemy.pos[0] + dx, enemy.pos[1] + dy)
        if not bf.is_walkable(p) or bf.occupied(p):
            continue
        d = manhattan(p, goal)
        if d < best_dist:
            best_dist = d
            best = p
    return best


def _charmed_act(bf: Battlefield, enemy: Enemy, events: list[str]) -> None:
    """A dominated enemy attacks the nearest hostile enemy."""
    hostiles = [e for e in bf.living_enemies() if not e.charmed and e is not enemy]
    if not hostiles:
        return
    hostiles.sort(key=lambda e: manhattan(e.pos, enemy.pos))
    target = hostiles[0]
    if target.pos in enemy_threat_cells(bf, enemy):
        target.hp -= 1
        if target.hp <= 0:
            target.alive = False
            events.append(f"Your dominated {enemy.name} slays a {target.name}.")
        else:
            events.append(f"Your dominated {enemy.name} wounds a {target.name}.")
    else:
        step = _enemy_step(bf, enemy, random.Random(0))
        if step is not None:
            enemy.pos = step


# --------------------------------------------------------------------------
# Turn orchestration
# --------------------------------------------------------------------------


class Outcome(Enum):
    ONGOING = "ongoing"
    VICTORY = "victory"   # king slain
    DEFEAT = "defeat"     # mage dead


def end_player_turn(bf: Battlefield, rng: random.Random) -> tuple[Outcome, list[str]]:
    """Run the enemy phase and evaluate the outcome."""
    bf.turn += 1
    events = run_enemy_turn(bf, rng)
    mage = bf.mage
    assert mage is not None
    mage.tick_cooldowns()

    king = bf.king()
    if king is None:
        return Outcome.VICTORY, events
    if mage.hp <= 0:
        return Outcome.DEFEAT, events
    return Outcome.ONGOING, events
