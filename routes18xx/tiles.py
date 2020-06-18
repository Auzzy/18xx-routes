import collections
import json

from routes18xx import get_data_file


_TILE_FILENAME = "tiles.json"
_TILES = {}

class Tile(object):
    @staticmethod
    def create(id, edges, value, quantity, upgrade_level, is_city=False, capacity=0, upgrade_attrs=set()):
        
        paths = collections.defaultdict(list)
        if is_city and "chicago" not in upgrade_attrs:
            exits = set(edges)
            for side in exits:
                paths[side].extend(list(exits - {side}))
        else:
            for edge in edges:
                paths[edge[0]].append(edge[1])
                paths[edge[1]].append(edge[0])

        return Tile(id, paths, int(value), int(quantity), int(upgrade_level), is_city, capacity, upgrade_attrs)

    def __init__(self, id, paths, value, quantity, phase, is_city=False, capacity=0, upgrade_attrs=set()):
        self.id = id
        self.paths = {enter: tuple(exits) for enter, exits in paths.items()}
        self.value = value
        self.quantity = quantity
        self.upgrade_level = upgrade_level
        self.is_city = is_city
        self.capacity = capacity
        self.upgrade_attrs = set(upgrade_attrs)


def _load_all(game):
    with open(get_data_file(game, _TILE_FILENAME)) as tiles_file:
        tiles_json = json.load(tiles_file)

    return {int(id): Tile.create(int(id), **args) for id, args in tiles_json.items()}

def get_tile(game, tile_id):
    global _TILES
    if not _TILES:
        _TILES = _load_all(game)

    return _TILES.get(int(tile_id))