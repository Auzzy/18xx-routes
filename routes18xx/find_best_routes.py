import argparse
import functools
import itertools
import logging
import math
import multiprocessing
import os
import queue
import sys

from routes18xx import boardstate, railroads
from routes18xx.board import Board
from routes18xx.game import Game
from routes18xx.route import Route

LOG = logging.getLogger("routes18xx")

def route_set_value(route_set):
    return sum(route.value for route in route_set)

def _is_overlapping(active_route, routes_to_check):
    return any(True for route in routes_to_check if active_route.overlap(route)) if routes_to_check else False

def _find_best_sub_route_set(global_best_value, sorted_routes, selected_routes=None):
    selected_routes = selected_routes or []

    minor_routes = []
    best_route_set = selected_routes
    best_route_set_value = route_set_value(selected_routes)
    if best_route_set_value > global_best_value.value:
        global_best_value.value = best_route_set_value

    for minor_route in sorted_routes[0]:
        if not _is_overlapping(minor_route, selected_routes):
            if sorted_routes[1:]:
                # Already selected routes + the current route + the maximum possible value of the remaining train routes.
                max_possible_route_set = selected_routes + [minor_route] + [routes[0] for routes in sorted_routes[1:]]
                max_possible_value = route_set_value(max_possible_route_set)
                # That must be more than the current best route set value, or we bail from this iteration.
                if max_possible_value <= global_best_value.value:
                    return best_route_set

                sub_route_set = _find_best_sub_route_set(global_best_value, sorted_routes[1:], selected_routes + [minor_route])
                sub_route_set_value = route_set_value(sub_route_set)
                if sub_route_set_value >= global_best_value.value:
                    best_route_set = sub_route_set
                    best_route_set_value = sub_route_set_value
                    global_best_value.value = sub_route_set_value
            else:
                return selected_routes + [minor_route]
    return best_route_set

def _find_best_sub_route_set_worker(input_queue, global_best_value):
    best_route_sets = []
    while True:
        try:
            sorted_routes = input_queue.get_nowait()
            best_route_set = _find_best_sub_route_set(global_best_value, sorted_routes)

            if best_route_set:
                best_route_sets.append(best_route_set)
        except queue.Empty:
            return best_route_sets

def _get_train_sets(railroad):
    train_sets = []
    for train_count in range(1, len(railroad.trains) + 1):
        train_combinations = set(itertools.combinations(railroad.trains, train_count))
        train_sets += [tuple(sorted(train_set, key=lambda train: train.collect)) for train_set in train_combinations]
    return train_sets


def chunk_sequence(sequence, chunk_length):
    """Yield successive n-sized chunks from l."""
    for index in range(0, len(sequence), chunk_length):
        yield sequence[index:index + chunk_length]


def _get_route_sets(railroad, route_by_train):
    manager = multiprocessing.Manager()
    input_queue = manager.Queue()

    sorted_routes_by_train = {train: sorted(routes, key=lambda route: route.value, reverse=True) for train, routes in route_by_train.items()}

    proc_count = os.cpu_count()
    best_route_sets = []
    with multiprocessing.Pool(processes=proc_count) as pool:
        # Using half the processes as workers seems to result in faster processing times.
        worker_count = proc_count / 2
        for train_set in _get_train_sets(railroad):
            sorted_routes = [sorted_routes_by_train[train] for train in train_set]

            if all(sorted_routes):
                # Cut routes into 1 chunk per worker and put it on the queue
                chunk_size = math.ceil(len(sorted_routes[0]) / worker_count)
                for root_routes in chunk_sequence(sorted_routes[0], chunk_size):
                    input_queue.put_nowait([root_routes] + sorted_routes[1:])
    
                # Allow the workers to compare notes on what the best route value is
                global_best_value = manager.Value('i', 0)
    
                # Give each worker the input queue and the best value reference
                worker_promises = []
                for k in range(math.ceil(worker_count)):
                    promise = pool.apply_async(_find_best_sub_route_set_worker, (input_queue, global_best_value))
                    worker_promises.append(promise)
        
                # Add the results to the list
                for promise in worker_promises:
                    values = promise.get()
                    best_route_sets.extend(values)

    return best_route_sets

