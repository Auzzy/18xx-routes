import argparse
import logging
import sys

import os

from routes1846 import boardstate, find_best_routes, private_companies, railroads


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("active-railroad",
            help="The name of the railroad for whom to find the route. Must be present in the railroads file.")
    parser.add_argument("board-state-file",
            help=("CSV file containing the board state. Semi-colon is the column separator. The columns are: "
                  "coord; tile_id; orientation"))
    parser.add_argument("railroads-file",
            help=("CSV file containing railroads. Semi-colon is the column separator. The columns are: "
                  "name; trains (comma-separated); stations (comma-separated); chicago_station_exit (optional)"))
    parser.add_argument("-p", "--private-companies-file",
            help=("CSV file containing private company info. Semi-colon is the column separator. A column's precise "
                  "meaning depends on the company. The columns are: "
                  "name; owner; coordinate (optional)."))
    parser.add_argument("-v", "--verbose", action="store_true")
    return vars(parser.parse_args())

if __name__ == "__main__":
    args = parse_args()

    logger = logging.getLogger("routes1846")
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.DEBUG if args["verbose"] else logging.INFO)

    board = boardstate.load_from_csv(args["board-state-file"])
    railroads = railroads.load_from_csv(board, args["railroads-file"])
    private_companies.load_from_csv(board, railroads, args.get("private_companies_file"))
    board.validate()

    active_railroad = railroads[args["active-railroad"]]
    if active_railroad.is_removed:
        raise ValueError("Cannot calculate routes for a removed railroad: {}".format(active_railroad.name))

    best_routes = find_best_routes(board, railroads, active_railroad)
    print("RESULT")
    for route in best_routes:
        city_path = " -> ".join("{} [{}]".format(city.name, route.city_values[city]) for city in route.visited_cities)
        print("{}: {} = {} ({})".format(route.train, route, route.value, city_path))