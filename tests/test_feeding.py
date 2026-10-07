import pytest

from snekfeed.feeding import Feeding
from snekfeed.state import GameState


def test_purchase_through_meal_credit():
    state = GameState(hearts=100, tummy=0, mood=0)
    feeding = Feeding(state)

    purchase = feeding.buy("berry")
    assert purchase.snack_id is not None
    assert purchase.denial is None
    assert state.hearts == 90
    assert state.snacks_eaten == 0
    assert not feeding.claim(purchase.snack_id), "falling snacks cannot be claimed"

    assert feeding.advance(0, landed_ids=(purchase.snack_id,)) == ()
    assert feeding.claim(purchase.snack_id)
    assert feeding.advance(0.4) == ()
    assert state.snacks_eaten == 0
    assert feeding.snacks[0].bite == pytest.approx(0.4 / 0.45)

    credits = feeding.advance(0.1)
    assert len(credits) == 1
    assert credits[0].snack_id == purchase.snack_id
    assert credits[0].key == "berry"
    assert credits[0].levels_gained == 0
    assert state.tummy == 12
    assert state.xp == 5
    assert state.mood > 0
    assert state.snacks_eaten == 1
    assert feeding.snacks == ()
    assert feeding.advance(1) == (), "meal credit must not repeat"


def test_auto_bowl_waits_through_falling_waiting_and_chewing_then_refills_next_frame():
    state = GameState(hearts=1000, tummy=0)
    state.care["bowl"] = 1
    feeding = Feeding(state)
    snack_id = feeding.buy("berry").snack_id
    assert snack_id is not None

    feeding.advance(1)
    assert len(feeding.snacks) == 1
    assert state.hearts == 990
    feeding.advance(0, landed_ids=(snack_id,))
    feeding.advance(1)
    assert state.hearts == 990
    assert feeding.claim(snack_id)
    assert len(feeding.advance(0.5)) == 1
    assert feeding.snacks == (), "bowl checks outstanding snacks before meal credit"
    assert state.hearts == 990

    feeding.advance(0)
    assert len(feeding.snacks) == 1
    assert feeding.snacks[0].source == "bowl"
    assert feeding.snacks[0].phase == "falling"
    assert state.hearts == 980
    assert state.bowl_timer == 24


def test_claimed_snack_reserves_room_but_digestion_can_allow_a_purchase():
    state = GameState(hearts=100, tummy=90)
    feeding = Feeding(state)
    first = feeding.buy("berry").snack_id
    assert first is not None
    feeding.advance(0, landed_ids=(first,))
    assert feeding.claim(first)

    assert feeding.eligibility("berry").denial == "tummy_full"
    assert feeding.buy("berry").denial == "tummy_full"
    assert state.hearts == 90, "denial must not charge"

    state.tick(5)
    assert feeding.eligibility("berry").allowed
    assert feeding.buy("berry").snack_id is not None
    assert state.hearts == 80
    assert feeding.buy("berry").denial == "tummy_full"


@pytest.mark.parametrize(
    ("key", "hearts", "tummy", "denial"),
    [("blue", 1000, 0, "locked"), ("berry", 5, 0, "insufficient_hearts"),
     ("berry", 100, 100, "tummy_full")],
)
def test_purchase_denial_agrees_with_eligibility_without_payment(key, hearts, tummy, denial):
    state = GameState(hearts=hearts, tummy=tummy)
    feeding = Feeding(state)
    assert feeding.eligibility(key).denial == denial
    assert feeding.buy(key).denial == denial
    assert state.hearts == hearts
    assert feeding.snacks == ()


def test_manual_cap_includes_claimed_snacks():
    state = GameState(hearts=1000, tummy=0)
    feeding = Feeding(state)
    for _ in range(8):
        assert feeding.buy("berry").snack_id is not None
    snack_id = feeding.snacks[0].id
    feeding.advance(0, landed_ids=(snack_id,))
    assert feeding.claim(snack_id)
    assert feeding.eligibility("berry").denial == "outstanding_cap"
    assert feeding.buy("berry").denial == "outstanding_cap"
    assert state.hearts == 920


def test_feast_bypasses_caps_then_reserves_and_credits_full_growth():
    state = GameState(hearts=1000, tummy=0)
    feeding = Feeding(state)
    for _ in range(8):
        feeding.buy("berry")
    state.tummy = 100
    feeding.feast()
    assert len(feeding.snacks) == 11
    assert state.hearts == 920
    feast = [snack for snack in feeding.snacks if snack.source == "feast"]
    assert [snack.ordinal for snack in feast] == [0, 1, 2]
    assert all(snack.key == "berry" for snack in feast)
    assert not feeding.eligibility("berry").allowed

    feeding.advance(0, landed_ids=(feast[0].id,))
    assert feeding.claim(feast[0].id), "awake eating has no hard tummy gate"
    assert len(feeding.advance(0.5)) == 1
    assert state.tummy == 100
    assert state.xp == 5
    assert state.snacks_eaten == 1


