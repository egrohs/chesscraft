"""Headless smoke test: boots the game, drives every scene, checks puzzles.

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
from chessrpg.game import Game  # noqa: E402
from chessrpg.puzzles import PUZZLES, PuzzleSession  # noqa: E402


def check_puzzles() -> None:
    """Every puzzle must be legal and its solution must be playable."""
    for puzzle in PUZZLES:
        session = PuzzleSession(puzzle)
        for i, uci in enumerate(puzzle.solution):
            if i % 2 == 0:
                # Player move: must be legal and accepted by the session.
                move = chess.Move.from_uci(uci)
                assert move in session.board.legal_moves, (
                    f"{puzzle.id}: illegal player move {uci} at step {i}"
                )
                result = session.try_move(move)
                assert result in ("correct", "solved"), f"{puzzle.id}: {result}"
            else:
                # Opponent replies are applied inside try_move; just confirm
                # the session advanced past them.
                assert session.step > i, f"{puzzle.id}: opponent reply {uci} not applied"
        assert session.solved, f"{puzzle.id}: solution did not finish the puzzle"
        print(f"  ok  {puzzle.id:<4} {puzzle.name:<22} {len(puzzle.solution)} plies")


def drive_scene(game: Game, name: str, frames: int = 8, **kwargs) -> None:
    game.scenes_mgr.switch(name, **kwargs)
    for _ in range(30):  # let the fade finish
        game.scenes_mgr.update(1 / 60)
    for _ in range(frames):
        game.scenes_mgr.update(1 / 60)
        game.screen.fill((0, 0, 0))
        game.scenes_mgr.draw(game.screen)
    print(f"  ok  scene '{name}' rendered")


def main() -> int:
    print("Checking puzzle library...")
    check_puzzles()

    print("Booting game...")
    game = Game()

    print("Driving scenes...")
    drive_scene(game, "menu")
    drive_scene(game, "level_select")
    drive_scene(game, "hero")
    drive_scene(game, "help")
    drive_scene(game, "puzzle", puzzle_id="p1")

    # Simulate solving p1 through the scene's board interaction.
    scene = game.scenes["puzzle"]
    scene.on_enter(puzzle_id="p1")
    src = chess.A1
    dst = chess.A8
    scene._handle_board_action(("move", src, dst))
    assert scene._result == "victory", "p1 should be solved by Ra8#"
    print("  ok  solved p1 through the scene, result overlay shown")

    # Render the result overlay.
    for _ in range(5):
        game.scenes_mgr.update(1 / 60)
        game.scenes_mgr.draw(game.screen)
    print("  ok  result overlay rendered")

    # Wrong move path
    scene.on_enter(puzzle_id="p2")
    scene._handle_board_action(("move", chess.A2, chess.A3))
    assert scene.session.mistakes == 1, "wrong move should count a mistake"
    print("  ok  wrong move counted")

    # Hint path
    gold_before = game.profile.hero.gold
    scene._on_hint()
    assert game.profile.hero.gold == gold_before - config.HINT_COST
    assert scene.board_view.hint_move is not None
    print("  ok  hint consumed gold and highlighted a move")

    pygame.quit()
    print("\nAll smoke tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
