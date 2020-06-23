import collections
import json

from routes18xx.cell import Cell
from routes18xx.tokens import Station
import itertools

BASE_BOARD_FILENAME = "base-board.json"

class BoardSpace(object):
    def __init__(self, name, cell, upgrade_level, paths, is_city=False, upgrade_attrs=set(),
            properties={}, is_terminus=False):
        self.name = name or str(cell)
        self.cell = cell
        self.upgrade_level = None if upgrade_level == 4 else upgrade_level  # A built-in upgrade_level 4 tile is similar to a terminus
        self._paths = paths
        self.tokens = []

        self.is_city = is_city
        self.upgrade_attrs = set(upgrade_attrs)
        self.properties = properties
        self.is_terminus = is_terminus

    def paths(self, enter_from=None, railroad=None):
        if railroad and railroad.is_removed:
            raise ValueError("A removed railroad cannot run routes: {}".format(railroad.name))

        if enter_from:
            return self._paths[enter_from]
        else:
            return tuple(self._paths.keys())

    def place_token(self, railroad, TokenType):
        self.tokens.append(TokenType.place(self.cell, railroad, self.properties))

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

    def value(self, game, railroad):
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
    def create(coord, name, upgrade_level=0, edges=[], value=0, capacity=0, upgrade_attrs=set(), properties={}):
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
            return SplitCity(name, cell, upgrade_level, paths, neighbors, value, split_city_capacity, upgrade_attrs, properties=properties)
        else:
            return City(name, cell, upgrade_level, paths, neighbors, value, capacity, upgrade_attrs, properties=properties)

    def __init__(self, name, cell, upgrade_level, paths, neighbors, value, capacity, upgrade_attrs=set(), properties={}):
        super(City, self).__init__(name, cell, upgrade_level, paths, True, upgrade_attrs, properties)

        self.neighbors = neighbors
        self._value = value
        self.capacity = capacity
        self._stations = []

    @property
    def stations(self):
        return tuple(self._stations)

    def value(self, game, railroad):
        return self._value + sum(token.value(game, railroad) for token in self.tokens)

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
    def __init__(self, name, cell, upgrade_level, paths, neighbors, value, capacity, upgrade_attrs, properties):
        super(SplitCity, self).__init__(name, cell, upgrade_level, paths, neighbors, value, capacity, upgrade_attrs, properties)

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

class Terminus(BoardSpace):
    @staticmethod
    def create(coord, name, edges, values, is_east=False, is_west=False, properties={}):
        cell = Cell.from_coord(coord)

        paths = {cell.neighbors[side]: [] for side in edges}
        neighbors = set(paths.keys())

        if is_east:
            return EasternTerminus(name, cell, paths, values, properties)
        elif is_west:
            return WesternTerminus(name, cell, paths, values, properties)
        else:
            return Terminus(name, cell, paths, values, properties)

    def __init__(self, name, cell, paths, neighbors, value_dict, properties):
        super(Terminus, self).__init__(name, cell, None, paths, True, is_terminus=True, properties=properties)

        self.neighbors = neighbors
        self.phase_value = {phase: val for phase, val in value_dict["phase"].items()}

    def value(self, game, railroad):
        for phase, value in sorted(self.phase_value.items(), reverse=True):
            if game.compare_phases(phase) >= 0:
                base_value = value
                break
        else:
            raise ValueError("No value could be found for the provided phase: {}".format(game.current_phase))

        return base_value + sum(token.value(game, railroad) for token in self.tokens)

    def passable(self, enter_cell, railroad):
        return False

class EasternTerminus(Terminus):
    def __init__(self, name, cell, paths, neighbors, value_dict, properties):
        super(EasternTerminus, self).__init__(name, cell, paths, neighbors, value_dict, properties)
        
        self.e2w_bonus = value_dict["e2w-bonus"]

    def value(self, game, railroad, east_to_west=False):
        return super(EasternTerminus, self).value(game, railroad) + (self.e2w_bonus if east_to_west else 0)

class WesternTerminus(Terminus):
    def __init__(self, name, cell, paths, neighbors, value_dict, properties):
        super(WesternTerminus, self).__init__(name, cell, paths, neighbors, value_dict, properties)
        
        self.e2w_bonus = value_dict["e2w-bonus"]

    def value(self, game, railroad, east_to_west=False):
        return super(WesternTerminus, self).value(game, railroad) + (self.e2w_bonus if east_to_west else 0)

def load(game):
    board_tiles = []
    with open(game.get_data_file(BASE_BOARD_FILENAME)) as board_file:
        board_json = json.load(board_file)
        board_tiles.extend([Track.create(coord, **track_args) for coord, track_args in board_json.get("tracks", {}).items()])
        board_tiles.extend([City.create(coord, **city_args) for coord, city_args in board_json.get("cities", {}).items()])
        board_tiles.extend([Terminus.create(coord, **board_edge_args) for coord, board_edge_args in board_json.get("termini", {}).items()])
    return board_tiles