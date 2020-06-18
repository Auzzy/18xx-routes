import itertools

from routes18xx import boardtile
from routes18xx.cell import Cell, get_chicago_cell, board_cells
from routes18xx.placedtile import Chicago, PlacedTile
from routes18xx.tokens import Station

class Board(object):
    @staticmethod
    def load(game):
        board_tiles = {board_tile.cell: board_tile for board_tile in boardtile.load(game)}
        return Board(board_tiles)

    def __init__(self, board_tiles):
        self._board_tiles = board_tiles
        self._placed_tiles = {}

    def place_tile(self, coord, tile, orientation):
        cell = Cell.from_coord(coord)
        if cell == get_chicago_cell() or tile.is_chicago:
            raise ValueError("Since Chicago ({}) is a special tile, please use Board.place_chicago().".format(get_chicago_cell()))

        if int(orientation) not in range(0, 6):
            raise ValueError("Orientation out of range. Expected between 0 and 5, inclusive. Got {}.".format(orientation))

        old_tile = self.get_space(cell)
        self._validate_place_tile_space_type(tile, old_tile)
        self._validate_place_tile_neighbors(cell, tile, orientation)
        if old_tile:
            self._validate_place_tile_upgrade(old_tile, cell, tile, orientation)

            self._placed_tiles[cell] = PlacedTile.place(old_tile.name, cell, tile, orientation, port_value=old_tile.port_value, meat_value=old_tile.meat_value)
        else:
            self._placed_tiles[cell] = PlacedTile.place(None, cell, tile, orientation)

    def place_station(self, coord, railroad):
        cell = Cell.from_coord(coord)
        if cell == get_chicago_cell():
            raise ValueError("Since Chicago ({}) is a special tile, please use Board.place_chicago_station().".format(get_chicago_cell()))

        tile = self.get_space(cell)
        if not tile.is_city:
            raise ValueError("{} is not a city, so it cannot have a station.".format(cell))

        tile.add_station(railroad)

    def place_chicago(self, tile):
        cell = get_chicago_cell()
        old_tile = self._placed_tiles.get(cell) or self._board_tiles.get(cell)
        if not old_tile.phase or old_tile.phase >= tile.phase:
            raise ValueError("{}: Going from phase {} to phase {} is not an upgrade.".format(cell, old_tile.phase, tile.phase))

        new_tile = Chicago.place(tile, old_tile.exit_cell_to_station, port_value=old_tile.port_value, meat_value=old_tile.meat_value)
        self._placed_tiles[cell] = new_tile

    def place_chicago_station(self, railroad, exit_side):
        chicago = self.get_space(get_chicago_cell())
        exit_cell = get_chicago_cell().neighbors[exit_side]
        chicago.add_station(railroad, exit_cell)

    def place_seaport_token(self, coord, railroad):
        if railroad.is_removed:
            raise ValueError("A removed railroad cannot place Steamboat Company's token: {}".format(railroad.name))

        current_cell = Cell.from_coord(coord)
        for cell in board_cells():
            space = self.get_space(cell)
            if space and space.port_token and cell != current_cell:
                raise ValueError("Cannot place the seaport token on {}. It's already been placed on {}.".format(current_cell, cell))

        self.get_space(current_cell).place_seaport_token(railroad)

    def place_meat_packing_token(self, coord, railroad):
        if railroad.is_removed:
            raise ValueError("A removed railroad cannot place Meat Packing Company's token: {}".format(railroad.name))

        current_cell = Cell.from_coord(coord)
        for cell in board_cells():
            space = self.get_space(cell)
            if space and space.meat_token and cell != current_cell:
                raise ValueError("Cannot place the meat packing token on {}. It's already been placed on {}.".format(current_cell, cell))

        self.get_space(current_cell).place_meat_packing_token(railroad)

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
        if old_tile and old_tile.is_terminal_city:
            raise ValueError("Cannot upgrade the terminal cities.")

        if not old_tile or not old_tile.is_city:
            if tile.is_city or tile.is_z:
                tile_type = "Z city" if tile.is_z else "city"
                raise ValueError("{} is a track space, but you placed a {} ({}).".format(cell, tile_type, tile.id))
        elif old_tile.is_z:
            if not tile.is_z:
                tile_type = "city" if tile.is_city else "track"
                raise ValueError("{} is a Z city space, but you placed a {} ({}).".format(cell, tile_type, tile.id))
        elif old_tile.is_city:
            if not tile.is_city or tile.is_z:
                tile_type = "Z city" if tile.is_z else "track"
                raise ValueError("{} is a regular city space, but you placed a {} ({}).".format(cell, tile_type, tile.id))

    def _validate_place_tile_neighbors(self, cell, tile, orientation):
        for neighbor in PlacedTile.get_paths(cell, tile, orientation):
            neighbor_space = self.get_space(neighbor)
            if neighbor_space and  neighbor_space.upgrade_level is None and cell not in neighbor_space.paths():
                tile_type = "terminal city" if neighbor_space.is_terminal_city else "pre-printed gray tile"
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