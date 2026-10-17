# Arcane Descent

A **tactical roguelike** for PC inspired by *Hoplite*, with a dark-fantasy
theme. You play a mage crossing a grid battlefield to reach a line of fire on
the enemy king at the far side. Every turn is a chess-like decision: read the
threats, position yourself, and find the angle to strike. Built with
**pygame-ce** and **python-chess**.

> **Full rules:** see [`MANUAL.md`](MANUAL.md) for the complete rulebook
> (terrain, line of sight, every spell, enemy patterns, sanctuaries, puzzles
> and roguelike progression).

## The loop

1. **Cross the battlefield.** Move one cell or cast one spell per turn, then
   every enemy acts. Reach a position with a clear line to the enemy king.
2. **Slay the king.** The king is walled off at the top of the field, guarded
   by chess-inspired enemies. Create an opening and land a spell.
3. **Descend.** When the king falls, the pieces fade and you take the stairs to
   a deeper, harder level. Spells and health carry over.
4. **Learn at sanctuaries.** Step on a glowing shrine to choose one of three
   new spells, then solve a themed chess puzzle to master it.
5. **Death ends the run** - but tactics you solve on the first try are
   remembered forever and can be learned without the trial next time.

## Features

- **Turn-based tactical combat** on a procedurally generated grid with walls,
  pillars, rubble, sanctuaries and stairs.
- **Chess-piece enemies** with predictable patterns: pawns march forward,
  rooks sweep ranks and files, bishops hold diagonals, knights leap in an L,
  and the king strikes in all eight directions. Red cells show every threat.
- **Line of sight and cover** - walls and pillars block sight and movement;
  rubble blocks movement but not sight.
- **Seven spells** with clear rules (range, area, cooldown, line of sight):
  - **Arcane Bolt** - straight-line projectile.
  - **Blink** - teleport to a visible cell.
  - **Arcane Blast** - area explosion.
  - **Aegis** - absorb the next hit.
  - **Phase Lance** - bolt that ignores walls.
  - **Ricochet** - bolt that bounces off the first wall.
  - **Dominate** - turn an enemy into a temporary ally.
- **Sanctuary puzzles** - each spell is taught by a themed chess tactic
  (open file, long diagonal, fork, pin, smothered mate...). Solve it to learn
  the spell; a wrong move resets the trial and costs a little life.
- **Roguelike progression** - fresh layouts each run, growing difficulty,
  persistent meta-progression of mastered tactics.
- **Clean dark-fantasy UI** - reachable cells, spell targets, threatened cells,
  HP, cooldowns, turn counter and a combat chronicle.

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

| Action            | Input                                      |
| ----------------- | ------------------------------------------ |
| Move              | Click a highlighted reachable cell         |
| Select a spell    | Click its card or press `1`-`9`            |
| Cast a spell      | With a spell ready, click a highlighted target |
| End turn          | `Space` or the **End Turn** button         |
| Back to move mode | `Tab` or right click                       |
| Abandon run       | `Esc` or the back button                   |

## Spells and their teaching puzzles

Each spell is tied to a chess tactic. At a sanctuary you pick one of three
offered spells and must solve its puzzle to learn it.

| Spell        | Tactic theme        | Puzzle              |
| ------------ | ------------------- | ------------------- |
| Arcane Bolt  | The open file       | `t_line`            |
| Blink        | The quiet step      | `t_reposition`      |
| Arcane Blast | The long diagonal   | `t_area`            |
| Aegis        | The fortress        | `t_defence`         |
| Phase Lance  | The leaping knight  | `t_pierce`          |
| Ricochet     | The discovered line | `t_reflect`         |
| Dominate     | The pin             | `t_charm`           |

## Project layout

```
main.py                     entry point
chessrpg/
  config.py                 window, layout and tuning constants
  theme.py                  palette, fonts, drawing helpers
  assets.py                 standard glyph pieces + art-token extraction
  ui.py                     buttons, labels, bars, tooltips
  board.py                  chess board renderer (used by the sanctuary)
  combat.py                 battlefield, spells, LOS, enemy AI, turn loop
  run.py                    level generation + roguelike run state
  puzzles.py                puzzle library + themed sanctuary puzzles
  scene.py                  scene base class + fade transitions
  rpg.py                    hero stats, tactics and save profile
  game.py                   window, main loop, scene wiring
  scenes/
    menu.py                 main menu
    combat_scene.py         battlefield, HUD, spell bar, turn flow
    sanctuary_scene.py      spell choice + chess puzzle
    hero_scene.py           character sheet and mastered tactics
    help_scene.py           how to play
tools/
  smoke_test.py             headless test of rules, generation and scenes
  verify_puzzles.py         prints each puzzle's solution in SAN
  screenshots.py            renders each scene to tools/shots/*.png
```

## Adding a spell

1. Add a `Spell` to `SPELL_LIBRARY` in `chessrpg/combat.py`.
2. Add its tactical theme to `SPELL_THEME` and a `Puzzle` to `THEMED_PUZZLES`
   in `chessrpg/puzzles.py`.
3. Handle its `SpellKind` in `cast_spell` and `_target_ok` (combat scene).

## Testing

```bash
python tools/smoke_test.py     # rules, generation, run flow and every scene
python tools/screenshots.py    # writes PNGs of each scene to tools/shots/
```

The smoke test checks that every spell has a valid teaching puzzle, that the
combat rules (bolt, pierce, blast, teleport, shield, charm, threat map) behave
correctly, that generated levels are solvable with a reachable sanctuary, that
the run flow carries spells across descents, and that every scene renders.
