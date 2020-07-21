import importlib
import json
import os

from routes18xx import tiles
from routes18xx.rules import Rules

_DIR_NAME = "data"
_DATA_ROOT_DIR = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), _DIR_NAME)))

_GAME_FILENAME = "game.json"

class Game:
    @staticmethod
    def get_game_data_file(game_name, filename):
        return os.path.join(_DATA_ROOT_DIR, game_name, filename)

    @staticmethod
    def load(game_name):
        with open(Game.get_game_data_file(game_name, _GAME_FILENAME)) as game_file:
            game_json = json.load(game_file)

        rules = Rules.load(game_json)

        game = Game(game_name, game_json["phases"], game_json.get("privates_close", {}), rules)

        game.tiles = tiles.load_all(game)

        return game

    def __init__(self, game_name, phases, privates_close, rules, tiles={}):
        self.name = game_name
        self.phases = phases
        self.privates_close = privates_close
        self.rules = rules
        self.tiles = tiles

        self.current_phase = None

    def get_data_file(self, filename):
        return Game.get_game_data_file(self.name, filename)

    def capture_phase(self, railroads):
        self.current_phase = self.detect_phase(railroads)
        return self.current_phase

    def detect_phase(self, railroads):
        all_train_phases = [train.phase for railroad in railroads.values() for train in railroad.trains]
        return str(max(all_train_phases, key=lambda phase: self.phases.index(phase))) if all_train_phases else self.phases[0]

    def compare_phases(self, other, current=None):
        current = current or self.current_phase
        if not current:
            raise ValueError("Did not provide the current phase, and it has not been previously captured.")

        other_id = self.phases.index(other)
        current_id = self.phases.index(current)
        if current_id > other_id:
            return 1
        elif current_id < other_id:
            return -1
        else:
            return 0

    def private_is_closed(self, name, phase=None):
        close_phase = self.privates_close.get(name)
        if not close_phase:
            return False
        return self.compare_phases(close_phase, phase) >= 0

    def filter_invalid_routes(self, routes, board, railroad):
        return self._hook("filter_invalid_routes", routes, routes, board, railroad)

    def hook_route_set_values(self, route_set, railroad):
        default_values = {route: route.value for route in route_set}
        return self._hook("hook_route_set_values", default_values, route_set, railroad)

    def hook_route_max_value(self, route, railroad):
        return self._hook("hook_route_max_value", route.value, route, railroad)

    def get_game_submodule(self, name):
        try:
            return importlib.import_module(f"{self._get_game_module_name()}.{name}")
        except ModuleNotFoundError:
            return None

    def _get_game_module_name(self):
        return f"routes18xx.games.routes{self.name}"

    def _get_game_module(self):
        try:
            return importlib.import_module(self._get_game_module_name())
        except ModuleNotFoundError:
            return None

    def _hook(self, hook_name, retval, *args):
        game_module = self._get_game_module()
        if game_module and hasattr(game_module, hook_name):
            hook_func = getattr(game_module, hook_name)
            return hook_func(*args)
        else:
            return retval
