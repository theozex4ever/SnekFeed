"""The terrarium: background, decor layout, dropped snacks, the golden butterfly."""

from __future__ import annotations

import math
import random

import pygame
from pygame.math import Vector2

from . import art
from . import config as C
from . import draw as D

# How many of each decor are drawn (the rest still count, the home just looks full).
VISIBLE_CAP = {"pebble": 10, "fern": 9, "rock": 4, "mush": 5, "pond": 2, "house": 1}
DECOR_SIZE = {"pebble": 34, "fern": 48, "rock": 60, "mush": 46, "pond": 120, "house": 96}


class Food:
    def __init__(self, key: str, pos, drop_from: float = 160) -> None:
        self.key = key
        self.pos = Vector2(pos)
        self.drop = drop_from  # height above ground
        self.vy = 0.0
        self.landed = False
        self.bite = 0.0
        self.t = random.random() * 5

    def update(self, dt: float) -> bool:
        """Returns True on the frame it lands."""
        self.t += dt
        if self.landed:
            return False
        self.vy += 900 * dt
        self.drop -= self.vy * dt
        if self.drop <= 0:
            if self.vy > 220:
                self.drop, self.vy = 0.0, -self.vy * 0.35
                return False
            self.drop, self.landed = 0.0, True
            return True
        return False

    def draw(self, surf) -> None:
        bob = 0 if not self.landed else math.sin(self.t * 3) * 1.5
        k = max(0.0, 1 - self.drop / 200)
        D.shadow(surf, (self.pos.x, self.pos.y + 10), 13 * (0.5 + 0.5 * k), 5 * (0.5 + 0.5 * k), 35)
        art.snack(surf, self.key, (self.pos.x, self.pos.y - self.drop + bob), 32, self.bite)


class Butterfly:
    def __init__(self, area: pygame.Rect) -> None:
        self.area = area
        left = random.random() < 0.5
        self.pos = Vector2(area.left - 30 if left else area.right + 30, random.uniform(area.top + 60, area.bottom - 60))
        self.vel = Vector2(1 if left else -1, 0) * 60
        self.t = 0.0
        self.life = C.BUTTERFLY_LIFETIME
        self.wander = Vector2(area.center)

    def update(self, dt: float) -> None:
        self.t += dt
        self.life -= dt
        if random.random() < dt * 0.7:
            self.wander = Vector2(random.uniform(self.area.left + 60, self.area.right - 60),
                                  random.uniform(self.area.top + 60, self.area.bottom - 60))
        if self.life < 2.5:  # fly away
            self.wander = Vector2(self.pos.x + (1 if self.vel.x >= 0 else -1) * 400, self.area.top - 80)
        steer = (self.wander - self.pos)
        if steer.length() > 1:
            steer.scale_to_length(90)
        self.vel += (steer - self.vel) * min(1.0, dt * 1.2)
        self.pos += self.vel * dt
        self.pos.y += math.sin(self.t * 4) * 20 * dt

    @property
    def alive(self) -> bool:
        return self.life > 0

    def hit(self, p) -> bool:
        return self.pos.distance_to(p) < 34

    def draw(self, surf) -> None:
        art.butterfly(surf, (self.pos.x, self.pos.y), 38, self.t * 11, int(90 + 40 * math.sin(self.t * 5)))


class Habitat:
    def __init__(self) -> None:
        self.rect = pygame.Rect(C.HABITAT)
        self.inner = self.rect.inflate(-24, -24)
        self.bg = self._build_background()
        self.slots = self._build_slots()
        self.phases = {k: [random.random() * 6 for _ in v] for k, v in self.slots.items()}
        self.bowl_pos = Vector2(self.inner.right - 60, self.inner.bottom - 34)

    def _build_background(self) -> pygame.Surface:
        rng = random.Random(7)
        w, h = self.rect.size
        ground = pygame.Surface((w, h))
        ground.fill(C.GRASS)
        # Dappled light and shade: big soft radial blobs, no hard edges.
        for _ in range(16):
            D.glow(ground, C.GRASS_DARK, (rng.uniform(0, w), rng.uniform(0, h)), rng.uniform(70, 150), 160)
        for _ in range(10):
            D.glow(ground, (236, 250, 232), (rng.uniform(0, w), rng.uniform(0, h)), rng.uniform(60, 130), 140)
        for _ in range(60):
            x, y = rng.uniform(20, w - 20), rng.uniform(20, h - 20)
            for a in (-0.45, 0.0, 0.45):
                D.line(ground, (180, 222, 192), (x, y), (x + math.sin(a) * 7, y - 9))
        for _ in range(28):
            x, y = rng.uniform(30, w - 30), rng.uniform(30, h - 30)
            petal = rng.choice([(255, 255, 255), (255, 214, 226), (226, 214, 250), (255, 240, 190)])
            for i in range(5):
                a = i * math.tau / 5
                D.circle(ground, petal, (x + math.cos(a) * 3.5, y + math.sin(a) * 3.5), 3)
            D.circle(ground, (255, 220, 140), (x, y), 2.2)
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (255, 255, 255, 255), bg.get_rect(), border_radius=28)
        bg.blit(ground, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        pygame.draw.rect(bg, (195, 228, 205), bg.get_rect(), width=4, border_radius=28)
        return bg

    def _build_slots(self) -> dict:
        rng = random.Random(42)
        r = self.inner
        taken: list[tuple[Vector2, float]] = []
        fixed = {
            "house": [Vector2(r.left + 70, r.top + 110)],
            "pond": [Vector2(r.right - 120, r.top + 120), Vector2(r.left + 150, r.bottom - 40)],
        }
        slots: dict[str, list[Vector2]] = {}
        for key, pts in fixed.items():
            slots[key] = pts
            taken += [(p, DECOR_SIZE[key] * 0.55) for p in pts]
        bowl = Vector2(r.right - 60, r.bottom - 34)
        taken.append((bowl, 40))
        for key in ("rock", "mush", "fern", "pebble"):
            pts = []
            tries = 0
            while len(pts) < VISIBLE_CAP[key] and tries < 600:
                tries += 1
                p = Vector2(rng.uniform(r.left + 30, r.right - 30), rng.uniform(r.top + 50, r.bottom - 10))
                rad = DECOR_SIZE[key] * 0.55
                if all(p.distance_to(q) > rad + qr for q, qr in taken):
                    pts.append(p)
                    taken.append((p, rad))
            slots[key] = pts
        return slots

    def random_drop_point(self, avoid: Vector2) -> Vector2:
        r = self.inner.inflate(-60, -80)
        best = None
        for _ in range(10):
            p = Vector2(random.uniform(r.left, r.right), random.uniform(r.top + 30, r.bottom))
            if p.distance_to(avoid) > 140:
                return p
            best = p
        return best

    def draw_background(self, surf) -> None:
        D.panel(surf, self.rect, C.GRASS, 28, 5)
        surf.blit(self.bg, self.rect.topleft)

    def draw_decor(self, surf, counts: dict, t: float, has_bowl: bool) -> None:
        items = []
        for key, pts in self.slots.items():
            shown = min(counts.get(key, 0), len(pts))
            for i in range(shown):
                items.append((pts[i].y, key, pts[i], self.phases[key][i]))
        if has_bowl:
            items.append((self.bowl_pos.y, "bowl", self.bowl_pos, 0))
        for _, key, p, ph in sorted(items, key=lambda it: it[0]):
            if key == "bowl":
                art.bowl(surf, p, 54)
            else:
                art.decor(surf, key, p, DECOR_SIZE[key], t, ph)
