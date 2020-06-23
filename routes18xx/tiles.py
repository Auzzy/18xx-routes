import collections
import itertools
import json


_TILE_FILENAME = "tiles.json"
_TILES = {}

class Tile(object):
    @staticmethod
    def _calc_paths(edges):
        paths = collections.defaultdict(list)
        for exits in edges:
            if isinstance(exits, list):
                for path in itertools.permutations(exits, 2):
                    paths[path[0]].append(path[1])
            else:
                paths[exits] = []
        return paths

    @staticmethod
    def create(id, edges, value, quantity, upgrade_level, is_city=False, is_town=False, is_terminus=False, capacity=0, upgrade_attrs=set()):
        paths = Tile._calc_paths(edges)

        if isinstance(capacity, dict):
            split_city_capacity = {}
            for branch_paths_str, branch_capacity in capacity.items():
                branch_path_dict = Tile._calc_paths(json.loads(branch_paths_str))
                branch_path_list = []
                for entrance, exits in branch_path_dict.items():
                    if not exits:
                        branch_paths = [(entrance, )]
                    else:
                        branch_paths = [(entrance, exit) for exit in exits]
                    branch_path_list.extend(tuple(branch_paths))

                split_city_capacity[tuple(branch_path_list)] = branch_capacity
            capacity = split_city_capacity

        return Tile(id, paths, int(value), int(quantity), int(upgrade_level), is_city, is_town, is_terminus, capacity, upgrade_attrs)

    def __init__(self, id, paths, value, quantity, upgrade_level, is_city=False, is_town=False, is_terminus=False, capacity=0, upgrade_attrs=set()):
        self.id = id
        self.paths = {enter: tuple(exits) for enter, exits in paths.items()}
        self.value = value
        self.quantity = quantity
        self.upgrade_level = upgrade_level
        self.is_city = is_city
        self.is_town = is_town
        self.is_terminus = is_terminus
        self.capacity = capacity
        self.upgrade_attrs = set(upgrade_attrs)

        self.is_stop = self.is_city or self.is_town or self.is_terminus


def _load_all(game):
    with open(game.get_data_file(_TILE_FILENAME)) as tiles_file:
        tiles_json = json.load(tiles_file)

    return {int(id): Tile.create(int(id), **args) for id, args in tiles_json.items()}

def get_tile(game, tile_id):
    global _TILES
    if not _TILES:
        _TILES = _load_all(game)

    return _TILES.get(int(tile_id))