"""RPG progression layer: hero stats, XP, gold and persistent profile."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict

from . import config


@dataclass
class Hero:
    """The player's champion. Stats grow as puzzles are solved."""

    name: str = "Aria"
    title: str = "Squire of the Board"
    level: int = 1
    xp: int = 0
    gold: int = 120
    rating: int = 800

    # Combat stats (flavour + future mechanics)
    tactics: int = 5
    focus: int = 5
    resolve: int = 5

    # Progress
    solved: list = field(default_factory=list)   # puzzle ids
    unlocked: list = field(default_factory=lambda: ["p1"])

    # Roguelike meta-progression: spells whose chess tactic was solved on the
    # first try. These can be learned without the trial in future runs.
    learned_tactics: list = field(default_factory=list)
    best_depth: int = 0
    runs: int = 0

    @property
    def xp_to_next(self) -> int:
        return 100 + (self.level - 1) * 60

    @property
    def xp_ratio(self) -> float:
        return min(1.0, self.xp / self.xp_to_next)

    def gain_xp(self, amount: int) -> bool:
        """Add XP, returning True if the hero levelled up."""
        self.xp += amount
        levelled = False
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.tactics += 1
            self.focus += 1
            self.resolve += 1
            self.rating += 40
            levelled = True
        return levelled

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Hero":
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


class Profile:
    """Loads / saves the hero and settings to disk."""

    def __init__(self) -> None:
        self.hero = Hero()
        self.settings = {"sound": True, "show_hints": True, "art_set": "class"}

    def load(self) -> None:
        if not os.path.exists(config.SAVE_FILE):
            return
        try:
            with open(config.SAVE_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self.hero = Hero.from_dict(data.get("hero", {}))
            self.settings.update(data.get("settings", {}))
        except (OSError, ValueError, TypeError):
            # Corrupt save: start fresh rather than crash.
            self.hero = Hero()

    def save(self) -> None:
        os.makedirs(config.SAVE_DIR, exist_ok=True)
        payload = {"hero": self.hero.to_dict(), "settings": self.settings}
        try:
            with open(config.SAVE_FILE, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, indent=2)
        except OSError:
            pass

    def reset(self) -> None:
        self.hero = Hero()
        self.save()
