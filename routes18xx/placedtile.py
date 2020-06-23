import collections

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
            raise ValueError("Placing tile {} in orientation {} at {} goes off-map.".format(tile.id, orientation, cell))

        return paths

    @staticmethod
    def place(name, cell, tile, orientation, properties={}):
        paths = PlacedTile.get_paths(cell, tile, orientation)
        return PlacedTile(name, cell, tile, paths, properties)

    def __init__(self, name, cell, tile, paths={}, properties={}):
        self.name = name or str(cell)
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
            raise ValueError("{} already has a station in {} ({}).".format(railroad.name, self.name, self.cell))

        if self.capacity <= len(self.stations):
            raise ValueError("{} ({}) cannot hold any more stations.".format(self.name, self.cell))

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
            raise ValueError("A removed railroad cannot run routes: {}".format(railroad.name))

        if enter_from:
            return self._paths[enter_from]
        else:
            return tuple(self._paths.keys())

class SplitCity(PlacedTile):
    @staticmethod
    def _map_branches_to_cells(cell, orientation, branch_to_station):
        branches_to_cells = {}
        for branch, value in branch_to_station.items():
            branch_to_cells = []
            for path in branch:
                path_to_cells = []
                for side in path:
                    rotated_side = int(orientation) if isinstance(side, Cell) else PlacedTile._rotate(side, orientation)
                    path_to_cells.append(cell.neighbors[rotated_side])
                branch_to_cells.append(tuple(path_to_cells))
            branches_to_cells[tuple(branch_to_cells)] = value
        return branches_to_cells

    @staticmethod
    def place(name, cell, tile, orientation, properties={}):
        paths = PlacedTile.get_paths(cell, tile, orientation)
        return SplitCity(name, cell, tile, orientation, paths, properties)

    def __init__(self, name, cell, tile, orientation, paths={}, properties={}):
        super().__init__(name, cell, tile, paths, properties)

        self.capacity = SplitCity._map_branches_to_cells(cell, orientation, self.capacity)
        self.branch_to_station = {key: [] for key in self.capacity.keys()}

    def add_station(self, railroad, branch):
        if self.has_station(railroad.name):
            raise ValueError("{} already has a station in {} ({}).".format(railroad.name, self.name, self.cell))

        split_branch = tuple()
        for branch_key, value in self.capacity.items():
            if branch in branch_key:
                split_branch = branch_key
                break
        else:
            raise ValueError("Attempted to add a station to a non-existant branch of a split city: {}".format(branch))

        if self.capacity[split_branch] <= len(self.branch_to_station[split_branch]):
            raise ValueError("The {} branch of {} ({}) cannot hold any more stations.".format(branch, self.name, self.cell))

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
        raise ValueError("The requested station was not found: {}".format(user_station))