"""Headless smoke test: boots the game, drives every scene, checks the loop.

Run with:  python tools/smoke_test.py
Uses the dummy SDL video driver so it works without a display.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chess  # noqa: E402
import pygame  # noqa: E402

from chessrpg import config  # noqa: E402
from chessrpg.combat import (  # noqa: E402
    Battlefield,
    Enemy,
    EnemyKind,
    Mage,
    Outcome,
    SPELL_LIBRARY,
    SpellKind,
    Tile,
    cast_spell,
    end_player_turn,
    threatened_cells,
)
from chessrpg.game import Game  # noqa: E402
from chessrpg.puzzles import THEMED_PUZZLES, PuzzleSession, themed_puzzle_for  # noqa: E402
from chessrpg.run import Run, generate_level, spell_offers  # noqa: E402


# --------------------------------------------------------------------------
# Logic tests
# --------------------------------------------------------------------------
def check_themed_puzzles() -> None:
    for key, puzzle in THEMED_PUZZLES.items():
        session = PuzzleSession(puzzle)
        for i, uci in enumerate(puzzle.solution):
            if i % 2 == 0:
                move = chess.Move.from_uci(uci)
                assert move in session.board.legal_moves, f"{puzzle.id}: illegal {uci}"
                result = session.try_move(move)
                assert result in ("correct", "solved"), f"{puzzle.id}: {result}"
            else:
                assert session.step > i, f"{puzzle.id}: reply {uci} not applied"
        assert session.solved, f"{puzzle.id}: not solved"
        print(f"  ok  themed puzzle {key:<12} {puzzle.id}")


def check_spell_themes() -> None:
    for sid in SPELL_LIBRARY:
        assert themed_puzzle_for(sid) is not None, f"{sid} has no teaching puzzle"
    print("  ok  every spell has a teaching puzzle")


def _open_field(width=9, height=9) -> Battlefield:
    tiles = [[Tile.FLOOR for _ in range(width)] for _ in range(height)]
    for x in range(width):
        tiles[0][x] = Tile.WALL
        tiles[height - 1][x] = Tile.WALL
    for y in range(height):
        tiles[y][0] = Tile.WALL
        tiles[y][width - 1] = Tile.WALL
    bf = Battlefield(width, height, tiles)
    bf.mage = Mage(pos=(4, 7))
    return bf


def check_combat_rules() -> None:
    # Bolt hits the first enemy in a straight line.
    bf = _open_field()
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 4), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["bolt"], (4, 4))
    assert res.ok and res.killed, "bolt should kill a 2hp pawn with 2 damage"
    assert bf.enemy_at((4, 4)) is None
    print("  ok  bolt kills first enemy in line")

    # Bolt blocked by a wall.
    bf = _open_field()
    bf.tiles[5][4] = Tile.WALL
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 3), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["bolt"], (4, 3))
    assert not res.ok, "bolt should be blocked by a wall"
    print("  ok  bolt blocked by wall")

    # Pierce ignores walls.
    bf = _open_field()
    bf.tiles[5][4] = Tile.WALL
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 3), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["pierce"], (4, 3))
    assert res.ok and res.killed, "pierce should ignore the wall"
    print("  ok  pierce ignores walls")

    # Blast hits an area.
    bf = _open_field()
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 4), hp=2, max_hp=2))
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(5, 4), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["blast"], (4, 4))
    assert res.ok and len(res.killed) == 2, "blast should hit both adjacent enemies"
    print("  ok  blast hits area")

    # Teleport moves the mage.
    bf = _open_field()
    res = cast_spell(bf, SPELL_LIBRARY["teleport"], (4, 3))
    assert res.ok and bf.mage.pos == (4, 3)
    print("  ok  teleport moves mage")

    # Shield absorbs a hit.
    bf = _open_field()
    bf.mage.pos = (4, 4)
    bf.enemies.append(Enemy(kind=EnemyKind.ROOK, pos=(4, 2), hp=3, max_hp=3))
    cast_spell(bf, SPELL_LIBRARY["shield"], (4, 4))
    hp_before = bf.mage.hp
    end_player_turn(bf, __import__("random").Random(0))
    assert bf.mage.hp == hp_before, "shield should absorb the hit"
    print("  ok  shield absorbs a hit")

    # Charm converts an enemy.
    bf = _open_field()
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 5), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["charm"], (4, 5))
    assert res.ok and bf.enemy_at((4, 5)).charmed
    print("  ok  charm converts enemy")

    # Threat map reflects chess patterns.
    bf = _open_field()
    bf.enemies.append(Enemy(kind=EnemyKind.ROOK, pos=(4, 4), hp=3, max_hp=3))
    threats = threatened_cells(bf)
    assert (4, 1) in threats and (1, 4) in threats, "rook should threaten its rank/file"
    assert (5, 5) not in threats, "rook should not threaten diagonals"
    print("  ok  threat map matches chess patterns")


def check_tactic_spells() -> None:
    import random as _random

    # Open Lines: shove an enemy one cell further along the line.
    bf = _open_field()
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 4), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["push"], (4, 4))
    assert res.ok and bf.enemy_at((4, 3)) is not None, "push should shove the enemy back"
    print("  ok  open lines shoves an enemy")

    # Pawn Break: destroy a wall tile.
    bf = _open_field()
    bf.tiles[4][4] = Tile.WALL
    res = cast_spell(bf, SPELL_LIBRARY["break"], (4, 4))
    assert res.ok and bf.tile((4, 4)) == Tile.FLOOR, "break should open the wall"
    print("  ok  pawn break opens a wall")

    # Windmill: hits every enemy on the mage's rank and file.
    bf = _open_field()
    bf.mage.pos = (4, 4)
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 2), hp=2, max_hp=2))
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(2, 4), hp=2, max_hp=2))
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(6, 6), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["cross"], (4, 4))
    assert res.ok and len(res.killed) == 2, "windmill should kill the two on rank/file"
    assert bf.enemy_at((6, 6)) is not None, "windmill should spare off-axis enemies"
    print("  ok  windmill hits rank and file")

    # Fork: strikes the target and a second adjacent enemy.
    bf = _open_field()
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 4), hp=2, max_hp=2))
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(5, 4), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["fork"], (4, 4))
    assert res.ok and len(res.killed) == 2, "fork should hit two enemies"
    print("  ok  fork strikes two enemies")

    # Sacrifice: pay life for shield and refreshed cooldowns.
    bf = _open_field()
    bf.mage.cooldowns["bolt"] = 3
    hp0 = bf.mage.hp
    res = cast_spell(bf, SPELL_LIBRARY["sacrifice"], bf.mage.pos)
    assert res.ok and bf.mage.hp == hp0 - 1 and bf.mage.shield == 2
    assert bf.mage.cooldowns["bolt"] == 0, "sacrifice should refresh cooldowns"
    print("  ok  sacrifice trades life for shield + tempo")

    # Stalemate: flee to a cell not under threat.
    bf = _open_field()
    bf.mage.pos = (4, 4)
    bf.enemies.append(Enemy(kind=EnemyKind.ROOK, pos=(4, 2), hp=3, max_hp=3))
    res = cast_spell(bf, SPELL_LIBRARY["escape"], bf.mage.pos)
    assert res.ok and bf.mage.pos != (4, 4), "escape should move the mage"
    print("  ok  stalemate flees to safety")

    # Deflection: nearby enemies become feared and flee.
    bf = _open_field()
    bf.mage.pos = (4, 4)
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 5), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["fear"], bf.mage.pos)
    assert res.ok and bf.enemy_at((4, 5)).feared, "deflection should fear the enemy"
    print("  ok  deflection fears nearby enemies")

    # Discovered Attack: damage + a free extra action.
    bf = _open_field()
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 4), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["discover"], (4, 4))
    assert res.ok and bf.mage.extra_action, "discovered attack should grant an extra action"
    print("  ok  discovered attack grants tempo")

    # Pin: freeze an enemy so it cannot act.
    bf = _open_field()
    bf.mage.pos = (4, 4)
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 5), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["pin"], (4, 5))
    assert res.ok and bf.enemy_at((4, 5)).pinned, "pin should freeze the enemy"
    pos_before = bf.enemy_at((4, 5)).pos
    end_player_turn(bf, _random.Random(0))
    assert bf.enemy_at(pos_before) is not None, "a pinned enemy must not move"
    print("  ok  pin freezes an enemy")

    # Minefield: a mine detonates only when an enemy steps on it.
    bf = _open_field()
    bf.mage.pos = (4, 7)
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 5), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["mine"], (4, 6))
    assert res.ok and (4, 6) in bf.mines, "mine should be laid"
    end_player_turn(bf, _random.Random(0))
    assert (4, 6) not in bf.mines, "the pawn should trigger the mine"
    print("  ok  minefield detonates on an enemy")

    # Triangulation: spend a turn for shield + cooldown reduction.
    bf = _open_field()
    bf.mage.cooldowns["bolt"] = 2
    res = cast_spell(bf, SPELL_LIBRARY["tempo"], bf.mage.pos)
    assert res.ok and bf.mage.shield == 1 and bf.mage.cooldowns["bolt"] == 1
    print("  ok  triangulation trades tempo for advantage")

    # Skewer: hits the enemy behind the first in line.
    bf = _open_field()
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 5), hp=2, max_hp=2))
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 3), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["sniper"], (4, 3))
    assert res.ok and bf.enemy_at((4, 3)) is None, "skewer should hit the rear enemy"
    assert bf.enemy_at((4, 5)) is not None, "skewer should spare the front enemy"
    print("  ok  skewer strikes the enemy behind")

    # Interference: raise a wall that blocks sight.
    bf = _open_field()
    res = cast_spell(bf, SPELL_LIBRARY["wall"], (4, 5))
    assert res.ok and (4, 5) in bf.temp_walls, "wall should be raised"
    assert bf.blocks_sight((4, 5)), "the wall should block line of sight"
    print("  ok  interference raises a sight wall")

    # Clearance: sidestep, shoving an adjacent enemy aside.
    bf = _open_field()
    bf.mage.pos = (4, 4)
    bf.enemies.append(Enemy(kind=EnemyKind.PAWN, pos=(4, 5), hp=2, max_hp=2))
    res = cast_spell(bf, SPELL_LIBRARY["clearance"], (4, 5))
    assert res.ok and bf.mage.pos == (4, 5), "clearance should move the mage in"
    assert bf.enemy_at((4, 6)) is not None, "clearance should shove the enemy aside"
    print("  ok  clearance sidesteps and shoves")


def check_level_generation() -> None:
    for depth in range(1, 6):
        level = generate_level(depth, seed=depth * 7)
        bf = level.battlefield
        assert bf.king() is not None, f"depth {depth}: no king"
        assert bf.mage is not None, f"depth {depth}: no mage"
        assert level.sanctuary_pos is not None, f"depth {depth}: no sanctuary"
        # The mage must be able to reach the sanctuary.
        reach = bf.reachable(bf.mage.pos, 40)
        assert level.sanctuary_pos in reach, f"depth {depth}: sanctuary unreachable"
        print(f"  ok  depth {depth}: {bf.width}x{bf.height}, "
              f"{len(bf.living_enemies())} enemies, sanctuary reachable")


def check_run_flow() -> None:
    run = Run(seed=1234)
    run.start()
    assert run.depth == 1 and run.level is not None
    offers = spell_offers(run, run.rng, 3)
    assert len(offers) == 3, "should offer three spells"
    run.learn_spell(offers[0])
    assert offers[0] in run.mage.spells
    run.descend()
    assert run.depth == 2 and run.levels_cleared == 1
    # Learned spell carries over.
    assert offers[0] in run.mage.spells, "learned spell should persist across levels"
    print("  ok  run flow: offers, learning, descent, carry-over")


# --------------------------------------------------------------------------
# Scene tests
# --------------------------------------------------------------------------
def drive_scene(game: Game, name: str, frames: int = 8, **kwargs) -> None:
    game.scenes_mgr.switch(name, **kwargs)
    for _ in range(30):
        game.scenes_mgr.update(1 / 60)
    for _ in range(frames):
        game.scenes_mgr.update(1 / 60)
        game.screen.fill((0, 0, 0))
        game.scenes_mgr.draw(game.screen)
    print(f"  ok  scene '{name}' rendered")


def check_scenes(game: Game) -> None:
    drive_scene(game, "menu")
    drive_scene(game, "hero")
    drive_scene(game, "help")

    run = Run(seed=99)
    run.start()
    drive_scene(game, "combat", run=run)

    # Move the mage one step and end the turn.
    scene = game.scenes["combat"]
    scene.on_enter(run=run)
    mage = scene.bf.mage
    start = mage.pos
    if scene.reachable:
        target = next(iter(scene.reachable))
        scene._on_cell_click(target)
        assert mage.pos == target, "mage should move to a reachable cell"
    print("  ok  combat: mage moved")

    # The sanctuary may only be visited once per level.
    sanc_pos = run.level.sanctuary_pos
    assert sanc_pos is not None
    scene.reachable = {sanc_pos}
    scene._on_cell_click(sanc_pos)
    assert run.level.sanctuary_used, "entering the sanctuary should mark it used"
    assert game.scenes_mgr._next and game.scenes_mgr._next[0] == "sanctuary", \
        "first visit opens the shrine"
    game.scenes_mgr._next = None
    scene.on_enter(run=run)
    scene.reachable = {sanc_pos}
    scene._on_cell_click(sanc_pos)
    assert not (game.scenes_mgr._next and game.scenes_mgr._next[0] == "sanctuary"), \
        "second visit must not reopen the shrine"
    print("  ok  combat: sanctuary visitable only once per level")



    # Cast a bolt at an enemy if one is in line.
    scene._select_spell("bolt")
    assert scene.mode == "bolt"
    print("  ok  combat: spell selected")

    # Sanctuary scene.
    drive_scene(game, "sanctuary", run=run)
    sanc = game.scenes["sanctuary"]
    sanc.on_enter(run=run)
    assert len(sanc.offers) == 3
    sanc._choose(sanc.offers[0])
    assert sanc.phase == "puzzle"
    print("  ok  sanctuary: chose a spell, puzzle opened")

    # Solve the sanctuary puzzle through the board.
    puzzle = sanc.session.puzzle
    for i, uci in enumerate(puzzle.solution):
        if i % 2 == 0:
            mv = chess.Move.from_uci(uci)
            sanc._handle_board_action(("move", mv.from_square, mv.to_square))
    assert sanc.phase == "learned", "solving the puzzle should teach the spell"
    print("  ok  sanctuary: puzzle solved, spell learned")


def main() -> int:
    print("Checking themed puzzles...")
    check_themed_puzzles()
    check_spell_themes()

    print("Checking combat rules...")
    check_combat_rules()

    print("Checking chess-tactic spells...")
    check_tactic_spells()

    print("Checking level generation...")
    check_level_generation()

    print("Checking run flow...")
    check_run_flow()

    print("Booting game...")
    game = Game()

    print("Driving scenes...")
    check_scenes(game)

    pygame.quit()
    print("\nAll smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
