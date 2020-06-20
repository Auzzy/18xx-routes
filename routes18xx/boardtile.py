import collections
import json

from routes18xx.cell import Cell
from routes18xx.tokens import MeatPackingToken, SeaportToken, Station
import itertools

BASE_BOARD_FILENAME = "base-board.json"

class BoardSpace(object):
    def __init__(self, name, cell, upgrade_level, paths, is_city=False, upgrade_attrs=set(), is_terminal_city=False,
            port_value=0, meat_value=0):
        self.name = name or str(cell)
        self.cell = cell
        self.upgrade_level = None if upgrade_level == 4 else upgrade_level  # A built-in upgrade_level 4 tile is similar to a terminal city
        self._paths = paths
        self.port_value = port_value
        self.port_token = None
        self.meat_value = meat_value
        self.meat_token = None

        self.is_city = is_city
        self.upgrade_attrs = set(upgrade_attrs)
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
    def create(coord, edges, upgrade_level=None):
        cell = Cell.from_coord(coord)
        
        paths = collections.defaultdict(list)
        for start_edge, end_edge in edges:
            start_cell = cell.neighbors[start_edge]
            end_cell = cell.neighbors[end_edge]

            paths[start_cell].append(end_cell)
            paths[end_cell].append(start_cell)

        return Track(cell, upgrade_level, paths)

    def __init__(self, cell, upgrade_level, paths):
        super(Track, self).__init__(None, cell, upgrade_level, paths)

    def value(self, railroad, phase):
        return 0

class City(BoardSpace):
    @staticmethod
    def _calc_paths(cell, edges):
        paths = collections.defaultdict(list)
        for exits in edges:
            if isinstance(exits, list):
                for path in itertools.permutations(exits, 2):
                    paths[cell.neighbors[path[0]]].append(cell.neighbors[path[1]])
            else:
                paths[cell.neighbors[exits]] = []
        return paths

    @staticmethod
    def create(coord, name, upgrade_level=0, edges=[], value=0, capacity=0, upgrade_attrs=set(), port_value=0, meat_value=0):
        cell = Cell.from_coord(coord)

        neighbors = set()
        for sides in edges:
            if isinstance(sides, list):
                neighbors.update({cell.neighbors[side] for side in sides})
            else:
                neighbors.add(cell.neighbors[sides])

        paths = City._calc_paths(cell, edges)

        if isinstance(capacity, dict):
            split_city_capacity = {}
            for branch_paths_str, branch_capacity in capacity.items():
                branch_path_dict = City._calc_paths(cell, json.loads(branch_paths_str))
                branch_path_list = []
                for entrance, exits in branch_path_dict.items():
                    if not exits:
                        branch_paths = [(entrance, )]
                    else:
                        branch_paths = [(entrance, exit) for exit in exits]
                    branch_path_list.extend(tuple(branch_paths))

                split_city_capacity[tuple(branch_path_list)] = branch_capacity
            return SplitCity(name, cell, upgrade_level, paths, neighbors, value, split_city_capacity, upgrade_attrs, port_value=port_value, meat_value=meat_value)
        else:
            return City(name, cell, upgrade_level, paths, neighbors, value, capacity, upgrade_attrs, port_value=port_value, meat_value=meat_value)

    def __init__(self, name, cell, upgrade_level, paths, neighbors, value, capacity, upgrade_attrs=set(), port_value=0, meat_value=0):
        super(City, self).__init__(name, cell, upgrade_level, paths, True, upgrade_attrs, port_value=port_value, meat_value=meat_value)

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

class SplitCity(City):
    def __init__(self, name, cell, upgrade_level, paths, neighbors, value, capacity, upgrade_attrs, port_value, meat_value):
        super(SplitCity, self).__init__(name, cell, upgrade_level, paths, neighbors, value, capacity, upgrade_attrs,
                port_value=port_value, meat_value=meat_value)

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

def load(game):
    board_tiles = []
    with open(game.get_data_file(BASE_BOARD_FILENAME)) as board_file:
        board_json = json.load(board_file)
        board_tiles.extend([Track.create(coord, **track_args) for coord, track_args in board_json.get("tracks", {}).items()])
        board_tiles.extend([City.create(coord, **city_args) for coord, city_args in board_json.get("cities", {}).items()])
        board_tiles.extend([TerminalCity.create(coord, **board_edge_args) for coord, board_edge_args in board_json.get("edges", {}).items()])
    return board_tiles