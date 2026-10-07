"""Small antialiased drawing helpers, fonts, and cached text."""

from __future__ import annotations

import math

import pygame
import pygame.gfxdraw as gfx

from . import config as C


def _i(v: float) -> int:
    return int(round(v))


def circle(surf, color, center, r) -> None:
    r = _i(r)
    if r <= 0:
        return
    x, y = _i(center[0]), _i(center[1])
    gfx.filled_circle(surf, x, y, r, color)
    gfx.aacircle(surf, x, y, r, color)


def ring(surf, color, center, r) -> None:
    if r > 0:
        gfx.aacircle(surf, _i(center[0]), _i(center[1]), _i(r), color)


def ellipse(surf, color, center, rx, ry) -> None:
    rx, ry = _i(rx), _i(ry)
    if rx <= 0 or ry <= 0:
        return
    x, y = _i(center[0]), _i(center[1])
    gfx.filled_ellipse(surf, x, y, rx, ry, color)
    gfx.aaellipse(surf, x, y, rx, ry, color)


def polygon(surf, color, points) -> None:
    pts = [(_i(x), _i(y)) for x, y in points]
    if len(pts) >= 3:
        gfx.filled_polygon(surf, pts, color)
        gfx.aapolygon(surf, pts, color)


def line(surf, color, a, b, width=1) -> None:
    if width <= 1:
        pygame.draw.aaline(surf, color, a, b)
    else:
        pygame.draw.line(surf, color, a, b, width)
        circle(surf, color, a, width / 2 - 0.5)
        circle(surf, color, b, width / 2 - 0.5)


def arc(surf, color, center, r, start, end, width=2, steps=10) -> None:
    """Thick arc drawn as a polyline (angles in radians, y down)."""
    pts = [
        (center[0] + math.cos(start + (end - start) * i / steps) * r,
         center[1] + math.sin(start + (end - start) * i / steps) * r)
        for i in range(steps + 1)
    ]
    for a, b in zip(pts, pts[1:]):
        line(surf, color, a, b, width)


def heart(surf, color, center, size) -> None:
    cx, cy = center
    s = size
    circle(surf, color, (cx - s * 0.25, cy - s * 0.1), s * 0.3)
    circle(surf, color, (cx + s * 0.25, cy - s * 0.1), s * 0.3)
    polygon(surf, color, [(cx - s * 0.53, cy), (cx + s * 0.53, cy), (cx, cy + s * 0.5)])


def star(surf, color, center, r_out, r_in=None, points=5, rot=-math.pi / 2) -> None:
    r_in = r_out * 0.45 if r_in is None else r_in
    pts = []
    for i in range(points * 2):
        r = r_out if i % 2 == 0 else r_in
        a = rot + i * math.pi / points
        pts.append((center[0] + math.cos(a) * r, center[1] + math.sin(a) * r))
    polygon(surf, color, pts)


def darker(color, k=0.82):
    return tuple(max(0, int(c * k)) for c in color[:3])


def lighter(color, k=0.35):
    return tuple(int(c + (255 - c) * k) for c in color[:3])


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# --- soft alpha shapes (cached) -------------------------------------------------

_glow_cache: dict = {}


def glow(surf, color, center, radius, alpha=120) -> None:
    """Radial soft glow, blended additively-ish via alpha."""
    radius = max(2, _i(radius))
    key = (color[:3], radius)
    img = _glow_cache.get(key)
    if img is None:
        img = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        for i in range(radius, 0, -2):
            a = int(255 * (1 - i / radius) ** 1.8)
            gfx.filled_circle(img, radius, radius, i, (*color[:3], a))
        _glow_cache[key] = img
    img.set_alpha(alpha)
    surf.blit(img, (center[0] - radius, center[1] - radius))


_shadow_cache: dict = {}


def shadow(surf, center, rx, ry, alpha=40) -> None:
    rx, ry = max(2, _i(rx)), max(2, _i(ry))
    key = (rx, ry, alpha)
    img = _shadow_cache.get(key)
    if img is None:
        img = pygame.Surface((rx * 2 + 2, ry * 2 + 2), pygame.SRCALPHA)
        gfx.filled_ellipse(img, rx + 1, ry + 1, rx, ry, (*C.SHADOW, alpha))
        gfx.aaellipse(img, rx + 1, ry + 1, rx, ry, (*C.SHADOW, alpha))
        _shadow_cache[key] = img
    surf.blit(img, (center[0] - rx - 1, center[1] - ry - 1))


def panel(surf, rect, color, radius=18, shadow_offset=4, border=None) -> None:
    rect = pygame.Rect(rect)
    if shadow_offset:
        sh = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(sh, (*C.SHADOW, 28), sh.get_rect(), border_radius=radius)
        surf.blit(sh, (rect.x, rect.y + shadow_offset))
    pygame.draw.rect(surf, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surf, border, rect, width=2, border_radius=radius)


def bar(surf, rect, frac, fill, back=(240, 232, 238), radius=7) -> None:
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, back, rect, border_radius=radius)
    frac = max(0.0, min(1.0, frac))
    if frac > 0:
        w = max(radius * 2, int(rect.w * frac))
        pygame.draw.rect(surf, fill, (rect.x, rect.y, w, rect.h), border_radius=radius)
        hl = pygame.Rect(rect.x + 4, rect.y + 2, max(0, w - 8), max(2, rect.h // 4))
        pygame.draw.rect(surf, lighter(fill, 0.45), hl, border_radius=radius)


# --- fonts & text -------------------------------------------------------------------

_FONT_CANDIDATES = ("nunito", "quicksand", "fredoka", "varelaround", "poppins", "comfortaa")
_fonts: dict = {}
_text_cache: dict = {}


def font(size: int, bold: bool = False) -> pygame.font.Font:
    key = (size, bold)
    f = _fonts.get(key)
    if f is None:
        for name in _FONT_CANDIDATES:
            path = pygame.font.match_font(name, bold=bold)
            if path:
                f = pygame.font.Font(path, size)
                break
        else:
            f = pygame.font.Font(None, int(size * 1.35))
            f.set_bold(bold)
        _fonts[key] = f
    return f


def render(s: str, size: int, color=C.INK, bold: bool = False) -> pygame.Surface:
    key = (s, size, color, bold)
    img = _text_cache.get(key)
    if img is None:
        if len(_text_cache) > 600:
            _text_cache.clear()
        img = font(size, bold).render(s, True, color)
        _text_cache[key] = img
    return img


def text(surf, s, pos, size=18, color=C.INK, bold=False, anchor="topleft", alpha=255):
    img = render(s, size, color, bold)
    rect = img.get_rect(**{anchor: (_i(pos[0]), _i(pos[1]))})
    if alpha < 255:
        img = img.copy()
        img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


def wrap(s: str, size: int, width: int, bold: bool = False) -> list[str]:
    words, lines, cur = s.split(), [], ""
    f = font(size, bold)
    for w in words:
        trial = f"{cur} {w}".strip()
        if f.size(trial)[0] <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def reset_caches() -> None:
    """Drop fonts and rendered text; required if pygame is re-initialised."""
    _fonts.clear()
    _text_cache.clear()
