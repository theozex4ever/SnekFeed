<img src="assets/icon.svg" width="64" height="64" alt="">

# Snek Feed

[![CI](https://github.com/theozex4ever/SnekFeed/actions/workflows/ci.yml/badge.svg)](https://github.com/theozex4ever/SnekFeed/actions/workflows/ci.yml)
[![CodeQL](https://github.com/theozex4ever/SnekFeed/actions/workflows/codeql.yml/badge.svg)](https://github.com/theozex4ever/SnekFeed/actions/workflows/codeql.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776ab)

A cozy incremental pet game about feeding **Snek**, a small pastel snake who loves snacks.
Pet Snek for hearts, buy snacks, watch Snek grow longer, and fill the terrarium with cozy things.

Everything is drawn in code and every sound, including the background music, is synthesized at startup.
There are no image or audio assets; `assets/` only holds the app icon and Android splash.

## Run it

```sh
pip install -r requirements.txt
python main.py        # or: python -m snekfeed
```

Python 3.10+ and pygame 2.6.1+.

## Android

Snek Feed runs fullscreen in landscape on Android phones and tablets. The easy way is the debug APK from the
**Android** GitHub Actions workflow: run it by hand or push a `v*` tag, then download the `snekfeed-debug-apk` artifact
and install it (allow installing unknown apps when asked).

Android only accepts an update signed with the same key, and uninstalling deletes Snek's save, so the workflow
won't build without one fixed key. Create a debug keystore once and store it as the `ANDROID_DEBUG_KEYSTORE_BASE64`
repository secret:

```sh
keytool -genkeypair -keystore debug.keystore -alias androiddebugkey -storepass android -keypass android \
  -keyalg RSA -validity 10000 -dname "CN=Android Debug,O=Android,C=US"
base64 < debug.keystore | tr -d '\n' | gh secret set ANDROID_DEBUG_KEYSTORE_BASE64
```

To build it yourself, use [Buildozer](https://buildozer.readthedocs.io/) on Linux, macOS or WSL. On Ubuntu:

```sh
sudo apt install -y git zip unzip openjdk-17-jdk autoconf automake autopoint libtool libltdl-dev \
  pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev gettext
pip install buildozer==1.6.0 setuptools cython==0.29.34   # in a Python 3.10-3.12 venv
buildozer android debug                      # APK lands in bin/
buildozer android debug deploy run logcat    # install on a USB-debugging phone and follow the log
```

The first build downloads the Android SDK and NDK into `~/.buildozer`, asks you to accept the SDK licenses,
and takes a while. Later builds are quick. `buildozer.spec` uses a local pygame 2.6.1 recipe from `tools/p4a-recipes`.

## How to play

| Action | How |
| --- | --- |
| Pet Snek | Click or tap Snek, or hold the mouse button (or a finger) and stroke along Snek's body |
| Feed Snek | Buy a snack in the **Snacks** tab and it drops into the terrarium |
| Catch the golden butterfly | Click or tap it before it flutters away |
| Mute sounds and music | Speaker button, or `M` |
| Quit | `Esc`, the Android back button, or close the window (the game saves itself) |

The game autosaves every 30 seconds and on exit. On Android it also saves when the app goes to the background,
and the home keeps earning while you're away (the same 50% for up to 8 hours as offline progress),
so the welcome-back card greets you when you return.
Saves go to `~/.local/share/snekfeed/save.json` on Linux, `%APPDATA%\snekfeed` on Windows,
`~/Library/Application Support/snekfeed` on macOS, and the app's private storage on Android.
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
  device.py   platform detection and mobile display/input settings
  game.py     main loop that wires it all together
tests/        unit tests for the economy, plus headless end-to-end smoke tests (pytest)
tools/        Android icon and splash renderer, p4a pygame recipe
buildozer.spec  Android build settings
```

## Development

```sh
pip install -r requirements-dev.txt
SNEKFEED_DEBUG=1 python main.py   # H: lots of hearts, L: level up, B: summon butterfly
SNEKFEED_TOUCH=1 python main.py   # preview the phone's touch wording and text sizes
python tools/make_android_assets.py   # after editing assets/icon.svg
```

### Checks

CI runs exactly these, so a green run locally means a green run on GitHub:

```sh
ruff check .                # lint
ruff format --check .       # formatting (run `ruff format .` to fix)
mypy                        # types
pytest --cov                # tests, headless, with a coverage floor
```

Tests run headless: `tests/conftest.py` selects SDL's dummy video and audio drivers, so no window opens.
`tests/test_smoke.py` boots the real `Game` and plays it through the UI, the run loop, shedding and saving.
Tool settings (ruff, mypy, pytest, coverage) all live in `pyproject.toml`.

### Continuous integration

| Job | What it guards |
| --- | --- |
| Lint, format and types | `ruff check`, `ruff format --check` and `mypy` |
| Test | pytest with branch coverage on Linux for Python 3.10 to 3.13, plus Windows and macOS on 3.10 and 3.13 |
| Test (oldest supported pygame) | the `pygame>=2.6.1` promise, by running the suite on pygame 2.6.1 |
| Boot the game | `Game().run()` starts, handles a quit event, saves and exits 0 |
| Dependency audit | `pip-audit` against known vulnerabilities in what actually installs |
| Lint workflows | `actionlint` over `.github/workflows` |
| CodeQL, dependency review | static security analysis and risky-dependency checks on pull requests |
| CI passed | one aggregate check to require in branch protection |

Actions are pinned to commit SHAs and jobs run with read-only permissions.
Dependabot keeps actions and dev tools current, and `.git-blame-ignore-revs` hides the formatting commit from `git blame`.

## Ideas for next increments

- Hats and accessories bought with Shimmer Scales
- A snack journal or collection book, plus achievements
- Day and night cycle in the terrarium
- Seasonal snacks and visiting critters
- Gentle background music
- Multi-buy (x10, max) in the Home tab