def _find_best_routes_by_train(game, route_by_train, railroad):
    route_sets = _get_route_sets(railroad, route_by_train)

    game.hook_after_route_sets(route_sets, railroad)

    LOG.debug("Found %d route sets.", len(route_sets))
    for route_set in route_sets:
        for run_route in route_set:
            LOG.debug("{}: {} ({})".format(run_route.train, str(run_route), run_route.value))
        LOG.debug("")

    return max(route_sets, key=lambda route_set: sum(route.value for route in route_set)) if route_sets else {}

def _get_subroutes(routes, stations):
    subroutes = [route.subroutes(station.cell) for station in stations for route in routes]
    return set(itertools.chain.from_iterable([subroute for subroute in subroutes if subroute]))

def _walk_routes(game, board, railroad, enter_from, cell, length, visited=None):
    visited = visited or []

    tile = board.get_space(cell)
    if not tile or (enter_from and enter_from not in tile.paths()) or tile in visited:
        return (Route.empty(), )

    if tile.is_stop \
            and (not game.rules.towns_omit_from_limit or not tile.is_town):
        if length - 1 == 0 or (enter_from and not tile.passable(enter_from, railroad)):
            LOG.debug("- %s", ", ".join([str(tile.cell) for tile in visited + [tile]]))
            return (Route.single(tile), )

        remaining_stops = length - 1
    else:
        remaining_stops = length

    neighbors = tile.paths(enter_from, railroad)

    routes = []
    for neighbor in neighbors:
        neighbor_paths = _walk_routes(game, board, railroad, cell, neighbor, remaining_stops, visited + [tile])
        routes += [Route.single(tile).merge(neighbor_path) for neighbor_path in neighbor_paths if neighbor_path]

    if not routes and tile.is_stop:
        LOG.debug("- %s", ", ".join([str(tile.cell) for tile in visited + [tile]]))
        routes.append(Route.single(tile))

    return tuple(set(routes))

def _filter_invalid_routes(game, routes, board, railroad):
    """
    Given a collection of routes, returns a new set containing only valid routes. Invalid routes removed:
    - contain less than 2 cities, or
    - do not contain the railroad's station

    It also invokes a hook to allow each game specify its own filtering.

    This fltering after the fact keeps the path finding algorithm simpler. It allows groups of 3 cells to be considered
    (important for the Chicago checks), which would be tricky, since the algorithm operates on pairs of cells (at the
    time of writing).
    """
    stations = board.stations(railroad.name)

    # A sieve style filter. If a condition isn't met, iteration continues to the next item. Items meeting all conditions
    # are added to valid_routes at the end of the loop iteration.
    valid_routes = set()
    for route in routes:
        # A route must connect at least 2 stops.
        if len(route.stops) < 2:
            continue

        # Each route must contain at least 1 station
        stations_on_route = [station for station in stations if route.contains_cell(station.cell)]
        if not stations_on_route:
            continue

        valid_routes.add(route)

    return game.filter_invalid_routes(valid_routes, board, railroad)

def _find_routes_from_cell(game, board, railroad, cell, train):
    routes = _walk_routes(game, board, railroad, None, cell, train.visit)

    LOG.debug("Found %d routes starting at %s.", len(routes), cell)
    return routes

def _find_connected_cities(game,board, railroad, cell, dist):
    tiles = itertools.chain.from_iterable(_walk_routes(game, board, railroad, None, cell, dist))
    return {tile.cell for tile in tiles if tile.is_city or tile.is_terminus} - {cell}

def _find_connected_routes(game, board, railroad, station, train):
    LOG.debug("Finding connected cities.")
    connected_cities = _find_connected_cities(game, board, railroad, station.cell, train.visit - 1)
    LOG.debug("Connected cities: %s", ", ".join([str(cell) for cell in connected_cities]))

    LOG.debug("Finding routes starting from connected cities.")
    connected_routes = set()
    for cell in connected_cities:
        connected_routes.update(_find_routes_from_cell(game, board, railroad, cell, train))
    LOG.debug("Found %d routes from connected cities.", len(connected_routes))
    return connected_routes

