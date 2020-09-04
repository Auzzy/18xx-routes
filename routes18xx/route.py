import collections
import functools
import heapq
import itertools
import math
import numbers

from routes18xx.boardtile import EasternTerminus, WesternTerminus

class Route(object):
    @staticmethod
    def create(path):
        return Route(tuple(path))

    @staticmethod
    def empty():
        return Route(tuple())

    @staticmethod
    def single(tile):
        return Route.create((tile, ))

    def __init__(self, path):
        self._path = tuple(path)
        self._cell_to_space = {space.cell: space for space in self._path if space}
        self._edges = [{path[k-1], path[k]} for k in range(1, len(path))]

    def merge(self, route):
        return Route.create(self._path + route._path)

    def overlap(self, other):
        for edge in self._edges:
            if edge in other._edges:
                return True
        return False

    def subroutes(self, start):
        if not self.contains_cell(start):
            return Route.empty()

        start_index = [index for index, tile in enumerate(self._path) if tile.cell == start][0]
        backwards_subroutes = {Route.create(self._path[index:start_index + 1]) for index in range(start_index, -1, -1)}
        forwards_subroutes = {Route.create(self._path[start_index:index]) for index in range(start_index + 1, len(self._path) + 1)}
        subroutes = backwards_subroutes.union(forwards_subroutes)
        return [subroute for subroute in subroutes if len(subroute.stops) >= 2]

    def contains_cell(self, cell):
        return cell in [tile.cell for tile in self]

    def contains_station(self, station):
        if not self.contains_cell(station.cell):
            return False

        if station.branch:
            # If the station is on a branch, check that the path uses the correct branch, by confirming its neighbors
            # (if it has any) are part of the branch paths.
            station_space = self._cell_to_space[station.cell]
            station_space_index = self._path.index(station_space)

            branches = station_space.get_station_branch(station)
            spaces = {self._cell_to_space.get(cell) for cell in itertools.chain.from_iterable(branches)} - {None}
            if station_space_index != 0 and self._path[station_space_index - 1] not in spaces:
                return False
            if station_space_index != len(self._path) - 1 and self._path[station_space_index + 1] not in spaces:
                return False

        return True

    @property
    def cities(self):
        return [tile for tile in self._path if tile.is_city]

    @property
    def stops(self):
        return [tile for tile in self._path if tile.is_stop]

    def __iter__(self):
        return iter(self._path)

    def __bool__(self):
        return bool(self._path)
    
    def __len__(self):
        return len(self._path)

    def __hash__(self):
        return hash(tuple(sorted([tile.cell for tile in self._path])))

    def __eq__(self, other):
        return isinstance(other, Route) and set(other._path) == set(self._path)

    def __str__(self):
        return ", ".join([str(tile.cell) for tile in self])

    def _best_stops(self, game, train, route_stop_values, station_cities, include=None):
        always_include = (include or []).copy()

        # Find the station city to always include
        always_include.append(max(station_cities.items(), key=lambda tile_and_value: tile_and_value[1])[0])

        best_stops = train.route_best_stops(game, self, route_stop_values, always_include)

        # Add back in the stops marked always collect
        best_stops = {**best_stops, **{stop: route_stop_values[stop] for stop in always_include}}

        return _RunRoute(self, best_stops, train)

    def run(self, game, board, train, railroad):
        if railroad.is_removed:
            raise ValueError(f"Cannot run routes for a removed railroad: {railroad.name}")

        route_stop_values = train.route_stop_values(
            {tile: tile.value(game, railroad, train) for tile in self.stops}
        )
        station_cells = {station.cell for station in board.stations(railroad.name)}
        station_cities = {tile: value for tile, value in route_stop_values.items() if tile.cell in station_cells}

        run_route = self._best_stops(game, train, route_stop_values, station_cities)

        # Check if the route runs from east to west.
        termini = [self._path[0], self._path[-1]]
        east_to_west = {EasternTerminus, WesternTerminus} == set(map(type, termini))
        if east_to_west:
            # There is an east-west route. Confirm that a route including those
            # termini is the highest value route (including bonuses).
            route_stop_values_e2w = route_stop_values.copy()
            route_stop_values_e2w.update({terminus: terminus.value(game, railroad, train, east_to_west) for terminus in termini})

            run_route_e2w = self._best_stops(game, train, route_stop_values_e2w, station_cities, termini)

            return run_route_e2w if run_route_e2w.value >= run_route.value else run_route
        else:
            return run_route

class _RunRoute(object):
    def __init__(self, route, stop_value_dict, train):
        self._route = route
        self.train = train
        self.stop_values = stop_value_dict
        self.value = train.route_value(route, self.stop_values)

    def overlap(self, other):
        return self._route.overlap(other._route)

    def adjust_value(self, value_add):
        self.value += value_add

    @property
    def cities(self):
        return self._route.cities

    @property
    def stops(self):
        return self._route.stops

    @property
    def visited_cities(self):
        return [city for city in self.cities if city in self.stop_values]

    @property
    def visited_stops(self):
        return [stop for stop in self.stops if stop in self.stop_values]

    def __str__(self):
        return str(self._route)

    def __iter__(self):
        return iter(self._route)

@functools.total_ordering
class RouteSet:
    @staticmethod
    def create(game, railroad, routes):
        route_values = game.hook_route_set_values(routes, railroad)
        route_proxies = [_RouteProxy(route, value) for route, value in route_values.items()]
        return RouteSet(route_proxies)

    def __init__(self, routes):
        self.routes = routes
        self.value = sum(route.value for route in self.routes)

    def __iter__(self):
        return iter(self.routes)

    def __bool__(self):
        return bool(self.routes)

    def __gt__(self, other):
        if isinstance(other, numbers.Integral):
            return self.value > other
        elif isinstance(other, RouteSet):
            return self.value > other.value
        return NotImplemented

    def __eq__(self, other):
        if isinstance(other, numbers.Integral):
            return self.value == other
        elif isinstance(other, RouteSet):
            return self.value == other.value
        return NotImplemented

class _RouteProxy:
    def __init__(self, route, value):
        self.route = route
        self.value = value

    def __getattribute__(self, name):
        # The special attributes allow Python to pickle the class correctly,
        # for returning it through a promise. And __dict__ is needed for the
        # class to work properly.
        if name == "value" or \
                name in ("__dict__", "__setstate__", "__getstate__",
                        "__class__", "__reduce__", "__reduce_ex__",
                        "__getnewargs__", "__getnewargs_ex__"):
            return super().__getattribute__(name)
        else:
            return super().__getattribute__("route").__getattribute__(name)

    def __str__(self):
        return str(self.__dict__["route"])
    
    def __iter__(self):
        return iter(self.__dict__["route"])
