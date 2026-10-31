from itertools import pairwise

import pytest

from snekfeed import music

RATE = 4000  # low enough to render the whole loop quickly


@pytest.fixture(scope="module")
def loop():
    return music.compose(RATE)


def test_loop_is_a_whole_number_of_bars(loop):
    assert len(loop) == int(len(music.CHORDS) * music.BEATS_PER_BAR * 60 / music.BPM * RATE)
    assert len(music.MELODY) == len(music.CHORDS)


def test_loop_stays_quiet_under_the_sound_effects(loop):
    assert max(map(abs, loop)) == pytest.approx(music.PEAK)


def test_loop_has_no_seam(loop):
    # Ringing notes wrap to the start, so the jump from the last sample back to the first is as small
    # as any ordinary step between neighbouring samples.
    steps = [abs(b - a) for a, b in pairwise(loop)]
    assert abs(loop[0] - loop[-1]) <= max(steps)


def test_add_wraps_past_the_end():
    buf = [0.0] * 4
    music._add(buf, 3, [1.0, 2.0, 3.0], 0.5)
    assert buf == [1.0, 1.5, 0.0, 0.5]
