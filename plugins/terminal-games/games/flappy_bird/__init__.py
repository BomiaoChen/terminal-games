"""Registers FlappyBird into the game registry."""

from games.registry import register
from games.flappy_bird.game import FlappyBird

register("flappy-bird")(FlappyBird)
