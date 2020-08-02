import collections
import itertools

from routes18xx import boardtile, cell, games
from routes18xx.placedtile import PlacedTile, SplitCity
from routes18xx.tokens import Station

class Board(object):
    @staticmethod
    def load(game):
        cells = cell.load(game)
        board = Board(game, cells)
        board._board_tiles = {board_tile.cell: board_tile for board_tile in boardtile.load(game, board)}
        return board

    def __init__(self, game, cells):
        self.game = game
        self._cells = cells

        self._board_tiles = {}
        self._placed_tiles = {}

    def cell(self, coord):
        if len(coord) < 2 or len(coord) > 3:
            raise ValueError(f"Provided invalid coord: {coord}")

        row, col = coord[0], int(coord[1:])
        if row not in self._cells or col not in self._cells[row]:
            raise ValueError(f"The coordinate provided is not legal: {coord}")

        return self._cells[row][col]

    @property
    def cells(self):
        for row, columns in self._cells.items():
            for column, cell in columns.items():
                yield cell

    def place_tile(self, coord, tile, orientation):
        cell = self.cell(coord)

        if int(orientation) not in range(0, 6):
            raise ValueError(f"Orientation out of range. Expected between 0 and 5, inclusive. Got {orientation}.")

        old_tile = self.get_space(cell)
        self._validate_place_tile_space_type(tile, old_tile)
        self._validate_place_tile_neighbors(cell, tile, orientation)
        if old_tile:
            self._validate_place_tile_upgrade(old_tile, cell, tile, orientation)

        self._placed_tiles[cell] = PlacedTile.place(cell, tile, orientation, old_tile)

    def place_station(self, game, coord, railroad):
        cell = self.cell(coord)
        tile = self.get_space(cell)
        if not tile.is_city:
            raise ValueError(f"{cell} is not a city, so it cannot have a station.")

        if isinstance(tile, (boardtile.SplitCity, SplitCity)):
            raise ValueError(f"Since {coord} is a split city tile, please use Board.place_split_station().")

        tile.add_station(game, railroad)

    def place_split_station(self, game, coord, railroad, branch):
        cell = self.cell(coord)
        space = self.get_space(cell)
        if not space.is_city:
            raise ValueError(f"{cell} is not a city, so it cannot have a station.")

        branch_cells = tuple([self.cell(coord) for coord in branch])
        space.add_station(game, railroad, branch_cells)

    def place_token(self, coord, railroad, TokenType):
        if railroad.is_removed:
            raise ValueError(f"A removed railroad cannot place a token: {railroad.name}")

        current_cell = self.cell(coord)
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
        self._validate_tiles_connected()
        self._validate_tiles_upgrade_level()
        self._validate_tiles_quantity()

    def _validate_tiles_connected(self):
        invalid = []
        for cell, placed_tile in sorted(self._placed_tiles.items()):
            if not placed_tile.stations:
                for neighbor_cell in placed_tile.paths():
                    neighbor = self.get_space(neighbor_cell)
                    if neighbor and cell in neighbor.paths():
                        break
                else:
                    invalid.append(str(cell))

        if invalid:
            raise ValueError(f"Tiles at the following spots have no neighbors and no stations: {', '.join(invalid)}")

    def _validate_tiles_upgrade_level(self):
        invalid = []
        for cell, placed_tile in sorted(self._placed_tiles.items()):
            if self.game.compare_phases(self.game.upgrade_phases[placed_tile.upgrade_level]) < 0:
                invalid.append(str(cell))

        if invalid:
            raise ValueError(f"Tiles at the following spots cannot be placed until a later phase: {', '.join(invalid)}")

    def _validate_tiles_quantity(self):
        tile_count = collections.Counter([placed.tile for placed in self._placed_tiles.values()])
        invalid = []
        for tile, count in tile_count.items():
            if tile.quantity and tile.quantity < count:
                invalid = [tile.id]

        if invalid:
            raise ValueError(f"Found too many of the following tiles on the board: {', '.join(invalid)}")

    def _validate_place_tile_space_type(self, tile, old_tile):
        if old_tile:
            if old_tile.is_terminus:
                raise ValueError("Cannot upgrade the terminus.")
            elif old_tile.is_city != tile.is_city:
                raise ValueError("A city tile must be placed on a city board space.")
            elif old_tile.is_town != tile.is_town:
                raise ValueError("A town tile must be placed on a town board space.")
            elif tile.upgrade_attrs not in old_tile.upgrade_attrs:
                old_tile_type = " OR ".join(str(upgrade_attr) for upgrade_attr in old_tile.upgrade_attrs)
                raise ValueError(f"Tried to upgrade to a mismatched type. Expected: {old_tile_type}. Got: {tile.upgrade_attrs}.")
        else:
            if tile.is_stop:
                raise ValueError("Tried to place a non-track tile on a track space.")

    def _validate_place_tile_neighbors(self, cell, tile, orientation):
        for neighbor in PlacedTile.get_paths(cell, tile, orientation):
            neighbor_space = self.get_space(neighbor)
            if neighbor_space and  neighbor_space.upgrade_level is None and cell not in neighbor_space.paths():
                tile_type = "terminus" if neighbor_space.is_terminus else "pre-printed gray tile"
                raise ValueError(
                    f"Placing tile {tile.id} on {cell} in orientation {orientation} runs into the side of the {tile_type} at {neighbor_space.cell}.")

    def _validate_place_tile_upgrade(self, old_tile, cell, new_tile, orientation):
        if old_tile:
            if old_tile.upgrade_level is None:
                raise ValueError(f"{cell} cannot be upgraded.")
            elif old_tile.upgrade_level >= new_tile.upgrade_level:
                raise ValueError(f"{cell}: Going from upgrade level {old_tile.upgrade_level} to {new_tile.upgrade_level} is not an upgrade.")

            for old_start, old_ends in old_tile._paths.items():
                old_paths = tuple([(old_start, end) for end in old_ends])
                new_paths = tuple([(start, end) for start, ends in PlacedTile.get_paths(cell, new_tile, orientation).items() for end in ends])
                if not all(old_path in new_paths for old_path in old_paths):
                    raise ValueError(f"The new tile placed on {cell} does not preserve all the old paths.")
