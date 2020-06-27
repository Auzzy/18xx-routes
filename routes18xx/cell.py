import json

BASE_BOARD_FILENAME = "base-board.json"

_CELL_DB = {}

class Cell(object):
    @staticmethod
    def from_coord(coord):
        if len(coord) < 2 or len(coord) > 3:
            raise ValueError("Provided invalid coord: {}".format(coord))
        
        row, col = coord[0], int(coord[1:])
        if row not in _CELL_DB or col not in _CELL_DB[row]:
            raise ValueError("The coordinate provided is not legal: {}".format(coord))
        return _CELL_DB[row][col]

    def __init__(self, row, col):
        self.__row = row
        self.__col = col

    @property
    def neighbors(self):
        return {
            0: _CELL_DB.get(chr(ord(self.__row) + 1), {}).get(self.__col - 1),
            1: _CELL_DB.get(self.__row, {}).get(self.__col - 2),
            2: _CELL_DB.get(chr(ord(self.__row) - 1), {}).get(self.__col - 1),
            3: _CELL_DB.get(chr(ord(self.__row) - 1), {}).get(self.__col + 1),
            4: _CELL_DB.get(self.__row, {}).get(self.__col + 2),
            5: _CELL_DB.get(chr(ord(self.__row) + 1), {}).get(self.__col + 1)
        }

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
        return "{}{}".format(self.__row, self.__col)

    def __repr__(self):
        return str(self)

def initialize_cells(game):
    global _CELL_DB

    with open(game.get_data_file(BASE_BOARD_FILENAME)) as board_file:
        boundaries_json = json.load(board_file)["boundaries"]
        for row, col_ranges in boundaries_json.items():
            _CELL_DB[row] = {}
            for col_range in col_ranges:
                if isinstance(col_range, int):
                    _CELL_DB[row][col_range] = Cell(row, col_range)
                elif isinstance(col_range, list):
                    for col in range(col_range[0], col_range[1] + 1, 2):
                        _CELL_DB[row][col] = Cell(row, col)

def board_cells():
    for row, columns in _CELL_DB.items():
        for column, cell in columns.items():
            yield cell