"""
Games package. Importing this package registers all available games.
To add a new game: create games/<name>/__init__.py and games/<name>/game.py,
then add `from . import <name>` below.
"""

from . import flappy_bird  # noqa: F401
