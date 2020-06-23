import importlib
import json
import os

_DIR_NAME = "data"
_DATA_ROOT_DIR = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), _DIR_NAME)))

_GAME_FILENAME = "game.json"

class Rules:
    @staticmethod
    def load(rules):
        town_rules = rules.get("towns", {})
        return Rules(town_rules)

    def __init__(self, town_rules):
        self.towns_omit_from_limit = town_rules.get("omit_from_limit", False)

class Game:
    @staticmethod
    def _get_data_file(game, filename):
        return os.path.join(_DATA_ROOT_DIR, game, filename)

    @staticmethod
    def load(game):
        with open(Game._get_data_file(game, _GAME_FILENAME)) as game_file:
            game_json = json.load(game_file)

        rules = Rules.load(game_json.get("rules", {}))

        return Game(game, game_json["phases"], game_json.get("privates_close", {}), rules)

    def __init__(self, game, phases, privates_close, rules):
        self.game = game
        self.phases = phases
        self.privates_close = privates_close
        self.rules = rules

        self.current_phase = None

    def get_data_file(self, filename):
        return os.path.join(_DATA_ROOT_DIR, self.game, filename)

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

    def private_is_closed(self, name):
        close_phase = self.privates_close.get(name)
        if not close_phase:
            return False
        return self.compare_phases(close_phase) >= 0

    def filter_invalid_routes(self, routes, board, railroad):
        return self._hook("filter_invalid_routes", routes, routes, board, railroad)

    def hook_after_route_sets(self, route_sets, railroad):
        return self._hook("hook_after_route_sets", route_sets, route_sets, railroad)

    def get_game_submodule(self, name):
        try:
            return importlib.import_module("{}.{}".format(self._get_game_module_name(), name))
        except ModuleNotFoundError:
            return None

    def _get_game_module_name(self):
        return "routes18xx.games.routes{}".format(self.game)

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