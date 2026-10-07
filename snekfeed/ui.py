"""HUD, shop panel, toasts and the welcome-back card."""

from __future__ import annotations

import math

import pygame

from . import art
from . import config as C
from . import draw as D
from .feeding import Feeding
from .state import GameState, fmt, xp_needed

TABS = [("snacks", "Snacks"), ("home", "Home"), ("care", "Care"), ("shed", "Shed")]
ROW_H, ROW_GAP = 84, 8
ICON_BG = {"snacks": (255, 236, 240), "home": (228, 245, 233), "care": (238, 232, 252)}


def heart_amount(surf, amount: float, pos, size=18, color=C.INK, bold=True, anchor="midleft"):
    """Draw a small heart icon followed by a number. Returns the rect used."""
    img = D.render(fmt(amount), size, color, bold)
    w = int(size * 1.1) + img.get_width()
    h = max(img.get_height(), size)
    rect = pygame.Rect(0, 0, w, h)
    setattr(rect, anchor, (int(pos[0]), int(pos[1])))
    D.heart(surf, C.PINK, (rect.x + size * 0.45, rect.centery + 1), size * 0.85)
    surf.blit(img, img.get_rect(midleft=(rect.x + int(size * 1.1), rect.centery)))
    return rect


class Toasts:
    def __init__(self) -> None:
        self.queue: list[tuple[str, tuple]] = []
        self.t = 0.0

    def push(self, msg: str, color=C.LILAC) -> None:
        if not self.queue or self.queue[-1][0] != msg:
            self.queue.append((msg, color))

    def update(self, dt: float) -> None:
        if self.queue:
            self.t += dt
            if self.t > 2.8:
                self.queue.pop(0)
                self.t = 0.0

    def draw(self, surf, center_x: int, y: int) -> None:
        if not self.queue:
            return
        msg, color = self.queue[0]
        k = min(1.0, self.t * 6, (2.8 - self.t) * 4)
        img = D.render(msg, 19, C.INK, True)
        rect = img.get_rect(center=(center_x, y + int((1 - k) * -14)))
        box = rect.inflate(36, 18)
        layer = pygame.Surface(box.size, pygame.SRCALPHA)
        D.panel(layer, layer.get_rect(), (*color, 255), 16, 0)
        layer.blit(img, img.get_rect(center=(box.w // 2, box.h // 2)))
        layer.set_alpha(int(255 * max(0.0, k)))
        surf.blit(layer, box)


class UI:
    def __init__(self) -> None:
        self.tab = "snacks"
        self.panel = pygame.Rect(C.PANEL)
        self.hud = pygame.Rect(C.HABITAT[0], 16, C.HABITAT[2], C.HUD_H - 12)
        self.mute_rect = pygame.Rect(self.hud.right - 40, self.hud.y + 8, 30, 30)
        self.tab_rects = {}
        tw = (self.panel.w - 32) / len(TABS)
        for i, (key, _) in enumerate(TABS):
            self.tab_rects[key] = pygame.Rect(self.panel.x + 16 + int(i * tw), self.panel.y + 64, int(tw) - 6, 40)
        self.rows_top = self.panel.y + 118
        self.shed_confirm = 0.0
        self.shed_button = pygame.Rect(0, 0, 0, 0)
        self.skin_rects: dict[str, pygame.Rect] = {}
        self.hover = None
        self.t = 0.0
        self.toasts = Toasts()
        self.welcome: tuple[float, float] | None = None

    # ---- input -----------------------------------------------------------------

    def row_rect(self, i: int) -> pygame.Rect:
        return pygame.Rect(self.panel.x + 14, self.rows_top + i * (ROW_H + ROW_GAP), self.panel.w - 28, ROW_H)

    def items(self) -> list:
        return {"snacks": C.SNACKS, "home": C.DECOR, "care": C.CARE}.get(self.tab, [])

    def click(self, pos) -> tuple | None:
        """Translate a click into an action tuple, or None."""
        if self.welcome:
            self.welcome = None
            return ("noop",)
        if self.mute_rect.collidepoint(pos):
            return ("mute",)
        for key, rect in self.tab_rects.items():
            if rect.collidepoint(pos):
                self.tab = key
                self.shed_confirm = 0.0
                return ("tab",)
        if self.tab == "shed":
            if self.shed_button.collidepoint(pos):
                return ("shed",)
            for key, rect in self.skin_rects.items():
                if rect.collidepoint(pos):
                    return ("skin", key)
            return None
        for i, item in enumerate(self.items()):
            if self.row_rect(i).collidepoint(pos):
                return ({"snacks": "snack", "home": "decor", "care": "care"}[self.tab], item.key)
        return None

    def update(self, dt: float, mouse) -> None:
        self.t += dt
        self.shed_confirm = max(0.0, self.shed_confirm - dt)
        self.toasts.update(dt)
        self.hover = mouse

    # ---- HUD -----------------------------------------------------------------------

    def draw_hud(self, surf, st: GameState, muted: bool) -> None:
        r = self.hud
        D.panel(surf, r, C.WHITE, 22, 4)
        # Hearts
        D.heart(surf, C.PINK, (r.x + 38, r.y + 34), 34)
        D.circle(surf, D.lighter(C.PINK, 0.6), (r.x + 30, r.y + 27), 4)
        D.text(surf, fmt(st.hearts), (r.x + 64, r.y + 10), 30, C.INK, True)
        rate = st.passive_rate()
        rate_col = (210, 150, 60) if st.frenzy_left > 0 else C.INK_SOFT
        D.text(surf, f"+{fmt(rate)} per sec", (r.x + 66, r.y + 50), 15, rate_col, True)

        # Level & XP
        lx = r.x + 245
        D.circle(surf, C.LILAC_DEEP, (lx + 24, r.y + 40), 25)
        D.circle(surf, C.LILAC, (lx + 24, r.y + 40), 22)
        D.text(surf, "Lv", (lx + 24, r.y + 28), 12, C.INK, True, "center")
        D.text(surf, str(st.level), (lx + 24, r.y + 46), 20, C.INK, True, "center")
        D.text(surf, "Snek", (lx + 58, r.y + 14), 18, C.INK, True)
        need = xp_needed(st.level)
        D.bar(surf, (lx + 58, r.y + 42, 150, 14), st.xp / need, C.LILAC_DEEP)
        D.text(surf, f"{fmt(st.xp)} / {fmt(need)} growth", (lx + 58, r.y + 58), 12, C.INK_SOFT)

        # Tummy & mood
        bx = r.x + 480
        D.text(surf, "Tummy", (bx, r.y + 10), 13, C.INK_SOFT, True)
        D.bar(surf, (bx + 60, r.y + 13, 120, 13), st.tummy / C.TUMMY_MAX, (255, 185, 140))
        D.text(surf, "Mood", (bx, r.y + 40), 13, C.INK_SOFT, True)
        D.bar(surf, (bx + 60, r.y + 43, 120, 13), st.mood / C.MOOD_MAX, C.PINK)
        mm = st.mood_mult()
        D.text(surf, f"mood bonus x{mm:.2f}", (bx + 60, r.y + 60), 11, C.INK_SOFT)
        # Mute button
        D.circle(surf, C.CREAM, self.mute_rect.center, 14)
        mx, my = self.mute_rect.center
        D.polygon(surf, C.INK_SOFT, [(mx - 7, my - 3), (mx - 3, my - 3), (mx + 2, my - 8), (mx + 2, my + 8),
                                     (mx - 3, my + 3), (mx - 7, my + 3)])
        if muted:
            D.line(surf, C.PINK_DEEP, (mx + 5, my - 4), (mx + 11, my + 4), 2)
            D.line(surf, C.PINK_DEEP, (mx + 11, my - 4), (mx + 5, my + 4), 2)
        else:
            D.arc(surf, C.INK_SOFT, (mx + 2, my), 6, -0.9, 0.9, 2, 6)

    # ---- panel -----------------------------------------------------------------------

    def draw_panel(self, surf, st: GameState, feeding: Feeding, skin_preview) -> None:
        p = self.panel
        D.panel(surf, p, (252, 248, 255), 26, 5)
        D.text(surf, "Snek Feed", (p.x + 22, p.y + 14), 28, C.INK, True)
        D.heart(surf, C.PINK, (p.x + 182, p.y + 32), 16)
        D.text(surf, f"{st.snacks_eaten} snacks  {st.pets} pets", (p.right - 20, p.y + 26), 13, C.INK_SOFT,
               anchor="topright")
        for key, label in TABS:
            rect = self.tab_rects[key]
            active = key == self.tab
            locked = key == "shed" and st.sheds == 0 and st.level < C.SHED_MIN_LEVEL - 3
            col = C.LILAC if active else (240, 234, 248)
            pygame.draw.rect(surf, col, rect, border_radius=14)
            D.text(surf, "?" if locked else label, rect.center, 16, C.INK if active else C.INK_SOFT, True, "center")
            if key == "shed" and st.shed_gain() > 0 and not active:
                D.circle(surf, C.PINK_DEEP, (rect.right - 6, rect.top + 6), 5)
        if self.tab == "shed":
            self._draw_shed(surf, st, skin_preview)
            return
        for i, item in enumerate(self.items()):
            self._draw_row(surf, st, i, item, feeding)

    def _draw_row(self, surf, st: GameState, i: int, item, feeding: Feeding) -> None:
        rect = self.row_rect(i)
        unlocked = st.level >= item.unlock_level
        hover = unlocked and self.hover is not None and rect.collidepoint(self.hover)
        if self.tab == "snacks":
            cost = item.cost
            eligibility = feeding.eligibility(item.key)
            ok = eligibility.allowed
            full = unlocked and eligibility.denial == "tummy_full"
            badge = f"+{fmt(item.xp)} growth"
        elif self.tab == "home":
            cost = st.decor_cost(item.key)
            ok = unlocked and st.hearts >= cost
            full = False
            badge = f"x{st.decor[item.key]}  +{fmt(item.rate * st.mult(False))}/s each"
        else:
            cost = st.care_cost(item.key)
            maxed = st.care_maxed(item.key)
            ok = unlocked and not maxed and st.hearts >= cost
            full = maxed
            badge = f"Lv {st.care[item.key]}/{item.max_level}"

        lift = -2 if hover else 0
        r = rect.move(0, lift)
        D.panel(surf, r, C.WHITE if unlocked else (246, 242, 248), 18, 3 if unlocked else 0,
                C.LILAC if hover else None)
        icon = pygame.Rect(r.x + 10, r.y + 10, 64, 64)
        pygame.draw.rect(surf, ICON_BG[self.tab] if unlocked else (236, 232, 240), icon, border_radius=16)
        if unlocked:
            self._draw_icon(surf, item.key, icon.center)
            D.text(surf, item.name, (r.x + 86, r.y + 8), 18, C.INK, True)
            D.text(surf, item.blurb, (r.x + 86, r.y + 36), 13, C.INK_SOFT)
            D.text(surf, badge, (r.x + 86, r.y + 58), 12, C.MINT_DEEP if self.tab != "care" else C.LILAC_DEEP, True)
        else:
            D.text(surf, "?", icon.center, 30, (200, 190, 205), True, "center")
            D.text(surf, "???", (r.x + 86, r.y + 14), 18, (190, 180, 195), True)
            D.text(surf, f"Snek needs to reach Lv {item.unlock_level}", (r.x + 86, r.y + 40), 13, (180, 170, 185))
            return

        pill = pygame.Rect(0, 0, 92, 26)
        pill.topright = (r.right - 10, r.y + 9)
        if full:
            label = "MAX" if self.tab == "care" else "Full!"
            pygame.draw.rect(surf, C.DISABLED, pill, border_radius=15)
            D.text(surf, label, pill.center, 15, C.INK_SOFT, True, "center")
        else:
            pygame.draw.rect(surf, C.MINT if ok else C.DISABLED, pill, border_radius=15)
            heart_amount(surf, cost, pill.center, 15, C.INK if ok else (190, 160, 175), True, "center")

    def _draw_icon(self, surf, key: str, center) -> None:
        if self.tab == "snacks":
            art.snack(surf, key, center, 44)
        elif self.tab == "home":
            s = {"pond": 50, "house": 56, "rock": 50}.get(key, 46)
            art.decor(surf, key, (center[0], center[1] + s * 0.35 + (8 if key in ("mush", "house") else 0)),
                      s, self.t, 0)
        else:
            x, y = center
            if key == "brush":
                pygame.draw.rect(surf, (255, 200, 170), (x - 18, y - 4, 36, 14), border_radius=6)
                for i in range(7):
                    D.line(surf, C.LILAC_DEEP, (x - 15 + i * 5, y - 4), (x - 15 + i * 5, y - 14), 2)
            elif key == "rub":
                D.circle(surf, (255, 200, 170), (x, y), 18)
                D.arc(surf, C.PINK_DEEP, (x, y), 9, 0.3, 5.5, 3, 14)
            elif key == "bowl":
                art.bowl(surf, (x, y - 2), 48)
                art.snack(surf, "berry", (x, y - 10), 20)
            elif key == "song":
                D.circle(surf, C.LILAC_DEEP, (x - 8, y + 10), 6)
                D.circle(surf, C.LILAC_DEEP, (x + 10, y + 6), 6)
                D.line(surf, C.LILAC_DEEP, (x - 3, y + 10), (x - 3, y - 14), 3)
                D.line(surf, C.LILAC_DEEP, (x + 15, y + 6), (x + 15, y - 18), 3)
                D.line(surf, C.LILAC_DEEP, (x - 3, y - 14), (x + 15, y - 18), 4)

    def _draw_shed(self, surf, st: GameState, skin_preview) -> None:
        p = self.panel
        x, y = p.x + 22, self.rows_top
        card = pygame.Rect(p.x + 14, y, p.w - 28, 250)
        D.panel(surf, card, C.WHITE, 18, 3)
        D.text(surf, "Shed Skin", (x + 8, y + 12), 22, C.INK, True)
        msg = ("Once Snek reaches Lv 15, Snek can shed their skin. Snek becomes tiny again and the home resets, "
               "but Snek keeps Shimmer Scales: +5% hearts each, forever. Every shed reveals a new skin color.")
        for j, ln in enumerate(D.wrap(msg, 13, card.w - 36)):
            D.text(surf, ln, (x + 8, y + 44 + j * 18), 13, C.INK_SOFT)
        sy = y + 150
        D.text(surf, f"Shimmer Scales: {st.scales}  (x{st.scale_mult():.2f} hearts)", (x + 8, sy), 14, C.INK, True)
        gain = st.shed_gain()
        self.shed_button = pygame.Rect(card.x + 16, sy + 30, card.w - 32, 46)
        if gain:
            col = C.PINK if self.shed_confirm > 0 else C.BUTTER
            label = "Really? Click again to shed" if self.shed_confirm > 0 else f"Shed now for +{gain} scales"
        else:
            col, label = C.DISABLED, f"Grow Snek to Lv {C.SHED_MIN_LEVEL} first"
        hover = gain and self.hover is not None and self.shed_button.collidepoint(self.hover)
        D.panel(surf, self.shed_button.move(0, -2 if hover else 0), col, 16, 3 if gain else 0)
        D.text(surf, label, self.shed_button.center, 16, C.INK if gain else C.INK_SOFT, True, "center")

        # Skins
        sk = pygame.Rect(p.x + 14, card.bottom + 12, p.w - 28, 200)
        D.panel(surf, sk, C.WHITE, 18, 3)
        D.text(surf, "Skins", (sk.x + 16, sk.y + 12), 20, C.INK, True)
        unlocked = st.unlocked_skins()
        self.skin_rects = {}
        for i, skin in enumerate(C.SKINS):
            cx = sk.x + 46 + (i % 4) * 82
            cy = sk.y + 76 + (i // 4) * 80
            rect = pygame.Rect(cx - 30, cy - 30, 60, 60)
            if skin.key in unlocked:
                self.skin_rects[skin.key] = rect
                if skin.key == st.skin:
                    D.circle(surf, C.LILAC, (cx, cy), 33)
                skin_preview(surf, skin.key, (cx, cy))
                D.text(surf, skin.name, (cx, cy + 34), 12, C.INK_SOFT, True, "center")
            else:
                D.circle(surf, (240, 236, 244), (cx, cy), 26)
                D.text(surf, "?", (cx, cy), 22, (200, 190, 205), True, "center")

    # ---- overlays -----------------------------------------------------------------------

    def draw_welcome(self, surf) -> None:
        if not self.welcome:
            return
        away, earned = self.welcome
        dim = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        dim.fill((80, 60, 80, 90))
        surf.blit(dim, (0, 0))
        card = pygame.Rect(0, 0, 440, 230)
        card.center = (C.WIDTH // 2, C.HEIGHT // 2)
        D.panel(surf, card, C.CREAM, 26, 6)
        D.text(surf, "Welcome back!", (card.centerx, card.y + 40), 30, C.INK, True, "center")
        h, m = int(away // 3600), int(away % 3600 // 60)
        span = f"{h}h {m}m" if h else f"{m}m"
        D.text(surf, f"Snek kept the home cozy for {span}.", (card.centerx, card.y + 86), 16, C.INK_SOFT,
               anchor="center")
        heart_amount(surf, earned, (card.centerx, card.y + 130), 28, C.INK, True, "center")
        D.text(surf, "click anywhere to continue", (card.centerx, card.bottom - 30), 13, C.INK_SOFT,
               anchor="center")

    def draw_hint(self, surf, st: GameState, area: pygame.Rect) -> None:
        if st.pets < 5:
            msg = "Click Snek, or stroke Snek with the mouse held, to give pets"
        elif st.snacks_eaten == 0:
            msg = "Buy Snek a Strawberry in the Snacks tab"
        elif sum(st.decor.values()) == 0:
            msg = "Cozy items in the Home tab earn hearts on their own"
        elif st.level < 3:
            msg = "Snacks help Snek grow. Every level means more hearts"
        else:
            return
        a = int(200 + 55 * math.sin(self.t * 3))
        img = D.render(msg, 15, C.INK, True)
        box = img.get_rect(midbottom=(area.centerx, area.bottom - 14)).inflate(28, 14)
        layer = pygame.Surface(box.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*C.WHITE, 230), layer.get_rect(), border_radius=14)
        layer.blit(img, img.get_rect(center=(box.w // 2, box.h // 2)))
        layer.set_alpha(a)
        surf.blit(layer, box)
