"""Where the game runs: platform detection and mobile display and input settings.

Android builds come from python-for-android, which sets `ANDROID_PRIVATE`
to the app's private storage. `SNEKFEED_TOUCH=1` previews touch wording and
behaviour on a desktop. Pygame-free so the save rules can use it.
"""

from __future__ import annotations

import os
import sys

ANDROID = hasattr(sys, "getandroidapilevel") or "ANDROID_PRIVATE" in os.environ
TOUCH = ANDROID or os.environ.get("SNEKFEED_TOUCH") == "1"


def press_verb() -> str:
    """The word for a press in hints and prompts."""
    return "Tap" if TOUCH else "Click"


def android_save_root() -> str | None:
    """App-private storage on Android, outside the extracted app code."""
    return os.environ.get("ANDROID_PRIVATE") if ANDROID else None


def configure_sdl() -> None:
    """Set SDL hints that must exist before pygame initializes the display."""
    if ANDROID:
        # SDL reads hints from same-named environment variables; this one is
        # SDL_HINT_ORIENTATIONS and Android honours it too.
        os.environ.setdefault("SDL_IOS_ORIENTATIONS", "LandscapeLeft LandscapeRight")
        os.environ.setdefault("SDL_ANDROID_TRAP_BACK_BUTTON", "1")
        # Smooth rather than blocky upscaling of the SCALED display.
        os.environ.setdefault("PYGAME_FORCE_SCALE", "photo")


def display_flags() -> int:
    """Phones show the fixed layout scaled to fill the screen, letterboxed."""
    import pygame

    return pygame.SCALED | pygame.FULLSCREEN if ANDROID else 0
