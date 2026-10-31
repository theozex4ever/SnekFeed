"""A cozy, bouncy background loop, synthesized from code like the sound effects.

Sixteen bars in F major at an easy 96 BPM with a light swing: a warm pad, a bouncing bass, a soft
plucked arpeggio, a music-box melody and the odd high twinkle, over a hushed kick, brushed snare and
shaker. Notes that ring past the last bar wrap around to the start, so the loop repeats without a seam.

Rendering is pure Python and takes a moment, so `Audio` calls `compose` off the main thread.
"""

from __future__ import annotations

import math
import operator
import random
from typing import Any

BPM = 96
BEATS_PER_BAR = 4
BEAT = 60 / BPM
SWING = 0.08  # beats that each off-beat eighth is pushed late, for a gentle bounce

# One chord per bar: (bass root, pad voicing), MIDI note numbers.
F, AM, BB, C = (41, (53, 57, 60, 64)), (45, (52, 55, 57, 60)), (46, (53, 57, 58, 62)), (48, (52, 55, 60, 64))
DM, GM, BBM = (50, (53, 57, 60, 62)), (43, (53, 58, 62, 65)), (46, (53, 56, 58, 62))
CHORDS = [F, AM, BB, C, F, AM, BB, C, DM, AM, BB, F, GM, AM, BBM, C]

# Melody per bar: (note, start beat, length in beats).
MELODY: list[list[tuple[int, float, float]]] = [
    [(72, 0, 1.5), (69, 1.5, 0.5), (67, 2, 1), (69, 3, 1)],
    [(72, 0, 1.5), (76, 1.5, 0.5), (74, 2, 1), (72, 3, 1)],
    [(74, 0, 1.5), (72, 1.5, 0.5), (69, 2, 1), (65, 3, 1)],
    [(67, 0, 2), (64, 2, 1), (67, 3, 1)],
    [(72, 0, 1.5), (69, 1.5, 0.5), (67, 2, 1), (69, 3, 1)],
    [(72, 0, 1), (76, 1, 1), (79, 2, 1.5), (76, 3.5, 0.5)],
    [(77, 0, 1.5), (76, 1.5, 0.5), (74, 2, 1), (72, 3, 1)],
    [(74, 0, 1), (76, 1, 3)],
    [(77, 0, 1.5), (76, 1.5, 0.5), (74, 2, 2)],
    [(72, 0, 1.5), (74, 1.5, 0.5), (76, 2, 2)],
    [(74, 0, 1), (72, 1, 1), (69, 2, 1), (70, 3, 1)],
    [(69, 0, 4)],
    [(70, 0, 1.5), (69, 1.5, 0.5), (67, 2, 1), (65, 3, 1)],
    [(69, 0, 1.5), (67, 1.5, 0.5), (64, 2, 2)],
    [(65, 0, 1), (68, 1, 1), (70, 2, 1), (74, 3, 1)],
    [(72, 0, 2), (67, 2, 2)],
]

# The arpeggio walks the pad voicing in eighths, by index into the chord.
ARPEGGIO = [0, 1, 2, 3, 2, 1, 3, 2]
# Bass per bar: (offset from the root in semitones, start beat, length in beats).
BASS = [(0, 0, 1.2), (12, 1.5, 0.4), (7, 2, 0.9), (0, 3, 0.4), (7, 3.5, 0.4)]

# Twinkles fill the gaps where the melody holds a long note: bar -> (note, start beat).
TWINKLES: dict[int, list[tuple[int, float]]] = {
    3: [(84, 2.5), (88, 3), (91, 3.5)],
    7: [(88, 2), (91, 2.5), (96, 3)],
    11: [(81, 1.5), (84, 2), (89, 2.5), (93, 3)],
    15: [(91, 2.5), (88, 3), (84, 3.5)],
}

# Echo taps, (delay in seconds, gain). ROOM gives the plucks some air, ECHO adds a dotted-eighth echo to the melody.
ROOM = [(0.045, 0.16), (0.075, 0.1)]
ECHO = [*ROOM, (BEAT * 0.75, 0.18), (BEAT * 1.5, 0.07)]
PEAK = 0.3  # leaves headroom under the sound effects


