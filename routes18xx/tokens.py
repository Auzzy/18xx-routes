class Token(object):
    def __init__(self, cell, railroad):
        self.cell = cell
        self.railroad = railroad

class Station(Token):
    def __init__(self, cell, railroad, branch=None):
        super().__init__(cell, railroad)

        self.branch = branch

    def __str__(self):
        if self.branch:
            branch_str = self.branch[0] if len(self.branch) == 1 else str(list(self.branch))
            return f"{self.cell}:{branch_str}"
        else:
            return str(self.cell)

class PrivateCompanyToken(Token):
    @staticmethod
    def place(name, cell, railroad, properties):
        if railroad.is_removed:
            raise ValueError(f"A removed railroad cannot place a private company's token: {railroad.name}")

        return PrivateCompanyToken(name, cell, railroad)

    def __init__(self, name, cell, railroad, bonus=0):
        super().__init__(cell, railroad)

        self.name = name
        self.bonus = bonus

    def value(self, game, railroad):
        return self.bonus if not game.private_is_closed(self.name) and self.railroad == railroad else 0