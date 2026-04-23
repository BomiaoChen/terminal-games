from games.registry import register
from games.twenty48.game import Twenty48

register("2048")(Twenty48)
