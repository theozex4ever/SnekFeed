import json

import pytest

from snekfeed import state as S


@pytest.fixture
def game_type(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from snekfeed.game import Game
    import pygame

    yield Game
    pygame.quit()


def test_startup_reports_credit_and_checkpoints_before_play(tmp_path, game_type):
    path = tmp_path / "save.json"
    state = S.GameState()
    state.decor["pebble"] = 1
    assert S.save(state, path, now=0)
    game = game_type(str(path))
    assert game.saving_allowed
    assert game.ui.welcome is not None
    away, earned = game.ui.welcome
    assert away > 60 and earned >= 1
    assert game.st.hearts == pytest.approx(earned)
    assert S.load(path).hearts == pytest.approx(earned)
    game.running = False
    game.run()


def test_protected_session_never_saves_on_shed_autosave_or_exit(
    tmp_path, game_type, monkeypatch, capsys
):
    path = tmp_path / "save.json"
    path.write_text(json.dumps({"version": 2, "hearts": 123}))
    original = path.read_bytes()

    def forbidden(*args, **kwargs):
        pytest.fail("protected session attempted to save")

    monkeypatch.setattr(S, "save", forbidden)
    game = game_type(str(path))
    assert not game.saving_allowed
    assert "won't be saved" in game.ui.toasts.queue[0][0]
    game.st.level = 20
    game.ui.shed_confirm = 1
    game.do_action(("shed",))
    game.save_timer = 0
    game.update(0.1)
    game.running = False
    game.run()
    assert path.read_bytes() == original
    assert "Saving disabled" in capsys.readouterr().err


def test_autosave_failure_keeps_playing_and_exit_closes_pygame(
    tmp_path, game_type, monkeypatch, capsys
):
    import pygame

    path = tmp_path / "save.json"
    game = game_type(str(path))
    assert S.save(game.st, path, now=1000)
    original = path.read_bytes()

    def denied(*args):
        raise PermissionError("replace denied")

    monkeypatch.setattr(S.os, "replace", denied)
    game.save_timer = 0
    game.update(0.1)
    game.draw()
    assert game.running
    assert any("Couldn't save progress" in message for message, _ in game.ui.toasts.queue)
    game.running = False
    game.run()
    assert not pygame.get_init()
    assert path.read_bytes() == original
    assert game.st.saved_at == 1000
    assert "Couldn't save progress" in capsys.readouterr().err


def test_unexpected_exit_save_error_still_closes_pygame(tmp_path, game_type, monkeypatch):
    import pygame

    game = game_type(str(tmp_path / "save.json"))

    def broken(*args):
        raise RuntimeError("unexpected programming error")

    monkeypatch.setattr(S, "save", broken)
    game.running = False
    with pytest.raises(RuntimeError, match="unexpected programming error"):
        game.run()
    assert not pygame.get_init()
