"""Tactical puzzle definitions and validation.

A puzzle is a FEN position plus a sequence of moves the player must find.
The player always plays the side to move; the opponent's replies are
scripted, so a puzzle is a deterministic "find the line" challenge.

Puzzle fields
-------------
id          unique key, also used for save progress
name        display name
fen         starting position
solution    list of UCI moves, player and opponent alternating
goal        "mate" | "win" | "draw" | "promote"
difficulty  1..5 stars
xp, gold    rewards
briefing    flavour text shown before the puzzle
hint        a nudge shown when the player asks for help
chapter     grouping for the level select map
"""

from __future__ import annotations

from dataclasses import dataclass

import chess


@dataclass
class Puzzle:
    id: str
    name: str
    fen: str
    solution: list[str]
    goal: str = "mate"
    difficulty: int = 1
    xp: int = 40
    gold: int = 20
    briefing: str = ""
    hint: str = ""
    chapter: str = "Prologue"

    @property
    def board(self) -> chess.Board:
        return chess.Board(self.fen)

    @property
    def player_color(self) -> chess.Color:
        return self.board.turn

    @property
    def player_moves(self) -> list[str]:
        """Solution moves the player must play (even indices)."""
        return self.solution[0::2]

    @property
    def stars(self) -> str:
        return "*" * self.difficulty + "." * (5 - self.difficulty)


# --------------------------------------------------------------------------
# Puzzle library
# --------------------------------------------------------------------------
PUZZLES: list[Puzzle] = [
    Puzzle(
        id="p1",
        name="First Blood",
        fen="6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1",
        solution=["a1a8"],
        goal="mate",
        difficulty=1,
        xp=40,
        gold=25,
        chapter="Prologue",
        briefing="The enemy king hides behind his pawns. Your rook sees the "
                 "back rank - deliver the blow.",
        hint="The back rank is undefended. Slide the rook all the way up.",
    ),
    Puzzle(
        id="p2",
        name="The Fork",
        fen="r3k2r/ppp2ppp/8/3N4/8/8/PPP2PPP/R3K2R w KQkq - 0 1",
        solution=["d5c7", "e8d7", "c7a8"],
        goal="win",
        difficulty=2,
        xp=60,
        gold=35,
        chapter="Prologue",
        briefing="A knight in the centre can touch everything. Find the "
                 "square where it attacks king and rook at once.",
        hint="Look for a square that checks the king and hits a rook.",
    ),
    Puzzle(
        id="p3",
        name="Back Rank Execution",
        fen="6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
        solution=["d1d8"],
        goal="mate",
        difficulty=1,
        xp=45,
        gold=25,
        chapter="Prologue",
        briefing="The black king's own pawns are his prison. Punish him.",
        hint="The eighth rank is empty. One move ends it.",
    ),
    Puzzle(
        id="p4",
        name="Smothered Mate",
        fen="6rk/6pp/8/6N1/8/8/8/6K1 w - - 0 1",
        solution=["g5f7"],
        goal="mate",
        difficulty=3,
        xp=90,
        gold=50,
        chapter="Chapter I - The Knight's Path",
        briefing="The king is buried alive by his own pieces. A knight can "
                 "reach where nothing else can.",
        hint="A knight check the king cannot escape - and no piece can take it.",
    ),
    Puzzle(
        id="p5",
        name="The Pawn Fork",
        fen="r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R b KQkq - 0 1",
        solution=["f6e4", "c3e4", "d7d5"],
        goal="win",
        difficulty=3,
        xp=80,
        gold=45,
        chapter="Chapter I - The Knight's Path",
        briefing="You are Black. Trade on e4 to draw the white knight out, "
                 "then find the pawn thrust that attacks two pieces at once.",
        hint="After Nxe4 Nxe4, a single pawn move hits both the knight and bishop.",
    ),
    Puzzle(
        id="p6",
        name="Promotion Race",
        fen="8/P6k/8/8/8/8/6K1/8 w - - 0 1",
        solution=["a7a8q"],
        goal="promote",
        difficulty=1,
        xp=40,
        gold=20,
        chapter="Chapter I - The Knight's Path",
        briefing="A lone pawn stands one step from glory. Push it home.",
        hint="Advance the pawn to the eighth rank.",
    ),
    Puzzle(
        id="p7",
        name="Double Attack",
        fen="2r3k1/5ppp/8/8/8/8/5PPP/2R3K1 w - - 0 1",
        solution=["c1c8"],
        goal="win",
        difficulty=2,
        xp=65,
        gold=35,
        chapter="Chapter II - The Rook's Gambit",
        briefing="Rooks love open files. Trade into a winning endgame.",
        hint="Capture on the eighth rank.",
    ),
    Puzzle(
        id="p8",
        name="The Pin",
        fen="r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 1",
        solution=["c4f7", "e8f7", "f3g5"],
        goal="win",
        difficulty=4,
        xp=120,
        gold=70,
        chapter="Chapter II - The Rook's Gambit",
        briefing="A sacrifice on f7 drags the king out. Follow up with "
                 "precision - the fork must land on the queen.",
        hint="Sacrifice the bishop on f7, then find the knight check that "
             "also attacks the queen on d8.",
    ),
]


