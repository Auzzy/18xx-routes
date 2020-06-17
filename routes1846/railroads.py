import csv
import itertools

from routes1846.tokens import Station
from routes1846.cell import CHICAGO_CELL, Cell

FIELDNAMES = ("name", "trains", "stations", "chicago_station_exit_coord")

TRAIN_TO_PHASE = {
    (2, 2): 1,
    (3, 5): 2,
    (4, 4): 2,
    (4, 6): 3,
    (5, 5): 3,
    (6, 6): 4,
    (7, 8): 4
}

RAILROAD_HOME_CITIES = {
    "Baltimore & Ohio": "G19",
    "Illinois Central": "K3",
    "New York Central": "D20",
    "Chesapeake & Ohio": "I15",
    "Erie": "E21",
    "Grand Trunk": "B16",
    "Pennsylvania": "F20"
}

REMOVABLE_RAILROADS = {
    "Chesapeake & Ohio",
    "Erie",
    "Pennsylvania"
}

class Train(object):
    @staticmethod
    def create(train_str):
        parts = train_str.split("/")
        collect = int(parts[0].strip())
        visit = int((parts[0] if len(parts) == 1 else parts[1]).strip())

        if (collect, visit) not in TRAIN_TO_PHASE:
            train_str = ", ".join(sorted(TRAIN_TO_PHASE.keys()))
            raise ValueError("Invalid train string found. Got ({}, {}), but expected one of {}".format(collect, visit, train_str))
        
        return Train(collect, visit, TRAIN_TO_PHASE[(collect, visit)])

    def __init__(self, collect, visit, phase):
        self.collect = collect
        self.visit = visit
        self.phase = phase

    def __str__(self):
        if self.collect == self.visit:
            return str(self.collect)
        else:
            return "{} / {}".format(self.collect, self.visit)

    def __hash__(self):
        return hash((self.phase, self.collect, self.visit))

    def __eq__(self, other):
        return isinstance(other, Train) and \
                self.phase == other.phase and \
                self.collect == other.collect and \
                self.visit == other.visit

class Railroad(object):
    @staticmethod
    def create(name, trains_str):
        trains = [Train.create(train_str) for train_str in trains_str.split(",") if train_str] if trains_str else []

        return Railroad(name, trains)

    def __init__(self, name, trains):
        self.name = name
        self.trains = trains
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


def load_from_csv(board, railroads_filepath):
    with open(railroads_filepath, newline='') as railroads_file:
        return load(board, csv.DictReader(railroads_file, fieldnames=FIELDNAMES, delimiter=';', skipinitialspace=True))

def load(board, railroads_rows):
    railroads = {}
    for railroad_args in railroads_rows:
        trains_str = railroad_args.get("trains")
        if trains_str and trains_str.lower() == "removed":
            name = railroad_args["name"]
            if name not in REMOVABLE_RAILROADS:
                raise ValueError("Attempted to remove a non-removable railroad.")

            railroad = RemovedRailroad.create(name)
        else:
            railroad = Railroad.create(railroad_args["name"], trains_str)

        if railroad.name in railroads:
            raise ValueError(f"Found multiple {railroad.name} definitions.")

        railroads[railroad.name] = railroad

        if railroad.name not in RAILROAD_HOME_CITIES:
            raise ValueError("Unrecognized railroad name: {}".format(railroad.name))

        # Place the home station
        board.place_station(RAILROAD_HOME_CITIES[railroad.name], railroad)

        station_coords_str = railroad_args.get("stations")
        if station_coords_str:
            station_coords = [coord.strip() for coord in station_coords_str.split(",")]
            for coord in station_coords:
                if coord and coord != RAILROAD_HOME_CITIES[railroad.name] and Cell.from_coord(coord) != CHICAGO_CELL:
                    board.place_station(coord, railroad)

            if str(CHICAGO_CELL) in station_coords:
                chicago_station_exit_coord = str(railroad_args.get("chicago_station_exit_coord", "")).strip()
                if not chicago_station_exit_coord:
                    raise ValueError("Chicago is listed as a station for {}, but not exit side was specified.".format(railroad.name))

                board.place_chicago_station(railroad, int(chicago_station_exit_coord))

    return railroads