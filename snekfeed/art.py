"""Procedural art for snacks, decor and props. Everything is drawn in code
so the game ships with zero image assets and scales to any icon size."""

from __future__ import annotations

import math
from itertools import pairwise

from . import draw as D

# --- snacks ---------------------------------------------------------------------------


def snack(surf, key: str, center, s: float, bite: float = 0.0) -> None:
    """Draw a snack of roughly `s` pixels across. `bite` (0-1) shrinks it."""
    s = s * (1.0 - 0.8 * bite)
    if s < 2:
        return
    x, y = center
    if key == "berry":
        D.heart(surf, (255, 125, 150), (x, y + s * 0.1), s)
        for dx, dy in ((-0.2, 0.0), (0.18, -0.02), (0.0, 0.2), (-0.08, -0.12), (0.1, 0.12)):
            D.ellipse(surf, (255, 236, 170), (x + dx * s, y + dy * s + s * 0.08), s * 0.04, s * 0.05)
        for a in (-0.9, -0.3, 0.3, 0.9):
            D.ellipse(surf, (120, 200, 140),
                      (x + math.sin(a) * s * 0.2, y - s * 0.22 - math.cos(a) * s * 0.04), s * 0.12, s * 0.07)
        D.line(surf, (110, 170, 120), (x, y - s * 0.24), (x + s * 0.05, y - s * 0.38), max(1, int(s * 0.06)))
        D.ellipse(surf, (255, 190, 205), (x - s * 0.22, y - s * 0.04), s * 0.08, s * 0.05)
    elif key == "blue":
        for dx, dy in ((-0.2, 0.12), (0.2, 0.12), (0.0, -0.14)):
            cx, cy = x + dx * s, y + dy * s
            D.circle(surf, (125, 145, 220), (cx, cy), s * 0.24)
            D.circle(surf, (155, 175, 240), (cx, cy), s * 0.21)
            D.circle(surf, (205, 215, 255), (cx - s * 0.08, cy - s * 0.08), s * 0.06)
            D.star(surf, (110, 120, 190), (cx + s * 0.05, cy + s * 0.04), s * 0.06, points=4)
        D.ellipse(surf, (130, 200, 150), (x + s * 0.12, y - s * 0.36), s * 0.12, s * 0.06)
    elif key == "egg":
        D.ellipse(surf, (225, 205, 180), (x, y), s * 0.34, s * 0.43)
        D.ellipse(surf, (255, 244, 225), (x, y), s * 0.32, s * 0.41)
        for dx, dy, r in ((-0.1, -0.15, 0.05), (0.12, -0.02, 0.06), (-0.05, 0.18, 0.04),
                          (0.14, 0.2, 0.035), (-0.16, 0.06, 0.035), (0.02, -0.28, 0.03)):
            D.circle(surf, (200, 165, 145), (x + dx * s, y + dy * s), s * r)
        D.ellipse(surf, (255, 255, 250), (x - s * 0.12, y - s * 0.2), s * 0.07, s * 0.1)
    elif key == "dump":
        pts = [(x - s * 0.45, y + s * 0.2)]
        for i in range(13):
            a = math.pi + math.pi * i / 12
            pts.append((x + math.cos(a) * s * 0.45, y + s * 0.2 + math.sin(a) * s * 0.5))
        pts.append((x + s * 0.45, y + s * 0.2))
        D.ellipse(surf, (230, 205, 175), (x, y + s * 0.2), s * 0.47, s * 0.13)
        D.polygon(surf, (250, 234, 210), pts)
        D.ellipse(surf, (250, 234, 210), (x, y + s * 0.2), s * 0.45, s * 0.1)
        for i in (-2, -1, 0, 1, 2):
            D.line(surf, (225, 195, 165), (x + i * s * 0.09, y - s * 0.28 + abs(i) * s * 0.05),
                   (x + i * s * 0.12, y - s * 0.12 + abs(i) * s * 0.05), max(1, int(s * 0.04)))
        D.ellipse(surf, (255, 248, 235), (x - s * 0.18, y - s * 0.02), s * 0.08, s * 0.05)
    elif key == "cake":
        top = [(x - s * 0.42, y - s * 0.05), (x + s * 0.42, y - s * 0.22), (x + s * 0.42, y + s * 0.3),
               (x - s * 0.42, y + s * 0.3)]
        D.polygon(surf, (250, 215, 170), top)
        D.polygon(surf, (255, 252, 245), [(x - s * 0.42, y + s * 0.08), (x + s * 0.42, y + s * 0.0),
                                          (x + s * 0.42, y + s * 0.08), (x - s * 0.42, y + s * 0.15)])
        D.polygon(surf, (255, 190, 210), [(x - s * 0.44, y - s * 0.1), (x + s * 0.44, y - s * 0.27),
                                          (x + s * 0.44, y - s * 0.17), (x - s * 0.44, y + s * 0.0)])
        D.heart(surf, (255, 125, 150), (x + s * 0.05, y - s * 0.32), s * 0.32)
        D.ellipse(surf, (120, 200, 140), (x + s * 0.05, y - s * 0.42), s * 0.07, s * 0.04)
    elif key == "mochi":
        D.circle(surf, (195, 175, 240), (x, y + s * 0.03), s * 0.42)
        D.circle(surf, (225, 210, 255), (x, y), s * 0.4)
        D.ellipse(surf, (245, 238, 255), (x - s * 0.14, y - s * 0.16), s * 0.12, s * 0.08)
        D.star(surf, (255, 225, 130), (x + s * 0.04, y + s * 0.04), s * 0.17)
    else:
        D.circle(surf, (255, 200, 200), center, s * 0.4)


