import collections
import json

from routes1846 import get_data_file
from routes1846.cell import Cell, CHICAGO_CELL
from routes1846.tokens import MeatPackingToken, SeaportToken, Station

BASE_BOARD_FILENAME = "base-board.json"

class BoardSpace(object):
    def __init__(self, name, cell, phase, paths, is_city=False, is_z=False, is_chicago=False, is_terminal_city=False,
            port_value=0, meat_value=0):
        self.name = name or str(cell)
        self.cell = cell
        self.phase = phase = None if phase == 4 else phase  # A built-in phase 4 tile is similar to a terminal city
        self._paths = paths
        self.port_value = port_value
        self.port_token = None
        self.meat_value = meat_value
        self.meat_token = None

        self.is_city = is_city
        self.is_z = is_z
        self.is_chicago = is_chicago
        self.is_terminal_city = is_terminal_city

    def paths(self, enter_from=None, railroad=None):
        if railroad and railroad.is_removed:
            raise ValueError("A removed railroad cannot run routes: {}".format(railroad.name))

        if enter_from:
            return self._paths[enter_from]
        else:
            return tuple(self._paths.keys())

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

class Track(BoardSpace):
    @staticmethod
    def create(coord, edges, phase=None):
        cell = Cell.from_coord(coord)
        
        paths = collections.defaultdict(list)
        for start_edge, end_edge in edges:
            start_cell = cell.neighbors[start_edge]
            end_cell = cell.neighbors[end_edge]

            paths[start_cell].append(end_cell)
            paths[end_cell].append(start_cell)

        return Track(cell, phase, paths)

    def __init__(self, cell, phase, paths):
        super(Track, self).__init__(None, cell, phase, paths)

    def value(self, railroad, phase):
        return 0

class City(BoardSpace):
    @staticmethod
    def create(coord, name, phase=0, edges=[], value=0, capacity=0, is_z=False, port_value=0, meat_value=0):
        cell = Cell.from_coord(coord)

        neighbors = {cell.neighbors[side] for side in edges}

        if cell == CHICAGO_CELL:
            paths = {cell.neighbors[side]: [] for side in edges}
            return Chicago(phase, paths, neighbors, value, capacity, port_value=port_value, meat_value=meat_value)
        else:
            paths = {neighbor: list(neighbors - {neighbor}) for neighbor in neighbors}
            return City(name, cell, phase, paths, neighbors, value, capacity, is_z, False, port_value=port_value, meat_value=meat_value)

    def __init__(self, name, cell, phase, paths, neighbors, value, capacity, is_z=False, is_chicago=False, port_value=0, meat_value=0):
        super(City, self).__init__(name, cell, phase, paths, True, is_z, is_chicago, port_value=port_value, meat_value=meat_value)

        self.neighbors = neighbors
        self._value = value
        self.capacity = capacity
        self._stations = []

    @property
    def stations(self):
        return tuple(self._stations)

    def value(self, railroad, phase):
        return self._value + self.port_bonus(railroad, phase) + self.meat_bonus(railroad, phase)

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

    def passable(self, enter_cell, railroad):
        return self.capacity - len(self.stations) > 0 or self.has_station(railroad.name)

class Chicago(City):
    def __init__(self, phase, paths, neighbors, value, capacity, port_value, meat_value):
        super(Chicago, self).__init__("Chicago", CHICAGO_CELL, phase, paths, neighbors, value, capacity, False, True,
                port_value=port_value, meat_value=meat_value)

        self.exit_cell_to_station = {}

    def add_station(self, railroad, exit_cell):
        station = super(Chicago, self).add_station(railroad)
        self.exit_cell_to_station[exit_cell] = station
        return station

    def passable(self, enter_cell, railroad):
        return False

    def get_station_exit_cell(self, user_station):
        for exit_cell, station in self.exit_cell_to_station.items():
            if station == user_station:
                return exit_cell
        raise ValueError("The requested station was not found: {}".format(user_station))

class TerminalCity(BoardSpace):
    @staticmethod
    def create(coord, name, edges, values, is_east=False, is_west=False, port_value=0, meat_value=0):
        cell = Cell.from_coord(coord)

        paths = {cell.neighbors[side]: [] for side in edges}
        neighbors = set(paths.keys())

        if is_east:
            return EastTerminalCity(name, cell, paths, neighbors, values, port_value=port_value, meat_value=meat_value)
        elif is_west:
            return WestTerminalCity(name, cell, paths, neighbors, values, port_value=port_value, meat_value=meat_value)
        else:
            return TerminalCity(name, cell, paths, neighbors, values, port_value=port_value, meat_value=meat_value)

    def __init__(self, name, cell, paths, neighbors, value_dict, port_value, meat_value):
        super(TerminalCity, self).__init__(name, cell, None, paths, True, is_terminal_city=True, port_value=port_value, meat_value=meat_value)

        self.neighbors = neighbors
        self.phase1_value = value_dict["phase1"]
        self.phase3_value = value_dict["phase3"]

    def value(self, railroad, phase):
        value = self.phase1_value if phase in (1, 2) else self.phase3_value
        return value + self.port_bonus(railroad, phase) + self.meat_bonus(railroad, phase)

    def passable(self, enter_cell, railroad):
        return False

class EastTerminalCity(TerminalCity):
    def __init__(self, name, cell, paths, neighbors, value_dict, port_value, meat_value):
        super(EastTerminalCity, self).__init__(name, cell, paths, neighbors, value_dict, port_value, meat_value)
        
        self.bonus = value_dict["bonus"]

    def value(self, railroad, phase, east_to_west=False):
        return super(EastTerminalCity, self).value(railroad, phase) + (self.bonus if east_to_west else 0)

class WestTerminalCity(TerminalCity):
    def __init__(self, name, cell, paths, neighbors, value_dict, port_value, meat_value):
        super(WestTerminalCity, self).__init__(name, cell, paths, neighbors, value_dict, port_value, meat_value)
        
        self.bonus = value_dict["bonus"]

    def value(self, railroad, phase, east_to_west=False):
        return super(WestTerminalCity, self).value(railroad, phase) + (self.bonus if east_to_west else 0)

def load():
    board_tiles = []
    with open(get_data_file(BASE_BOARD_FILENAME)) as board_file:
        board_json = json.load(board_file)
        board_tiles.extend([Track.create(coord, **track_args) for coord, track_args in board_json["tracks"].items()])
        board_tiles.extend([City.create(coord, **city_args) for coord, city_args in board_json["cities"].items()])
        board_tiles.extend([TerminalCity.create(coord, **board_edge_args) for coord, board_edge_args in board_json["edges"].items()])
    return board_tiles