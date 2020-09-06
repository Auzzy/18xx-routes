import collections
import functools
import heapq
import json
import math

_TRAINS_FILENAME = "trains.json"

@functools.total_ordering
class Train:
    @staticmethod
    def _get_name(collect, visit):
        if collect == math.inf:
            return "diesel"
        elif collect == visit:
            return str(collect)
        else:
            return f"{collect} / {visit}"

    @staticmethod
    def normalize_name(name):
        parts = name.split("/")
        try:
            collect = int(parts[0].strip())
        except ValueError:
            collect = math.inf
        visit = collect if len(parts) == 1 else int(parts[1].strip())
        return Train._get_name(collect, visit)

    @staticmethod
    def create(name, collect, visit, phase):
        if not collect:
            collect = math.inf

        if not visit:
            visit = collect

        name = name or Train._get_name(collect, visit)

        return Train(name, collect, visit, phase)

    def __init__(self, name, collect, visit, phase):
        self.name = name
        self.collect = collect
        self.visit = visit
        self.phase = phase

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash((self.collect, self.visit))

    def __eq__(self, other):
        return isinstance(other, Train) and \
                self.collect == other.collect and \
                self.visit == other.visit

    def __gt__(self, other):
        return self.collect > other.collect

    def is_end_of_route(self, game, board, railroad, enter_from, cell, visited_paths, visited_stops):
        tile = board.get_space(cell)
        return tile.is_stop \
            and (not game.rules.routes.omit_towns_from_limit or not tile.is_town) \
            and self.visit  - len(visited_stops) - 1 <= 0

    def route_best_stops(self, game, route, route_stop_values, always_include):
        # Only collect stops which aren't already set to be included.
        collect = self.collect - len(always_include)

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

        return stop_value_list if collect == math.inf else dict(heapq.nlargest(collect, stop_value_list, key=lambda stop_item: stop_item[1]))

    def route_stop_values(self, raw_visited_stop_values):
        return raw_visited_stop_values.copy()

    def route_value(self, route, stop_values):
        # Simply doing sum(self.stop_values.values()) fails to appropriately
        # count stops visited multiple times.
        return sum(stop_values.get(stop, 0) for stop in route.stops)

def convert(train_info, trains_str):
    if not trains_str:
        return []

    railroad_trains = []
    for train_str in trains_str.split(","):
        train_str = train_str.strip()
        if train_str:
            for train in train_info:
                if train.normalize_name(train_str) == train.name:
                    railroad_trains.append(train)
    return railroad_trains

def load_train_info(game):
    with open(game.get_data_file(_TRAINS_FILENAME)) as trains_file:
        trains_json = json.load(trains_file)

    return [Train.create(info.get("name"), info["collect"], info.get("visit"), info["phase"]) for info in trains_json["trains"]]