import csv
import itertools
import json

from routes18xx import trains
from routes18xx.tokens import Station
from routes18xx.cell import Cell

from routes18xx import boardtile, placedtile


_RAILROADS_FILENAME = "railroads.json"

FIELDNAMES = ("name", "trains", "stations")

class Railroad(object):
    @staticmethod
    def create(name, railroad_trains):
        return Railroad(name, railroad_trains)

    def __init__(self, name, railroad_trains):
        self.name = name
        self.trains = railroad_trains
        self._private_companies = []

    def add_private_company(self, name):
        self._private_companies.append(name)

    def has_private_company(self, name):
        return name in self._private_companies

    @property
    def is_removed(self):
        return False

class RemovedRailroad(Railroad):
    @staticmethod
    def create(name):
        return RemovedRailroad(name, [])

    def add_private_company(self, name):
        raise ValueError(f"Cannot assign a private company to a removed railroad: {self.name}")

    def has_private_company(self, name):
        raise ValueError(f"A removed failroad cannot hold any private companies: {self.name}")

    @property
    def is_removed(self):
        return True

def _split_station_entry(station_entry):
    if ':' not in station_entry:
        return station_entry, None

    coord, branch_str = station_entry.split(':')
    branch_str = branch_str.strip()
    if branch_str.startswith('[') and branch_str.endswith(']'):
        branch_str = branch_str[1:-1]
        branch = tuple([coord.strip() for coord in branch_str.split()])
    else:
        branch = (branch_str.strip(), )

    return coord.strip(), branch

def _load_railroad_info(game):
    with open(game.get_data_file(_RAILROADS_FILENAME)) as railroads_file:
        return json.load(railroads_file)

def load_from_csv(game, board, railroads_filepath):
    with open(railroads_filepath, newline='') as railroads_file:
        return load(game, board, csv.DictReader(railroads_file, fieldnames=FIELDNAMES, delimiter=';', skipinitialspace=True))

def load(game, board, railroads_rows):
    railroad_info = _load_railroad_info(game)
    train_info = trains.load_train_info(game)

    railroads = {}
    for railroad_args in railroads_rows:
        name = railroad_args["name"]
        info = railroad_info.get(name, {})
        if not info:
            raise ValueError(f"Unrecognized railroad name: {name}")

        trains_str = railroad_args.get("trains")
        if trains_str and trains_str.lower() == "removed":
            name = railroad_args["name"]
            if info.get("is_removable"):
                raise ValueError("Attempted to remove a non-removable railroad.")

            railroad = RemovedRailroad.create(name)
        else:
            railroad_trains = trains.convert(train_info, trains_str)
            railroad = Railroad.create(railroad_args["name"], railroad_trains)

        if railroad.name in railroads:
            raise ValueError(f"Found multiple {railroad.name} definitions.")

        railroads[railroad.name] = railroad

        # Place the home station
        board.place_station(info["home"], railroad)

        station_entries_str = railroad_args.get("stations")
        if station_entries_str:
            station_entries = [entry.strip() for entry in station_entries_str.split(",")]
            for entry in station_entries:
                coord, branch = _split_station_entry(entry)
                if coord and coord != info["home"]:
                    if isinstance(board.get_space(board.cell(coord)), (placedtile.SplitCity, boardtile.SplitCity)):
                        if not branch:
                            raise ValueError(f"A split city ({coord}) is listed as a station for {railroad.name}, but no station branch was specified.")

                        board.place_split_station(coord, railroad, branch)
                    else:
                        board.place_station(coord, railroad)

    for name, info in railroad_info.items():
        if name in railroads:
            for nickname in info.get("nicknames", []):
                railroads[nickname] = railroads[name]

    return railroads