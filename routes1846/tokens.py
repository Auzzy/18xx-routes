class Token(object):
    def __init__(self, cell, railroad):
        self.cell = cell
        self.railroad = railroad

class Station(Token):
    pass

class PrivateCompanyToken(Token):
    def __init__(self, cell, railroad):
        if railroad.is_removed:
            raise ValueError("A removed railroad cannot place a private company's token: {}".format(railroad.name))

        super().__init__(cell, railroad)

class SeaportToken(PrivateCompanyToken):
    pass

class MeatPackingToken(PrivateCompanyToken):
    pass