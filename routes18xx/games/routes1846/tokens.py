from routes18xx.tokens import PrivateCompanyToken

class SteamboatToken(PrivateCompanyToken):
    NAME = "Steamboat Company"
    COORDS = ("B8", "C5", "D14", "G19", "I1")

    @staticmethod
    def place(cell, railroad, properties):
        if railroad.is_removed:
            raise ValueError(f"A removed railroad cannot place the {SteamboatToken.NAME} token: {railroad.name}")

        if str(cell) not in SteamboatToken.COORDS:
            raise ValueError(f"It is not legal to place the {SteamboatToken.NAME} token on this space ({cell}).")

        bonus = properties.get("port_value")
        if not bonus:
            raise ValueError(f"{cell} does not define a {SteamboatToken.NAME} bonus value.")

        return SteamboatToken(SteamboatToken.NAME, cell, railroad, bonus)

class MeatPackingToken(PrivateCompanyToken):
    NAME = "Meat Packing Company"
    COORDS = ("D6", "I1")

    @staticmethod
    def place(cell, railroad, properties):
        if railroad.is_removed:
            raise ValueError(f"A removed railroad cannot place the {MeatPackingToken.NAME} token: {railroad.name}")

        if str(cell) not in MeatPackingToken.COORDS:
            raise ValueError(f"It is not legal to place the {MeatPackingToken.NAME} token on this space ({cell}).")

        bonus = properties.get("meat_value")
        if not bonus:
            raise ValueError(f"{cell} does not define a {MeatPackingToken.NAME} bonus value.")

        return MeatPackingToken(MeatPackingToken.NAME, cell, railroad, bonus)