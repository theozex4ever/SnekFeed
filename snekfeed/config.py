"""Static game data: palette, layout, and the economy tables.

Everything tunable about the game lives here so balancing never means
hunting through rendering or logic code.
"""

from dataclasses import dataclass

# --- Window & layout -------------------------------------------------------

WIDTH, HEIGHT = 1120, 720
FPS = 60
TITLE = "Snek Feed"

HUD_H = 92  # top bar over the habitat
PANEL_W = 380  # shop panel on the right
HABITAT = (16, HUD_H + 8, WIDTH - PANEL_W - 32, HEIGHT - HUD_H - 24)  # x, y, w, h
PANEL = (WIDTH - PANEL_W - 8, 16, PANEL_W - 8, HEIGHT - 32)
MIN_TOUCH_TEXT = 14  # phones scale the layout down, so fine print gets a floor

# --- Pastel palette --------------------------------------------------------

CREAM = (255, 246, 236)
INK = (92, 74, 90)  # soft cocoa-plum for text
INK_SOFT = (150, 130, 148)
WHITE = (255, 255, 255)
PINK = (255, 158, 181)
PINK_DEEP = (240, 120, 150)
PEACH = (255, 200, 168)
BUTTER = (255, 238, 160)
MINT = (184, 230, 201)
MINT_DEEP = (130, 200, 160)
SKY = (189, 224, 254)
LILAC = (217, 199, 245)
LILAC_DEEP = (170, 145, 220)
GRASS = (214, 240, 222)
GRASS_DARK = (196, 230, 206)
DISABLED = (232, 224, 230)
SHADOW = (60, 40, 60)


# --- Snacks: bought with hearts, feed XP and fill Snek's tummy -------------


@dataclass(frozen=True)
class Snack:
    key: str
    name: str
    cost: float
    xp: float
    fill: float  # tummy points
    unlock_level: int
    color: tuple
    blurb: str


SNACKS = [
    Snack("berry", "Strawberry", 10, 5, 12, 1, (255, 140, 160), "A juicy classic."),
    Snack("blue", "Blueberries", 75, 30, 15, 3, (150, 170, 240), "Tiny, round, perfect."),
    Snack("egg", "Quail Egg", 600, 180, 20, 6, (255, 240, 215), "Speckled and fancy."),
    Snack("dump", "Dumpling", 5_000, 1_000, 25, 10, (250, 230, 200), "Warm and squishy."),
    Snack("cake", "Shortcake", 40_000, 6_000, 30, 15, (255, 210, 225), "A birthday every day."),
    Snack("mochi", "Star Mochi", 320_000, 36_000, 35, 20, (220, 205, 255), "Tastes like stardust."),
]

# --- Cozy home decor: idle generators that also appear in the habitat ------


@dataclass(frozen=True)
class Decor:
    key: str
    name: str
    base_cost: float
    rate: float  # hearts per second each
    unlock_level: int
    blurb: str


DECOR_COST_GROWTH = 1.15  # the Cookie Clicker constant; it just feels right

DECOR = [
    Decor("pebble", "Mossy Pebble", 15, 0.2, 1, "Snek likes to lean on it."),
    Decor("fern", "Tiny Fern", 110, 1.0, 2, "Rustles when Snek wiggles by."),
    Decor("rock", "Warm Rock", 1_200, 8.0, 4, "Sunbathing spot."),
    Decor("mush", "Glowshroom", 13_000, 47.0, 7, "A soft glow at night."),
    Decor("pond", "Little Pond", 140_000, 260.0, 11, "Splish splash."),
    Decor("house", "Snek Cottage", 1_500_000, 1_400.0, 16, "A home of its own."),
]

# --- Care upgrades: levelled, each level multiplies cost by `cost_growth` ---


@dataclass(frozen=True)
class Care:
    key: str
    name: str
    base_cost: float
    cost_growth: float
    max_level: int
    unlock_level: int
    blurb: str


CARE = [
    Care("brush", "Soft Brush", 50, 6.0, 25, 1, "Pets give x2 hearts."),
    Care("rub", "Tummy Rubs", 200, 4.0, 10, 3, "Digest snacks 30% faster."),
    Care("bowl", "Auto Bowl", 2_500, 5.0, 8, 5, "Serves a snack when Snek is peckish."),
    Care("song", "Lullabies", 800, 5.0, 10, 4, "Mood fades 25% slower."),
]

# --- Growth -----------------------------------------------------------------

XP_BASE = 20
XP_GROWTH = 1.6
LEVEL_BONUS = 0.15  # +15% hearts per level beyond 1 (additive)
TUMMY_MAX = 100.0
DIGEST_PER_SEC = 1.0
PECKISH_AT = 30.0  # below this Snek asks for food
MOOD_DECAY_PER_SEC = 0.25
MOOD_PER_PET = 1.5
MOOD_PER_SNACK = 6.0
MOOD_MAX = 100.0
MAX_SNACKS_ON_FLOOR = 8

# --- Golden butterfly (the "golden cookie") ---------------------------------

BUTTERFLY_MIN_GAP = 50.0
BUTTERFLY_MAX_GAP = 120.0
BUTTERFLY_LIFETIME = 13.0
FRENZY_SECONDS = 20.0
FRENZY_MULT = 7.0

# --- Shedding (prestige) ----------------------------------------------------

SHED_MIN_LEVEL = 15
SCALE_BONUS = 0.05  # +5% hearts per Shimmer Scale, forever

# --- Offline progress ---------------------------------------------------------

OFFLINE_EFFICIENCY = 0.5
OFFLINE_CAP_SECONDS = 8 * 3600

# --- Skins: unlocked one per shed --------------------------------------------


@dataclass(frozen=True)
class Skin:
    key: str
    name: str
    body: tuple
    belly: tuple
    spots: tuple


SKINS = [
    Skin("mint", "Mint", (160, 220, 180), (230, 248, 225), (130, 198, 158)),
    Skin("peach", "Peach", (255, 190, 160), (255, 236, 220), (240, 160, 130)),
    Skin("lilac", "Lilac", (200, 180, 240), (240, 232, 255), (170, 150, 220)),
    Skin("sky", "Sky", (160, 205, 245), (230, 243, 255), (130, 180, 230)),
    Skin("butter", "Butter", (250, 225, 140), (255, 248, 215), (230, 200, 110)),
    Skin("rose", "Rose", (250, 170, 195), (255, 230, 238), (230, 140, 170)),
    Skin("rainbow", "Rainbow", (0, 0, 0), (255, 250, 245), (0, 0, 0)),  # special-cased
]
