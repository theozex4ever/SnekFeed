import importlib
import os
import time

import pygame
import pytest

from snekfeed import config as C
from snekfeed import device
from snekfeed import state as S
from snekfeed.ui import UI


@pytest.fixture
def game(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    from snekfeed.game import Game

    g = Game(str(tmp_path / "save.json"))
    g.st.decor["pebble"] = 10
    yield g
    pygame.quit()


def press(game, kind, pos, touch=True):
    game.handle(pygame.event.Event(kind, pos=pos, button=1, touch=touch))


# ---- platform -------------------------------------------------------------------------


def test_android_is_detected_from_python_for_android_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("ANDROID_PRIVATE", str(tmp_path))
    try:
        android = importlib.reload(device)
        assert android.ANDROID and android.TOUCH
        assert android.press_verb() == "Tap"
        assert S.default_save_path() == os.path.join(str(tmp_path), "snekfeed", "save.json")
    finally:
        monkeypatch.delenv("ANDROID_PRIVATE")
        importlib.reload(device)


def test_android_sets_sdl_hints_without_overriding_existing_ones(monkeypatch):
    monkeypatch.setattr(device, "ANDROID", True)
    monkeypatch.setenv("SDL_ANDROID_TRAP_BACK_BUTTON", "0")
    for name in ("SDL_IOS_ORIENTATIONS", "PYGAME_FORCE_SCALE"):
        monkeypatch.setenv(name, "")  # Registers the variable so teardown removes what configure_sdl sets.
        monkeypatch.delenv(name)
    device.configure_sdl()
    assert os.environ["SDL_IOS_ORIENTATIONS"] == "LandscapeLeft LandscapeRight"
    assert os.environ["PYGAME_FORCE_SCALE"] == "photo"
    assert os.environ["SDL_ANDROID_TRAP_BACK_BUTTON"] == "0"
    assert device.display_flags() == pygame.SCALED | pygame.FULLSCREEN


def test_desktop_keeps_its_window_and_save_location(monkeypatch):
    monkeypatch.setattr(device, "ANDROID", False)
    monkeypatch.setenv("ANDROID_PRIVATE", "/data/should-not-be-used")
    assert device.display_flags() == 0
    assert "should-not-be-used" not in S.default_save_path()


# ---- background and foreground --------------------------------------------------------------


def test_backgrounding_saves_and_resuming_credits_time_away(game, monkeypatch):
    path = game.save_path
    monkeypatch.setattr(time, "time", lambda: 5000.0)
    game.handle(pygame.event.Event(pygame.APP_WILLENTERBACKGROUND))
    paused_at = game.suspended_at
    assert paused_at == 5000.0
    assert S.load(path).saved_at == 5000.0
    hearts = game.st.hearts
    expected = game.st.passive_rate(False) * 600 * C.OFFLINE_EFFICIENCY

    game.resume(now=paused_at + 600)
    assert game.suspended_at is None
    assert game.st.hearts == pytest.approx(hearts + expected)
    assert game.ui.welcome == (pytest.approx(600), pytest.approx(game.st.hearts - hearts))
    assert S.load(path).hearts == pytest.approx(game.st.hearts), "Credit is checkpointed on resume"


def test_background_events_are_idempotent(game):
    game.suspend(now=1000)
    game.suspend(now=2000)
    assert game.suspended_at == 1000, "A later background event must not shorten time away"
    game.resume(now=1100)
    hearts = game.st.hearts
    game.resume(now=5000)
    assert game.st.hearts == hearts, "Resuming twice must not credit twice"


def test_short_pause_credits_quietly(game):
    game.suspend(now=1000)
    game.resume(now=1030)
    assert game.ui.welcome is None


def test_clock_going_backwards_credits_nothing(game):
    game.suspend(now=1000)
    hearts = game.st.hearts
    game.resume(now=500)
    assert game.st.hearts == hearts


def test_undismissed_welcome_card_adds_up(game):
    game.ui.welcome = (120.0, 50.0)
    game.suspend(now=1000)
    game.resume(now=1030)
    away, earned = game.ui.welcome
    assert away == pytest.approx(150)
    assert earned > 50


def test_time_in_background_is_not_also_played(game, monkeypatch):
    game.suspend(now=1000)
    drawn = []
    monkeypatch.setattr(game, "draw", lambda: drawn.append(True))
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()
    assert not drawn


def test_protected_session_does_not_save_on_background(game, monkeypatch):
    game.saving_allowed = False
    monkeypatch.setattr(S, "save", lambda *a: pytest.fail("protected session saved"))
    game.suspend(now=1000)
    game.resume(now=2000)
    assert game.ui.welcome is not None


def test_termination_ignores_a_queued_foreground_and_never_renders(game, monkeypatch):
    # SDL's nativeSendQuit wakes a paused pump, which can queue foreground events behind the quit.
    game.suspend(now=1000)
    game.st.hearts = 4321.0
    rendered = []
    monkeypatch.setattr(game, "update", lambda dt: rendered.append("update"))
    monkeypatch.setattr(game, "draw", lambda: rendered.append("draw"))
    monkeypatch.setattr(pygame.display, "flip", lambda: rendered.append("flip"))
    for kind in (pygame.APP_TERMINATING, pygame.QUIT, pygame.APP_DIDENTERFOREGROUND):
        pygame.event.post(pygame.event.Event(kind))
    expected = 4321.0 + game.st.passive_rate(False) * 3600 * C.OFFLINE_EFFICIENCY
    monkeypatch.setattr(time, "time", lambda: 4600.0)
    game.run()
    assert rendered == []
    assert not pygame.get_init()

    saved = S.load(game.save_path)
    assert saved.saved_at == 4600.0
    assert saved.hearts == pytest.approx(expected), "The background hour is credited exactly once, at exit"
    recovery = S.recover(game.save_path, now=4660.0)
    assert recovery.away == pytest.approx(60.0)


def test_render_device_reset_rebuilds_the_display(game, monkeypatch):
    rebuilt = pygame.Surface((C.WIDTH, C.HEIGHT))
    calls = []
    monkeypatch.setattr(device, "ANDROID", True)
    monkeypatch.setattr(pygame.display, "set_mode", lambda *args: calls.append(args) or rebuilt)
    game.handle(pygame.event.Event(pygame.RENDER_DEVICE_RESET))
    assert calls == [((C.WIDTH, C.HEIGHT), pygame.SCALED | pygame.FULLSCREEN)]
    assert game.screen is rebuilt


# ---- back button ------------------------------------------------------------------------------


@pytest.mark.parametrize("key", [pygame.K_AC_BACK, pygame.K_ESCAPE])
def test_back_closes_welcome_card_before_quitting(game, key):
    game.ui.welcome = (600.0, 10.0)
    game.handle(pygame.event.Event(pygame.KEYDOWN, key=key))
    assert game.ui.welcome is None and game.running
    game.handle(pygame.event.Event(pygame.KEYDOWN, key=key))
    assert not game.running


# ---- touch ------------------------------------------------------------------------------------------


def test_lifting_a_finger_clears_hover(game):
    snek = tuple(int(v) for v in game.snek.head)
    press(game, pygame.MOUSEBUTTONDOWN, snek)
    assert game.mouse == snek and game.stroking and game.st.pets == 1
    press(game, pygame.MOUSEBUTTONUP, snek)
    assert game.mouse is None and not game.stroking


def test_mouse_release_keeps_hover(game):
    game.mouse = (200, 300)
    press(game, pygame.MOUSEBUTTONUP, (200, 300), touch=False)
    assert game.mouse == (200, 300)


def test_mute_button_takes_a_fingertip_near_miss():
    ui, st = UI(), S.GameState()
    r = ui.mute_rect
    assert ui.click((r.right + 1, r.bottom + 8), st) == ("mute",)
    assert ui.click(ui.tab_rects["home"].center, st) == ("tab",), "Tabs stay reachable"


@pytest.mark.parametrize("touch, verb", [(True, "Tap"), (False, "Click")])
def test_prompts_use_the_device_press_verb(monkeypatch, touch, verb):
    from snekfeed import draw as D

    monkeypatch.setattr(device, "TOUCH", touch)
    pygame.font.init()
    D.reset_caches()
    try:
        surface = pygame.Surface((C.WIDTH, C.HEIGHT))
        ui, st = UI(), S.GameState(level=C.SHED_MIN_LEVEL)
        ui.welcome = (600.0, 10.0)
        ui.draw_hint(surface, st, surface.get_rect())
        ui.draw_welcome(surface)
        ui.welcome = None
        ui.click(ui.tab_rects["shed"].center, st)
        ui.click(ui._shed_button.center, st)
        shown = []
        real = D.render
        monkeypatch.setattr(D, "render", lambda s, *a, **k: shown.append(s) or real(s, *a, **k))
        ui.welcome = (600.0, 10.0)
        ui.draw_hint(surface, st, surface.get_rect())
        ui.draw_welcome(surface)
        ui.draw_panel(surface, st, None, lambda *args: None)
        assert f"{verb} Snek, or stroke Snek" in shown[0]
        assert f"{verb.lower()} anywhere to continue" in shown
        assert f"Really? {verb} again to shed" in shown
    finally:
        D.reset_caches()
        pygame.font.quit()


def test_touch_text_has_a_size_floor(monkeypatch):
    from snekfeed import draw as D

    pygame.font.init()
    D.reset_caches()
    try:
        monkeypatch.setattr(device, "TOUCH", True)
        assert D.font(11) is D.font(C.MIN_TOUCH_TEXT)
        assert D.font(20) is not D.font(C.MIN_TOUCH_TEXT)
    finally:
        D.reset_caches()
        pygame.font.quit()