def hz(note: int) -> float:
    return 440 * 2 ** ((note - 69) / 12)


def loop_seconds() -> float:
    return len(CHORDS) * BEATS_PER_BAR * BEAT


def _box_envelope(dur: float, rate: int) -> tuple[list[float], list[float]]:
    """Pitch-independent envelopes for a music-box note: the body, and its quick-fading overtone."""
    n, attack, held, release = int(rate * (dur + 1.6)), rate * 0.004, rate * dur, rate * 0.18
    body = [
        min(1.0, i / attack) * math.exp(-i / (rate * 0.7)) * (math.exp(-(i - held) / release) if i > held else 1.0)
        for i in range(n)
    ]
    shine = [b * 0.22 * math.exp(-i / (rate * 0.15)) for i, b in enumerate(body)]
    return body, shine


def _music_box(f: float, envelopes: tuple[list[float], list[float]], rate: int) -> list[float]:
    body, shine = envelopes
    w = math.tau * f / rate
    sines = [math.sin(w * i) for i in range(len(body))]
    cosines = [math.cos(w * i) for i in range(len(body))]
    # sin 2p = 2 sin p cos p and sin 3p = sin p (3 - 4 sin² p) spare two more sin calls per sample.
    return [
        b * s * (1 + 0.05 * (3 - 4 * s * s)) + 2 * h * s * c
        for b, h, s, c in zip(body, shine, sines, cosines, strict=True)
    ]


def _bell(f: float, rate: int) -> list[float]:
    n = int(rate * 1.4)
    w = math.tau * f / rate
    return [
        min(1.0, i / (rate * 0.002)) * math.exp(-i / (rate * 0.4)) * (math.sin(w * i) + 0.3 * math.sin(2.76 * w * i))
        for i in range(n)
    ]


def _pluck(f: float, rate: int) -> list[float]:
    n = int(rate * 0.5)
    w = math.tau * f / rate
    return [
        min(1.0, i / (rate * 0.003)) * math.exp(-i / (rate * 0.12)) * (math.sin(w * i) + 0.35 * math.sin(2 * w * i))
        for i in range(n)
    ]


def _kick(rate: int) -> list[float]:
    """A soft, round thump: a sine sweeping down from 110 Hz."""
    out, phase = [], 0.0
    for i in range(int(rate * 0.3)):
        t = i / rate
        phase += math.tau * (50 + 60 * math.exp(-t / 0.04)) / rate
        out.append(min(1.0, i / (rate * 0.003)) * math.exp(-t / 0.09) * math.sin(phase))
    return out


def _noise_hit(rate: int, decay: float, smooth: float, seed: int) -> list[float]:
    """Brushed noise. Subtracting a smoothed copy keeps only the airy top, so it never sounds harsh."""
    rng = random.Random(seed)
    out, low = [], 0.0
    for i in range(int(rate * decay * 5)):
        x = rng.uniform(-1, 1)
        low = low * smooth + x * (1 - smooth)
        out.append((x - low) * min(1.0, i / (rate * 0.002)) * math.exp(-i / (rate * decay)))
    return out


def _pad_envelope(dur: float, rate: int) -> list[float]:
    attack, release = 0.25, 0.9
    n, rise, held = int(rate * (dur + release)), rate * attack, rate * dur
    return [
        math.sin(i / rise * math.pi / 2) ** 2
        if i < rise
        else math.exp(-(i - held) / (rate * release * 0.35))
        if i > held
        else 1.0
        for i in range(n)
    ]


def _pad_tone(note: int, n: int, rate: int) -> list[float]:
    """A pair of slightly detuned sines, the slow beating between them is what makes it warm."""
    w1, w2 = (math.tau * hz(note) * d / rate for d in (0.9985, 1.0015))
    return [math.sin(w1 * i) + math.sin(w2 * i) for i in range(n)]


