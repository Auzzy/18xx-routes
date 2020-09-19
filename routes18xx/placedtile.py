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
            raise ValueError(f"Placing tile {tile.id} in orientation {orientation} at {cell} is illegal.")

        return paths

    @staticmethod
    def place(cell, tile, orientation, old_space=None):
        # Determining if the new tile is a split city allows placements which
        # convert a split city into a regular city, as can happen in many games.
        if isinstance(tile.capacity, dict):
            if tile.is_city:
                return SplitCity.place(cell, tile, orientation, old_space)
            elif tile.is_town:
                return SplitTown.place(cell, tile, orientation, old_space)

        name = old_space.name if old_space else None
        nickname = old_space.nickname if old_space else None
        properties = old_space.properties if old_space else {}
        home = old_space.home if old_space and old_space.is_city else []
        reserved = old_space.reserved if old_space and old_space.is_city else []

        paths = PlacedTile.get_paths(cell, tile, orientation)
        return PlacedTile(name, nickname, cell, tile, paths, home, reserved, properties)

    def __init__(self, name, nickname, cell, tile, paths={}, home=[], reserved=[], properties={}):
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

        self.home = home or []
        self.reserved = reserved or []

    def value(self, game, railroad, train):
        return self.tile.value + sum(token.value(game, railroad) for token in self.tokens)

    def passable(self, enter_cell, exit_cell, railroad):
        # Towns and track tiles are always passable, as is starting from this tile.
        if not enter_cell or not self.is_stop or self.is_town:
            return True
        # A terminus is never passable (unless the start of a path, but that's handled above)
        if self.is_terminus:
            return False

        return self.capacity - len(self.stations) > 0 or self.has_station(railroad.name)

    @property
    def stations(self):
        return tuple(self._stations)

    def _assert_preserves_reservations(self, game, railroad):
        def _preserves_space(reservations):
            unclaimed_reservations = [name for name in reservations if not self.has_station(name)]
            return railroad.name in reservations \
                or not unclaimed_reservations \
                or len(self.stations) + len(unclaimed_reservations) + 1 <= self.capacity

        reservations = self.home.copy()
        if game.rules.stations.reserved_until and game.compare_phases(game.rules.stations.reserved_until) < 0:
            reservations.extend(self.reserved.copy())

        if not _preserves_space(reservations):
            unclaimed_home = [name for name in self.home if not self.has_station(name)]
            if unclaimed_home:
                raise ValueError(f"{self.name} ({self.cell}) must leave space for its home railroad(s): {', '.join(unclaimed_home)}.")
            else:
                unclaimed_reservations = [name for name in self.reserved if not self.has_station(name)]
                raise ValueError(f"{self.name} ({self.cell}) must leave space for its reservation(s): {', '.join(unclaimed_reservations)}.")

    def add_station(self, game, railroad):
        if self.has_station(railroad.name):
            raise ValueError(f"{railroad.name} already has a station in {self.name} ({self.cell}).")

        if len(self.stations) >= self.capacity:
            raise ValueError(f"{self.name} ({self.cell}) cannot hold any more stations.")

        self._assert_preserves_reservations(game, railroad)

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
        home = old_space.home if old_space and old_space.is_city else []
        reserved = old_space.reserved if old_space and old_space.is_city else []

        paths = PlacedTile.get_paths(cell, tile, orientation)
        return SplitCity(name, nickname, cell, tile, orientation, paths, properties)

    def __init__(self, name, nickname, cell, tile, orientation, paths={}, home=[], reserved=[], properties={}):
        super().__init__(name, nickname, cell, tile, paths, home, reserved, properties)

        self.capacity = SplitCity._map_branches_to_cells(cell, orientation, self.capacity)
        self.branches = set(self.capacity.keys())
        self.branch_to_station = {key: [] for key in self.branches}

    def add_station(self, game, railroad, branch):
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

        station = Station(self.cell, railroad, branch)
        self._stations.append(station)
        self.branch_to_station[split_branch].append(station)
        return station

    def passable(self, enter_cell, exit_cell, railroad):
        # Starting from a city is always legal
        if not enter_cell:
            return True

        for branch, stations in self.branch_to_station.items():
            # Only look at the branch formed by the enter and exit cells
            if (enter_cell, exit_cell) not in branch:
                continue

            # Check branch capacity
            if len(stations) < self.capacity[branch]:
                return True

            # Check if this branch has a station belonging to the railroad
            for station in stations:
                if station.railroad == railroad:
                    return True

        return False

    def get_station_branch(self, user_station):
        for branch, stations in self.branch_to_station.items():
            if user_station in stations:
                return branch
        raise ValueError(f"The requested station was not found: {user_station}")

class SplitTown(PlacedTile):
    @staticmethod
    def place(cell, tile, orientation, old_space=None):
        name = old_space.name if old_space else None
        nickname = old_space.nickname if old_space else None
        properties = old_space.properties if old_space else {}

        paths = PlacedTile.get_paths(cell, tile, orientation)
        return SplitTown(name, nickname, cell, tile, orientation, paths, properties)

    def __init__(self, name, nickname, cell, tile, orientation, paths={}, properties={}):
        super().__init__(name, nickname, cell, tile, paths, properties)

        self.capacity = SplitCity._map_branches_to_cells(cell, orientation, self.capacity)
        self.branches = set(self.capacity.keys())