"""Global configuration: window, layout, timing and paths."""

from __future__ import annotations

import os

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART_DIR = os.path.join(ROOT_DIR, "art")
DATA_DIR = os.path.join(ROOT_DIR, "data")
SAVE_DIR = os.path.join(ROOT_DIR, "saves")
SAVE_FILE = os.path.join(SAVE_DIR, "profile.json")

# --------------------------------------------------------------------------
# Window
# --------------------------------------------------------------------------
TITLE = "Chess RPG - Tactical Trials"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60

# --------------------------------------------------------------------------
# Board layout
# --------------------------------------------------------------------------
BOARD_SQUARES = 8
BOARD_PIXELS = 576                      # 8 * 72
SQUARE_SIZE = BOARD_PIXELS // BOARD_SQUARES
BOARD_MARGIN = 24

# --------------------------------------------------------------------------
# Gameplay tuning
# --------------------------------------------------------------------------
HINT_COST = 25                          # gold spent per hint
MOVE_ANIM_MS = 140                      # piece slide duration
FLASH_MS = 420                          # capture / error flash duration
