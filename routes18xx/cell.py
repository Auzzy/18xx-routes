import collections
import json

BASE_BOARD_FILENAME = "base-board.json"
ORIENTATIONS = {"flat", "pointed"}

NEIGHBOR_TRANFORM = {
    "flat": {
        0: [1, -1],
        1: [-1, -1],
        2: [-2, 0],
        3: [-1, 1],
        4: [1, 1],
        5: [2, 0]
    },
    "pointed": {
        0: [1, -1],
        1: [0, -2],
        2: [-1, -1],
        3: [-1, 1],
        4: [0, 2],
        5: [1, 1]
    }
}
FLIPPED_NEIGHBOR_TRANSFORM = {}
for orientation, factor_dict in NEIGHBOR_TRANFORM.items():
    FLIPPED_NEIGHBOR_TRANSFORM[orientation] = {side: [factor[1], factor[0]] for side, factor in factor_dict.items()}

class Cell(object):
    def __init__(self, row, col):
        self.__row = row
        self.__col = col

        self.__neighbors = {}

    @property
    def neighbors(self):
        return self.__neighbors

    @neighbors.setter
    def neighbors(self, neighbors_dict):
        if not self.__neighbors:
            self.__neighbors = neighbors_dict

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if not isinstance(other, Cell):
            return False
        return self.__col == other.__col and self.__row == other.__row

    def __gt__(self, other):
        if self.__row == other.__row:
            return self.__col > other.__col
        else:
            return self.__row > other.__row

    def __lt__(self, other):
        if self.__row == other.__row:
            return self.__col < other.__col
        else:
            return self.__row < other.__row

    def __ge__(self, other):
        return self > other or self == other

    def __le__(self, other):
        return self < other or self == other

    def __str__(self):
        return f"{self.__row}{self.__col}"

    def __repr__(self):
        return str(self)

def _set_neighbors(board_info_json, cell_grid, transform_dict):
    orientation = board_info_json["orientation"]
    if orientation not in ORIENTATIONS:
        raise ValueError(f"Orientation should be one of {', '.join(ORIENTATIONS)}. Got {orientation}.")

    if set(transform_dict.keys()) != ORIENTATIONS:
        raise ValueError(f"Transform dictionary should have exactly {len(ORIENTATIONS)} keys: {', '.join(ORIENTATIONS)}")

    for row, cols in cell_grid.items():
        for col, cell in cols.items():
            for side, factor in transform_dict[orientation].items():
                cell.neighbors[side] = cell_grid.get(chr(ord(row) + factor[0]), {}).get(col + factor[1])

def _load_flipped_coords(board_info_json):
    # Normalize the coords such that letters are always first, since that's a
    # more natural way to represent coordinates. This means interpreting the
    # column values (the letters) as rows (and vice versa), and using the
    # flipped neighbor offsets
    cell_grid = collections.defaultdict(dict)
    for row, col_ranges in board_info_json["boundaries"].items():
        row = int(row)
        for col_range in col_ranges:
            if isinstance(col_range, str):
                cell_grid[col_range][row] = Cell(col_range, row)
            elif isinstance(col_range, list):
                for col in range(ord(col_range[0]), ord(col_range[1]) + 1, 2):
                    cell_grid[chr(col)][row] = Cell(chr(col), row)

    _set_neighbors(board_info_json, cell_grid, FLIPPED_NEIGHBOR_TRANSFORM)

    return cell_grid

def _load_standard_coords(board_info_json):
    cell_grid = collections.defaultdict(dict)
    for row, col_ranges in board_info_json["boundaries"].items():
        for col_range in col_ranges:
            if isinstance(col_range, int):
                cell_grid[row][col_range] = Cell(row, col_range)
            elif isinstance(col_range, list):
                for col in range(col_range[0], col_range[1] + 1, 2):
                    cell_grid[row][col] = Cell(row, col)

    _set_neighbors(board_info_json, cell_grid, NEIGHBOR_TRANFORM)

    return cell_grid

def load(game):
    with open(game.get_data_file(BASE_BOARD_FILENAME)) as board_file:
        board_info_json = json.load(board_file)["info"]

    if board_info_json.get("coords", "letter-number") == "letter-number":
        return _load_standard_coords(board_info_json)
    else:
        return _load_flipped_coords(board_info_json)