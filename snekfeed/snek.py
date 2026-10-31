"""Snek: movement, moods, and the (very important) cute rendering."""

from __future__ import annotations

import colorsys
import math
import random
from collections import deque

import pygame
from pygame.math import Vector2

from . import config as C
from . import draw as D
from .feeding import Feeding
from .habitat import Food

SKINS = {s.key: s for s in C.SKINS}


def target_length(level: int) -> int:
    return min(64, 10 + 2 * (level - 1))


def body_radius(level: int) -> float:
    return 15.0 + min(level, 30) * 0.4


class Snek:
    def __init__(self, area: pygame.Rect, level: int) -> None:
        self.area = area
        self.reset(level)

    def reset(self, level: int) -> None:
        self.level = level
        self.radius = body_radius(level)
        start = Vector2(self.area.centerx, self.area.centery + 40)
        self.heading = -0.3
        self.segments = [
            start - Vector2(math.cos(self.heading), math.sin(self.heading)) * i * self.spacing()
            for i in range(target_length(level))
        ]
        self.trail: deque[Vector2] = deque(Vector2(p) for p in self.segments)
        self.target = Vector2(start)
        self.state = "idle"  # idle | wander | seek | eat | sleep
        self.state_t = 1.5
        self.t = 0.0
        self.wiggle = 0.0
        self.happy_t = 0.0
        self.blink_t = 2.0
        self.tongue_t = 0.0
        self.tongue_cd = 3.0
        self.eat_t = 0.0
        self.food_id: int | None = None
        self.bulges: list[float] = []
        self.grow_cd = 0.0
        self.look = Vector2()
        self.zzz_cd = 0.0

    def spacing(self) -> float:
        return self.radius * 0.62

    @property
    def head(self) -> Vector2:
        return self.segments[0]

    def set_level(self, level: int) -> None:
        self.level = level
        self.radius = body_radius(level)

    # ---- interaction ----------------------------------------------------------------

    def hit(self, pos) -> bool:
        p = Vector2(pos)
        r = self.radius * 1.25
        return any(p.distance_squared_to(s) < r * r for s in [*self.segments[::2], self.head])

    def petted(self) -> None:
        self.happy_t = 0.9
        if self.state == "sleep":
            self.state, self.state_t = "idle", 1.0

    def swallow(self) -> None:
        self.bulges.append(0.0)

    # ---- update -----------------------------------------------------------------------

    def update(
        self, dt: float, foods: dict[int, Food], feeding: Feeding, tummy_full: bool, mouse, butterfly_pos
    ) -> None:
        """Advance movement and request claims; observe feeding's meal clock."""
        self.t += dt
        self.happy_t = max(0.0, self.happy_t - dt)
        self.state_t -= dt
        self._blink_and_tongue(dt)
        self._grow(dt)
        self.bulges = [b + dt * 9 for b in self.bulges if b < len(self.segments) + 4]

        # Eyes follow the cursor or the butterfly when nearby: tiny, but it sells "alive".
        look_at = butterfly_pos or mouse
        if look_at is not None and self.head.distance_to(look_at) < 260:
            d = Vector2(look_at) - self.head
            self.look = d.normalize() if d.length() > 1 else Vector2()
        else:
            self.look = Vector2(math.cos(self.heading), math.sin(self.heading))

        snacks = {snack.id: snack for snack in feeding.snacks}
        if self.state == "eat":
            meal = snacks.get(self.food_id) if self.food_id is not None else None
            if meal is None:
                self.food_id = None
                self.state, self.state_t = "idle", random.uniform(0.6, 1.4)
            else:
                self.eat_t = meal.chew_seconds
            self._follow()
            return

        live_foods = [
            (snack_id, foods[snack_id])
            for snack_id, snack in snacks.items()
            if snack.phase == "waiting" and snack_id in foods
        ]
        if live_foods and self.state != "eat":
            if self.state == "sleep" and tummy_full:
                pass  # food coma: the snack waits until Snek wakes up
            else:
                self.food_id, food = min(live_foods, key=lambda pair: self.head.distance_squared_to(pair[1].pos))
                self.state = "seek"
                self.target = Vector2(food.pos)

        if self.state == "seek":
            sought_food = foods.get(self.food_id) if self.food_id is not None else None
            snack = snacks.get(self.food_id) if self.food_id is not None else None
            if sought_food is None or snack is None or snack.phase != "waiting":
                self.state, self.state_t = "idle", 0.5
            elif self.head.distance_to(sought_food.pos) < self.radius * 1.4 + 6:
                if feeding.claim(snack.id):
                    self.state, self.eat_t = "eat", 0.0
            else:
                # Arrive steering: slow down and turn tighter near the snack so Snek never orbits it.
                dist = self.head.distance_to(sought_food.pos)
                k = max(0.4, min(1.0, dist / 90))
                self._move_towards(sought_food.pos, dt, speed=125 * k, turn=5.0 / k)
        elif self.state == "wander":
            self._move_towards(self.target, dt, speed=62, turn=2.6)
            if self.head.distance_to(self.target) < 18 or self.state_t <= 0:
                self.state, self.state_t = "idle", random.uniform(1.2, 3.5)
        elif self.state == "idle":
            if self.state_t <= 0:
                if tummy_full and random.random() < 0.55:
                    self.state, self.state_t = "sleep", random.uniform(8, 14)
                else:
                    self.state, self.state_t = "wander", 9.0
                    self.target = self._random_point()
        elif self.state == "sleep":
            self.zzz_cd -= dt
            if self.state_t <= 0:
                self.state, self.state_t = "idle", 1.0

        self._follow()

    def _random_point(self) -> Vector2:
        m = int(self.radius * 2.5)
        inner = self.area.inflate(-m * 2, -m * 2)
        for _ in range(8):
            p = Vector2(random.uniform(inner.left, inner.right), random.uniform(inner.top, inner.bottom))
            if p.distance_to(self.head) > 120:
                return p
        return p

    def _move_towards(self, target, dt, speed, turn) -> None:
        to = Vector2(target) - self.head
        desired = math.atan2(to.y, to.x)
        diff = (desired - self.heading + math.pi) % math.tau - math.pi
        self.heading += max(-turn * dt, min(turn * dt, diff))
        self.wiggle += dt * (speed / 11)
        move_angle = self.heading + math.sin(self.wiggle) * 0.55
        step = Vector2(math.cos(move_angle), math.sin(move_angle)) * speed * dt
        new_head = self.head + step
        m = self.radius * 1.3
        new_head.x = max(self.area.left + m, min(self.area.right - m, new_head.x))
        new_head.y = max(self.area.top + m, min(self.area.bottom - m, new_head.y))
        self.segments[0] = new_head

    def _follow(self) -> None:
        """Lay the body along the path the head actually travelled.

        Following the trail (rather than chaining each segment to the previous
        one) preserves the S-curves of the slither instead of pulling taut.
        """
        head = self.head
        if not self.trail or self.trail[0].distance_to(head) >= 1.5:
            self.trail.appendleft(Vector2(head))
        gap = self.spacing()
        n = len(self.segments)
        want, walked, prev, i = gap, 0.0, head, 1
        used = 0
        for p in self.trail:
            used += 1
            d = prev.distance_to(p)
            while i < n and d > 0 and walked + d >= want:
                # Rounding can push the ratio a hair past 1, which Vector2.lerp rejects.
                self.segments[i] = prev.lerp(p, min(1.0, (want - walked) / d))
                i += 1
                want += gap
            walked += d
            prev = p
            if i >= n:
                break
        for j in range(i, n):  # trail too short (fresh growth): chain behind
            delta = self.segments[j] - self.segments[j - 1]
            if delta.length() > gap:
                self.segments[j] = self.segments[j - 1] + delta * (gap / delta.length())
        while len(self.trail) > used + 40:
            self.trail.pop()

    def _grow(self, dt) -> None:
        self.grow_cd -= dt
        want = target_length(self.level)
        if self.grow_cd <= 0:
            if len(self.segments) < want:
                self.segments.append(Vector2(self.segments[-1]))
                self.grow_cd = 0.07
            elif len(self.segments) > want:
                self.segments.pop()
                self.grow_cd = 0.02

    def _blink_and_tongue(self, dt) -> None:
        self.blink_t -= dt
        if self.blink_t < -0.12:
            self.blink_t = random.uniform(2.0, 5.0)
        self.tongue_cd -= dt
        self.tongue_t = max(0.0, self.tongue_t - dt)
        if self.tongue_cd <= 0 and self.state in ("idle", "wander", "seek"):
            self.tongue_t = 0.35
            self.tongue_cd = random.uniform(2.5, 6.0)

    def wants_zzz(self) -> bool:
        if self.state == "sleep" and self.zzz_cd <= 0:
            self.zzz_cd = 0.9
            return True
        return False

    # ---- drawing -------------------------------------------------------------------------

    def _colors(self, skin_key: str, i: int, n: int):
        skin = SKINS.get(skin_key, SKINS["mint"])
        if skin.key == "rainbow":
            h = (i / max(1, n) * 0.85 + self.t * 0.05) % 1.0
            body = tuple(int(c * 255) for c in colorsys.hls_to_rgb(h, 0.8, 0.75))
            return body, skin.belly, D.darker(body, 0.88)
        return skin.body, skin.belly, skin.spots

    def draw(self, surf, skin_key: str) -> None:
        n = len(self.segments)
        R = self.radius
        radii = []
        for i in range(n):
            u = i / max(1, n - 1)
            r = R * (1.0 - 0.68 * u**2.2)
            for b in self.bulges:
                r *= 1.0 + 0.38 * math.exp(-((i - b) ** 2) / 3.0)
            radii.append(r)

        # Soft drop shadow under the whole body.
        for i in range(n - 1, -1, -3):
            D.shadow(surf, (self.segments[i].x + 3, self.segments[i].y + radii[i] * 0.7), radii[i], radii[i] * 0.45, 22)

        # Outline pass, then fill pass, then a glossy highlight stripe.
        for i in range(n - 1, 0, -1):
            body, _, _ = self._colors(skin_key, i, n)
            D.circle(surf, D.darker(body, 0.78), self.segments[i], radii[i] + 2)
        for i in range(n - 1, 0, -1):
            body, _, _ = self._colors(skin_key, i, n)
            D.circle(surf, body, self.segments[i], radii[i])
        for i in range(n - 1, 0, -1):
            body, belly, spots = self._colors(skin_key, i, n)
            p = self.segments[i]
            if i % 3 == 1 and i < n - 2:
                d = self.segments[i - 1] - self.segments[i + 1]
                side = Vector2(-d.y, d.x).normalize() if d.length() > 0.01 else Vector2(0, 1)
                side *= 1 if (i // 3) % 2 else -1
                D.circle(surf, spots, p + side * radii[i] * 0.42, radii[i] * 0.3)
        for i in range(n - 1, 0, -1):
            body, belly, _ = self._colors(skin_key, i, n)
            p = self.segments[i]
            D.circle(surf, D.mix(belly, body, 0.55), (p.x - radii[i] * 0.2, p.y - radii[i] * 0.28), radii[i] * 0.4)

        self._draw_head(surf, skin_key, R)

    def _draw_head(self, surf, skin_key, R) -> None:
        body, belly, _ = self._colors(skin_key, 0, len(self.segments))
        h = self.head
        neck = self.segments[1] if len(self.segments) > 1 else h - Vector2(1, 0)
        fwd = h - neck
        fwd = fwd.normalize() if fwd.length() > 0.01 else Vector2(1, 0)
        side = Vector2(-fwd.y, fwd.x)
        hr = R * 1.28
        squish = 1.0 + 0.08 * math.sin(self.t * 14) * (self.happy_t > 0)
        c = h + fwd * R * 0.15

        D.circle(surf, D.darker(body, 0.78), c, hr * squish + 2)
        D.circle(surf, body, c, hr * squish)
        D.circle(surf, D.mix(belly, body, 0.25), c - Vector2(hr * 0.3, hr * 0.38), hr * 0.3)

        # Upright chibi face: always looks at the viewer, leaning toward where Snek is going.
        f = c + fwd * hr * 0.22
        mouth = f + Vector2(0, hr * 0.36)

        # Tongue
        if self.tongue_t > 0 and self.state != "sleep":
            k = math.sin(self.tongue_t / 0.35 * math.pi)
            base = c + fwd * hr * 0.85
            tip = base + fwd * R * 0.9 * k
            D.line(surf, (240, 120, 150), base, tip, 3)
            for s in (-1, 1):
                D.line(surf, (240, 120, 150), tip, tip + (fwd * 0.6 + side * 0.5 * s) * R * 0.35 * k, 2)
            D.circle(surf, body, c + fwd * hr * 0.75, hr * 0.22)

        # Blush
        for s in (-1, 1):
            D.ellipse(surf, (255, 175, 190), (f.x + s * hr * 0.6, f.y + hr * 0.22), hr * 0.2, hr * 0.12)

        # Eyes
        eye_r = hr * 0.33
        for s in (-1, 1):
            e = Vector2(f.x + s * hr * 0.4, f.y - hr * 0.1)
            if self.happy_t > 0:
                D.arc(surf, C.INK, (e.x, e.y + eye_r * 0.35), eye_r * 0.7, math.pi * 1.1, math.pi * 1.9, 3)
            elif self.state == "sleep":
                D.arc(surf, C.INK, (e.x, e.y - eye_r * 0.2), eye_r * 0.65, math.pi * 0.15, math.pi * 0.85, 3)
            elif self.blink_t < 0:
                D.line(surf, C.INK, (e.x - eye_r * 0.7, e.y), (e.x + eye_r * 0.7, e.y), 3)
            else:
                D.circle(surf, C.WHITE, e, eye_r)
                D.ring(surf, D.darker(body, 0.7), e, eye_r)
                pupil = e + self.look * eye_r * 0.3
                D.circle(surf, (70, 55, 75), pupil, eye_r * 0.7)
                D.circle(surf, C.WHITE, pupil + Vector2(-eye_r * 0.25, -eye_r * 0.28), eye_r * 0.27)
                D.circle(surf, C.WHITE, pupil + Vector2(eye_r * 0.22, eye_r * 0.2), eye_r * 0.1)

        # Mouth
        if self.state == "eat" and self.eat_t < 0.4:
            D.circle(surf, (150, 80, 110), mouth, hr * 0.2 * (0.6 + 0.4 * abs(math.sin(self.eat_t * 18))))
        elif self.state == "sleep":
            D.circle(surf, D.darker(body, 0.6), mouth, hr * 0.06)
        else:
            for s in (-1, 1):
                D.arc(surf, C.INK, (mouth.x + s * hr * 0.1, mouth.y - hr * 0.04), hr * 0.1, 0.15, math.pi - 0.15, 2, 6)
