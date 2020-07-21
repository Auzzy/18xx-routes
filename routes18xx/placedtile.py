import collections
import itertools

from routes18xx import boardtile
from routes18xx.cell import Cell
from routes18xx.tokens import Station

class PlacedTile(object):
    @staticmethod
    def _rotate(side, orientation):
        # ((side num) + (number of times rotated)) mod (number of sides)
        return (side + int(orientation)) % 6

    @staticmethod
    def get_paths(cell, tile, orientation):
        paths = {}
        for start, ends in tile.paths.items():
            start_cell = cell.neighbors[PlacedTile._rotate(start, orientation)]
            paths[start_cell] = tuple([cell.neighbors[PlacedTile._rotate(end, orientation)] for end in ends])

        if None in paths:
            raise ValueError(f"Placing tile {tile.id} in orientation {orientation} at {cell} goes off-map.")

        return paths

    @staticmethod
    def place(cell, tile, orientation, old_space=None):
        if isinstance(old_space, (boardtile.SplitCity, SplitCity)):
            return SplitCity.place(cell, tile, orientation, old_space)

        name = old_space.name if old_space else None
        nickname = old_space.nickname if old_space else None
        properties = old_space.properties if old_space else {}

        paths = PlacedTile.get_paths(cell, tile, orientation)
        return PlacedTile(name, nickname, cell, tile, paths, properties)

    def __init__(self, name, nickname, cell, tile, paths={}, properties={}):
        self.name = name or str(cell)
        self.nickname = nickname or self.name
        self.cell = cell
        self.tile = tile
        self.capacity = tile.capacity
        self._paths = paths
        self.properties = properties

        self._stations = []
        self.tokens = []
        self.upgrade_level = self.tile.upgrade_level
        self.is_city = self.tile.is_city
        self.is_town = self.tile.is_town
        self.is_terminus = self.tile.is_terminus
        self.is_stop = self.tile.is_stop
        self.upgrade_attrs = self.tile.upgrade_attrs

    def value(self, game, railroad, train):
        return self.tile.value + sum(token.value(game, railroad) for token in self.tokens)

    def passable(self, enter_cell, railroad):
        if not self.is_stop or self.is_town:
            return True
        if self.is_terminus:
            return False

        return self.capacity - len(self.stations) > 0 or self.has_station(railroad.name)

    @property
    def stations(self):
        return tuple(self._stations)

    def add_station(self, railroad):
        if self.has_station(railroad.name):
            raise ValueError(f"{railroad.name} already has a station in {self.name} ({self.cell}).")

        if self.capacity <= len(self.stations):
            raise ValueError(f"{self.name} ({self.cell}) cannot hold any more stations.")

        station = Station(self.cell, railroad)
        self._stations.append(station)
        return station

    def get_station(self, railroad_name):
        for station in self._stations:
            if station.railroad.name == railroad_name:
                return station
        return None

    def has_station(self, railroad_name):
        return bool(self.get_station(railroad_name))

    def place_token(self, railroad, TokenType):
        self.tokens.append(TokenType.place(self.cell, railroad, self.properties))

    def paths(self, enter_from=None, railroad=None):
        if railroad and railroad.is_removed:
            raise ValueError(f"A removed railroad cannot run routes: {railroad.name}")

        if enter_from:
            return self._paths[enter_from]
        else:
            return tuple(self._paths.keys())

class SplitCity(PlacedTile):
    @staticmethod
    def _branches_with_unique_exits(branch_dict):
        # Indicating a branch on a split city can be done by a single unqiue
        # neighbor, if such a neighbor exists. This determines what they are,
        # then add them to the branch keys.
        branch_to_cells = {branch_key: tuple(set(itertools.chain.from_iterable(branch_key))) for branch_key in branch_dict}
        unique_exit_cells = {}
        for key, cells in branch_to_cells.items():
            # Get all the neighbors that appear in branches other than the
            # current one, and remove them from the current branch. If any
            # remain, they must be unique.
            # unique_exit_cells[key] = set(cells) - set(itertools.chain.from_iterable(set(branch_to_cells.values()) - {cells}))
            unique_exits = set(cells) - set(itertools.chain.from_iterable(set(branch_to_cells.values()) - {cells}))
            unique_exit_cells[key] = {(cell, ) for cell in unique_exits}

        new_branch_dict = {}
        for old_key, value in branch_dict.items():
            new_key = tuple(set(old_key).union(unique_exit_cells[old_key]))
            new_branch_dict[new_key] = value

        return new_branch_dict

    @staticmethod
    def _map_branches_to_cells(cell, orientation, raw_branch_dict):
        branch_dict = {}
        # Tiles indicate their neighbors by side number relative to upright.
        # Once placed, given the placement orientation, we need to know their
        # neighboring coordinates.
        for raw_branch, value in raw_branch_dict.items():
            branch_paths = []
            for path in raw_branch:
                path_cells = []
                for side in path:
                    rotated_side = int(orientation) if isinstance(side, Cell) else PlacedTile._rotate(side, orientation)
                    path_cells.append(cell.neighbors[rotated_side])
                branch_paths.append(tuple(path_cells))
            branch_dict[tuple(branch_paths)] = value

        return SplitCity._branches_with_unique_exits(branch_dict)

    @staticmethod
    def place(cell, tile, orientation, old_space=None):
        name = old_space.name if old_space else None
        nickname = old_space.nickname if old_space else None
        properties = old_space.properties if old_space else {}

        paths = PlacedTile.get_paths(cell, tile, orientation)
        return SplitCity(name, nickname, cell, tile, orientation, paths, properties)

    def __init__(self, name, nickname, cell, tile, orientation, paths={}, properties={}):
        super().__init__(name, nickname, cell, tile, paths, properties)

        self.capacity = SplitCity._map_branches_to_cells(cell, orientation, self.capacity)
        self.branch_to_station = {key: [] for key in self.capacity.keys()}

    def add_station(self, railroad, branch):
        if self.has_station(railroad.name):
            raise ValueError(f"{railroad.name} already has a station in {self.name} ({self.cell}).")

        split_branch = tuple()
        for branch_key, value in self.capacity.items():
            if branch in branch_key:
                split_branch = branch_key
                break
        else:
            raise ValueError(f"Attempted to add a station to a non-existant branch of a split city: {branch}")

        if self.capacity[split_branch] <= len(self.branch_to_station[split_branch]):
            raise ValueError(f"The {branch} branch of {self.name} ({self.cell}) cannot hold any more stations.")

        station = Station(self.cell, railroad)
        self._stations.append(station)
        self.branch_to_station[split_branch].append(station)
        return station

    def passable(self, enter_cell, railroad):
        for branch, stations in self.branch_to_station.items():
            for path in branch:
                if enter_cell in path:
                    if len(stations) < self.capacity[branch]:
                        return True

                    for station in stations:
                        if station.railroad == railroad:
                            return True
        return False

    def get_station_branch(self, user_station):
        for branch, stations in self.branch_to_station.items():
            if user_station in stations:
                return branch
        raise ValueError(f"The requested station was not found: {user_station}")
