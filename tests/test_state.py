import random

import pytest

from snekfeed import config as C
from snekfeed import state as S


def test_pet_earns_hearts_and_mood():
    st = S.GameState(mood=50)
    value = st.pet()
    assert value > 0
    assert st.hearts == pytest.approx(value)
    assert st.mood > 50


def test_snack_requires_hearts_room_and_unlock():
    st = S.GameState(hearts=5)
    assert not st.buy_snack("berry")
    st.hearts = 1000
    assert not st.buy_snack("blue"), "blueberries unlock at Lv 3"
    st.tummy = C.TUMMY_MAX
    assert not st.buy_snack("berry"), "full tummy"
    st.tummy = 0
    assert st.buy_snack("berry")
    assert st.hearts == 990


def test_eating_levels_up():
    st = S.GameState()
    gained = st.gain_xp(S.xp_needed(1) + S.xp_needed(2) + 1)
    assert gained == 2 and st.level == 3
    assert st.xp == pytest.approx(1)


def test_decor_cost_scales_and_generates():
    st = S.GameState(hearts=1_000)
    first = st.decor_cost("pebble")
    assert st.buy_decor("pebble")
    assert st.decor_cost("pebble") == pytest.approx(first * C.DECOR_COST_GROWTH)
    before = st.hearts
    st.tick(10)
    assert st.hearts > before


def test_care_maxes_out():
    st = S.GameState(hearts=1e30)
    for _ in range(40):
        st.buy_care("brush")
    assert st.care["brush"] == S.CARE_BY_KEY["brush"].max_level


def test_auto_bowl_serves_only_when_peckish():
    st = S.GameState(hearts=1000, tummy=80)
    st.care["bowl"] = 1
    assert st.auto_bowl_pick(0) is None
    st.tummy = 5
    assert st.auto_bowl_pick(0) == "berry"
    assert st.auto_bowl_pick(0) is None, "cooldown"


def test_shed_resets_and_keeps_scales():
    st = S.GameState(hearts=1e9, level=20)
    st.decor["fern"] = 10
    gain = st.shed()
    assert gain > 0 and st.scales == gain and st.sheds == 1
    assert st.level == 1 and st.hearts == 0 and st.decor["fern"] == 0
    assert st.skin == "peach" and st.scale_mult() > 1


def test_cannot_shed_early():
    st = S.GameState(level=C.SHED_MIN_LEVEL - 1)
    assert st.shed() == 0 and st.sheds == 0


def test_offline_progress_is_capped():
    st = S.GameState(saved_at=0)
    st.decor["pebble"] = 10
    expected = st.passive_rate(False) * C.OFFLINE_CAP_SECONDS * C.OFFLINE_EFFICIENCY
    away, earned = st.apply_offline(now=10 * C.OFFLINE_CAP_SECONDS)
    assert away == 10 * C.OFFLINE_CAP_SECONDS
    assert earned == pytest.approx(expected)


def test_butterfly_rewards():
    st = S.GameState()
    kinds = set()
    rng = random.Random(1)
    st.decor["pebble"] = 1
    for _ in range(50):
        kinds.add(st.butterfly_reward(rng)[0])
    assert kinds == {"lucky", "frenzy", "feast"}


def test_save_roundtrip(tmp_path):
    st = S.GameState(hearts=123, level=4)
    st.decor["fern"] = 3
    path = str(tmp_path / "save.json")
    S.save(st, path)
    loaded = S.load(path)
    assert loaded.hearts == 123 and loaded.level == 4 and loaded.decor["fern"] == 3


def test_load_tolerates_garbage(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("not json")
    assert S.load(str(path)) is None


@pytest.mark.parametrize("n,s", [(0, "0"), (5.5, "5.5"), (999, "999"), (1234, "1.23K"), (45_600_000, "45.6M")])
def test_fmt(n, s):
    assert S.fmt(n) == s
