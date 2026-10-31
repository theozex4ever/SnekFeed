"""Main loop: wires the state, Snek, the habitat and the UI together."""

from __future__ import annotations

import math
import os
import random
import sys
import time

import pygame
from pygame.math import Vector2

from . import art
from . import config as C
from . import device
from . import draw as D
from . import state as S
from .audio import Audio
from .feeding import Denial, Feeding, MealCredit
from .fx import FX
from .habitat import Butterfly, Food, Habitat
from .snek import Snek
from .ui import UI

AUTOSAVE_EVERY = 30.0
STROKE_DISTANCE = 45.0  # pixels of mouse travel over Snek per pet while holding
WELCOME_MIN_AWAY = 60.0  # seconds away before the welcome-back card is worth showing
BACK_KEYS = (pygame.K_ESCAPE, pygame.K_AC_BACK)  # Android's back button arrives as AC_BACK


class Game:
    def __init__(self, save_path: str | None = None) -> None:
        device.configure_sdl()
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        D.reset_caches()
        pygame.display.set_caption(C.TITLE)
        self.screen = pygame.display.set_mode((C.WIDTH, C.HEIGHT), device.display_flags())
        self.clock = pygame.time.Clock()
        self.audio = Audio()
        self.save_path = save_path or S.default_save_path()
        self.debug = os.environ.get("SNEKFEED_DEBUG") == "1"

        recovery = S.recover(self.save_path)
        self.st = recovery.state
        self.saving_allowed = recovery.can_save
        self.ui = UI()
        self._welcome_back(recovery.away, recovery.earned)
        if recovery.problem:
            messages = {
                "invalid_save": "Couldn't read your save. Kept a backup and started fresh.",
                "unsupported_version": "Save version unsupported. Fresh play won't be saved.",
                "read_failed": "Couldn't open your save. Fresh play won't be saved.",
                "preserve_failed": "Couldn't back up your invalid save. Fresh play won't be saved.",
                "checkpoint_failed": "Couldn't save progress. Will try again at the next save.",
            }
            self.ui.toasts.push(messages[recovery.problem], C.PEACH)
        if recovery.preserved_path:
            print(f"Original save preserved at {recovery.preserved_path}", file=sys.stderr)

        self.habitat = Habitat()
        self.snek = Snek(self.habitat.inner, self.st.level)
        self.fx = FX()
        self.feeding = Feeding(self.st)
        self.foods: dict[int, Food] = {}  # Presentation only; feeding owns membership.
        self.butterfly: Butterfly | None = None
        self.butterfly_timer = random.uniform(C.BUTTERFLY_MIN_GAP * 0.5, C.BUTTERFLY_MAX_GAP * 0.6)
        self.save_timer = AUTOSAVE_EVERY
        self.t = 0.0
        self.mouse: tuple[int, int] | None = None
        self.stroking = False
        self.stroke_acc = 0.0
        self.last_mouse = None
        self.running = True
        self.suspended_at: float | None = None  # wall clock when the app went to the background
        self.mini_snek = Snek(pygame.Rect(0, 0, 60, 60), 1)
        pygame.display.set_icon(self._make_icon())

    # ---- helpers ---------------------------------------------------------------------

    def _sync_foods(self) -> None:
        """Project feeding observations onto food physics and appearance."""
        current = self.feeding.snacks
        for snack in current:
            if snack.id not in self.foods:
                if snack.source == "bowl":
                    pos = Vector2(self.habitat.bowl_pos.x - 50, self.habitat.bowl_pos.y - 6)
                    height = 60
                else:
                    pos = self.habitat.random_drop_point(self.snek.head)
                    height = 200 + snack.ordinal * 60 if snack.source == "feast" else 180
                self.foods[snack.id] = Food(snack.key, pos, height)
            food = self.foods[snack.id]
            food.bite = snack.bite
        current_ids = {snack.id for snack in current}
        for snack_id in self.foods.keys() - current_ids:
            del self.foods[snack_id]

    def _save_progress(self, exiting: bool = False) -> bool:
        if not self.saving_allowed:
            if exiting:
                print(f"Saving disabled to protect {self.save_path}; session progress wasn't saved.",
                      file=sys.stderr)
            return False
        if S.save(self.st, self.save_path):
            return True
        if exiting:
            print(f"Couldn't save progress to {self.save_path}.", file=sys.stderr)
        else:
            self.ui.toasts.push("Couldn't save progress. Will try again at the next save.", C.PEACH)
        return False

    def _welcome_back(self, away: float, earned: float) -> None:
        """Show the welcome-back card, adding to one the player hasn't dismissed yet."""
        if self.ui.welcome:
            away, earned = away + self.ui.welcome[0], earned + self.ui.welcome[1]
        if away > WELCOME_MIN_AWAY and earned >= 1:
            self.ui.welcome = (away, earned)

    def suspend(self, now: float | None = None) -> None:
        """The app is going to the background, where it may be killed: save now."""
        if self.suspended_at is not None:
            return
        self.suspended_at = time.time() if now is None else now
        self.stroking = False
        self.mouse = None
        self._save_progress()

    def resume(self, now: float | None = None) -> None:
        """Credit the time spent in the background as offline time, then checkpoint it."""
        if self.suspended_at is None:
            return
        self._welcome_back(*self._credit_background(now))
        self.save_timer = AUTOSAVE_EVERY
        self._save_progress()
        self.clock.tick()  # don't count the pause as a frame

    def _credit_background(self, now: float | None = None) -> tuple[float, float]:
        """End a suspension, crediting its interval. Returns (seconds_away, hearts_earned)."""
        now = time.time() if now is None else now
        away = max(0.0, now - self.suspended_at)
        self.suspended_at = None
        return away, self.st.credit_away(away)

    def _make_icon(self) -> pygame.Surface:
        icon = pygame.Surface((64, 64), pygame.SRCALPHA)
        self.draw_skin_preview(icon, self.st.skin, (32, 32))
        return icon

    def draw_skin_preview(self, surf, skin_key, center, snek: Snek | None = None) -> None:
        """A tiny wiggly Snek used for the skin picker and the window icon."""
        mini = snek or self.mini_snek
        mini.radius = 7.5
        cx, cy = center
        mini.segments = [Vector2(cx + 15 - i * 4.2, cy + 2 + math.sin(i * 0.75) * 6) for i in range(9)]
        mini.look = Vector2(0.3, 1)
        mini.state, mini.happy_t, mini.blink_t, mini.tongue_t, mini.bulges = "idle", 0, 1, 0, []
        mini.draw(surf, skin_key)

    # ---- actions ---------------------------------------------------------------------------

    def pet(self, pos) -> None:
        value = self.st.pet()
        self.snek.petted()
        self.fx.hearts(pos[0], pos[1] - 10, 3)
        self.fx.popup(pos[0], pos[1] - 30, f"+{S.fmt(value)}")
        self.audio.play("pet")

    def do_action(self, action: tuple) -> None:
        kind = action[0]
        if kind == "mute":
            self.audio.muted = not self.audio.muted
        elif kind == "tab":
            self.audio.play("pet")
        elif kind == "deny":
            self.audio.play("deny")
        elif kind == "snack":
            purchase = self.feeding.buy(action[1])
            if purchase.snack_id is not None:
                self._sync_foods()
                self.audio.play("buy")
            else:
                self._deny_reason(purchase.denial)
        elif kind == "decor":
            if self.st.buy_decor(action[1]):
                self.audio.play("buy")
                p = self.habitat.slots[action[1]]
                idx = min(self.st.decor[action[1]], len(p)) - 1
                if self.st.decor[action[1]] <= len(p):
                    self.fx.sparkles(p[idx].x, p[idx].y - 20, 12, C.MINT)
            else:
                self.audio.play("deny")
        elif kind == "care":
            if self.st.buy_care(action[1]):
                self.audio.play("buy")
                name = S.CARE_BY_KEY[action[1]].name
                self.ui.toasts.push(f"{name} is now Lv {self.st.care[action[1]]}", C.LILAC)
            else:
                self.audio.play("deny")
        elif kind == "shed":
            gain = self.feeding.shed()
            if gain == 0:
                self.audio.play("deny")
            else:
                self._sync_foods()
                self.snek.reset(self.st.level)
                self.fx.sparkles(self.snek.head.x, self.snek.head.y, 40, C.LILAC, 90)
                self.ui.toasts.push(f"Snek shed their skin! +{gain} Shimmer Scales", C.BUTTER)
                self.audio.play("shed")
                self._save_progress()
        elif kind == "skin":
            self.st.skin = action[1]
            self.audio.play("pet")

    def _deny_reason(self, denial: Denial | None) -> None:
        self.audio.play("deny")
        if denial == "outstanding_cap":
            self.ui.toasts.push("That's plenty of snacks for now!")
        elif denial == "tummy_full":
            self.ui.toasts.push("Snek's tummy is full! Let Snek digest a bit.", C.PEACH)

    def on_eaten(self, credit: MealCredit) -> None:
        food = self.foods[credit.snack_id]
        levels = credit.levels_gained
        self.snek.swallow()
        snack = S.SNACKS_BY_KEY[food.key]
        self.fx.crumbs(food.pos.x, food.pos.y, snack.color, 8)
        self.fx.hearts(self.snek.head.x, self.snek.head.y - 20, 2)
        self.fx.popup(self.snek.head.x, self.snek.head.y - 40, f"+{S.fmt(snack.xp)} growth", C.LILAC_DEEP, 18)
        self.audio.play("munch")
        if levels:
            self.snek.set_level(self.st.level)
            self.fx.sparkles(self.snek.head.x, self.snek.head.y, 30, C.BUTTER, 70)
            self.audio.play("level")
            for lv in range(self.st.level - levels + 1, self.st.level + 1):
                new = self.st.unlocks_at(lv)
                extra = f"  New: {', '.join(new)}" if new else ""
                self.ui.toasts.push(f"Snek grew to Lv {lv}!{extra}", C.BUTTER)

    def catch_butterfly(self) -> None:
        bf = self.butterfly
        self.butterfly = None
        kind, amount = self.st.butterfly_reward(random)
        self.fx.sparkles(bf.pos.x, bf.pos.y, 26, C.BUTTER, 80)
        self.audio.play("flutter")
        if kind == "lucky":
            self.fx.popup(bf.pos.x, bf.pos.y - 20, f"+{S.fmt(amount)}", C.PINK_DEEP, 28)
            self.ui.toasts.push(f"Lucky butterfly! +{S.fmt(amount)} hearts", C.BUTTER)
        elif kind == "frenzy":
            self.ui.toasts.push(f"Butterfly blessing! Hearts x{int(C.FRENZY_MULT)} for {int(amount)}s", C.BUTTER)
        else:
            self.feeding.feast()
            self._sync_foods()
            self.ui.toasts.push("Butterfly feast! Free snacks rain down", C.BUTTER)

    # ---- loop --------------------------------------------------------------------------------

    def handle(self, event) -> None:
        if not self.running:
            return  # Android can queue a foreground event behind its quit; leave exiting to run()
        if event.type in (pygame.QUIT, pygame.APP_TERMINATING):
            self.running = False
        elif event.type == pygame.RENDER_DEVICE_RESET:
            # Android lost the GL context while backgrounded; set_mode rebuilds the scaled renderer.
            self.screen = pygame.display.set_mode((C.WIDTH, C.HEIGHT), device.display_flags())
        elif event.type in (pygame.APP_WILLENTERBACKGROUND, pygame.APP_DIDENTERBACKGROUND):
            self.suspend()
        elif event.type in (pygame.APP_WILLENTERFOREGROUND, pygame.APP_DIDENTERFOREGROUND):
            self.resume()
        elif event.type == pygame.KEYDOWN:
            if event.key in BACK_KEYS:
                if self.ui.welcome:
                    self.ui.welcome = None
                else:
                    self.running = False
            elif event.key == pygame.K_m:
                self.audio.muted = not self.audio.muted
            elif self.debug and event.key == pygame.K_h:
                self.st.earn(max(1000, self.st.hearts * 9))
            elif self.debug and event.key == pygame.K_l:
                self.st.gain_xp(S.xp_needed(self.st.level) - self.st.xp)
                self.snek.set_level(self.st.level)
            elif self.debug and event.key == pygame.K_b:
                self.butterfly = Butterfly(self.habitat.rect)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._is_touch(event):
                self.mouse = event.pos
            self.mouse_down(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.stroking = False
            if self._is_touch(event):
                self.mouse = None  # a lifted finger isn't hovering anywhere
        elif event.type == pygame.MOUSEMOTION:
            self.mouse = event.pos
            if self.stroking and self.snek.hit(event.pos) and self.last_mouse:
                self.stroke_acc += Vector2(event.pos).distance_to(self.last_mouse)
                if self.stroke_acc >= STROKE_DISTANCE:
                    self.stroke_acc = 0.0
                    self.pet(event.pos)
            self.last_mouse = event.pos

    @staticmethod
    def _is_touch(event) -> bool:
        return device.TOUCH or getattr(event, "touch", False)

    def mouse_down(self, pos) -> None:
        action = self.ui.click(pos, self.st)
        if action:
            self.do_action(action)
            return
        if self.butterfly and self.butterfly.hit(pos):
            self.catch_butterfly()
        elif self.snek.hit(pos):
            self.pet(pos)
            self.stroking = True
            self.stroke_acc = 0.0
            self.last_mouse = pos

    def update(self, dt: float) -> None:
        self.t += dt
        st = self.st
        st.tick(dt)

        landed_ids = []
        for snack_id, f in self.foods.items():
            if f.update(dt):
                landed_ids.append(snack_id)
                self.audio.play("plop")
                self.fx.crumbs(f.pos.x, f.pos.y + 6, (200, 235, 210), 4)

        for credit in self.feeding.advance(dt, landed_ids=landed_ids):
            self.on_eaten(credit)
        self._sync_foods()

        tummy_full = st.tummy > C.TUMMY_MAX * 0.85
        bf_pos = self.butterfly.pos if self.butterfly else None
        mouse = self.mouse if self.mouse and self.habitat.rect.collidepoint(self.mouse) else None
        self.snek.update(dt, self.foods, self.feeding, tummy_full, mouse, bf_pos)
        self._sync_foods()
        if self.snek.wants_zzz():
            self.fx.zzz(self.snek.head.x + 14, self.snek.head.y - 24)

        self.butterfly_timer -= dt
        if self.butterfly is None and self.butterfly_timer <= 0:
            self.butterfly = Butterfly(self.habitat.rect)
            self.butterfly_timer = random.uniform(C.BUTTERFLY_MIN_GAP, C.BUTTERFLY_MAX_GAP)
        if self.butterfly:
            self.butterfly.update(dt)
            if random.random() < dt * 12:
                self.fx.sparkles(self.butterfly.pos.x, self.butterfly.pos.y, 1, C.BUTTER, 10)
            if not self.butterfly.alive:
                self.butterfly = None

        self.fx.update(dt)
        self.ui.update(dt, self.mouse)
        self.save_timer -= dt
        if self.save_timer <= 0:
            self.save_timer = AUTOSAVE_EVERY
            self._save_progress()

    def draw(self) -> None:
        surf = self.screen
        surf.fill(C.CREAM)
        self.habitat.draw_background(surf)
        self.habitat.draw_decor(surf, self.st.decor, self.t, self.st.care["bowl"] > 0)
        for f in sorted(self.foods.values(), key=lambda f: f.pos.y):
            f.draw(surf)
        self.snek.draw(surf, self.st.skin)
        self._draw_thought(surf)
        if self.butterfly:
            self.butterfly.draw(surf)
        self.fx.draw(surf)
        if self.st.frenzy_left > 0:
            self._draw_frenzy(surf)
        self.ui.draw_hint(surf, self.st, self.habitat.rect)
        self.ui.draw_hud(surf, self.st, self.audio.muted)
        self.ui.draw_panel(surf, self.st, self.feeding, self.draw_skin_preview)
        self.ui.toasts.draw(surf, self.habitat.rect.centerx, self.habitat.rect.y + 30)
        self.ui.draw_welcome(surf)

    def _draw_thought(self, surf) -> None:
        if not self.st.is_peckish() or self.feeding.snacks or self.snek.state == "sleep":
            return
        h = self.snek.head
        bob = math.sin(self.t * 3) * 3
        bx, by = h.x + 34, h.y - 52 + bob
        bx = min(max(bx, self.habitat.rect.left + 30), self.habitat.rect.right - 30)
        by = max(by, self.habitat.rect.top + 30)
        D.circle(surf, C.WHITE, (h.x + 14, h.y - 22 + bob), 4)
        D.circle(surf, C.WHITE, (h.x + 22, h.y - 32 + bob), 6)
        D.circle(surf, C.WHITE, (bx, by), 22)
        art.snack(surf, self.st.best_snack(), (bx, by), 26)

    def _draw_frenzy(self, surf) -> None:
        r = self.habitat.rect
        k = self.st.frenzy_left / C.FRENZY_SECONDS
        bar = pygame.Rect(r.centerx - 120, r.bottom - 34, 240, 12)
        D.bar(surf, bar, k, C.BUTTER, (255, 250, 230))
        D.text(surf, f"x{int(C.FRENZY_MULT)} hearts", (bar.centerx, bar.y - 12), 15, (210, 150, 60), True, "center")

    def run(self) -> None:
        try:
            while self.running:
                dt = min(0.1, self.clock.tick(C.FPS) / 1000)
                for event in pygame.event.get():
                    self.handle(event)
                if not self.running:
                    break
                if self.suspended_at is not None:
                    continue  # no drawing while Android has taken the screen away
                self.update(dt)
                self.draw()
                pygame.display.flip()
        finally:
            try:
                if self.suspended_at is not None:
                    # Killed from the background: the exit save moves the save cursor to now,
                    # so credit the background interval first or recovery would skip it.
                    self._credit_background()
                self._save_progress(exiting=True)
            finally:
                pygame.quit()


def main() -> None:
    Game().run()