# --------------------------------------------------------------------------
# Sanctuary puzzles: one per tactical theme, used to unlock spells.
#
# Each spell is tied to a chess tactic. When the mage reaches a sanctuary the
# game offers three spells; the player picks one and must solve its themed
# puzzle to learn it. Solving it on the first try permanently records the
# tactic in the profile so future runs can learn that spell without the test.
# --------------------------------------------------------------------------

THEMED_PUZZLES: dict[str, Puzzle] = {
    # Straight-line attack -> the rook's open file.
    "line": Puzzle(
        id="t_line", name="The Open File",
        fen="6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1",
        solution=["a1a8"], goal="mate", difficulty=1,
        briefing="A rook owns the file it stands on. Clear the back rank.",
        hint="Slide the rook to the eighth rank - the king has no escape.",
    ),
    # Repositioning -> the king's quiet step.
    "reposition": Puzzle(
        id="t_reposition", name="The Quiet Step",
        fen="8/8/8/4k3/8/8/4P3/4K3 w - - 0 1",
        solution=["e1d2"], goal="win", difficulty=1,
        briefing="Sometimes the best move is a small step to a better square.",
        hint="Step the king toward the centre to support the pawn.",
    ),
    # Area control -> the bishop's diagonal sweep.
    "area": Puzzle(
        id="t_area", name="The Long Diagonal",
        fen="6k1/5ppp/8/8/8/8/5PPP/2B3K1 w - - 0 1",
        solution=["c1a3"], goal="win", difficulty=2,
        briefing="A bishop commands a whole diagonal. Find the active square.",
        hint="Swing the bishop to a3 to eye the long diagonal.",
    ),
    # Defence -> the shield of a solid structure.
    "defence": Puzzle(
        id="t_defence", name="The Fortress",
        fen="6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
        solution=["d1d8"], goal="mate", difficulty=1,
        briefing="A solid back rank is a shield. Break through it.",
        hint="The eighth rank is empty - deliver the back-rank mate.",
    ),
    # Piercing -> the knight leaps over everything.
    "pierce": Puzzle(
        id="t_pierce", name="The Leaping Knight",
        fen="6rk/6pp/8/6N1/8/8/8/6K1 w - - 0 1",
        solution=["g5f7"], goal="mate", difficulty=3,
        briefing="A knight ignores the pieces in its way. Leap to the kill.",
        hint="A knight check the king cannot escape - and nothing can take it.",
    ),
    # Reflection -> the discovered attack.
    "reflect": Puzzle(
        id="t_reflect", name="The Discovered Line",
        fen="r3k2r/ppp2ppp/8/3N4/8/8/PPP2PPP/R3K2R w KQkq - 0 1",
        solution=["d5c7", "e8d7", "c7a8"], goal="win", difficulty=2,
        briefing="A fork bounces your attack between two targets at once.",
        hint="Find the square where the knight checks the king and hits a rook.",
    ),
    # Domination -> the pin that freezes a piece.
    "charm": Puzzle(
        id="t_charm", name="The Pin",
        fen="r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 1",
        solution=["c4f7", "e8f7", "f3g5"], goal="win", difficulty=4,
        briefing="A pinned piece cannot move. Sacrifice to drag the king out.",
        hint="Sacrifice the bishop on f7, then fork king and queen with the knight.",
    ),
    # -- chess-tactic spells -------------------------------------------
    # Open Lines -> clearing a file for the rook.
    "open_lines": Puzzle(
        id="t_open_lines", name="The Cleared File",
        fen="6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1",
        solution=["a1a8"], goal="mate", difficulty=1,
        briefing="Open a line and the rook pours through it.",
        hint="The a-file is clear - slide the rook to the eighth rank.",
    ),
    # Pawn Break -> a pawn thrust that cracks the structure.
    "pawn_break": Puzzle(
        id="t_pawn_break", name="The Pawn Break",
        fen="8/P6k/8/8/8/8/6K1/8 w - - 0 1",
        solution=["a7a8q"], goal="promote", difficulty=1,
        briefing="A pawn break smashes a hole in the defence. Push through.",
        hint="March the pawn to the eighth rank and promote.",
    ),
    # Windmill -> a rook sweeping rank and file.
    "windmill": Puzzle(
        id="t_windmill", name="The Windmill",
        fen="6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
        solution=["d1d8"], goal="mate", difficulty=1,
        briefing="A windmill sweeps the whole rank and file. Let it spin.",
        hint="The eighth rank is empty - the rook sweeps to d8.",
    ),
    # Fork -> one move hitting two targets.
    "fork": Puzzle(
        id="t_fork", name="The Fork",
        fen="r3k2r/ppp2ppp/8/3N4/8/8/PPP2PPP/R3K2R w KQkq - 0 1",
        solution=["d5c7", "e8d7", "c7a8"], goal="win", difficulty=2,
        briefing="A fork attacks two pieces at once. Find the square.",
        hint="A knight move that checks the king and hits a rook.",
    ),
    # Sacrifice -> giving material for a greater gain.
    "sacrifice": Puzzle(
        id="t_sacrifice", name="The Sacrifice",
        fen="r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 1",
        solution=["c4f7", "e8f7", "f3g5"], goal="win", difficulty=4,
        briefing="Give material to gain something greater. Sacrifice on f7.",
        hint="Sacrifice the bishop on f7, then fork king and queen.",
    ),
    # Stalemate -> escaping to safety.
    "escape": Puzzle(
        id="t_escape", name="The Escape",
        fen="8/8/8/4k3/8/8/4P3/4K3 w - - 0 1",
        solution=["e1d2"], goal="win", difficulty=1,
        briefing="When danger closes in, slip to a safer square.",
        hint="Step the king toward the centre, away from the edge.",
    ),
    # Deflection -> driving a piece away.
    "deflection": Puzzle(
        id="t_deflection", name="The Deflection",
        fen="6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1",
        solution=["a1a8"], goal="mate", difficulty=1,
        briefing="Deflect the defender and the back rank falls.",
        hint="The back rank is undefended - the rook delivers mate.",
    ),
    # Discovered attack -> a hidden line revealed.
    "discovered": Puzzle(
        id="t_discovered", name="The Discovered Attack",
        fen="r3k2r/ppp2ppp/8/3N4/8/8/PPP2PPP/R3K2R w KQkq - 0 1",
        solution=["d5c7", "e8d7", "c7a8"], goal="win", difficulty=2,
        briefing="Move one piece and reveal the attack of another.",
        hint="The knight uncovers the line - check the king and hit a rook.",
    ),
    # Pin -> freezing a piece in place.
    "pin": Puzzle(
        id="t_pin", name="The Pin",
        fen="r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 0 1",
        solution=["c4f7", "e8f7", "f3g5"], goal="win", difficulty=4,
        briefing="A pinned piece cannot move. Freeze it, then strike.",
        hint="Sacrifice on f7 to drag the king out, then fork with the knight.",
    ),
    # Trap -> a hidden mine waiting for the enemy.
    "trap": Puzzle(
        id="t_trap", name="The Trap",
        fen="6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
        solution=["d1d8"], goal="mate", difficulty=1,
        briefing="Set the trap and let the enemy walk into it.",
        hint="The back rank is a trap - the rook springs it on d8.",
    ),
    # Triangulation -> losing a tempo to gain an advantage.
    "tempo": Puzzle(
        id="t_tempo", name="The Triangulation",
        fen="8/8/8/4k3/8/8/4P3/4K3 w - - 0 1",
        solution=["e1d2"], goal="win", difficulty=1,
        briefing="Lose a tempo to gain a better position. A quiet step wins.",
        hint="Step the king toward the centre to support the pawn.",
    ),
    # Skewer -> striking the piece behind.
    "skewer": Puzzle(
        id="t_skewer", name="The Skewer",
        fen="6rk/6pp/8/6N1/8/8/8/6K1 w - - 0 1",
        solution=["g5f7"], goal="mate", difficulty=3,
        briefing="A skewer strikes the piece behind the first. Leap to the kill.",
        hint="A knight check the king cannot escape - nothing can take it.",
    ),
    # Interference -> cutting a line with a wall.
    "interference": Puzzle(
        id="t_interference", name="The Interference",
        fen="6k1/5ppp/8/8/8/8/5PPP/2B3K1 w - - 0 1",
        solution=["c1a3"], goal="win", difficulty=2,
        briefing="Cut the enemy's line of attack. Block the diagonal.",
        hint="Swing the bishop to a3 to control the long diagonal.",
    ),
    # Clearance -> moving a piece aside to free a square.
    "clearance": Puzzle(
        id="t_clearance", name="The Clearance",
        fen="8/8/8/4k3/8/8/4P3/4K3 w - - 0 1",
        solution=["e1d2"], goal="win", difficulty=1,
        briefing="Clear the square so another piece can use it.",
        hint="Step the king aside to free the e-file for the pawn.",
    ),
}

