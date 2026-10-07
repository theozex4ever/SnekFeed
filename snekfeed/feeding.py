"""Pygame-free ownership of outstanding snacks and their meal credit."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Literal

from . import config as C
from .state import SNACKS_BY_KEY, GameState

Denial = Literal["outstanding_cap", "locked", "tummy_full", "insufficient_hearts"]


@dataclass(frozen=True)
class OutstandingSnack:
    id: int
    key: str
    source: Literal["manual", "bowl", "feast"] = "manual"
    ordinal: int = 0
    phase: Literal["falling", "waiting", "claimed"] = "falling"
    chew_seconds: float = 0.0

    @property
    def bite(self) -> float:
        return min(1.0, self.chew_seconds / 0.45)


@dataclass(frozen=True)
class PurchaseResult:
    snack_id: int | None
    denial: Denial | None


@dataclass(frozen=True)
class SnackEligibility:
    denial: Denial | None

    @property
    def allowed(self) -> bool:
        return self.denial is None


@dataclass(frozen=True)
class MealCredit:
    snack_id: int
    key: str
    levels_gained: int


class Feeding:
    def __init__(self, state: GameState) -> None:
        self._state = state
        self._snacks: dict[int, OutstandingSnack] = {}
        self._next_id = 0
        self._claimed_id: int | None = None

    @property
    def snacks(self) -> tuple[OutstandingSnack, ...]:
        return tuple(self._snacks.values())

    def eligibility(self, key: str) -> SnackEligibility:
        snack = SNACKS_BY_KEY[key]  # Validate before checking mutable state.
        if len(self._snacks) >= C.MAX_SNACKS_ON_FLOOR:
            return SnackEligibility("outstanding_cap")
        if not self._state.snack_unlocked(key):
            return SnackEligibility("locked")
        if not self._state.has_room(self._reserved_fill()):
            return SnackEligibility("tummy_full")
        if self._state.hearts < snack.cost:
            return SnackEligibility("insufficient_hearts")
        return SnackEligibility(None)

    def buy(self, key: str) -> PurchaseResult:
        eligibility = self.eligibility(key)
        if not eligibility.allowed:
            return PurchaseResult(None, eligibility.denial)
        self._state.buy_snack(key, self._reserved_fill())
        return PurchaseResult(self._offer(key, "manual"), None)

    def feast(self) -> tuple[int, ...]:
        key = self._state.best_snack()
        return tuple(self._offer(key, "feast", ordinal) for ordinal in range(3))

    def shed(self) -> int:
        gain = self._state.shed()
        if gain:
            self._snacks.clear()
            self._claimed_id = None
        return gain

    def _offer(self, key: str, source: Literal["manual", "bowl", "feast"], ordinal: int = 0) -> int:
        snack_id = self._next_id
        self._next_id += 1
        self._snacks[snack_id] = OutstandingSnack(snack_id, key, source, ordinal)
        return snack_id

    def _reserved_fill(self) -> float:
        return sum(SNACKS_BY_KEY[snack.key].fill for snack in self._snacks.values())

    def claim(self, snack_id: int) -> bool:
        snack = self._snacks.get(snack_id)
        if snack is None or snack.phase != "waiting" or self._claimed_id is not None:
            return False
        self._snacks[snack_id] = replace(snack, phase="claimed")
        self._claimed_id = snack_id
        return True

    def advance(self, dt: float, landed_ids: Iterable[int] = ()) -> tuple[MealCredit, ...]:
        if not math.isfinite(dt) or dt < 0:
            raise ValueError("elapsed time must be finite and nonnegative")
        for snack_id in landed_ids:
            snack = self._snacks.get(snack_id)
            if snack is not None and snack.phase == "falling":
                self._snacks[snack_id] = replace(snack, phase="waiting")

        # Check before credit, so a finished meal can be replaced next frame.
        if not self._snacks:
            key = self._state.auto_bowl_pick(0)
            if key is not None:
                self._offer(key, "bowl")

        if self._claimed_id is None:
            return ()
        snack = self._snacks[self._claimed_id]
        snack = replace(snack, chew_seconds=snack.chew_seconds + dt)
        if snack.chew_seconds < 0.5:
            self._snacks[snack.id] = snack
            return ()
        levels = self._state.eat(snack.key)
        del self._snacks[snack.id]
        self._claimed_id = None
        return (MealCredit(snack.id, snack.key, levels),)
