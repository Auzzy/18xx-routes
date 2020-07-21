import collections
import itertools
import json

from routes18xx.cell import Cell
from routes18xx.tokens import Station

BASE_BOARD_FILENAME = "base-board.json"

class BoardSpace(object):
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

    def __init__(self, name, nickname, cell, upgrade_level, paths, upgrade_attrs=set(), properties={}):
        self.name = name or str(cell)
        self.nickname = nickname or self.name
        self.cell = cell
        self.upgrade_level = None if upgrade_level == 4 else upgrade_level  # A built-in upgrade_level 4 tile is similar to a terminus
        self._paths = paths
        self.tokens = []

        self.is_city = isinstance(self, City)
        self.is_town = isinstance(self, Town)
        self.is_terminus = isinstance(self, Terminus)
        self.is_stop = self.is_city or self.is_terminus or self.is_town
        self.upgrade_attrs = set(upgrade_attrs)
        self.properties = properties

    def paths(self, enter_from=None, railroad=None):
        if railroad and railroad.is_removed:
            raise ValueError(f"A removed railroad cannot run routes: {railroad.name}")

        if enter_from:
            return self._paths[enter_from]
        else:
            return tuple(self._paths.keys())

    def place_token(self, railroad, TokenType):
        self.tokens.append(TokenType.place(self.cell, railroad, self.properties))

    def passable(self, enter_cell, railroad):
        return True

class Track(BoardSpace):
    @staticmethod
    def create(cell, edges, upgrade_level=None):
        paths = BoardSpace._calc_paths(cell, edges)

        return Track(cell, upgrade_level, paths)

    def __init__(self, cell, upgrade_level, paths):
        super().__init__(None, None, cell, upgrade_level, paths)

    def value(self, game, railroad, train):
        return 0

class Town(BoardSpace):
    @staticmethod
    def create(cell, name, nickname=None, upgrade_level=0, edges=[], value=0, upgrade_attrs=set(), properties={}):
        paths = BoardSpace._calc_paths(cell, edges)

        return Town(name, nickname, cell, upgrade_level, paths, value, upgrade_attrs, properties)

    def __init__(self, name, nickname, cell, upgrade_level, paths, value, upgrade_attrs=set(), properties={}):
        super().__init__(name, nickname, cell, upgrade_level, paths, upgrade_attrs, properties)

        self._value = value

    def value(self, game, railroad, train):
        return self._value + sum(token.value(game, railroad) for token in self.tokens)

class City(BoardSpace):
    @staticmethod
    def create(cell, name, nickname=None, upgrade_level=0, edges=[], value=0, capacity=0, upgrade_attrs=set(), properties={}):
        paths = BoardSpace._calc_paths(cell, edges)

        if isinstance(capacity, dict):
            return SplitCity.create(name, nickname, cell, upgrade_level, paths, value, capacity, upgrade_attrs, properties)
        else:
            return City(name, nickname, cell, upgrade_level, paths, value, capacity, upgrade_attrs, properties)

    def __init__(self, name, nickname, cell, upgrade_level, paths, value, capacity, upgrade_attrs=set(), properties={}):
        super().__init__(name, nickname, cell, upgrade_level, paths, upgrade_attrs, properties)

        self._value = value
        self.capacity = capacity
        self._stations = []

    @property
    def stations(self):
        return tuple(self._stations)

    def value(self, game, railroad, train):
        return self._value + sum(token.value(game, railroad) for token in self.tokens)

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

    def passable(self, enter_cell, railroad):
        return self.capacity - len(self.stations) > 0 or self.has_station(railroad.name)

