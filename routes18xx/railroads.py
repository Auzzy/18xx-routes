import csv
import itertools
import json

from routes18xx import get_data_file, trains
from routes18xx.tokens import Station
from routes18xx.cell import get_chicago_cell, Cell

_RAILROADS_FILENAME = "railroads.json"

FIELDNAMES = ("name", "trains", "stations", "chicago_station_exit_coord")

class Railroad(object):
    @staticmethod
    def create(name, railroad_trains):
        return Railroad(name, railroad_trains)

    def __init__(self, name, railroad_trains):
        self.name = name
        self.trains = railroad_trains
        self.has_mail_contract = False

    def assign_mail_contract(self):
        self.has_mail_contract = True

    @property
    def is_removed(self):
        return False

class RemovedRailroad(Railroad):
    @staticmethod
    def create(name):
        return RemovedRailroad(name)

    def __init__(self, name):
        super().__init__(name, [])

        self.has_mail_contract = False

    def assign_mail_contract(self):
        raise ValueError("Cannot assign Mail Contract to a removed railroad: {}".format(self.name))

    @property
    def is_removed(self):
        return True

def _load_railroad_info(game):
    with open(get_data_file(game, _RAILROADS_FILENAME)) as railroads_file:
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
            raise ValueError("Unrecognized railroad name: {}".format(name))

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

        station_coords_str = railroad_args.get("stations")
        if station_coords_str:
            station_coords = [coord.strip() for coord in station_coords_str.split(",")]
            for coord in station_coords:
                if coord and coord != info["home"] and Cell.from_coord(coord) != get_chicago_cell():
                    board.place_station(coord, railroad)

            if str(get_chicago_cell()) in station_coords:
                chicago_station_exit_coord = str(railroad_args.get("chicago_station_exit_coord", "")).strip()
                if not chicago_station_exit_coord:
                    raise ValueError("Chicago is listed as a station for {}, but not exit side was specified.".format(railroad.name))

                board.place_chicago_station(railroad, int(chicago_station_exit_coord))

    for name, info in railroad_info.items():
        if name in railroads:
            for nickname in info.get("nicknames", []):
                railroads[nickname] = railroads[name]

    return railroads