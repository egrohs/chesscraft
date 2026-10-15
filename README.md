# Chess RPG - Tactical Trials

A chess **simulation RPG** for PC inspired by *Master of Chess*, built with
**pygame-ce** and **python-chess**. Instead of playing full games, you advance
through a campaign of **tactical puzzles**, earning XP and gold and levelling
up your hero.

## Features

- **Dark-fantasy RPG interface** - animated main menu, chapter map, hero sheet.
- **Painted character art** - the illustrations in `art/` are turned into
  circular piece tokens at runtime (see `chessrpg/assets.py`).
- **Full chess rules** - powered by `python-chess`, so every move is legal.
- **Tactical puzzles** - find the winning line; wrong moves cost reward.
- **RPG progression** - XP, levels, gold, stats and a persistent save file.
- **Hints** - spend gold to reveal the next correct move.
- **Click or drag** to move pieces, with legal-move dots and capture rings.

## Requirements

- Python 3.10+
- `pygame-ce`
- `python-chess`

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

## Controls

| Action            | Input                                  |
| ----------------- | -------------------------------------- |
| Select / move     | Left click a piece, then a target square |
| Drag and drop     | Press and drag a piece                 |
| Cancel selection  | Right click or click empty space       |
| Back to menu      | `Esc`                                  |

## Project layout

```
main.py                     entry point
chessrpg/
  config.py                 window, layout and tuning constants
  theme.py                  palette, fonts, drawing helpers
  assets.py                 art loading + piece-token extraction
  ui.py                     buttons, labels, bars, tooltips
  board.py                  board rendering and mouse input
  scene.py                  scene base class + fade transitions
  rpg.py                    hero stats, XP and save profile
  puzzles.py                puzzle library + solution validation
  game.py                   window, main loop, scene wiring
  scenes/
    menu.py                 main menu
    level_select.py         chapter map
    puzzle_scene.py         gameplay + HUD + result overlay
    hero_scene.py           character sheet
    help_scene.py           how to play
tools/
  smoke_test.py             headless test of puzzles and every scene
  verify_puzzles.py         prints each puzzle's solution in SAN
  screenshots.py            renders each scene to tools/shots/*.png
```

## Adding a puzzle

Append a `Puzzle` to `PUZZLES` in `chessrpg/puzzles.py`:

```python
Puzzle(
    id="p9",
    name="My Puzzle",
    fen="6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1",
    solution=["a1a8"],          # UCI moves, player and opponent alternating
    goal="mate",
    difficulty=2,
    xp=60, gold=30,
    chapter="Chapter II - The Rook's Gambit",
    briefing="...",
    hint="...",
)
```

Then validate it:

```bash
python tools/verify_puzzles.py
```

## Testing

```bash
python tools/smoke_test.py     # boots the game headless and drives every scene
python tools/screenshots.py    # writes PNGs of each scene to tools/shots/
```

The smoke test checks that every puzzle's solution is legal and playable, that
all scenes render, and that solving / wrong-move / hint flows behave correctly.
