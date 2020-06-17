import collections

from routes1846.cell import Cell, CHICAGO_CELL
from routes1846.tokens import MeatPackingToken, SeaportToken, Station

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
    def place(name, cell, tile, orientation, stations=[], port_value=None, meat_value=None):
        paths = PlacedTile.get_paths(cell, tile, orientation)
        return PlacedTile(name, cell, tile, stations, paths, port_value, meat_value)

    def __init__(self, name, cell, tile, stations=[], paths={}, port_value=None, meat_value=None):
        self.name = name or str(cell)
        self.cell = cell
        self.tile = tile
        self.capacity = tile.capacity
        self._stations = list(stations)
        self._paths = paths
        self.port_value = port_value
        self.port_token = None
        self.meat_value = meat_value
        self.meat_token = None
        
        self.phase = self.tile.phase
        self.is_city = self.tile.is_city
        self.is_z = self.tile.is_z
        self.is_terminal_city = False

    def value(self, railroad, phase):
        return self.tile.value + self.port_bonus(railroad, phase) + self.meat_bonus(railroad, phase)

    def passable(self, enter_cell, railroad):
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

    def place_seaport_token(self, railroad):
        if railroad.is_removed:
            raise ValueError("A removed railroad cannot place Steamboat Company's token: {}".format(railroad.name))

        if self.port_value == 0:
            raise ValueError("It is not legal to place the seaport token on this space ({}).".format(self.cell))

        self.port_token = SeaportToken(self.cell, railroad)

    def place_meat_packing_token(self, railroad):
        if railroad.is_removed:
            raise ValueError("A removed railroad cannot place Meat Packing Company's token: {}".format(railroad.name))

        if self.meat_value == 0:
            raise ValueError("It is not legal to place the meat packing token on this space ({}).".format(self.cell))

        self.meat_token = MeatPackingToken(self.cell, railroad)

    def port_bonus(self, railroad, phase):
        return self.port_value if phase != 4 and self.port_token and self.port_token.railroad == railroad else 0

    def meat_bonus(self, railroad, phase):
        return self.meat_value if phase != 4 and self.meat_token and self.meat_token.railroad == railroad else 0

    def paths(self, enter_from=None, railroad=None):
        if railroad and railroad.is_removed:
            raise ValueError("A removed railroad cannot run routes: {}".format(railroad.name))

        if enter_from:
            return self._paths[enter_from]
        else:
            return tuple(self._paths.keys())

class Chicago(PlacedTile):
    @staticmethod
    def place(tile, exit_cell_to_station={}, port_value=None, meat_value=None):
        paths = PlacedTile.get_paths(CHICAGO_CELL, tile, 0)
        return Chicago(tile, exit_cell_to_station, paths, port_value, meat_value)

    def __init__(self, tile, exit_cell_to_station={}, paths={}, port_value=None, meat_value=None):
        super(Chicago, self).__init__("Chicago", CHICAGO_CELL, tile, list(exit_cell_to_station.values()), paths, port_value, meat_value)
        
        self.exit_cell_to_station = exit_cell_to_station

    def paths(self, enter_from=None, railroad=None):
        paths = list(super(Chicago, self).paths(enter_from))
        if railroad:
            enter_from_station = self.exit_cell_to_station.get(enter_from)
            if enter_from_station:
                if enter_from_station.railroad != railroad:
                    paths = []
            else:
                if not enter_from:
                    station = self.get_station(railroad.name)
                    paths = [self.get_station_exit_cell(station), Cell.from_coord("C5")] if station else []
                else:
                    for exit in paths:
                        station = self.exit_cell_to_station.get(exit)
                        if station and station.railroad != railroad:
                            paths.remove(exit)
        return tuple(paths)

    def add_station(self, railroad, exit_cell):
        if exit_cell not in self.paths():
            raise ValueError("Illegal exit cell for Chicago")

        station = super(Chicago, self).add_station(railroad)
        self.exit_cell_to_station[exit_cell] = station
        return station

    def get_station_exit_cell(self, user_station):
        for exit_cell, station in self.exit_cell_to_station.items():
            if station == user_station:
                return exit_cell
        raise ValueError("The requested station was not found: {}".format(user_station))

    def passable(self, enter_cell, railroad):
        chicago_station = self.exit_cell_to_station.get(enter_cell)
        if chicago_station:
            return chicago_station.railroad == railroad
        else:
            return True