import json

BASE_BOARD_FILENAME = "base-board.json"

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

def load(game):
    cell_grid = {}
    with open(game.get_data_file(BASE_BOARD_FILENAME)) as board_file:
        boundaries_json = json.load(board_file)["boundaries"]

    for row, col_ranges in boundaries_json.items():
        cell_grid[row] = {}
        for col_range in col_ranges:
            if isinstance(col_range, int):
                cell_grid[row][col_range] = Cell(row, col_range)
            elif isinstance(col_range, list):
                for col in range(col_range[0], col_range[1] + 1, 2):
                    cell_grid[row][col] = Cell(row, col)

    for row, cols in cell_grid.items():
        for col, cell in cols.items():
            cell.neighbors = {
                0: cell_grid.get(chr(ord(row) + 1), {}).get(col - 1),
                1: cell_grid.get(row, {}).get(col - 2),
                2: cell_grid.get(chr(ord(row) - 1), {}).get(col - 1),
                3: cell_grid.get(chr(ord(row) - 1), {}).get(col + 1),
                4: cell_grid.get(row, {}).get(col + 2),
                5: cell_grid.get(chr(ord(row) + 1), {}).get(col + 1)
            }

    return cell_grid