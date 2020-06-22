import itertools

from routes18xx import boardtile, games
from routes18xx.cell import Cell, board_cells, initialize_cells
from routes18xx.placedtile import PlacedTile, SplitCity
from routes18xx.tokens import Station

class Board(object):
    @staticmethod
    def load(game):
        initialize_cells(game)

        board_tiles = {board_tile.cell: board_tile for board_tile in boardtile.load(game)}
        return Board(board_tiles)

    def __init__(self, board_tiles):
        self._board_tiles = board_tiles
        self._placed_tiles = {}

    def place_tile(self, coord, tile, orientation):
        cell = Cell.from_coord(coord)

        if int(orientation) not in range(0, 6):
            raise ValueError("Orientation out of range. Expected between 0 and 5, inclusive. Got {}.".format(orientation))

        old_tile = self.get_space(cell)
        self._validate_place_tile_space_type(tile, old_tile)
        self._validate_place_tile_neighbors(cell, tile, orientation)
        if old_tile:
            self._validate_place_tile_upgrade(old_tile, cell, tile, orientation)

            if isinstance(old_tile, (boardtile.SplitCity, SplitCity)):
                self._placed_tiles[cell] = SplitCity.place(old_tile.name, cell, tile, orientation, old_tile.properties)
            else:
                self._placed_tiles[cell] = PlacedTile.place(old_tile.name, cell, tile, orientation, old_tile.properties)
        else:
            self._placed_tiles[cell] = PlacedTile.place(None, cell, tile, orientation)

    def place_station(self, coord, railroad):
        cell = Cell.from_coord(coord)
        tile = self.get_space(cell)
        if not tile.is_city:
            raise ValueError("{} is not a city, so it cannot have a station.".format(cell))

        if isinstance(tile, (boardtile.SplitCity, SplitCity)):
            raise ValueError("Since {} is a split city tile, please use Board.place_split_station().".format(coord))

        tile.add_station(railroad)

    def place_split_station(self, coord, railroad, branch):
        cell = Cell.from_coord(coord)
        space = self.get_space(cell)
        if not space.is_city:
            raise ValueError("{} is not a city, so it cannot have a station.".format(cell))

        path = tuple([Cell.from_coord(coord) for coord in branch])
        space.add_station(railroad, path)

    def place_token(self, coord, railroad, TokenType):
        if railroad.is_removed:
            raise ValueError("A removed railroad cannot place a token: {}".format(railroad.name))

        current_cell = Cell.from_coord(coord)
        self.get_space(current_cell).place_token(railroad, TokenType)

    def stations(self, railroad_name=None):
        all_tiles = list(self._placed_tiles.values()) + list(self._board_tiles.values())
        all_stations = itertools.chain.from_iterable([tile.stations for tile in all_tiles if isinstance(tile, (boardtile.City, PlacedTile))])
        if railroad_name:
            return tuple([station for station in all_stations if station.railroad.name == railroad_name])
        else:
            return tuple(all_stations)

    def get_space(self, cell):
        return self._placed_tiles.get(cell) or self._board_tiles.get(cell)

    def validate(self):
        invalid = []
        for cell, placed_tile in self._placed_tiles.items():
            if not placed_tile.stations:
                for neighbor_cell in placed_tile.paths():
                    neighbor = self.get_space(neighbor_cell)
                    if neighbor and cell in neighbor.paths():
                        break
                else:
                    invalid.append(cell)

        if invalid:
            invalid_str = ", ".join([str(cell) for cell in invalid])
            raise ValueError("Tiles at the following spots have no neighbors and no stations: {}".format(invalid_str))

    def _validate_place_tile_space_type(self, tile, old_tile):
        if old_tile and old_tile.is_terminus:
            raise ValueError("Cannot upgrade the terminus.")

        if old_tile:
            if tile.is_stop:
                if old_tile.upgrade_attrs != tile.upgrade_attrs:
                    old_tile_type = ", ".join(old_tile.upgrade_attrs)
                    tile_type = ", ".join(tile.upgrade_attrs)
                    raise ValueError("Tried to mix a {} tile and a {} tile.".format(old_tile_type, tile_type))
        else:
            if tile.is_stop:
                raise ValueError("Tried to place a non-track tile on a track space.")

    def _validate_place_tile_neighbors(self, cell, tile, orientation):
        for neighbor in PlacedTile.get_paths(cell, tile, orientation):
            neighbor_space = self.get_space(neighbor)
            if neighbor_space and  neighbor_space.upgrade_level is None and cell not in neighbor_space.paths():
                tile_type = "terminus" if neighbor_space.is_terminus else "pre-printed gray tile"
                raise ValueError("Placing tile {} on {} in orientation {} runs into the side of the {} at {}.".format(
                    tile.id, cell, orientation, tile_type, neighbor_space.cell))

    def _validate_place_tile_upgrade(self, old_tile, cell, new_tile, orientation):
        if old_tile:
            if old_tile.upgrade_level is None:
                raise ValueError("{} cannot be upgraded.".format(cell))
            elif old_tile.upgrade_level >= new_tile.upgrade_level:
                raise ValueError("{}: Going from upgrade level {} to {} is not an upgrade.".format(cell, old_tile.upgrade_level, new_tile.upgrade_level))

            for old_start, old_ends in old_tile._paths.items():
                old_paths = tuple([(old_start, end) for end in old_ends])
                new_paths = tuple([(start, end) for start, ends in PlacedTile.get_paths(cell, new_tile, orientation).items() for end in ends])
                if not all(old_path in new_paths for old_path in old_paths):
                    raise ValueError("The new tile placed on {} does not preserve all the old paths.".format(cell))