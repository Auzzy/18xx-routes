import itertools

CHICAGO_CELL = None  # Defined below
CHICAGO_CONNECTIONS_CELL = None  # Defined below
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

_CELL_DB = {
    "A": {15: Cell("A", 15)},
    "B": {col: Cell("B", col) for col in range(8, 19, 2)},
    "C": {col: Cell("C", col) for col in itertools.chain([5], range(7, 18, 2), [21])},
    "D": {col: Cell("D", col) for col in itertools.chain(range(6, 15, 2), range(18, 23, 2))},
    "E": {col: Cell("E", col) for col in range(5, 24, 2)},
    "F": {col: Cell("F", col) for col in range(4, 23, 2)},
    "G": {col: Cell("G", col) for col in range(3, 22, 2)},
    "H": {col: Cell("H", col) for col in itertools.chain(range(2, 17, 2), [20])},
    "I": {col: Cell("I", col) for col in itertools.chain(range(1, 12, 2), range(15, 18, 2))},
    "J": {col: Cell("J", col) for col in itertools.chain(range(4, 11, 2))},
    "K": {3: Cell("K", 3)}
}

CHICAGO_CELL = Cell.from_coord("D6")
CHICAGO_CONNECTIONS_CELL = Cell.from_coord("C5")

def board_cells():
    for row, columns in _CELL_DB.items():
        for column, cell in columns.items():
            yield cell