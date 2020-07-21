import csv

from routes18xx.board import Board


FIELDNAMES = ("coord", "tile_id", "orientation")

def load_from_csv(game, board_state_filepath):
    with open(board_state_filepath, newline='') as tiles_file:
        board_state_rows = csv.DictReader(tiles_file, fieldnames=FIELDNAMES, delimiter=';', skipinitialspace=True)
        return load(game, board_state_rows)

def load(game, board_state_rows):
    board = Board.load(game)

    tile_args_dicts = []
    for tile_args in board_state_rows:
        missing = [arg for arg in FIELDNAMES if tile_args.get(arg) is None]
        if missing:
            raise ValueError(f"Invalid board state input. Row missing {', '.join(missing)}: {tile_args}")

        tile_id = tile_args.pop("tile_id")
        tile_args["tile"] = game.tiles.get(tile_id)
        if not tile_args["tile"]:
            raise ValueError(f"No tile with the tile ID {tile_id} was found.")
        
        tile_args_dicts.append(tile_args)

    for tile_args in sorted(tile_args_dicts, key=lambda adict: adict["tile"].upgrade_level):
        board.place_tile(**tile_args)

    return board