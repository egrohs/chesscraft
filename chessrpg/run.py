"""Level generation and the roguelike run state.

A *run* is a sequence of dungeon levels. Each level is a procedurally varied
battlefield: the mage starts at the bottom, the enemy king is walled off at the
top, and chess-inspired enemies plus a sanctuary are scattered between. Clear
the king to descend to the next, harder level. Death ends the run, but tactics
learned by solving a sanctuary puzzle on the first try are remembered forever.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from .combat import (
    Battlefield,
    Enemy,
    EnemyKind,
    Mage,
    SPELL_LIBRARY,
    Tile,
)

# --------------------------------------------------------------------------
# Level configuration
# --------------------------------------------------------------------------

# Grid size grows a little with depth to keep the crossing interesting.
def _grid_for_depth(depth: int) -> tuple[int, int]:
    width = 9 + min(3, depth // 2)
    height = 9 + min(3, depth // 2)
    return width, height


# Enemy budget per depth: (pawns, rooks, bishops, knights)
def _enemy_budget(depth: int) -> dict[EnemyKind, int]:
    return {
        EnemyKind.PAWN: 2 + depth,
        EnemyKind.ROOK: 1 + depth // 2,
        EnemyKind.BISHOP: 1 + (depth + 1) // 2,
        EnemyKind.KNIGHT: depth // 2,
    }


@dataclass
class Level:
    """A generated battlefield plus its metadata."""

    depth: int
    battlefield: Battlefield
    sanctuary_pos: Optional[tuple[int, int]]
    stairs_pos: tuple[int, int]
    seed: int


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------


def generate_level(depth: int, seed: int) -> Level:
    """Build a fresh, solvable battlefield for ``depth`` (1-based)."""
    rng = random.Random(seed)
    width, height = _grid_for_depth(depth)

    # Start with an open floor.
    tiles = [[Tile.FLOOR for _ in range(width)] for _ in range(height)]

    # Outer walls.
    for x in range(width):
        tiles[0][x] = Tile.WALL
        tiles[height - 1][x] = Tile.WALL
    for y in range(height):
        tiles[y][0] = Tile.WALL
        tiles[y][width - 1] = Tile.WALL

    # The king's keep: a walled pocket at the top with a single gate.
    keep_left = width // 2 - 1
    keep_right = width // 2 + 1
    keep_bottom = 2
    for x in range(keep_left, keep_right + 1):
        tiles[keep_bottom][x] = Tile.WALL
    gate_x = rng.choice([keep_left, keep_right])
    tiles[keep_bottom][gate_x] = Tile.FLOOR
    king_pos = (width // 2, 1)

    # Scatter cover: pillars and rubble, avoiding the keep and the start.
    start = (width // 2, height - 2)
    protected = {king_pos, start, (width // 2, keep_bottom), (gate_x, keep_bottom)}
    for _ in range(width + height):
        x = rng.randint(2, width - 3)
        y = rng.randint(keep_bottom + 1, height - 3)
        if (x, y) in protected:
            continue
        tiles[y][x] = rng.choice([Tile.PILLAR, Tile.RUBBLE, Tile.WALL])

    # Sanctuary: a guaranteed reachable cell in the lower half.
    sanctuary_pos = _find_open(tiles, rng, y_range=(height // 2, height - 2))
    if sanctuary_pos is not None:
        tiles[sanctuary_pos[1]][sanctuary_pos[0]] = Tile.SANCTUARY

    # Stairs appear where the king stood once it falls (visual only).
    stairs_pos = king_pos

    bf = Battlefield(width, height, tiles)

    # Place the mage.
    bf.mage = Mage(pos=start)

    # Place the king.
    bf.enemies.append(Enemy(kind=EnemyKind.KING, pos=king_pos, hp=3, max_hp=3, is_king=True))

    # Place the rest of the enemies in the middle band.
    budget = _enemy_budget(depth)
    occupied = {king_pos, start}
    if sanctuary_pos:
        occupied.add(sanctuary_pos)
    for kind, count in budget.items():
        for _ in range(count):
            spot = _find_open(tiles, rng, y_range=(keep_bottom + 1, height - 3),
                              avoid=occupied)
            if spot is None:
                continue
            occupied.add(spot)
            hp = 3 if kind == EnemyKind.ROOK else 2
            bf.enemies.append(Enemy(kind=kind, pos=spot, hp=hp, max_hp=hp))

    return Level(depth=depth, battlefield=bf, sanctuary_pos=sanctuary_pos,
                 stairs_pos=stairs_pos, seed=seed)


def _find_open(tiles, rng: random.Random, *, y_range: tuple[int, int],
               avoid: Optional[set] = None) -> Optional[tuple[int, int]]:
    avoid = avoid or set()
    height = len(tiles)
    width = len(tiles[0])
    candidates = [
        (x, y)
        for y in range(max(1, y_range[0]), min(height - 1, y_range[1] + 1))
        for x in range(1, width - 1)
        if tiles[y][x] == Tile.FLOOR and (x, y) not in avoid
    ]
    if not candidates:
        return None
    return rng.choice(candidates)


# --------------------------------------------------------------------------
# Run state
# --------------------------------------------------------------------------


@dataclass
class Run:
    """The state of a single roguelike attempt."""

    seed: int
    depth: int = 1
    level: Optional[Level] = None
    mage: Optional[Mage] = None
    rng: random.Random = field(default_factory=random.Random)
    finished: bool = False
    victory: bool = False
    levels_cleared: int = 0
    spells_learned: list[str] = field(default_factory=list)

    def start(self) -> None:
        self.rng = random.Random(self.seed)
        self.depth = 1
        self.finished = False
        self.victory = False
        self.levels_cleared = 0
        self.spells_learned = []
        self.mage = Mage(pos=(0, 0))
        self._load_level()

    def _load_level(self) -> None:
        level_seed = self.rng.randint(0, 2**31 - 1)
        self.level = generate_level(self.depth, level_seed)
        # Carry the mage's spells and health across levels.
        assert self.level.battlefield.mage is not None
        if self.mage is not None:
            carried = self.mage
            new_mage = self.level.battlefield.mage
            new_mage.spells = list(carried.spells)
            new_mage.charges = dict(carried.charges)
            new_mage.hp = carried.hp
            new_mage.max_hp = carried.max_hp
            new_mage.shield = carried.shield
            self.mage = new_mage
        else:
            self.mage = self.level.battlefield.mage

    def descend(self) -> None:
        """Advance to the next, harder level after slaying the king."""
        self.levels_cleared += 1
        self.depth += 1
        self._load_level()

    def learn_spell(self, spell_id: str) -> None:
        if self.mage is not None and spell_id in SPELL_LIBRARY:
            self.mage.learn(spell_id)
            if spell_id not in self.spells_learned:
                self.spells_learned.append(spell_id)

    def end(self, victory: bool) -> None:
        self.finished = True
        self.victory = victory


# --------------------------------------------------------------------------
# Sanctuary spell offers
# --------------------------------------------------------------------------


def spell_offers(run: Run, rng: random.Random, count: int = 3) -> list[str]:
    """Pick ``count`` spells the mage does not yet know, each with a theme."""
    known = set(run.mage.spells) if run.mage else set()
    pool = [sid for sid in SPELL_LIBRARY if sid not in known]
    rng.shuffle(pool)
    return pool[:count]
