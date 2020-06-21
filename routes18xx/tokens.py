class Token(object):
    def __init__(self, cell, railroad):
        self.cell = cell
        self.railroad = railroad

class Station(Token):
    pass

class PrivateCompanyToken(Token):
    @staticmethod
    def place(name, cell, railroad, properties):
        if railroad.is_removed:
            raise ValueError("A removed railroad cannot place a private company's token: {}".format(railroad.name))

        return PrivateCompanyToken(cell, railroad)

    def __init__(self, name, cell, railroad, bonus=0):
        super().__init__(cell, railroad)

        self.name = name
        self.bonus = bonus

    def value(self, game, railroad):
        return self.bonus if not game.private_is_closed(self.name) and self.railroad == railroad else 0