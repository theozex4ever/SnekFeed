"""Tiny synthesized sound effects and background music. No audio files and no numpy needed.

If no audio device is available the game simply runs silently.
"""

from __future__ import annotations

import array
import math
import random
import threading

import pygame

from . import music

RATE = 22050


def _env(i: int, n: int, attack: float = 0.01) -> float:
    a = max(1, int(n * attack))
    if i < a:
        return i / a
    return (1 - (i - a) / max(1, n - a)) ** 2


def _tone(f0: float, f1: float, dur: float, vol: float = 0.3, harmonics: float = 0.15) -> list[float]:
    n = int(RATE * dur)
    out, phase = [], 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * (i / n)
        phase += math.tau * f / RATE
        s = math.sin(phase) + harmonics * math.sin(2 * phase)
        out.append(s * vol * _env(i, n))
    return out


def _noise(dur: float, vol: float = 0.2, smooth: float = 0.6) -> list[float]:
    n = int(RATE * dur)
    out, prev = [], 0.0
    for i in range(n):
        prev = prev * smooth + random.uniform(-1, 1) * (1 - smooth)
        out.append(prev * vol * 3 * _env(i, n, 0.05))
    return out


def _pcm(samples: list[float], channels: int) -> bytes:
    mono = array.array("h", [int(max(-1.0, min(1.0, s)) * 32767) for s in samples])
    if channels == 1:
        return mono.tobytes()
    data = array.array("h", [0]) * (len(mono) * channels)
    for c in range(channels):
        data[c::channels] = mono
    return data.tobytes()


_music_cache: dict[tuple[int, int], bytes] = {}
_music_lock = threading.Lock()


def _music_pcm(rate: int, channels: int) -> bytes:
    """The rendered loop, synthesized once per process for each output format."""
    with _music_lock:
        if (rate, channels) not in _music_cache:
            _music_cache[rate, channels] = _pcm(music.compose(rate), channels)
        return _music_cache[rate, channels]


def _seq(*parts: list[float], gap: float = 0.0) -> list[float]:
    out: list[float] = []
    for p in parts:
        out += p + [0.0] * int(RATE * gap)
    return out


class Audio:
    MUSIC_VOLUME = 0.6
    MUSIC_FADE_MS = 2500

    def __init__(self) -> None:
        self.enabled = True
        self._muted = False
        self.sounds: dict[str, list[pygame.mixer.Sound]] = {}
        self._music: pygame.mixer.Channel | None = None
        self._music_pcm: bytes | None = None
        try:
            global RATE
            if not pygame.mixer.get_init():
                pygame.mixer.init(RATE, -16, 1, 512)
            freq, size, self.channels = pygame.mixer.get_init()
            if size != -16:
                raise TypeError("unsupported sample format")
            RATE = freq
            self._build()
            pygame.mixer.set_reserved(1)  # sound effects never steal the music's channel
            self._music = pygame.mixer.Channel(0)
        except (pygame.error, TypeError):
            self.enabled = False
            return
        # The loop takes a few seconds to synthesize, so render it off the main thread and start it in `update`.
        threading.Thread(target=self._render_music, args=(RATE, self.channels), daemon=True).start()

    def _render_music(self, rate: int, channels: int) -> None:
        self._music_pcm = _music_pcm(rate, channels)

    @property
    def muted(self) -> bool:
        return self._muted

    @muted.setter
    def muted(self, value: bool) -> None:
        self._muted = value
        if self._music is not None:
            if value:
                self._music.pause()
            else:
                self._music.unpause()

    def update(self) -> None:
        """Start the music once its render finishes. Call every frame."""
        if self._music_pcm is None or self._music is None:
            return
        pcm, self._music_pcm = self._music_pcm, None
        try:
            self._music.set_volume(self.MUSIC_VOLUME)
            self._music.play(pygame.mixer.Sound(buffer=pcm), loops=-1, fade_ms=self.MUSIC_FADE_MS)
            if self._muted:
                self._music.pause()
        except pygame.error:
            self._music = None

    def _make(self, samples: list[float]) -> pygame.mixer.Sound:
        return pygame.mixer.Sound(buffer=_pcm(samples, self.channels))

    def _build(self) -> None:
        note = lambda n: 440 * 2 ** ((n - 69) / 12)  # noqa: E731 - midi -> Hz
        self.sounds = {
            "pet": [self._make(_tone(f, f * 1.35, 0.09, 0.22)) for f in (620, 700, 780, 880)],
            "plop": [self._make(_tone(420, 190, 0.12, 0.3))],
            "buy": [self._make(_seq(_tone(note(79), note(79), 0.08, 0.2), _tone(note(84), note(84), 0.14, 0.2)))],
            "munch": [self._make(_seq(_noise(0.05, 0.25), _noise(0.05, 0.2), gap=0.04))],
            "level": [self._make(_seq(*[_tone(note(n), note(n), 0.12, 0.2) for n in (72, 76, 79, 84)]))],
            "flutter": [self._make(_seq(*[_tone(note(n), note(n), 0.07, 0.14) for n in (88, 91, 96)]))],
            "deny": [self._make(_tone(240, 200, 0.12, 0.2))],
            "shed": [
                self._make(
                    _seq(*[_tone(note(n), note(n) * 1.01, 0.1, 0.18) for n in (60, 64, 67, 71, 72, 76, 79, 84, 88)])
                )
            ],
        }

    def play(self, name: str) -> None:
        if self.enabled and not self.muted and name in self.sounds:
            random.choice(self.sounds[name]).play()
