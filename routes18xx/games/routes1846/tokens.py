from routes18xx.tokens import PrivateCompanyToken

class SteamboatToken(PrivateCompanyToken):
    COORDS = ("B8", "C5", "D14", "G19", "I1")

    @staticmethod
    def place(cell, railroad, properties):
        if railroad.is_removed:
            raise ValueError(f"A removed railroad cannot place the seaport token: {railroad.name}")

        if str(cell) not in SteamboatToken.COORDS:
            raise ValueError(f"It is not legal to place the seaport token on this space ({cell}).")

        bonus = properties.get("port_value")
        if not bonus:
            raise ValueError(f"{cell} does not define a seaport bonus value.")

        return SteamboatToken("Steamboat Company", cell, railroad, bonus)

class MeatPackingToken(PrivateCompanyToken):
    COORDS = ("D6", "I1")

    @staticmethod
    def place(cell, railroad, properties):
        if railroad.is_removed:
            raise ValueError(f"A removed railroad cannot place the meat packing token: {railroad.name}")

        if str(cell) not in MeatPackingToken.COORDS:
            raise ValueError(f"It is not legal to place the meat packing token on this space ({cell}).")

        bonus = properties.get("meat_value")
        if not bonus:
            raise ValueError(f"{cell} does not define a meat packing bonus value.")

        return MeatPackingToken("Meat Packing Company", cell, railroad, bonus)