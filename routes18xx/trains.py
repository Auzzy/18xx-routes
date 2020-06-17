import json

from routes18xx import get_data_file

_TRAINS_FILENAME = "trains.json"

class Train:
    @staticmethod
    def _get_name(collect, visit):
        if collect == visit:
            return str(collect)
        else:
            return "{} / {}".format(collect, visit)

    @staticmethod
    def create(name, collect, visit, phase):
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

class TrainContainer(Train):
    @staticmethod
    def from_string(train_str):
        parts = train_str.split("/")
        collect = int(parts[0].strip())
        visit = int((parts[0] if len(parts) == 1 else parts[1]).strip())
        return TrainContainer(collect, visit)

    def __init__(self, collect, visit):
        self.collect = collect
        self.visit = visit

def convert(train_info, trains_str):
    if not trains_str:
        return []

    railroad_trains = []
    for train_str in trains_str.split(","):
        if train_str:
            raw_train = TrainContainer.from_string(train_str)
            if raw_train in train_info:
                railroad_trains.append(train_info[train_info.index(raw_train)])
    return railroad_trains

def load_train_info(game):
    with open(get_data_file(game, _TRAINS_FILENAME)) as trains_file:
        trains_json = json.load(trains_file)

    return [Train.create(info.get("name"), info["collect"], info.get("visit"), info["phase"]) for info in trains_json["trains"]]