def _find_all_routes(game, board, railroad):
    LOG.info("Finding all possible routes for each train from %s's stations.", railroad.name)

    stations = board.stations(railroad.name)

    routes_by_train = {}
    for train in railroad.trains:
        if train not in routes_by_train:
            routes = set()
            for station in stations:
                LOG.debug("Finding routes starting at station at %s.", station.cell)
                routes.update(_find_routes_from_cell(game, board, railroad, station.cell, train))

                LOG.debug("Finding routes which pass through station at %s.", station.cell)
                connected_paths = _find_connected_routes(game, board, railroad, station, train)
                routes.update(connected_paths)

            LOG.debug("Add subroutes")
            routes.update(_get_subroutes(routes, stations))

            LOG.debug("Filtering out invalid routes")
            routes_by_train[train] = _filter_invalid_routes(game, routes, board, railroad)

    LOG.info("Found %d routes.", sum(len(route) for route in routes_by_train.values()))
    for train, routes in routes_by_train.items():
        for route in routes:
            LOG.debug("{}: {}".format(train, str(route)))

    return routes_by_train

def find_best_routes(game, board, railroads, active_railroad):
    if active_railroad.is_removed:
        raise ValueError("Cannot calculate routes for a removed railroad: {}".format(active_railroad.name))

    game.capture_phase(railroads)

    LOG.info("Finding the best route for %s.", active_railroad.name)

    routes = _find_all_routes(game, board, active_railroad)

    LOG.info("Calculating route values.")
    route_value_by_train = {}
    for train in routes:
        route_value_by_train[train] = [route.run(game, board, train, active_railroad) for route in routes[train]]

    return _find_best_routes_by_train(game, route_value_by_train, active_railroad)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("game",
            help="The name of the game to use. Usually just the \"year\" (e.g. 1846, 18AL, etc).")
    parser.add_argument("active-railroad",
            help="The name of the railroad for whom to find the route. Must be present in the railroads file.")
    parser.add_argument("board-state-file",
            help=("CSV file containing the board state. Semi-colon is the column separator. The columns are: "
                  "coord; tile_id; orientation"))
    parser.add_argument("railroads-file",
            help=("CSV file containing railroads. Semi-colon is the column separator. The columns are: "
                  "name; trains (comma-separated); stations (comma-separated); station_branch_map (optional, repeating)"))
    parser.add_argument("-p", "--private-companies-file",
            help=("CSV file containing private company info. Semi-colon is the column separator. A column's precise "
                  "meaning depends on the company. The columns are: "
                  "name; owner; coordinate (optional)."))
    parser.add_argument("-v", "--verbose", action="store_true")
    return vars(parser.parse_args())

def main():
    args = parse_args()

    logger = logging.getLogger("routes18xx")
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.DEBUG if args["verbose"] else logging.INFO)

    game = Game.load(args["game"])
    board = boardstate.load_from_csv(game, args["board-state-file"])
    railroads_in_play = railroads.load_from_csv(game, board, args["railroads-file"])
    game.capture_phase(railroads_in_play)

    private_companies_module = game.get_game_submodule("private_companies")
    if private_companies_module:
        private_companies_module.load_from_csv(game, board, railroads_in_play, args.get("private_companies_file"))
    board.validate()

    active_railroad = railroads_in_play[args["active-railroad"]]
    if active_railroad.is_removed:
        raise ValueError("Cannot calculate routes for a removed railroad: {}".format(active_railroad.name))

    best_routes = find_best_routes(game, board, railroads_in_play, active_railroad)
    print("RESULT")
    for route in best_routes:
        stop_path = " -> ".join("{} [{}]".format(stop.name, route.stop_values[stop]) for stop in route.visited_stops)
        print("{}: {} = {} ({})".format(route.train, route, route.value, stop_path))

if __name__ == "__main__":
    main()