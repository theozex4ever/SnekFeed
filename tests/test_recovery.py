import json
import math

import pytest

from snekfeed import config as C
from snekfeed import state as S


def write_save(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def test_missing_save_starts_saveable_without_creating_file(tmp_path):
    path = tmp_path / "missing" / "save.json"
    result = S.recover(path, now=1000)
    assert result.state == S.GameState(saved_at=1000)
    assert result.can_save and result.problem is None
    assert (result.away, result.earned) == (0, 0)
    assert not path.exists()
    assert S.save(result.state, path, now=1001)


@pytest.mark.parametrize("version", [None, 1])
def test_missing_fields_and_timestamp_default_without_credit(tmp_path, version):
    path = tmp_path / "save.json"
    data = {"decor": {"pebble": 3, "future_item": "ignored"}, "tick": 7, "future_field": ["ignored"]}
    if version is not None:
        data["version"] = version
    write_save(path, data)
    # Deliberately far beyond wall-clock time: a missing timestamp still must
    # not manufacture an offline interval from the real clock.
    result = S.recover(path, now=10_000_000_000)
    assert result.problem is None and result.can_save
    assert (result.away, result.earned) == (0, 0)
    assert result.state.decor["pebble"] == 3
    assert result.state.decor["fern"] == 0
    result.state.tick(1)
    assert result.state.hearts > 0
    assert "tick" not in result.state.to_dict()


@pytest.mark.parametrize(
    "data",
    [
        [],
        None,
        {"decor": []},
        {"care": None},
        {"hearts": "oops"},
        {"hearts": True},
        {"hearts": -1},
        {"hearts": float("nan")},
        {"xp": float("inf")},
        {"saved_at": -1},
        {"saved_at": "yesterday"},
        {"level": 0},
        {"level": 2.0},
        {"sheds": True},
        {"scales": -1},
        {"pets": 1.5},
        {"snacks_eaten": "3"},
        {"tummy": 101},
        {"mood": -1},
        {"skin": []},
        {"decor": {"pebble": 2.9}},
        {"decor": {"fern": True}},
        {"care": {"brush": 26}},
        {"care": {"bowl": -1}},
        {"bowl_timer": -1},
        {"frenzy_left": "20"},
        {"xp": S.xp_needed(1)},
        {"level": 1510},
        {"level": 1512},
        {"decor": {"pebble": 10_000}},
        {"scales": 10**300, "decor": {"house": 10**300}},
        {"scales": 10**303, "decor": {"house": 100}},
        {"hearts": 1.7e308, "scales": 10**301, "decor": {"house": 1}},
        {"hearts": 10**1000},
        {"version": True},
        {"version": "1"},
    ],
)
def test_malformed_save_is_rejected_and_preserved_before_fresh_save(tmp_path, data):
    path = tmp_path / "save.json"
    write_save(path, data)
    original = path.read_bytes()
    assert S.load(path) is None
    result = S.recover(path, now=1000)
    assert result.problem == "invalid_save" and result.can_save
    assert result.state == S.GameState(saved_at=1000)
    assert path.read_bytes() == original
    backup = next(tmp_path.glob("save.json.rejected-*.bak"))
    assert str(backup) == result.preserved_path
    assert backup.read_bytes() == original
    assert S.save(result.state, path, now=1001)
    assert S.load(path).saved_at == 1001
    assert backup.read_bytes() == original


@pytest.mark.parametrize(
    "raw",
    [
        b"not json",
        b"\xff",
        b'{"decor": ',
        b"[" * 2000 + b"]" * 2000,
    ],
)
def test_bad_encoding_and_json_preserve_original_bytes(tmp_path, raw):
    path = tmp_path / "save.json"
    path.write_bytes(raw)
    result = S.recover(path, now=1000)
    assert result.problem == "invalid_save"
    assert path.read_bytes() == raw
    assert next(tmp_path.glob("*.bak")).read_bytes() == raw


def test_rejected_backups_have_unique_names(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("not json")
    first = S.recover(path, now=1000)
    second = S.recover(path, now=1000)
    assert first.preserved_path != second.preserved_path
    assert len(list(tmp_path.glob("*.bak"))) == 2


@pytest.mark.parametrize("version", [0, 2, 999])
def test_unsupported_version_is_protected(tmp_path, version):
    path = tmp_path / "save.json"
    write_save(path, {"version": version, "hearts": 123})
    original = path.read_bytes()
    result = S.recover(path, now=1000)
    assert result.problem == "unsupported_version" and not result.can_save
    assert result.state.hearts == 0
    assert path.read_bytes() == original
    assert not list(tmp_path.glob("*.bak"))


def test_unreadable_path_is_protected(tmp_path):
    path = tmp_path / "save.json"
    path.mkdir()
    result = S.recover(path, now=1000)
    assert result.problem == "read_failed" and not result.can_save
    assert path.is_dir()
    assert not result.preserved_path


def test_preservation_failure_protects_original(tmp_path, monkeypatch):
    path = tmp_path / "save.json"
    path.write_text("not json")

    def denied(*args, **kwargs):
        raise PermissionError("backup denied")

    monkeypatch.setattr(S.shutil, "copyfileobj", denied)
    result = S.recover(path, now=1000)
    assert result.problem == "preserve_failed" and not result.can_save
    assert path.read_text() == "not json"
    assert not list(tmp_path.glob("*.bak"))


def test_recovery_checkpoints_existing_offline_rules_once(tmp_path):
    path = tmp_path / "save.json"
    state = S.GameState(
        hearts=100, run_hearts=100, lifetime_hearts=200, tummy=90, mood=70, frenzy_left=20, bowl_timer=12
    )
    state.decor["pebble"] = 10
    expected = state.passive_rate(False) * C.OFFLINE_CAP_SECONDS * C.OFFLINE_EFFICIENCY
    assert S.save(state, path, now=0)
    now = 10 * C.OFFLINE_CAP_SECONDS
    result = S.recover(path, now=now)
    assert result.problem is None
    assert result.away == now and result.earned == pytest.approx(expected)
    assert result.state.hearts == pytest.approx(100 + expected)
    assert result.state.run_hearts == pytest.approx(100 + expected)
    assert result.state.lifetime_hearts == pytest.approx(200 + expected)
    assert result.state.tummy == 0 and result.state.mood == 25
    assert result.state.frenzy_left == 0 and result.state.bowl_timer == 12
    reopened = S.recover(path, now=now)
    assert (reopened.away, reopened.earned) == (0, 0)
    assert reopened.state.hearts == pytest.approx(result.state.hearts)
    assert S.load(path).saved_at == now


def test_future_timestamp_gets_no_credit_and_low_mood_stays_low(tmp_path):
    path = tmp_path / "save.json"
    state = S.GameState(mood=10, frenzy_left=20)
    state.decor["pebble"] = 1
    assert S.save(state, path, now=2000)
    result = S.recover(path, now=1000)
    assert (result.away, result.earned) == (0, 0)
    assert result.state.mood == 10 and result.state.frenzy_left == 0
    assert S.load(path).saved_at == 1000


def test_failed_checkpoint_keeps_credit_and_retry_commits_it(tmp_path, monkeypatch):
    path = tmp_path / "save.json"
    state = S.GameState()
    state.decor["pebble"] = 1
    assert S.save(state, path, now=0)
    original = path.read_bytes()
    replace = S.os.replace

    def denied(*args):
        raise PermissionError("replace denied")

    monkeypatch.setattr(S.os, "replace", denied)
    result = S.recover(path, now=1000)
    assert result.problem == "checkpoint_failed" and result.can_save
    assert result.state.hearts == pytest.approx(result.earned)
    assert result.earned > 0 and path.read_bytes() == original
    repeated = S.recover(path, now=1000)
    assert repeated.earned == result.earned  # documented until a write succeeds
    monkeypatch.setattr(S.os, "replace", replace)
    assert S.save(result.state, path, now=1000)
    assert S.recover(path, now=1000).earned == 0


def test_failed_write_keeps_disk_and_timestamp_and_cleans_tmp(tmp_path, monkeypatch):
    path = tmp_path / "save.json"
    state = S.GameState(hearts=123)
    assert S.save(state, path, now=1000)
    original = path.read_bytes()
    state.hearts = 456

    def denied(*args):
        raise PermissionError("replace denied")

    monkeypatch.setattr(S.os, "replace", denied)
    assert not S.save(state, path, now=2000)
    assert state.saved_at == 1000 and path.read_bytes() == original
    assert not (tmp_path / "save.json.tmp").exists()


def test_invalid_live_state_is_not_written(tmp_path):
    path = tmp_path / "save.json"
    state = S.GameState()
    assert S.save(state, path, now=1000)
    original = path.read_bytes()
    state.hearts = math.nan
    assert not S.save(state, path, now=2000)
    assert state.saved_at == 1000 and path.read_bytes() == original


def test_save_accepts_bare_filename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert S.save(S.GameState(), "save.json", now=1000)
    assert S.load("save.json").saved_at == 1000


def test_load_is_read_only_and_existing_skin_fallback_is_preserved(tmp_path):
    path = tmp_path / "save.json"
    write_save(path, {"saved_at": 0, "hearts": 100, "skin": "rainbow", "sheds": 0})
    original = path.read_bytes()
    loaded = S.load(path)
    assert loaded.hearts == 100 and loaded.saved_at == 0
    assert loaded.skin == "mint" and path.read_bytes() == original
