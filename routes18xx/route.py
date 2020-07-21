import functools
import heapq
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
        self._edges = [{path[k-1], path[k]} for k in range(1, len(path))]

    def merge(self, route):
        return Route.create(self._path + route._path)

    def _best_stops(self, game, train, route_stop_values, station_cities, include=None):
        always_include = [(city, route_stop_values[city]) for city in (include or [])]

        # Find the station city to always include
        always_include.append(max(station_cities.items(), key=lambda tile_and_value: tile_and_value[1]))

        path_towns = [(stop, value) for stop, value in route_stop_values.items() if stop.is_town]
        if game.rules.towns_omit_from_limit:
            always_include.extend(path_towns)

        # Remove from consideration the station city and any stops that should always be included.
        stop_values = route_stop_values.copy()
        for to_include in always_include:
            del stop_values[to_include[0]]

        # The route can collect stops only after accounting for anything marked always collect
        collect = train.collect - len(always_include)
        if game.rules.towns_omit_from_limit:
            collect += len(path_towns)
        best_stops = stop_values if collect == math.inf else dict(heapq.nlargest(collect, stop_values.items(), key=lambda stop_item: stop_item[1]))

        # Add back in the stops marked always collect
        best_stops.update(dict(always_include))

        return best_stops, sum(best_stops.values())

    def value(self, game, board, railroad, train):
        route_stop_values = {tile: tile.value(game, railroad, train) for tile in self if tile.is_stop}
        station_cells = {station.cell for station in board.stations(railroad.name)}
        station_cities = {tile: value for tile, value in route_stop_values.items() if tile.cell in station_cells}

        best_stops, route_value = self._best_stops(game, train, route_stop_values, station_cities)

        # Check if the route runs from east to west.
        termini = [self._path[0], self._path[-1]]
        east_to_west = all(isinstance(tile, (EasternTerminus, WesternTerminus)) for tile in termini) and type(termini[0]) != type(termini[1])
        if east_to_west:
            # There is an east-west route. Confirm that a route including those
            # termini is the highest value route (including bonuses).
            route_stop_values_e2w = route_stop_values.copy()
            route_stop_values_e2w.update({terminus: terminus.value(game, railroad, train, east_to_west) for terminus in termini})

            best_stops_e2w, route_value_e2w = self._best_stops(game, train, route_stop_values_e2w, station_cities, termini)

            return best_stops_e2w if route_value_e2w >= route_value else best_stops
        else:
            return best_stops

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

    def run(self, game, board, train, railroad):
        if railroad.is_removed:
            raise ValueError(f"Cannot run routes for a removed railroad: {railroad.name}")

        visited_stops = self.value(game, board, railroad, train)
        return _RunRoute(self, visited_stops, train)

class _RunRoute(object):
    def __init__(self, route, visited_stop_values, train):
        self._route = route
        self.stop_values = dict.fromkeys(route.stops, 0)
        self.stop_values.update(visited_stop_values)
        self.value = sum(self.stop_values.values())
        self.train = train

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
        return [city for city in self.cities if self.stop_values[city] > 0]

    @property
    def visited_stops(self):
        return [stop for stop in self.stops if self.stop_values[stop] > 0]

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
