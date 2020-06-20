import importlib
import json
import os

_DIR_NAME = "data"
_DATA_ROOT_DIR = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), _DIR_NAME)))

class Game:
    @staticmethod
    def load(game):
        return Game(game)

    def __init__(self, game,):
        self.game = game

    def get_data_file(self, filename):
        return os.path.join(_DATA_ROOT_DIR, self.game, filename)

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