class SplitCity(City):
    @staticmethod
    def _branches_with_unique_exits(branch_dict):
        # Indicating a branch on a split city can be done by a single unqiue
        # neighbor, if such a neighbor exists. This determines what they are,
        # then add them to the branch keys.
        branch_to_sides = {branch_key: tuple(set(itertools.chain.from_iterable(branch_key))) for branch_key in branch_dict}
        unique_exit_sides = {}
        for key, sides in branch_to_sides.items():
            # Get all the neighbors that appear in branches other than the
            # current one, and remove them from the current branch. If any
            # remain, they must be unique.
            unique_exits = set(sides) - set(itertools.chain.from_iterable(set(branch_to_sides.values()) - {sides}))
            unique_exit_sides[key] = {(side, ) for side in unique_exits}

        new_branch_dict = {}
        for old_key, value in branch_dict.items():
            new_key = tuple(set(old_key).union(unique_exit_sides[old_key]))
            new_branch_dict[new_key] = value

        return new_branch_dict

    @staticmethod
    def create(name, nickname, cell, upgrade_level, paths, value, capacity, upgrade_attrs, properties):
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

        split_city_capacity = SplitCity._branches_with_unique_exits(split_city_capacity)

        return SplitCity(name, nickname, cell, upgrade_level, paths, value, split_city_capacity, upgrade_attrs, properties)

    def __init__(self, name, nickname, cell, upgrade_level, paths, value, capacity, upgrade_attrs, properties):
        super().__init__(name, nickname, cell, upgrade_level, paths, value, capacity, upgrade_attrs, properties)

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

class Terminus(BoardSpace):
    @staticmethod
    def create(cell, name, edges, values, nickname=None, is_east=False, is_west=False, properties={}):
        paths = {cell.neighbors[side]: [] for side in edges}

        if is_east:
            return EasternTerminus(name, nickname, cell, paths, values, properties)
        elif is_west:
            return WesternTerminus(name, nickname, cell, paths, values, properties)
        else:
            return Terminus(name, nickname, cell, paths, values, properties)

    def __init__(self, name, nickname, cell, paths, value_dict, properties):
        super().__init__(name, nickname, cell, None, paths, properties=properties)

        self.phase_value = {phase: val for phase, val in value_dict.get("phase", {}).items()}
        self.train_value = {train: val for train, val in value_dict.get("train", {}).items()}

    def value(self, game, railroad, train):
        if train.name in self.train_value:
            base_value = self.train_value[train.name]
        else:
            for phase, value in sorted(self.phase_value.items(), reverse=True):
                if game.compare_phases(phase) >= 0:
                    base_value = value
                    break
            else:
                raise ValueError(f"No value could be found for the provided phase: {game.current_phase}")

        return base_value + sum(token.value(game, railroad) for token in self.tokens)

    def passable(self, enter_cell, railroad):
        return False

class EasternTerminus(Terminus):
    def __init__(self, name, nickname, cell, paths, value_dict, properties):
        super().__init__(name, nickname, cell, paths, value_dict, properties)
        
        self.e2w_bonus = value_dict["e2w-bonus"]

    def value(self, game, railroad, train, east_to_west=False):
        return super().value(game, railroad, train) + (self.e2w_bonus if east_to_west else 0)

class WesternTerminus(Terminus):
    def __init__(self, name, nickname, cell, paths, value_dict, properties):
        super().__init__(name, nickname, cell, paths, value_dict, properties)
        
        self.e2w_bonus = value_dict["e2w-bonus"]

    def value(self, game, railroad, train, east_to_west=False):
        return super().value(game, railroad, train) + (self.e2w_bonus if east_to_west else 0)

def load(game, board):
    board_tiles = []
    with open(game.get_data_file(BASE_BOARD_FILENAME)) as board_file:
        board_json = json.load(board_file)
        board_tiles.extend([Track.create(board.cell(coord), **track_args) for coord, track_args in board_json.get("tracks", {}).items()])
        board_tiles.extend([Town.create(board.cell(coord), **town_args) for coord, town_args in board_json.get("towns", {}).items()])
        board_tiles.extend([City.create(board.cell(coord), **city_args) for coord, city_args in board_json.get("cities", {}).items()])
        board_tiles.extend([Terminus.create(board.cell(coord), **board_edge_args) for coord, board_edge_args in board_json.get("termini", {}).items()])
    return board_tiles