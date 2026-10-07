<img src="assets/icon.svg" width="64" height="64" alt="">

# Snek Feed

A cozy incremental pet game about feeding **Snek**, a small pastel snake who loves snacks.
Pet Snek for hearts, buy snacks, watch Snek grow longer, and fill the terrarium with cozy things.

Everything is drawn in code and every sound is synthesized at startup. There are no image or audio assets.

## Run it

```sh
pip install -r requirements.txt
python main.py        # or: python -m snekfeed
```

Python 3.10+ and pygame 2.5+.

## How to play

| Action | How |
| --- | --- |
| Pet Snek | Click Snek, or hold the mouse button and stroke along Snek's body |
| Feed Snek | Buy a snack in the **Snacks** tab and it drops into the terrarium |
| Catch the golden butterfly | Click it before it flutters away |
| Mute | Speaker button, or `M` |
| Quit | `Esc` or close the window (the game saves itself) |

The game autosaves every 30 seconds and on exit. Saves go to `~/.local/share/snekfeed/save.json` on Linux,
`%APPDATA%\snekfeed` on Windows, and `~/Library/Application Support/snekfeed` on macOS.
Malformed saves are kept in a sibling `save.json.rejected-*.bak` before starting fresh.
If a save cannot be read, has an unsupported version, or cannot be backed up,
the game warns you and protects the existing file by disabling saving for that session.

## The loop

The design borrows the parts that make the best games in this space stick.

1. **Pet for hearts.** Clicking is the starting engine, like the big cookie in *Cookie Clicker*.
   Stroking Snek with the mouse held gives pets too, because it feels nicer than clicking.
2. **Buy snacks, Snek grows.** Snacks give growth points. Every level adds +15% to all hearts, makes Snek
   visibly longer and chubbier, and unlocks the next snack, decor or care item. The next unlocks show as `???`.
3. **Tummy gates feeding.** Snek digests over time. Buying snacks reserves tummy space until they are eaten,
   including while Snek chews, so a full tummy stops further purchases. Hearts aren't the only limit,
   which gives the *Tamagotchi* or *Finch* rhythm of checking back in. A full Snek naps in a food coma.
   Nothing is ever punished. Snek can't get sick or leave.
4. **Mood is a bonus, never a penalty.** Pets and snacks raise mood, which multiplies hearts from 1.0x to 1.5x.
5. **Decorate the home (idle generators).** Pebbles, ferns, warm rocks, glowshrooms, ponds and a cottage earn
   hearts every second and actually appear in the terrarium. This is the *Neko Atsume* "my yard fills up" feeling.
   Prices grow 1.15x per purchase, the classic *Cookie Clicker* curve.
6. **Care upgrades.** Soft Brush doubles pet power. Tummy Rubs speed digestion. Lullabies slow mood decay.
   The Auto Bowl serves snacks while you're idle.
7. **Golden butterfly.** A *Cookie Clicker* "golden cookie" visits every minute or two.
   Catching it gives a heart windfall, a x7 heart blessing, or a rain of free snacks.
8. **Shed skin (prestige).** From Lv 15, Snek can shed. Snek becomes tiny again and the home resets,
   but Snek keeps Shimmer Scales (+5% hearts each, forever) and unlocks a new pastel skin. The last skin is a rainbow.
9. **Offline progress.** The home keeps earning at 50% while you're away, for up to 8 hours.
   A welcome-back card shows what Snek earned.

## Project layout

```
snekfeed/
  config.py   palette, layout and every economy table (start balancing here)
  state.py    game state and economy rules, pygame-free and unit tested
  feeding.py  snack lifecycle, reservations, Auto Bowl and meal credit, pygame-free
  snek.py     Snek's movement, moods and rendering
  habitat.py  terrarium, decor layout, dropped snacks, golden butterfly
  ui.py       HUD, shop panel, shed screen, toasts, hints
  art.py      procedural snack, decor and prop art
  fx.py       particles and popups
  audio.py    synthesized sound effects
  game.py     main loop that wires it all together
tests/        economy tests (pytest)
```

## Development

```sh
python -m pytest
SNEKFEED_DEBUG=1 python main.py   # H: lots of hearts, L: level up, B: summon butterfly
```

## Ideas for next increments

- Hats and accessories bought with Shimmer Scales
- A snack journal or collection book, plus achievements
- Day and night cycle in the terrarium
- Seasonal snacks and visiting critters
- Gentle background music
- Multi-buy (x10, max) in the Home tab
