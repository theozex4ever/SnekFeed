"""Render assets/icon.svg into the PNGs buildozer.spec uses for the Android icon and presplash.

Run from anywhere: python tools/make_android_assets.py
"""

import io
import os
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame

ASSETS = Path(__file__).resolve().parent.parent / "assets"
CREAM = (0xFF, 0xF6, 0xEC)  # matches android.presplash_color


def render_svg(size: int) -> pygame.Surface:
    svg = (ASSETS / "icon.svg").read_text(encoding="utf-8")
    svg = svg.replace("<svg ", f'<svg width="{size}" height="{size}" ', 1)
    return pygame.image.load(io.BytesIO(svg.encode("utf-8")), "icon.svg")


def main() -> None:
    pygame.init()
    pygame.image.save(render_svg(512), str(ASSETS / "icon.png"))

    # Same aspect as the game's 1120x720 view; Android fits it to the screen over the cream presplash color.
    splash = pygame.Surface((1120, 720))
    splash.fill(CREAM)
    icon = render_svg(288)
    splash.blit(icon, icon.get_rect(center=splash.get_rect().center))
    pygame.image.save(splash, str(ASSETS / "presplash.png"))
    pygame.quit()
    print(f"wrote {ASSETS / 'icon.png'} and {ASSETS / 'presplash.png'}")


if __name__ == "__main__":
    main()