# Spell id -> tactical theme key.
SPELL_THEME = {
    "bolt": "line",
    "teleport": "reposition",
    "blast": "area",
    "shield": "defence",
    "pierce": "pierce",
    "reflect": "reflect",
    "charm": "charm",
    # -- chess-tactic spells -------------------------------------------
    "push": "open_lines",
    "break": "pawn_break",
    "cross": "windmill",
    "fork": "fork",
    "sacrifice": "sacrifice",
    "escape": "escape",
    "fear": "deflection",
    "discover": "discovered",
    "pin": "pin",
    "mine": "trap",
    "tempo": "tempo",
    "sniper": "skewer",
    "wall": "interference",
    "clearance": "clearance",
}


def themed_puzzle_for(spell_id: str) -> Puzzle | None:
    """Return the chess puzzle that teaches ``spell_id``."""
    theme = SPELL_THEME.get(spell_id)
    return THEMED_PUZZLES.get(theme) if theme else None


def get_puzzle(puzzle_id: str) -> Puzzle | None:
    for p in PUZZLES:
        if p.id == puzzle_id:
            return p
    for p in THEMED_PUZZLES.values():
        if p.id == puzzle_id:
            return p
    return None


def puzzles_in_chapter(chapter: str) -> list[Puzzle]:
    return [p for p in PUZZLES if p.chapter == chapter]


