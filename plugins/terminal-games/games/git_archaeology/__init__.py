"""Registers GitArchaeology into the game registry."""

from games.registry import register
from games.git_archaeology.game import GitArchaeology

register("git-archaeology")(GitArchaeology)
