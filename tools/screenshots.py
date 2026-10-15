"""Render each scene to a PNG so the UI can be reviewed without a display.

Run with:  python tools/screenshots.py
Outputs to: tools/shots/*.png
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chess  # noqa: E402
import pygame  # noqa: E402

from chessrpg.game import Game  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")


def settle(game: Game, frames: int = 40) -> None:
    for _ in range(frames):
        game.scenes_mgr.update(1 / 60)


def shot(game: Game, name: str) -> None:
    game.screen.fill((0, 0, 0))
    game.scenes_mgr.draw(game.screen)
    path = os.path.join(OUT, f"{name}.png")
    pygame.image.save(game.screen, path)
    print("  wrote", path)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    game = Game()

    # Menu
    settle(game)
    shot(game, "01_menu")

    # Level select (first chapter)
    game.scenes_mgr.switch("level_select")
    settle(game)
    shot(game, "02_level_select")

    # Puzzle p1 - initial
    game.scenes_mgr.switch("puzzle", puzzle_id="p1")
    settle(game)
    shot(game, "03_puzzle_start")

    # Puzzle p1 - with a piece selected (legal move dots)
    scene = game.scenes["puzzle"]
    scene.board_view.selected = chess.A1
    scene.board_view.legal_targets = {
        m.to_square for m in scene.session.board.legal_moves if m.from_square == chess.A1
    }
    shot(game, "04_puzzle_selected")

    # Puzzle p1 - solved (result overlay)
    scene._handle_board_action(("move", chess.A1, chess.A8))
    settle(game, 20)
    shot(game, "05_puzzle_victory")

    # Hero sheet
    game.scenes_mgr.switch("hero")
    settle(game)
    shot(game, "06_hero")

    # Help
    game.scenes_mgr.switch("help")
    settle(game)
    shot(game, "07_help")

    pygame.quit()
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
