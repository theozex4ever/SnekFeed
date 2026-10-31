"""python-for-android's pygame recipe, moved from its pinned pygame 2.1.0 to 2.6.1.

Upstream's 2.1.0 is listed as broken against p4a's current SDL2. The PyPI sdist is used
instead of the GitHub tag archive because it ships the Cython-generated C sources.
"""

from pythonforandroid.recipes.pygame import Pygame2Recipe


class PygameRecipe(Pygame2Recipe):
    version = "2.6.1"
    url = "https://files.pythonhosted.org/packages/source/p/pygame/pygame-{version}.tar.gz"
    md5sum = "cb6bf42a449b0bb1f53c534bcbcc220c"


recipe = PygameRecipe()
