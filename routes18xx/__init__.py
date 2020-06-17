import os.path

_DIR_NAME = "data"
_DATA_ROOT_DIR = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(__file__), _DIR_NAME)))

def get_data_file(game, filename):
    return os.path.join(_DATA_ROOT_DIR, game, filename)

from routes18xx.find_best_routes import find_best_routes, LOG