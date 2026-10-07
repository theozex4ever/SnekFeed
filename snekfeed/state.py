"""Snek's game state and every economy rule.

This module has no pygame dependency so the numbers can be unit tested
and balanced headlessly.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field

from . import config as C

SNACKS_BY_KEY = {s.key: s for s in C.SNACKS}
DECOR_BY_KEY = {d.key: d for d in C.DECOR}
CARE_BY_KEY = {c.key: c for c in C.CARE}
SAVE_VERSION = 1


def xp_needed(level: int) -> float:
    return C.XP_BASE * C.XP_GROWTH ** (level - 1)


@dataclass
class GameState:
    hearts: float = 0.0
    run_hearts: float = 0.0  # earned since the last shed
    lifetime_hearts: float = 0.0
    level: int = 1
    xp: float = 0.0
    tummy: float = 35.0
    mood: float = 60.0
    decor: dict = field(default_factory=lambda: {d.key: 0 for d in C.DECOR})
    care: dict = field(default_factory=lambda: {c.key: 0 for c in C.CARE})
    scales: int = 0
    sheds: int = 0
    skin: str = "mint"
    frenzy_left: float = 0.0
    bowl_timer: float = 0.0
    pets: int = 0
    snacks_eaten: int = 0
    saved_at: float = field(default_factory=time.time)

    # ---- multipliers -------------------------------------------------------

    def level_mult(self) -> float:
        return 1.0 + C.LEVEL_BONUS * (self.level - 1)

    def scale_mult(self) -> float:
        return 1.0 + C.SCALE_BONUS * self.scales

    def mood_mult(self) -> float:
        """A happy Snek makes a cozier home: 1.0x when sulky, 1.5x when beaming."""
        return 1.0 + 0.5 * (self.mood / C.MOOD_MAX)

    def frenzy_mult(self) -> float:
        return C.FRENZY_MULT if self.frenzy_left > 0 else 1.0

    def mult(self, include_frenzy: bool = True) -> float:
        m = self.level_mult() * self.scale_mult() * self.mood_mult()
        return m * self.frenzy_mult() if include_frenzy else m

    # ---- income ------------------------------------------------------------

    def base_rate(self) -> float:
        return sum(DECOR_BY_KEY[k].rate * n for k, n in self.decor.items())

    def passive_rate(self, include_frenzy: bool = True) -> float:
        return self.base_rate() * self.mult(include_frenzy)

    def pet_value(self) -> float:
        # Pets stay relevant late game by also echoing 2% of idle income.
        base = 2 ** self.care["brush"] + 0.02 * self.base_rate()
        return base * self.mult()

    def earn(self, amount: float) -> None:
        self.hearts += amount
        self.run_hearts += amount
        self.lifetime_hearts += amount

    def pet(self) -> float:
        value = self.pet_value()
        self.earn(value)
        self.pets += 1
        self.mood = min(C.MOOD_MAX, self.mood + C.MOOD_PER_PET)
        return value

    # ---- tummy & mood -------------------------------------------------------

    def digest_rate(self) -> float:
        return C.DIGEST_PER_SEC * (1.0 + 0.3 * self.care["rub"])

    def mood_decay(self) -> float:
        return C.MOOD_DECAY_PER_SEC * 0.75 ** self.care["song"]

    def is_peckish(self) -> bool:
        return self.tummy < C.PECKISH_AT

    def has_room(self, pending_fill: float = 0.0) -> bool:
        return self.tummy + pending_fill < C.TUMMY_MAX

    def tick(self, dt: float) -> None:
        self.earn(self.passive_rate() * dt)
        self.tummy = max(0.0, self.tummy - self.digest_rate() * dt)
        self.mood = max(0.0, self.mood - self.mood_decay() * dt)
        self.frenzy_left = max(0.0, self.frenzy_left - dt)
        self.bowl_timer = max(0.0, self.bowl_timer - dt)

    # ---- snacks & growth ----------------------------------------------------

    def snack_unlocked(self, key: str) -> bool:
        return self.level >= SNACKS_BY_KEY[key].unlock_level

    def can_buy_snack(self, key: str, pending_fill: float = 0.0) -> bool:
        snack = SNACKS_BY_KEY[key]
        return (
            self.snack_unlocked(key)
            and self.hearts >= snack.cost
            and self.has_room(pending_fill)
        )

    def buy_snack(self, key: str, pending_fill: float = 0.0) -> bool:
        if not self.can_buy_snack(key, pending_fill):
            return False
        self.hearts -= SNACKS_BY_KEY[key].cost
        return True

    def eat(self, key: str) -> int:
        """Snek eats a snack. Returns how many levels were gained."""
        snack = SNACKS_BY_KEY[key]
        self.tummy = min(C.TUMMY_MAX, self.tummy + snack.fill)
        self.mood = min(C.MOOD_MAX, self.mood + C.MOOD_PER_SNACK)
        self.snacks_eaten += 1
        return self.gain_xp(snack.xp)

    def gain_xp(self, amount: float) -> int:
        self.xp += amount
        gained = 0
        while self.xp >= xp_needed(self.level):
            self.xp -= xp_needed(self.level)
            self.level += 1
            gained += 1
        return gained

    def unlocks_at(self, level: int) -> list[str]:
        names = [s.name for s in C.SNACKS if s.unlock_level == level]
        names += [d.name for d in C.DECOR if d.unlock_level == level]
        names += [c.name for c in C.CARE if c.unlock_level == level]
        if level == C.SHED_MIN_LEVEL:
            names.append("Shedding")
        return names

    # ---- decor ---------------------------------------------------------------

    def decor_unlocked(self, key: str) -> bool:
        return self.level >= DECOR_BY_KEY[key].unlock_level

    def decor_cost(self, key: str) -> float:
        return DECOR_BY_KEY[key].base_cost * C.DECOR_COST_GROWTH ** self.decor[key]

    def buy_decor(self, key: str) -> bool:
        cost = self.decor_cost(key)
        if not self.decor_unlocked(key) or self.hearts < cost:
            return False
        self.hearts -= cost
        self.decor[key] += 1
        return True

    # ---- care ----------------------------------------------------------------

    def care_unlocked(self, key: str) -> bool:
        return self.level >= CARE_BY_KEY[key].unlock_level

    def care_maxed(self, key: str) -> bool:
        return self.care[key] >= CARE_BY_KEY[key].max_level

    def care_cost(self, key: str) -> float:
        c = CARE_BY_KEY[key]
        return c.base_cost * c.cost_growth ** self.care[key]

    def buy_care(self, key: str) -> bool:
        cost = self.care_cost(key)
        if not self.care_unlocked(key) or self.care_maxed(key) or self.hearts < cost:
            return False
        self.hearts -= cost
        self.care[key] += 1
        return True

    def bowl_interval(self) -> float:
        return 24.0 / (1.0 + 0.5 * (self.care["bowl"] - 1))

    def auto_bowl_pick(self, pending_fill: float) -> str | None:
        """Pick the best snack the Auto Bowl should serve right now, if any.

        It only serves when Snek is peckish, nothing is waiting on the floor,
        and it never spends more than half the hearts in the bank.
        """
        if self.care["bowl"] == 0 or self.bowl_timer > 0 or pending_fill > 0:
            return None
        if not self.is_peckish():
            return None
        for snack in reversed(C.SNACKS):
            if self.snack_unlocked(snack.key) and snack.cost <= self.hearts * 0.5:
                self.hearts -= snack.cost
                self.bowl_timer = self.bowl_interval()
                return snack.key
        return None

    # ---- golden butterfly ---------------------------------------------------------

    def best_snack(self) -> str:
        return [s for s in C.SNACKS if self.snack_unlocked(s.key)][-1].key

    def butterfly_reward(self, rng: random.Random) -> tuple[str, float]:
        """Returns (kind, amount). kind is 'lucky', 'frenzy' or 'feast'."""
        roll = rng.random()
        if roll < 0.5 or self.base_rate() == 0:
            amount = 13 + max(
                10 * self.pet_value(),
                min(self.hearts * 0.15, self.passive_rate(False) * 900),
            )
            self.earn(amount)
            return "lucky", amount
        if roll < 0.8:
            self.frenzy_left = C.FRENZY_SECONDS
            return "frenzy", C.FRENZY_SECONDS
        return "feast", 0.0

    # ---- shedding (prestige) -------------------------------------------------------

    def shed_gain(self) -> int:
        if self.level < C.SHED_MIN_LEVEL:
            return 0
        return int((self.level - 10) ** 1.5)

    def next_skin(self) -> str:
        return C.SKINS[min(self.sheds, len(C.SKINS) - 1)].key

    def unlocked_skins(self) -> list[str]:
        return [s.key for s in C.SKINS[: self.sheds + 1]]

    def shed(self) -> int:
        gain = self.shed_gain()
        if gain == 0:
            return 0
        self.scales += gain
        self.sheds += 1
        self.skin = self.next_skin()
        self.hearts = 0.0
        self.run_hearts = 0.0
        self.level = 1
        self.xp = 0.0
        self.tummy = 35.0
        self.mood = 80.0
        self.decor = {d.key: 0 for d in C.DECOR}
        self.care = {c.key: 0 for c in C.CARE}
        self.frenzy_left = 0.0
        self.bowl_timer = 0.0
        return gain

    # ---- offline -------------------------------------------------------------------

    def apply_offline(self, now: float | None = None) -> tuple[float, float]:
        """Credit time spent away. Returns (seconds_away, hearts_earned)."""
        now = time.time() if now is None else now
        away = max(0.0, now - self.saved_at)
        credited = min(away, C.OFFLINE_CAP_SECONDS)
        earned = self.passive_rate(False) * credited * C.OFFLINE_EFFICIENCY
        self.earn(earned)
        self.tummy = max(0.0, self.tummy - self.digest_rate() * credited)
        # Snek misses you, but never drops below "a little lonely".
        self.mood = max(min(self.mood, 25.0), self.mood - self.mood_decay() * credited)
        self.frenzy_left = 0.0
        self.saved_at = now
        return away, earned

    # ---- persistence -----------------------------------------------------------------

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["version"] = SAVE_VERSION
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "GameState":
        state = cls()
        for key, value in data.items():
            if key in ("decor", "care"):
                getattr(state, key).update(
                    {k: int(v) for k, v in value.items() if k in getattr(state, key)}
                )
            elif hasattr(state, key):
                setattr(state, key, value)
        if state.skin not in state.unlocked_skins():
            state.skin = "mint"
        return state


def default_save_path() -> str:
    if sys.platform == "win32":
        root = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        root = os.path.expanduser("~/Library/Application Support")
    else:
        root = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
    return os.path.join(root, "snekfeed", "save.json")


def save(state: GameState, path: str) -> None:
    state.saved_at = time.time()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=1)
    os.replace(tmp, path)


def load(path: str) -> GameState | None:
    try:
        with open(path, encoding="utf-8") as f:
            return GameState.from_dict(json.load(f))
    except (OSError, ValueError, TypeError):
        return None


def fmt(n: float) -> str:
    """Short, friendly number formatting: 999, 1.23K, 45.6M ..."""
    if n < 1000:
        return f"{n:.1f}" if 0 < n < 10 and n != int(n) else f"{int(n):,}"
    suffixes = ["K", "M", "B", "T", "Qa", "Qi", "Sx", "Sp", "Oc", "No", "Dc"]
    exp = min(int(math.log10(n) // 3), len(suffixes))
    value = n / 1000**exp
    digits = 2 if value < 10 else 1 if value < 100 else 0
    return f"{value:.{digits}f}{suffixes[exp - 1]}"
