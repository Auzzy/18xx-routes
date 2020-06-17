import csv

from routes1846.board import Board
from routes1846.tiles import get_tile

FIELDNAMES = ("coord", "tile_id", "orientation")

def load_from_csv(board_state_filepath):
    with open(board_state_filepath, newline='') as tiles_file:
        board_state_rows = csv.DictReader(tiles_file, fieldnames=FIELDNAMES, delimiter=';', skipinitialspace=True)
        return load(board_state_rows)

def load(board_state_rows):
    board = Board.load()

    tile_args_dicts = []
    for tile_args in board_state_rows:
        missing = [arg for arg in FIELDNAMES if tile_args.get(arg) is None]
        if missing:
            raise ValueError("Invalid board state input. Row missing {}: {}".format(", ".join(missing), tile_args))

        tile_id = tile_args.pop("tile_id")
        tile_args["tile"] = get_tile(tile_id)
        if not tile_args["tile"]:
            raise ValueError("No tile with the tile ID {} was found.".format(tile_id))
        
        tile_args_dicts.append(tile_args)

    for tile_args in sorted(tile_args_dicts, key=lambda adict: adict["tile"].phase):
        if tile_args["tile"].is_chicago:
            board.place_chicago(tile_args["tile"])
        else:
            board.place_tile(**tile_args)

    return board