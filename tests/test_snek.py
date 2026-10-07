from itertools import pairwise

import pygame
import pytest

from snekfeed.snek import Snek

AREA = pygame.Rect(0, 0, 700, 520)


@pytest.mark.parametrize("level", range(1, 61))
def test_body_follows_the_trail_at_every_level(level):
    """A fresh body is spaced exactly one gap apart, so float rounding once pushed lerp's
    parameter to 1.0000000000000002 and pygame raised ValueError (a crash on load)."""
    snek = Snek(AREA, level)
    snek._follow()
    gap = snek.spacing()
    for a, b in pairwise(snek.segments):
        assert a.distance_to(b) == pytest.approx(gap, rel=1e-6)