def chapters() -> list[str]:
    seen: list[str] = []
    for p in PUZZLES:
        if p.chapter not in seen:
            seen.append(p.chapter)
    return seen


class PuzzleSession:
    """Tracks progress through a single puzzle's solution line."""

    def __init__(self, puzzle: Puzzle) -> None:
        self.puzzle = puzzle
        self.board = puzzle.board
        self.step = 0
        self.mistakes = 0
        self.hints_used = 0
        self.solved = False
        self.failed = False
        self.history: list[chess.Move] = []

    # ------------------------------------------------------------------
    @property
    def expected_uci(self) -> str | None:
        if self.step < len(self.puzzle.solution):
            return self.puzzle.solution[self.step]
        return None

    @property
    def is_player_turn(self) -> bool:
        return self.step % 2 == 0 and not self.solved and not self.failed

    @property
    def progress(self) -> float:
        return self.step / max(1, len(self.puzzle.solution))

    # ------------------------------------------------------------------
    def try_move(self, move: chess.Move) -> str:
        """Attempt a player move.

        Returns one of: "correct", "wrong", "solved", "failed".
        """
        expected = self.expected_uci
        if expected is None:
            return "solved"

        if move.uci() != expected:
            self.mistakes += 1
            return "wrong"

        self.board.push(move)
        self.history.append(move)
        self.step += 1

        if self.step >= len(self.puzzle.solution):
            self.solved = True
            return "solved"

        # Scripted opponent reply
        reply = chess.Move.from_uci(self.puzzle.solution[self.step])
        self.board.push(reply)
        self.history.append(reply)
        self.step += 1

        if self.step >= len(self.puzzle.solution):
            self.solved = True
            return "solved"
        return "correct"

    def hint_move(self) -> chess.Move | None:
        expected = self.expected_uci
        if expected is None:
            return None
        self.hints_used += 1
        return chess.Move.from_uci(expected)

    def reset(self) -> None:
        self.board = self.puzzle.board
        self.step = 0
        self.mistakes = 0
        self.hints_used = 0
        self.solved = False
        self.failed = False
        self.history.clear()

    def score(self) -> tuple[int, int]:
        """Return (xp, gold) earned, reduced by mistakes and hints."""
        xp = self.puzzle.xp
        gold = self.puzzle.gold
        xp = max(10, xp - self.mistakes * 10 - self.hints_used * 5)
        gold = max(5, gold - self.mistakes * 5 - self.hints_used * 5)
        return xp, gold
