import collections
import itertools
import json


_TILE_DB_FILENAME = "tiles-db.json"
_GAME_TILES_FILENAME = "tiles.json"

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
    def create(id, edges, value, quantity, upgrade_level, is_city=False, is_town=False, is_terminus=False, capacity=0, upgrade_attrs=[]):
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

        quantity = int(quantity) if quantity else None

        return Tile(id, paths, int(value), quantity, int(upgrade_level), is_city, is_town, is_terminus, capacity, upgrade_attrs)

    def __init__(self, id, paths, value, quantity, upgrade_level, is_city=False, is_town=False, is_terminus=False, capacity=0, upgrade_attrs=[]):
        self.id = id
        self.paths = {enter: tuple(exits) for enter, exits in paths.items()}
        self.value = value
        self.quantity = quantity
        self.upgrade_level = upgrade_level
        self.is_city = is_city
        self.is_town = is_town
        self.is_terminus = is_terminus
        self.capacity = capacity
        self.upgrade_attrs = sorted(upgrade_attrs)

        self.is_stop = self.is_city or self.is_town or self.is_terminus


def load_all(game):
    with open(game.get_global_data_file(_TILE_DB_FILENAME)) as tiles_file:
        tiles_db_json = json.load(tiles_file)
    with open(game.get_data_file(_GAME_TILES_FILENAME)) as tiles_file:
        game_tiles_json = json.load(tiles_file)

    return {id: Tile.create(id, quantity=quantity, **tiles_db_json[id]) for id, quantity in game_tiles_json.items()}