# --- decor ---------------------------------------------------------------------------


def decor(surf, key: str, center, s: float, t: float = 0.0, phase: float = 0.0) -> None:
    """Draw a decor piece; `center` is the base (ground contact point)."""
    x, y = center
    if key == "pebble":
        D.shadow(surf, (x, y + s * 0.05), s * 0.42, s * 0.12)
        D.ellipse(surf, (190, 185, 205), (x, y - s * 0.12), s * 0.4, s * 0.25)
        D.ellipse(surf, (215, 210, 228), (x - s * 0.04, y - s * 0.16), s * 0.34, s * 0.19)
        D.ellipse(surf, (165, 215, 170), (x + s * 0.06, y - s * 0.3), s * 0.2, s * 0.08)
        D.ellipse(surf, (240, 238, 248), (x - s * 0.18, y - s * 0.2), s * 0.07, s * 0.04)
    elif key == "fern":
        D.shadow(surf, (x, y), s * 0.3, s * 0.08)
        sway = math.sin(t * 1.6 + phase) * 0.08
        for i, a in enumerate((-1.0, -0.5, 0.0, 0.5, 1.0)):
            ang = -math.pi / 2 + a + sway
            length = s * (0.7 - abs(a) * 0.15)
            _leaf(surf, (x, y), ang, length, s * 0.13,
                  (125, 200, 150) if i % 2 else (150, 215, 170))
    elif key == "rock":
        D.glow(surf, (255, 205, 150), (x, y - s * 0.2), s * 0.85, int(80 + 35 * math.sin(t * 1.3 + phase)))
        D.shadow(surf, (x, y + s * 0.04), s * 0.5, s * 0.13)
        D.ellipse(surf, (190, 180, 196), (x, y - s * 0.17), s * 0.5, s * 0.26)
        D.ellipse(surf, (214, 205, 218), (x - s * 0.03, y - s * 0.22), s * 0.44, s * 0.19)
        D.ellipse(surf, (236, 230, 238), (x - s * 0.2, y - s * 0.28), s * 0.13, s * 0.05)
        for k, dx in enumerate((-0.14, 0.12)):
            ox = x + dx * s
            wob = math.sin(t * 2.5 + phase + k) * s * 0.03
            pts = [(ox + math.sin(j * 1.6 + t * 3 + k) * s * 0.04 + wob, y - s * 0.48 - j * s * 0.06) for j in range(5)]
            for a, b in pairwise(pts):
                D.line(surf, (255, 180, 150), a, b, 2)
    elif key == "mush":
        pulse = 0.5 + 0.5 * math.sin(t * 2.0 + phase)
        D.glow(surf, (255, 235, 170), (x, y - s * 0.45), s * 0.9, int(60 + 60 * pulse))
        D.shadow(surf, (x, y), s * 0.25, s * 0.07)
        D.polygon(surf, (250, 240, 225), [(x - s * 0.1, y), (x + s * 0.1, y), (x + s * 0.07, y - s * 0.45),
                                          (x - s * 0.07, y - s * 0.45)])
        cap = [(x - s * 0.38, y - s * 0.42)]
        for i in range(13):
            a = math.pi + math.pi * i / 12
            cap.append((x + math.cos(a) * s * 0.38, y - s * 0.42 + math.sin(a) * s * 0.36))
        D.polygon(surf, (255, 170, 190), cap)
        for dx, dy, r in ((-0.18, -0.55, 0.06), (0.1, -0.68, 0.07), (0.22, -0.5, 0.045), (-0.04, -0.5, 0.04)):
            D.circle(surf, (255, 248, 240), (x + dx * s, y + dy * s), s * r)
    elif key == "pond":
        D.ellipse(surf, (160, 200, 235), (x, y - s * 0.2), s * 0.62, s * 0.3)
        D.ellipse(surf, (190, 225, 250), (x, y - s * 0.2), s * 0.58, s * 0.26)
        k = (t * 0.5 + phase) % 1.0
        D.ellipse(surf, D.mix((230, 245, 255), (190, 225, 250), k), (x + s * 0.12, y - s * 0.2),
                  s * 0.1 + s * 0.25 * k, s * 0.04 + s * 0.1 * k)
        D.circle(surf, (150, 210, 160), (x - s * 0.28, y - s * 0.18), s * 0.11)
        D.polygon(surf, (190, 225, 250), [(x - s * 0.28, y - s * 0.18), (x - s * 0.15, y - s * 0.24),
                                          (x - s * 0.17, y - s * 0.12)])
        D.circle(surf, (255, 190, 210), (x - s * 0.3, y - s * 0.2), s * 0.04)
    elif key == "house":
        D.shadow(surf, (x, y + s * 0.02), s * 0.55, s * 0.12)
        D.polygon(surf, (250, 240, 228), [(x - s * 0.4, y), (x + s * 0.4, y), (x + s * 0.4, y - s * 0.5),
                                          (x - s * 0.4, y - s * 0.5)])
        D.polygon(surf, (225, 205, 240), [(x + s * 0.18, y - s * 0.62), (x + s * 0.3, y - s * 0.62),
                                          (x + s * 0.3, y - s * 0.85), (x + s * 0.18, y - s * 0.85)])
        D.polygon(surf, (200, 175, 235), [(x - s * 0.52, y - s * 0.46), (x + s * 0.52, y - s * 0.46),
                                          (x, y - s * 0.95)])
        D.polygon(surf, (255, 200, 170), [(x - s * 0.1, y), (x + s * 0.1, y), (x + s * 0.1, y - s * 0.28),
                                          (x - s * 0.1, y - s * 0.28)])
        D.circle(surf, (255, 200, 170), (x, y - s * 0.28), s * 0.1)
        D.circle(surf, (255, 240, 160), (x - s * 0.25, y - s * 0.3), s * 0.08)
        D.circle(surf, (255, 240, 160), (x + s * 0.25, y - s * 0.3), s * 0.08)
        D.heart(surf, (255, 160, 185), (x, y - s * 0.66), s * 0.14)
    else:
        D.circle(surf, (200, 200, 200), (x, y - s * 0.2), s * 0.2)


