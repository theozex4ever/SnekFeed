from types import SimpleNamespace
from unittest.mock import Mock

import pygame
import pytest

from snekfeed import config as C
from snekfeed import draw as D
from snekfeed import state as S
from snekfeed.feeding import Feeding
from snekfeed.game import Game
from snekfeed.ui import UI

# Click visible layout positions, rather than reading private hit geometry.
SHED_BUTTON = (C.PANEL[0] + C.PANEL[2] // 2, C.PANEL[1] + 118 + 203)


def skin_position(key):
    i = next(i for i, skin in enumerate(C.SKINS) if skin.key == key)
    return (C.PANEL[0] + 60 + (i % 4) * 82, C.PANEL[1] + 118 + 338 + (i // 4) * 80)


@pytest.fixture
def shop():
    assert not pygame.display.get_init()
    ui, st = UI(), S.GameState(level=C.SHED_MIN_LEVEL)
    assert ui.click(ui.tab_rects["shed"].center, st) == ("tab",)
    return ui, st


@pytest.fixture
def render_panel():
    # Software surfaces and fonts suffice; never initialize a display.
    pygame.font.init()
    D.reset_caches()
    surface = pygame.Surface((C.WIDTH, C.HEIGHT))

    def render(ui, st):
        ui.draw_panel(surface, st, 0, lambda *args: None)
        assert not pygame.display.get_init()

    yield render
    D.reset_caches()
    pygame.font.quit()


def test_enter_shed_and_confirm_before_any_render(shop):
    ui, st = shop
    assert not pygame.get_init()
    assert ui.click(SHED_BUTTON, st) == ("noop",)
    assert ui.click(SHED_BUTTON, st) == ("shed",)
    assert st.sheds == 0, "Interaction emits an action; economy execution belongs to GameState"
    assert ui.click(SHED_BUTTON, st) == ("noop",), "Confirmation is consumed"


@pytest.mark.parametrize(("elapsed", "expected"), [(2.999, "shed"), (3.0, "noop"), (4.0, "noop")])
def test_confirmation_expires_in_update_time(shop, elapsed, expected):
    ui, st = shop
    assert ui.click(SHED_BUTTON, st) == ("noop",)
    ui.update(elapsed, None)
    assert ui.click(SHED_BUTTON, st) == (expected,)


@pytest.mark.parametrize("tab", ["shed", "snacks", "home", "care"])
def test_any_tab_click_cancels_confirmation(shop, tab):
    ui, st = shop
    assert ui.click(SHED_BUTTON, st) == ("noop",)
    assert ui.click(ui.tab_rects[tab].center, st) == ("tab",)
    if tab != "shed":
        assert ui.click(ui.tab_rects["shed"].center, st) == ("tab",)
    assert ui.click(SHED_BUTTON, st) == ("noop",)


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (skin_position("mint"), ("skin", "mint")),
        ((0, 0), None),
        (skin_position("peach"), None),
    ],
)
def test_other_clicks_do_not_cancel_confirmation(shop, target, expected):
    ui, st = shop
    assert ui.click(SHED_BUTTON, st) == ("noop",)
    assert ui.click(target, st) == expected
    assert ui.click(SHED_BUTTON, st) == ("shed",)


def test_mute_does_not_cancel_confirmation(shop):
    ui, st = shop
    assert ui.click(SHED_BUTTON, st) == ("noop",)
    assert ui.click(ui.mute_rect.center, st) == ("mute",)
    assert ui.click(SHED_BUTTON, st) == ("shed",)


def test_unavailable_shed_denies_without_arming(shop):
    ui, st = shop
    st.level = C.SHED_MIN_LEVEL - 1
    assert ui.click(SHED_BUTTON, st) == ("deny",)
    st.level = C.SHED_MIN_LEVEL
    assert ui.click(SHED_BUTTON, st) == ("noop",)


def test_confirmation_checks_current_shed_eligibility(shop):
    ui, st = shop
    assert ui.click(SHED_BUTTON, st) == ("noop",)
    st.level = C.SHED_MIN_LEVEL - 1
    assert ui.click(SHED_BUTTON, st) == ("deny",)
    st.level = C.SHED_MIN_LEVEL
    assert ui.click(SHED_BUTTON, st) == ("shed",), "Denial preserves the unexpired window"


@pytest.mark.parametrize("key", [skin.key for skin in C.SKINS])
def test_skin_selection_uses_current_unlocks_without_render(shop, key):
    ui, st = shop
    assert ui.click(skin_position(key), st) == (("skin", key) if key == "mint" else None)
    st.sheds = len(C.SKINS) - 1
    assert ui.click(skin_position(key), st) == ("skin", key)
    st.sheds = 0
    assert ui.click(skin_position(key), st) == (("skin", key) if key == "mint" else None)
    assert st.skin == "mint", "Interaction does not mutate the selected skin"


@pytest.mark.parametrize(("before", "after", "expected"), [(0, 1, ("skin", "peach")), (1, 0, None)])
def test_render_does_not_cache_skin_eligibility(shop, render_panel, before, after, expected):
    ui, st = shop
    st.sheds = before
    render_panel(ui, st)
    st.sheds = after
    assert ui.click(skin_position("peach"), st) == expected


def test_render_preserves_armed_confirmation(shop, render_panel):
    ui, st = shop
    assert ui.click(SHED_BUTTON, st) == ("noop",)
    render_panel(ui, st)
    render_panel(ui, st)
    assert ui.click(SHED_BUTTON, st) == ("shed",)


def test_welcome_dismissal_consumes_click_before_shop_action(shop):
    ui, st = shop
    ui.welcome = (120, 10)
    assert ui.click(SHED_BUTTON, st) == ("noop",)
    assert ui.welcome is None
    assert ui.click(SHED_BUTTON, st) == ("noop",)


@pytest.fixture
def game(shop, monkeypatch):
    ui, st = shop
    game = Game.__new__(Game)
    game.ui, game.st = ui, st
    game.audio = Mock()
    game.feeding = Feeding(st)
    game.feeding.feast()
    game.foods = {}
    game._sync_foods = Mock()
    game.saving_allowed = True
    game.snek = Mock(head=SimpleNamespace(x=100, y=100))
    game.snek.hit.return_value = False
    game.fx = Mock()
    game.butterfly = None
    game.save_path = "unused-save.json"
    monkeypatch.setattr(S, "save", Mock())
    return game


def test_game_executes_only_confirmed_shed_and_keeps_save_trigger(game):
    game.mouse_down(SHED_BUTTON)
    assert game.st.sheds == 0 and len(game.feeding.snacks) == 3
    game.audio.play.assert_not_called()
    game.snek.hit.assert_not_called()
    S.save.assert_not_called()

    game.mouse_down(SHED_BUTTON)
    assert game.st.sheds == 1 and game.st.level == 1
    assert game.feeding.snacks == ()
    game.snek.reset.assert_called_once_with(game.st.level)
    game.fx.sparkles.assert_called_once()
    game.audio.play.assert_called_once_with("shed")
    S.save.assert_called_once_with(game.st, game.save_path)

    game.mouse_down(SHED_BUTTON)
    assert game.st.sheds == 1
    assert game.audio.play.call_args.args == ("deny",)
    assert S.save.call_count == 1


def test_game_applies_only_currently_unlocked_skin_clicks(game):
    game.mouse_down(skin_position("peach"))
    assert game.st.skin == "mint"
    game.audio.play.assert_not_called()
    game.st.sheds = 1
    game.mouse_down(skin_position("peach"))
    assert game.st.skin == "peach"
    game.audio.play.assert_called_once_with("pet")
    S.save.assert_not_called()
