"""
Game registry. Use @register("game-name") to make a Game subclass discoverable.

Usage:
    from games.registry import register

    @register("flappy-bird")
    class FlappyBird(Game):
        ...
"""

_REGISTRY: dict[str, type] = {}


def register(name: str):
    """Class decorator that registers a Game subclass under the given name."""
    def decorator(cls):
        _REGISTRY[name] = cls
        cls._registry_name = name
        return cls
    return decorator


def get(name: str) -> type:
    """Return the Game class registered under name. Raises KeyError if not found."""
    if name not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY)) or "(none)"
        raise KeyError(f"Unknown game: {name!r}. Available: {available}")
    return _REGISTRY[name]


def list_games() -> list[str]:
    """Return sorted list of registered game names."""
    return sorted(_REGISTRY)
