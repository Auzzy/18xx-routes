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

def _create_impassable_dict(base_board_json):
    impassable_dict = collections.defaultdict(list)
    for path in base_board_json.get("impassable", []):
        impassable_dict[path[0]].append(path[1])
        impassable_dict[path[1]].append(path[0])
    return impassable_dict

def _set_neighbors(base_board_json, cell_grid, transform_dict):
    orientation = base_board_json["info"]["orientation"]
    if orientation not in ORIENTATIONS:
        raise ValueError(f"Orientation should be one of {', '.join(ORIENTATIONS)}. Got {orientation}.")

    if set(transform_dict.keys()) != ORIENTATIONS:
        raise ValueError(f"Transform dictionary should have exactly {len(ORIENTATIONS)} keys: {', '.join(ORIENTATIONS)}")

    impassable_dict = _create_impassable_dict(base_board_json)
    for row, cols in cell_grid.items():
        for col, cell in cols.items():
            for side, factor in transform_dict[orientation].items():
                neighbor = cell_grid.get(chr(ord(row) + factor[0]), {}).get(col + factor[1])
                cell.neighbors[side] = neighbor if str(neighbor) not in impassable_dict.get(str(cell), []) else None

def _load_flipped_coords(base_board_json):
    # Normalize the coords such that letters are always first, since that's a
    # more natural way to represent coordinates. This means interpreting the
    # column values (the letters) as rows (and vice versa), and using the
    # flipped neighbor offsets
    cell_grid = collections.defaultdict(dict)
    for row, col_ranges in base_board_json["info"]["boundaries"].items():
        row = int(row)
        for col_range in col_ranges:
            if isinstance(col_range, str):
                cell_grid[col_range][row] = Cell(col_range, row)
            elif isinstance(col_range, list):
                for col in range(ord(col_range[0]), ord(col_range[1]) + 1, 2):
                    cell_grid[chr(col)][row] = Cell(chr(col), row)

    _set_neighbors(base_board_json, cell_grid, FLIPPED_NEIGHBOR_TRANSFORM)

    return cell_grid

def _load_standard_coords(base_board_json):
    cell_grid = collections.defaultdict(dict)
    for row, col_ranges in base_board_json["info"]["boundaries"].items():
        for col_range in col_ranges:
            if isinstance(col_range, int):
                cell_grid[row][col_range] = Cell(row, col_range)
            elif isinstance(col_range, list):
                for col in range(col_range[0], col_range[1] + 1, 2):
                    cell_grid[row][col] = Cell(row, col)

    _set_neighbors(base_board_json, cell_grid, NEIGHBOR_TRANFORM)

    return cell_grid

def load(game):
    with open(game.get_data_file(BASE_BOARD_FILENAME)) as board_file:
        base_board_json = json.load(board_file)

    base_board_json["info"]["coords"] = base_board_json["info"].get("coords") or "letter-number"
    if base_board_json["info"]["coords"] == "letter-number":
        return _load_standard_coords(base_board_json), base_board_json["info"]
    else:
        return _load_flipped_coords(base_board_json), base_board_json["info"]
