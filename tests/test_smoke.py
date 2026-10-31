"""Headless end-to-end smoke tests: boot the real Game and play it through the real loop.

These catch what unit tests miss, such as a crash in a draw routine, a bad event handler, or a
start-up regression. CI runs them on every OS and Python version using SDL's dummy drivers.
"""

import json

import pygame
import pytest

from snekfeed import config as C
from snekfeed import state as S
from snekfeed.game import Game

FRAME = 1 / 60


@pytest.fixture
def make_game(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    path = tmp_path / "save.json"

    def make(state=None):
        if state is not None:
            assert S.save(state, path)
        return Game(str(path))

    make.path = path
    yield make
    pygame.quit()


def click(game, pos):
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
    game.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, pos=pos, button=1))


def step(game, seconds, until=None):
    for _ in range(round(seconds / FRAME)):
        game.update(FRAME)
        game.draw()
        if until is not None and until():
            return


def test_fresh_game_survives_ten_seconds_of_frames(make_game):
    game = make_game()
    step(game, 10)
    assert game.running
    assert game.st.lifetime_hearts == 0, "nothing earns until Snek is petted or decor is bought"


def test_player_session_through_the_ui(make_game):
    game = make_game()
    # Pet Snek by clicking it, then keep clicking the first shop row, which is the cheapest snack.
    for _ in range(20):
        click(game, (int(game.snek.head.x), int(game.snek.head.y)))
    assert game.st.hearts > 0
    first_row = game.ui.row_rect(0).center
    click(game, first_row)
    assert game.feeding.snacks, "the snack should be dropping into the terrarium"
    step(game, 30, until=lambda: not game.feeding.snacks)
    assert not game.feeding.snacks, "Snek should have eaten the snack"
    assert game.st.xp > 0 or game.st.level > 1

    # Visit every tab, which draws each panel.
    for tab_rect in list(game.ui.tab_rects.values()):
        click(game, tab_rect.center)
        step(game, 0.2)


def test_every_snack_decor_care_and_skin_renders(make_game):
    state = S.GameState(
        hearts=1e12,
        level=C.SHED_MIN_LEVEL + 10,
        decor={d.key: 12 for d in C.DECOR},
        care={c.key: c.max_level for c in C.CARE},
        sheds=len(C.SKINS) - 1,
    )
    game = make_game(state)
    for skin in C.SKINS:
        game.do_action(("skin", skin.key))
        for tab_rect in list(game.ui.tab_rects.values()):
            click(game, tab_rect.center)
            step(game, 0.1)
    for snack in C.SNACKS:
        game.st.tummy = 0
        game.do_action(("snack", snack.key))
        step(game, 0.2)
    step(game, 2)


def test_golden_butterfly_can_be_caught(make_game):
    game = make_game()
    game.butterfly_timer = 0
    step(game, 0.1)
    assert game.butterfly is not None
    game.butterfly.pos.update(game.habitat.rect.center)  # it spawns off-screen
    click(game, (int(game.butterfly.pos.x), int(game.butterfly.pos.y)))
    assert game.butterfly is None


def test_shed_resets_the_home_and_keeps_scales(make_game):
    game = make_game(S.GameState(level=C.SHED_MIN_LEVEL, hearts=500))
    game.do_action(("shed",))
    assert game.st.level == 1
    assert game.st.scales > 0
    assert game.snek.level == 1
    step(game, 2)


def test_run_loop_saves_and_exits_on_quit(make_game):
    game = make_game()
    game.st.hearts = 123
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()
    assert not pygame.get_init(), "run() should shut pygame down"
    saved = json.loads(make_game.path.read_text())
    assert saved["hearts"] == pytest.approx(123)


def test_save_round_trips_through_a_new_game(make_game):
    first = make_game()
    first.do_action(("tab",))
    first.st.hearts = 4321
    assert first._save_progress()
    pygame.quit()
    second = Game(str(make_game.path))
    assert second.st.hearts == pytest.approx(4321, rel=0.01)


def test_background_music_starts_and_follows_mute(make_game):
    game = make_game()
    game.audio._render_music(pygame.mixer.get_init()[0], game.audio.channels)  # skip the wait for the background render
    step(game, FRAME)
    channel = game.audio._music
    assert channel is not None and channel.get_busy()
    game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
    assert game.audio.muted
    game.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m))
    assert not game.audio.muted and channel.get_busy()