def _bass(f: float, dur: float, rate: int) -> list[float]:
    n, held = int(rate * (dur + 0.8)), rate * dur
    w = math.tau * f / rate
    out = []
    for i in range(n):
        env = min(1.0, i / (rate * 0.02)) * math.exp(-i / (rate * 1.4))
        if i > held:
            env *= math.exp(-(i - held) / (rate * 0.2))
        out.append(env * (math.sin(w * i) + 0.18 * math.sin(2 * w * i)))
    return out


def _add(buf: list[float], start: int, samples: list[float], gain: float) -> None:
    """Mix `samples` into the circular `buf` at `start`, wrapping past the end."""
    n, pos, k = len(buf), start % len(buf), 0
    while k < len(samples):
        take = min(n - pos, len(samples) - k)
        chunk = map(gain.__mul__, samples[k : k + take])
        buf[pos : pos + take] = map(operator.add, buf[pos : pos + take], chunk)
        k, pos = k + take, 0


def _echo(buf: list[float], rate: int, taps: list[tuple[float, float]]) -> list[float]:
    out = buf[:]
    for delay, gain in taps:
        _add(out, int(delay * rate), buf, gain)
    return out


def compose(rate: int) -> list[float]:
    """Render the whole loop as mono samples in [-PEAK, PEAK]."""
    n = int(loop_seconds() * rate)

    def at(bar: int, beat: float) -> int:
        if beat % 1 == 0.5:
            beat += SWING
        return int((bar * BEATS_PER_BAR + beat) * BEAT * rate)

    warm, plucks, bright = [0.0] * n, [0.0] * n, [0.0] * n
    cache: dict[tuple, Any] = {}

    def cached(key: tuple, make) -> Any:
        if key not in cache:
            cache[key] = make()
        return cache[key]

    envelope = _pad_envelope(BEATS_PER_BAR * BEAT, rate)
    for bar, (root, voicing) in enumerate(CHORDS):
        chord = [0.0] * len(envelope)
        for note in voicing:
            chord[:] = map(operator.add, chord, cached(("pad", note), lambda m=note: _pad_tone(m, len(envelope), rate)))
        _add(warm, at(bar, 0), list(map(operator.mul, chord, envelope)), 0.022)
        for offset, beat, length in BASS:
            tone = cached(
                ("bass", root + offset, length), lambda m=root + offset, ln=length: _bass(hz(m), ln * BEAT, rate)
            )
            _add(warm, at(bar, beat), tone, 0.2 if offset == 0 else 0.13)
        for step, index in enumerate(ARPEGGIO):
            note = voicing[index]
            _add(
                plucks,
                at(bar, step / 2),
                cached(("pluck", note), lambda m=note: _pluck(hz(m), rate)),
                0.05 + 0.02 * (step % 2 == 0),
            )
        kick, snare = cached(("kick",), lambda: _kick(rate)), cached(("snare",), lambda: _noise_hit(rate, 0.07, 0.6, 1))
        shaker = cached(("shaker",), lambda: _noise_hit(rate, 0.025, 0.3, 2))
        for beat in range(BEATS_PER_BAR):
            _add(warm, at(bar, beat), kick if beat % 2 == 0 else snare, 0.16 if beat % 2 == 0 else 0.05)
            _add(warm, at(bar, beat + 0.5), shaker, 0.035)
        for note, beat, length in MELODY[bar]:
            env = cached(("box-env", length), lambda ln=length: _box_envelope(ln * BEAT, rate))
            tone = cached(("box", note, length), lambda m=note, e=env: _music_box(hz(m), e, rate))
            _add(bright, at(bar, beat), tone, 0.2)
        for note, beat in TWINKLES.get(bar, ()):
            _add(bright, at(bar, beat), cached(("bell", note), lambda m=note: _bell(hz(m), rate)), 0.05)

    mix = list(map(operator.add, warm, _echo(plucks, rate, ROOM)))
    mix[:] = map(operator.add, mix, _echo(bright, rate, ECHO))
    peak = max(1e-9, max(map(abs, mix)))
    return list(map((PEAK / peak).__mul__, mix))
