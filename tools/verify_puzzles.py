import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chess
from chessrpg.puzzles import PUZZLES, THEMED_PUZZLES

def show(p):
    b = chess.Board(p.fen)
    print(f"--- {p.id} {p.name}  turn={'white' if b.turn else 'black'}")
    ok = True
    for i, uci in enumerate(p.solution):
        mv = chess.Move.from_uci(uci)
        if mv not in b.legal_moves:
            print(f"    ILLEGAL step {i}: {uci}  (legal: {[m.uci() for m in b.legal_moves][:12]})")
            ok = False
            break
        san = b.san(mv)
        b.push(mv)
        print(f"    {i}: {uci} = {san}")
    if ok:
        print(f"    final: check={b.is_check()} mate={b.is_checkmate()} over={b.is_game_over()}")

print("=== Campaign puzzles ===")
for p in PUZZLES:
    show(p)

print("\n=== Sanctuary (themed) puzzles ===")
for key, p in THEMED_PUZZLES.items():
    print(f"[theme: {key}]")
    show(p)
