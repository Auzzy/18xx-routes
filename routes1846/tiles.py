import collections
import json

from routes1846 import get_data_file


_TILE_FILENAME = "tiles.json"
_TILES = {}

class Tile(object):
    @staticmethod
    def create(id, edges, value, quantity, phase, is_city=False, is_z=False, is_chicago=False):
        
        paths = collections.defaultdict(list)
        if is_city and not is_chicago:
            exits = set(edges)
            for side in exits:
                paths[side].extend(list(exits - {side}))
        else:
            for edge in edges:
                paths[edge[0]].append(edge[1])
                paths[edge[1]].append(edge[0])

        return Tile(id, paths, int(value), int(quantity), int(phase), is_city, is_z, is_chicago)

    def __init__(self, id, paths, value, quantity, phase, is_city=False, is_z=False, is_chicago=False):
        self.id = id
        self.paths = {enter: tuple(exits) for enter, exits in paths.items()}
        self.value = value
        self.quantity = quantity
        self.phase = phase
        self.is_city = is_city
        self.is_z = is_z
        self.is_chicago = is_chicago

        if self.is_chicago:
            self.capacity = 4
        elif self.is_z:
            self.capacity = min(self.phase, 3)
        elif self.is_city:
            self.capacity = min(self.phase, 2)
        else:
            self.capacity = 0


def _load_all():
    with open(get_data_file(_TILE_FILENAME)) as tiles_file:
        tiles_json = json.load(tiles_file)

    return {int(id): Tile.create(int(id), **args) for id, args in tiles_json.items()}

def get_tile(tile_id):
    global _TILES
    if not _TILES:
        _TILES = _load_all()

    return _TILES.get(int(tile_id))