def _leaf(surf, base, ang, length, width, color) -> None:
    ca, sa = math.cos(ang), math.sin(ang)
    px, py = -sa, ca
    pts_l, pts_r = [], []
    for i in range(9):
        u = i / 8
        w = math.sin(u * math.pi) * width
        cx, cy = base[0] + ca * length * u, base[1] + sa * length * u
        pts_l.append((cx + px * w, cy + py * w))
        pts_r.append((cx - px * w, cy - py * w))
    D.polygon(surf, color, pts_l + pts_r[::-1])
    D.line(surf, D.lighter(color, 0.4), base, (base[0] + ca * length * 0.85, base[1] + sa * length * 0.85))


def bowl(surf, center, s: float) -> None:
    x, y = center
    D.shadow(surf, (x, y + s * 0.12), s * 0.55, s * 0.12)
    pts = []
    for i in range(13):
        a = math.pi * i / 12
        pts.append((x + math.cos(a) * s * 0.5, y + math.sin(a) * s * 0.3))
    D.polygon(surf, (200, 180, 235), pts)
    D.ellipse(surf, (225, 210, 250), (x, y), s * 0.5, s * 0.12)
    D.ellipse(surf, (185, 165, 220), (x, y), s * 0.42, s * 0.08)
    D.heart(surf, (255, 180, 200), (x, y + s * 0.15), s * 0.14)


def butterfly(surf, center, s: float, flap: float, alpha_glow: int = 90) -> None:
    x, y = center
    D.glow(surf, (255, 235, 150), (x, y), s * 1.5, alpha_glow)
    w = 0.25 + 0.75 * abs(math.sin(flap))
    for side in (-1, 1):
        D.ellipse(surf, (240, 180, 90), (x + side * s * 0.4 * w, y - s * 0.14), s * 0.44 * w + 1, s * 0.36)
        D.ellipse(surf, (255, 222, 130), (x + side * s * 0.4 * w, y - s * 0.14), s * 0.4 * w + 1, s * 0.32)
        D.ellipse(surf, (255, 244, 200), (x + side * s * 0.46 * w, y - s * 0.2), s * 0.14 * w + 1, s * 0.1)
        D.ellipse(surf, (240, 150, 175), (x + side * s * 0.28 * w, y + s * 0.22), s * 0.27 * w + 1, s * 0.21)
        D.ellipse(surf, (255, 190, 205), (x + side * s * 0.28 * w, y + s * 0.22), s * 0.23 * w + 1, s * 0.17)
    D.ellipse(surf, (150, 120, 140), (x, y + s * 0.04), s * 0.07, s * 0.3)
    D.line(surf, (150, 120, 140), (x - 1, y - s * 0.24), (x - s * 0.16, y - s * 0.46))
    D.line(surf, (150, 120, 140), (x + 1, y - s * 0.24), (x + s * 0.16, y - s * 0.46))
