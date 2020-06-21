from routes18xx.tokens import PrivateCompanyToken

class SteamboatToken(PrivateCompanyToken):
    COORDS = ("B8", "C5", "D14", "G19", "I1")

    @staticmethod
    def place(cell, railroad, properties):
        if railroad.is_removed:
            raise ValueError("A removed railroad cannot place the seaport token: {}".format(railroad.name))

        if str(cell) not in SteamboatToken.COORDS:
            raise ValueError("It is not legal to place the seaport token on this space ({}).".format(cell))

        bonus = properties.get("port_value")
        if not bonus:
            raise ValueError("{} does not define a seaport bonus value.".format(cell))

        return SteamboatToken("Steamboat Company", cell, railroad, bonus)

class MeatPackingToken(PrivateCompanyToken):
    COORDS = ("D6", "I1")

    @staticmethod
    def place(cell, railroad, properties):
        if railroad.is_removed:
            raise ValueError("A removed railroad cannot place the meat packing token: {}".format(railroad.name))

        if str(cell) not in MeatPackingToken.COORDS:
            raise ValueError("It is not legal to place the meat packing token on this space ({}).".format(cell))

        bonus = properties.get("meat_value")
        if not bonus:
            raise ValueError("{} does not define a meat packing bonus value.".format(cell))

        return MeatPackingToken("Meat Packing Company", cell, railroad, bonus)