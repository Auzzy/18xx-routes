class Token(object):
    def __init__(self, cell, railroad):
        self.cell = cell
        self.railroad = railroad

class Station(Token):
    pass

class PrivateCompanyToken(Token):
    @staticmethod
    def place(cell, railroad, properties):
        if railroad.is_removed:
            raise ValueError("A removed railroad cannot place a private company's token: {}".format(railroad.name))

        return PrivateCompanyToken(cell, railroad)

    def __init__(self, cell, railroad, bonus=0):
        super().__init__(cell, railroad)

        self.bonus = bonus

    def value(self, railroad, phase):
        return self.bonus if phase != 4 and self.railroad == railroad else 0