def test_shed_mid_meal_cancels_every_snack_and_stale_observations_cannot_credit():
    state = GameState(hearts=1e6, level=15, tummy=0, snacks_eaten=7)
    feeding = Feeding(state)
    feeding.feast()
    old_ids = tuple(snack.id for snack in feeding.snacks)
    feeding.advance(0, landed_ids=(old_ids[0], old_ids[1]))
    assert feeding.claim(old_ids[0])
    feeding.advance(0.4)

    assert feeding.shed() > 0
    assert feeding.snacks == ()
    assert state.snacks_eaten == 7
    assert state.level == 1
    assert state.xp == 0
    assert state.tummy == 35
    assert feeding.advance(1, landed_ids=old_ids) == ()
    assert not feeding.claim(old_ids[0])
    assert state.snacks_eaten == 7

    state.hearts = 100
    new_id = feeding.buy("berry").snack_id
    assert new_id is not None and new_id not in old_ids
    feeding.advance(0, landed_ids=old_ids)
    assert not feeding.claim(new_id), "an old landing must not land a new snack"


@pytest.mark.parametrize("dt", [-1, float("nan"), float("inf")])
def test_invalid_elapsed_time_is_rejected_before_landing_or_serving(dt):
    state = GameState(hearts=100, tummy=0)
    state.care["bowl"] = 1
    feeding = Feeding(state)
    with pytest.raises(ValueError, match="elapsed time"):
        feeding.advance(dt)
    assert state.hearts == 100
    assert state.bowl_timer == 0
    assert feeding.snacks == ()


def test_rejected_shed_and_repeated_observations_preserve_the_claimed_meal():
    state = GameState(hearts=100, tummy=95)
    feeding = Feeding(state)
    snack_id = feeding.buy("berry").snack_id
    assert snack_id is not None, "soft capacity admits the last snack even if it overfills"
    feeding.advance(0, landed_ids=(snack_id, snack_id))
    assert feeding.claim(snack_id)
    assert not feeding.claim(snack_id)
    assert feeding.shed() == 0
    assert len(feeding.snacks) == 1
    assert len(feeding.advance(0.5, landed_ids=(snack_id,))) == 1
    assert state.tummy == 100
    assert state.xp == 5
    assert state.snacks_eaten == 1
    assert state.hearts == 90


@pytest.mark.parametrize(
    ("hearts", "level", "tummy", "timer", "expected_key", "expected_hearts"),
    [(150, 3, 0, 0, "blue", 75), (149, 3, 0, 0, "berry", 139),
     (19, 3, 0, 0, None, 19), (1000, 3, 30, 0, None, 1000),
     (1000, 3, 0, 1, None, 1000)],
)
def test_auto_bowl_preserves_choice_half_budget_peckishness_and_cooldown(
    hearts, level, tummy, timer, expected_key, expected_hearts,
):
    state = GameState(hearts=hearts, level=level, tummy=tummy, bowl_timer=timer)
    state.care["bowl"] = 1
    feeding = Feeding(state)
    feeding.advance(0)
    assert [snack.key for snack in feeding.snacks] == ([] if expected_key is None else [expected_key])
    assert state.hearts == expected_hearts
    assert state.bowl_timer == (timer if expected_key is None else 24)


def test_feast_uses_best_unlocked_snack_and_its_fill_blocks_manual_purchase():
    state = GameState(hearts=1000, level=20, tummy=0)
    feeding = Feeding(state)
    feeding.feast()
    assert [snack.key for snack in feeding.snacks] == ["mochi", "mochi", "mochi"]
    assert state.hearts == 1000
    assert feeding.eligibility("berry").denial == "tummy_full"


def test_only_one_meal_can_be_claimed_and_credits_report_level_growth():
    state = GameState(hearts=100, tummy=0, xp=19)
    feeding = Feeding(state)
    feeding.feast()
    ids = tuple(snack.id for snack in feeding.snacks)
    feeding.advance(0, landed_ids=ids)
    assert feeding.claim(ids[0])
    assert not feeding.claim(ids[1])
    credits = feeding.advance(0.5)
    assert credits[0].levels_gained == 1
    assert state.level == 2
    assert feeding.claim(ids[1])
    assert feeding.advance(0.49) == (), "the next claim starts its own half-second"


def test_snack_rows_show_price_not_full_when_only_the_outstanding_cap_blocks(monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame = pytest.importorskip("pygame")
    from snekfeed import config as C
    from snekfeed import ui as ui_module

    pygame.init()
    try:
        surf = pygame.Surface((1280, 800))
        state = GameState(hearts=1e6, tummy=0.0)
        feeding = Feeding(state)
        for _ in range(C.MAX_SNACKS_ON_FLOOR):
            feeding.feast()
        assert feeding.eligibility(C.SNACKS[0].key).denial == "outstanding_cap"

        labels = []
        monkeypatch.setattr(ui_module.D, "text", lambda s, text, *a, **k: labels.append(text))
        ui = ui_module.UI()
        ui._draw_row(surf, state, 0, C.SNACKS[0], feeding)
        assert "Full!" not in labels

        state.tummy = C.TUMMY_MAX
        labels.clear()
        ui._draw_row(surf, state, 0, C.SNACKS[0], feeding)
        assert "Full!" not in labels  # cap still takes precedence over a full tummy

        feeding = Feeding(state)
        labels.clear()
        ui._draw_row(surf, state, 0, C.SNACKS[0], feeding)
        assert "Full!" in labels
    finally:
        pygame.quit()
