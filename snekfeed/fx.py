"""Juice: floating hearts, sparkles, crumbs, zZz and popup numbers."""

from __future__ import annotations

import math
import random

from . import config as C
from . import draw as D


class Particle:
    __slots__ = ("kind", "x", "y", "vx", "vy", "life", "max_life", "size", "color", "text", "phase")

    def __init__(self, kind, x, y, vx, vy, life, size, color, text=""):
        self.kind, self.x, self.y, self.vx, self.vy = kind, x, y, vx, vy
        self.life = self.max_life = life
        self.size, self.color, self.text = size, color, text
        self.phase = random.random() * math.tau


class FX:
    def __init__(self) -> None:
        self.items: list[Particle] = []

    def hearts(self, x, y, n=4, color=C.PINK) -> None:
        for _ in range(n):
            self.items.append(Particle("heart", x + random.uniform(-12, 12), y + random.uniform(-6, 6),
                                       random.uniform(-30, 30), random.uniform(-90, -50),
                                       random.uniform(0.8, 1.3), random.uniform(10, 18), color))

    def sparkles(self, x, y, n=8, color=C.BUTTER, spread=40) -> None:
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(20, spread * 2.5)
            self.items.append(Particle("spark", x, y, math.cos(a) * sp, math.sin(a) * sp,
                                       random.uniform(0.5, 1.0), random.uniform(4, 8), color))

    def crumbs(self, x, y, color, n=6) -> None:
        for _ in range(n):
            self.items.append(Particle("crumb", x, y, random.uniform(-70, 70), random.uniform(-120, -40),
                                       random.uniform(0.4, 0.7), random.uniform(2, 4), color))

    def popup(self, x, y, s, color=C.PINK_DEEP, size=22) -> None:
        self.items.append(Particle("text", x, y, random.uniform(-8, 8), -55, 1.1, size, color, s))

    def zzz(self, x, y) -> None:
        self.items.append(Particle("z", x, y, 14, -22, 2.2, 14, C.LILAC_DEEP, "z"))

    def update(self, dt: float) -> None:
        for p in self.items:
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.kind == "crumb":
                p.vy += 420 * dt
            elif p.kind == "spark":
                p.vx *= 1 - 3 * dt
                p.vy *= 1 - 3 * dt
            elif p.kind == "heart":
                p.x += math.sin(p.life * 6 + p.phase) * 20 * dt
        self.items = [p for p in self.items if p.life > 0]

    def draw(self, surf) -> None:
        for p in self.items:
            k = p.life / p.max_life
            if p.kind == "heart":
                s = p.size * (0.6 + 0.4 * min(1.0, (1 - k) * 5))
                D.heart(surf, D.mix(C.WHITE, p.color, min(1.0, k * 1.6)), (p.x, p.y), s)
            elif p.kind == "spark":
                D.star(surf, D.mix(C.WHITE, p.color, k), (p.x, p.y), p.size * (0.4 + k), points=4,
                       rot=p.life * 4)
            elif p.kind == "crumb":
                D.circle(surf, p.color, (p.x, p.y), p.size * k + 0.5)
            elif p.kind in ("text", "z"):
                alpha = int(255 * min(1.0, k * 2))
                size = p.size + (6 if p.kind == "z" and k < 0.5 else 0)
                D.text(surf, p.text, (p.x + 1, p.y + 2), size, C.WHITE, True, "center", alpha)
                D.text(surf, p.text, (p.x, p.y), size, p.color, True, "center", alpha)
