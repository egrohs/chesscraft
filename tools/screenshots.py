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
from chessrpg.run import Run  # noqa: E402

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

    # Combat - initial battlefield
    run = Run(seed=7)
    run.start()
    game.scenes_mgr.switch("combat", run=run)
    settle(game)
    shot(game, "02_combat_start")

    # Combat - spell selected (targets highlighted)
    scene = game.scenes["combat"]
    scene._select_spell("bolt")
    settle(game, 4)
    shot(game, "03_combat_bolt")

    # Combat - move mode (reachable cells)
    scene._select_move()
    settle(game, 4)
    shot(game, "04_combat_move")

    # Sanctuary - spell choice
    game.scenes_mgr.switch("sanctuary", run=run)
    settle(game)
    shot(game, "05_sanctuary_choose")

    # Sanctuary - puzzle
    sanc = game.scenes["sanctuary"]
    sanc.on_enter(run=run)
    sanc._choose(sanc.offers[0])
    settle(game, 4)
    shot(game, "06_sanctuary_puzzle")

    # Hero sheet
    game.scenes_mgr.switch("hero")
    settle(game)
    shot(game, "07_hero")

    # Help
    game.scenes_mgr.switch("help")
    settle(game)
    shot(game, "08_help")

    pygame.quit()
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
