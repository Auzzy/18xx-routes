import collections
import functools
import heapq
import json
import math

_TRAINS_FILENAME = "trains.json"

@functools.total_ordering
class Train:
    @staticmethod
    def _get_name(visit):
        return str(visit)

    @staticmethod
    def normalize_train_str(train_str):
        return Train._get_name(int(train_str.strip()))

    @staticmethod
    def create(phase, visit=math.inf, name=None, **kwargs):
        if name and name == "diesel":
            return Diesel.create(phase)
        if kwargs.get("multiplier", 0) == 2:
            return Double.create(phase, visit, name)
        if "collect" in kwargs:
            return Selection.create(phase, kwargs["collect"], visit, name)

        name = name or Train._get_name(visit)

        return Train(phase, visit, name)

    def __init__(self, phase, visit, name):
        self.phase = phase
        self.visit = visit
        self.name = name

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.visit)

    def __eq__(self, other):
        return isinstance(other, Train) and \
                self.visit == other.visit

    def __gt__(self, other):
        return self.visit > other.visit

    def is_end_of_route(self, game, board, railroad, enter_from, cell, visited_paths, visited_stops):
        tile = board.get_space(cell)
        return tile.is_stop \
            and (not game.rules.routes.omit_towns_from_limit or not tile.is_town) \
            and self.visit  - len(visited_stops) - 1 <= 0

    def route_best_stops(self, game, route, route_stop_values, always_include):
        # With this rule, towns will always be included because they don't count against the collection limit.
        if game.rules.routes.omit_towns_from_limit:
            always_include.extend([stop for stop in route_stop_values if stop.is_town])

        # Remove from consideration the station city and any stops that should always be included.
        stop_values = route_stop_values.copy()
        for to_include in always_include:
            del stop_values[to_include]

        # If a single stop appears multiple times, make sure it shows up mltiple times in the value list
        stop_value_list = list(stop_values.items())
        for space, count in collections.Counter(route).items():
            if count > 1 and space in route_stop_values:
                stop_value_list.extend([(space, route_stop_values[space])] * (count - 1))

        return dict(stop_value_list)

    def route_stop_values(self, raw_visited_stop_values):
        return raw_visited_stop_values.copy()

    def route_value(self, route, stop_values):
        # Simply doing sum(self.stop_values.values()) fails to appropriately
        # count stops visited multiple times.
        return sum(stop_values.get(stop, 0) for stop in route.stops)

class Diesel(Train):
    @staticmethod
    def normalize_train_str(train_str):
        return train_str.strip()

    @staticmethod
    def create(phase):
        return Diesel(phase)

    def __init__(self, phase):
        super().__init__(phase, math.inf, "diesel")

    def __hash__(self):
        return hash(self.visit)

    def __eq__(self, other):
        return isinstance(other, Diesel)

@functools.total_ordering
class Selection(Train):
    @staticmethod
    def _get_name(collect, visit):
        return f"{collect} / {visit}"

    @staticmethod
    def normalize_train_str(train_str):
        parts = train_str.split("/")
        if len(parts) != 2:
            raise ValueError("Malformatted selection train string: found {len(parts) - 1} forward-slashes.")
        collect = int(parts[0].strip())
        visit = int(parts[1].strip())
        return Selection._get_name(collect, visit)

    @staticmethod
    def create(phase, collect, visit, name):
        name = name or Selection._get_name(collect, visit)

        return Selection(phase, collect, visit, name)

    def __init__(self, phase, collect, visit, name):
        super().__init__(phase, visit, name)

        self.collect = collect

    def __hash__(self):
        return hash((self.collect, self.visit))

    def __eq__(self, other):
        return isinstance(other, Selection) and \
                self.visit == other.visit and \
                self.collect == other.collect

    def __gt__(self, other):
        if self.visit == other.visit:
            other_collect = other.collect if isinstance(other, Selection) else other.visit
            return self.collect > other_collect
        else:
            return self.visit > other.visit

    def route_best_stops(self, game, route, route_stop_values, always_include):
        # Only collect stops which aren't already set to be included.
        collect = self.collect - len(always_include)

        stop_values = super().route_best_stops(game, route, route_stop_values, always_include)

        return dict(heapq.nlargest(collect, stop_values.items(), key=lambda stop_item: stop_item[1]))

class Double(Train):
    @staticmethod
    def _get_name(visit):
        return f"{visit}D"

    @staticmethod
    def normalize_train_str(train_str):
        return Double._get_name(int(train_str.strip()[:-1]))

    @staticmethod
    def create(phase, visit, name):
        name = name or Double._get_name(visit)

        return Double(phase, visit, name)

    def __hash__(self):
        return hash(self.visit)

    def __eq__(self, other):
        return isinstance(other, Double) and \
                self.visit == other.visit

    def route_stop_values(self, raw_visited_stop_values):
        return {stop: value * (2 if not stop.is_town else 1) for stop, value in raw_visited_stop_values.items()}

def convert(train_info, trains_str):
    if not trains_str:
        return []

    railroad_trains = []
    for train_str in trains_str.split(","):
        train_str = train_str.strip()
        if train_str:
            for train in train_info:
                try:
                    normalized_train_str = train.normalize_train_str(train_str)
                except ValueError:
                    continue
                if normalized_train_str == train.name:
                    railroad_trains.append(train)
    return railroad_trains

def load_train_info(game):
    with open(game.get_data_file(_TRAINS_FILENAME)) as trains_file:
        trains_json = json.load(trains_file)

    return [Train.create(**info) for info in trains_json["trains"]]