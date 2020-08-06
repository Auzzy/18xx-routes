import itertools
import json

from routes18xx.trains import _TRAINS_FILENAME, Train, convert, load_train_info

class TrainLimitMaster:
    @staticmethod
    def load(train_limits, train_info):
        return TrainLimitMaster(
            {phase: TrainLimit.load(train_info, **limit_dict) for phase, limit_dict in train_limits.items()})

    def __init__(self, limit_dict):
        self.limit_dict = limit_dict

    def validate(self, game, railroad):
        phase_train_limit = self.limit_dict[game.current_phase]
        all_trains = phase_train_limit.get_trains()
        invalid_trains = set(railroad.trains) - all_trains
        if invalid_trains:
            invalid_trains_str = ', '.join(sorted(map(str, invalid_trains)))
            raise ValueError(f"{railroad.name} has invalid trains for the current phase: {invalid_trains_str}")

        phase_train_limit.validate(game, railroad)

class TrainLimit:
    @staticmethod
    def load(train_info, trains, total=None):
        if all(isinstance(train, dict) for train in trains):
            limits = tuple([TrainLimit.load(train_info, **category) for category in trains])
        else:
            limits = tuple(convert(train_info, ",".join(trains)))

        return TrainLimit(limits, total)

    def __init__(self, limits, total=None):
        self.limits = limits
        self.total = total

    def __hash__(self):
        return hash(self.limits)

    def get_trains(self):
        if all(isinstance(train, Train) for train in self.limits):
            return set(self.limits)
        else:
            return set(itertools.chain.from_iterable([limit.get_trains() for limit in self.limits]))

    def validate(self, game, railroad):
        all_trains = self.get_trains()
        railroad_trains = [train for train in railroad.trains if train in all_trains]
        if len(railroad_trains) > self.total:
            category_trains_str = ', '.join(sorted(map(str, all_trains)))
            railroad_trains_str = ', '.join(sorted(map(str, railroad_trains)))
            raise ValueError(f"Max {self.total} trains of the following types: {category_trains_str}. "
                    f"{railroad.name} has {len(railroad_trains)}: {railroad_trains_str}.")

        for limit in self.limits:
            if isinstance(limit, TrainLimit):
                limit.validate(game, railroad)

def load_train_limits(game):
    with open(game.get_data_file(_TRAINS_FILENAME)) as trains_file:
        trains_json = json.load(trains_file)

    return TrainLimitMaster.load(trains_json["train_limits"], load_train_info(game))